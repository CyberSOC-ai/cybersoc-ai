"""Prepare an evaluator's versioned CPU index from a verified ingestion release."""

import argparse
from pathlib import Path

import httpx

from rag.ingestion.core import IngestionError, canonical, digest, read_bytes
from .chunk import build as chunk_build
from .embed import build as embed_build, read_manifest
from .index import build as index_build, embedding_manifest
from .model import verify_model


def prepare(corpus, model, output, *, endpoint="http://127.0.0.1:6333", limit_per_source=100,
            reuse_chunks=None, reuse_vectors=None):
    corpus, model, output = Path(corpus).resolve(), Path(model).resolve(), Path(output).resolve()
    if output.exists():
        raise IngestionError("Use a new preparation output directory")
    if type(limit_per_source) is not int or limit_per_source < 1:
        raise IngestionError("Selection limit must be positive")
    if (reuse_chunks is None) != (reuse_vectors is None):
        raise IngestionError("Supply both reuse directories or neither")
    model_identity = verify_model(model)
    corpus_sha = digest(read_bytes(corpus / "manifest.json", 4*1024**2))
    if reuse_chunks is None:
        chunks, vectors = output / "chunks", output / "embeddings"
        chunk_build(corpus, corpus_sha, model / "tokenizer.json", chunks, limit_per_source=limit_per_source)
        chunk_sha = digest(read_bytes(chunks / "manifest.json", 4*1024**2))
        embed_build(chunks, chunk_sha, model, vectors)
    else:
        chunks, vectors = Path(reuse_chunks).resolve(), Path(reuse_vectors).resolve()
        chunk_sha = digest(read_bytes(chunks / "manifest.json", 4*1024**2))
    cm = read_manifest(chunks, chunk_sha)
    if cm["corpus_manifest_sha256"] != corpus_sha:
        raise IngestionError("Reused chunks do not match the selected ingestion corpus")
    vector_sha = digest(read_bytes(vectors / "manifest.json", 4*1024**2))
    em = embedding_manifest(vectors, vector_sha, chunk_sha, cm)
    if em["model"] != model_identity:
        raise IngestionError("Selected model differs from the saved embedding model")
    report = index_build(chunks, chunk_sha, vectors, vector_sha, output / "index", endpoint)
    # Hashes pin identities. Paths resolve on the host/container where preparation ran.
    ready = {"schema_version": "1.0.0", "state": "ready", "corpus_manifest_sha256": corpus_sha,
             "chunks": str(chunks), "vectors": str(vectors), "model": str(model),
             "index": str(output / "index"),
             "index_manifest_sha256": digest(read_bytes(output / "index/manifest.json", 4*1024**2)),
             "points_by_collection": report["points_by_collection"],
             "corpus_use": cm["corpus_use"], "preview_limit_per_source": cm["preview_limit_per_source"]}
    (output / "READY.json").write_bytes(canonical(ready) + b"\n")
    return ready


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("corpus", "model", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--limit-per-source", type=int, default=100)
    parser.add_argument("--endpoint", default="http://127.0.0.1:6333")
    parser.add_argument("--reuse-chunks", type=Path)
    parser.add_argument("--reuse-vectors", type=Path)
    args = parser.parse_args()
    try:
        result = prepare(args.corpus, args.model, args.output, endpoint=args.endpoint,
                         limit_per_source=args.limit_per_source,
                         reuse_chunks=args.reuse_chunks, reuse_vectors=args.reuse_vectors)
    except (IngestionError, OSError, httpx.HTTPError) as exc:
        parser.exit(1, f"Preparation failed: {exc}\n")
    print(canonical(result).decode())


if __name__ == "__main__":
    main()

"""Prepare an evaluator's versioned CPU index from a verified ingestion release."""

import argparse
from pathlib import Path

import httpx

from rag.ingestion.core import IngestionError, canonical, digest, read_bytes
from .chunk import build as chunk_build
from .embed import build as embed_build, read_manifest
from .index import build as index_build, embedding_manifest
from .model import verify_model
from .reuse import previous_release

DEFAULT_LIMIT = object()


def prepare(corpus, model, output, *, endpoint="http://127.0.0.1:6333", limit_per_source=DEFAULT_LIMIT,
            reuse_chunks=None, reuse_vectors=None, previous_ready=None, previous_ready_sha256=None):
    corpus, model, output = Path(corpus).resolve(), Path(model).resolve(), Path(output).resolve()
    if output.exists():
        raise IngestionError("Use a new preparation output directory")
    if (reuse_chunks is None) != (reuse_vectors is None):
        raise IngestionError("Supply both reuse directories or neither")
    if (previous_ready is None) != (previous_ready_sha256 is None):
        raise IngestionError("Supply both previous READY path and its SHA-256")
    if previous_ready is not None and reuse_chunks is not None:
        raise IngestionError("Choose incremental preparation or exact-release reuse")
    previous = None
    if previous_ready is not None:
        previous, receipt = previous_release(previous_ready, previous_ready_sha256)
        old_chunk_sha = receipt["identity"]["chunk_manifest_sha256"]
        old_vector_sha = receipt["identity"]["embedding_manifest_sha256"]
        old_cm = read_manifest(previous["chunks"], old_chunk_sha, check_eligibility=False)
        if (old_cm["corpus_manifest_sha256"] != previous["corpus_manifest_sha256"] or
                old_cm["preview_limit_per_source"] != previous["preview_limit_per_source"]):
            raise IngestionError("Previous READY/corpus selection mismatch")
    if limit_per_source is DEFAULT_LIMIT:
        limit_per_source = old_cm["preview_limit_per_source"] if previous is not None else 100
    if limit_per_source is not None and (type(limit_per_source) is not int or limit_per_source < 1):
        raise IngestionError("Selection limit must be positive, or None for all records")
    model_identity = verify_model(model)
    corpus_sha = digest(read_bytes(corpus / "manifest.json", 4*1024**2))
    if reuse_chunks is None:
        chunks, vectors = output / "chunks", output / "embeddings"
        chunk_previous = (previous["chunks"], old_chunk_sha) if previous is not None else None
        vector_previous = (*chunk_previous, previous["vectors"], old_vector_sha) if previous is not None else None
        chunk_build(corpus, corpus_sha, model / "tokenizer.json", chunks, limit_per_source=limit_per_source,
                    previous=chunk_previous)
        chunk_sha = digest(read_bytes(chunks / "manifest.json", 4*1024**2))
        embed_build(chunks, chunk_sha, model, vectors, previous=vector_previous)
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
    if previous is not None:
        ready["incremental"] = {"previous_ready_sha256": previous_ready_sha256,
                                "chunking": cm["incremental"], "embedding": em["incremental"],
                                "publication": "new_collections_previous_version_preserved"}
    (output / "READY.json").write_bytes(canonical(ready) + b"\n")
    return ready


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("corpus", "model", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    coverage = parser.add_mutually_exclusive_group()
    coverage.add_argument("--limit-per-source", type=int, default=DEFAULT_LIMIT)
    coverage.add_argument("--all-records", action="store_const", const=None, dest="limit_per_source")
    parser.add_argument("--endpoint", default="http://127.0.0.1:6333")
    parser.add_argument("--reuse-chunks", type=Path)
    parser.add_argument("--reuse-vectors", type=Path)
    parser.add_argument("--previous-ready", type=Path)
    parser.add_argument("--previous-ready-sha256")
    args = parser.parse_args()
    try:
        result = prepare(args.corpus, args.model, args.output, endpoint=args.endpoint,
                         limit_per_source=args.limit_per_source,
                         reuse_chunks=args.reuse_chunks, reuse_vectors=args.reuse_vectors,
                         previous_ready=args.previous_ready, previous_ready_sha256=args.previous_ready_sha256)
    except (IngestionError, OSError, httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        parser.exit(1, f"Preparation failed: {exc}\n")
    print(canonical(result).decode())


if __name__ == "__main__":
    main()

"""Stream verified chunks through BGE in bounded batches and publish vectors."""

import argparse
from importlib.metadata import distributions
import hashlib
import os
from pathlib import Path
import platform
import tempfile
import time
import uuid

from rag.ingestion.core import IngestionError, canonical, digest, parse_json, read_bytes
from .chunk import ROOT, git_state, implementation_identity
from .chunking import load_config
from .embedding import BGEEncoder, validate_vectors
from .model import verify_model


def read_manifest(directory, expected):
    directory = Path(directory)
    raw = read_bytes(directory / "manifest.json", 4 * 1024**2)
    if digest(raw) != expected:
        raise IngestionError("Chunk manifest hash mismatch")
    manifest = parse_json(raw)
    if manifest.get("artifact_kind") != "chunks_no_embeddings" or manifest.get("schema_version") != "1.0.0":
        raise IngestionError("Unsupported chunk artifact")
    config, checksum, _ = load_config(directory / "chunking-config.json")
    if checksum != manifest["config_sha256"] or config != manifest["config"]:
        raise IngestionError("Chunk configuration mismatch")
    splits = read_bytes(ROOT / "datasets/evaluation/soc-eval-v1/splits.json", 16 * 1024**2)
    policies = [parse_json(read_bytes(ROOT / f"datasets/knowledge/{name}-policy.json", 16 * 1024**2))
                for name in ("soc", "external")]
    if (digest(splits) != manifest["splits_sha256"] or
            sorted(digest(canonical(p)) for p in policies) != manifest["policy_sha256s"]):
        raise IngestionError("Chunk release is stale for current eligibility policy")
    return manifest


def chunk_records(directory, manifest):
    checksum, count, seen = hashlib.sha256(), 0, set()
    with (Path(directory) / "chunks.jsonl").open("rb") as stream:
        while line := stream.readline(8 * 1024**2 + 1):
            if len(line) > 8 * 1024**2 or not line.endswith(b"\n"):
                raise IngestionError("Invalid or oversized chunk line")
            checksum.update(line)
            chunk = parse_json(line)
            try:
                identity = chunk["chunk_id"]
                if (not identity.startswith("CHK-") or len(identity) != 68 or
                        str(uuid.UUID(hex=identity[4:36])) != chunk["point_id"] or identity in seen):
                    raise IngestionError("Invalid or duplicate chunk identity")
                if (chunk["config_sha256"] != manifest["config_sha256"] or
                        digest(chunk["content"].encode()) != chunk["content_sha256"] or
                        type(chunk["token_count"]) is not int or
                        not 2 <= chunk["token_count"] <= manifest["config"]["max_tokens"] or
                        len(chunk["embedding_text"]) > manifest["config"]["max_characters"] or
                        not chunk["embedding_text"].endswith(chunk["content"])):
                    raise IngestionError("Chunk text/configuration mismatch")
            except (KeyError, TypeError, ValueError) as exc:
                raise IngestionError("Invalid chunk record") from exc
            seen.add(identity)
            count += 1
            yield chunk
    if count != manifest["chunks"] or checksum.hexdigest() != manifest["output_sha256"]["chunks.jsonl"]:
        raise IngestionError("Chunk stream count/hash mismatch")


def build(chunks, manifest_sha256, model, output, batch_size=16):
    if type(batch_size) is not int or not 1 <= batch_size <= 16:
        raise IngestionError("Batch size must be between 1 and 16")
    output = Path(output)
    if output.exists():
        raise IngestionError("Use a new embedding output directory")
    manifest = read_manifest(chunks, manifest_sha256)
    implementation = implementation_identity()
    locks = {name: digest(read_bytes(ROOT / name, 65536)) for name in (
        "requirements.txt", "requirements-embeddings.txt", "infrastructure/docker/Dockerfile.embeddings")}
    encoder = BGEEncoder(model)
    started = time.perf_counter()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".embed-", dir=output.parent) as tmp:
        stage = Path(tmp) / "release"
        stage.mkdir()
        count, checksum = 0, hashlib.sha256()
        with (stage / "vectors.jsonl").open("xb") as target:
            pending = []

            def flush():
                nonlocal count
                values = validate_vectors(encoder.encode([c["embedding_text"] for c in pending],
                                                         [c["token_count"] for c in pending]), len(pending))
                for chunk, vector in zip(pending, values, strict=True):
                    raw = canonical({"chunk_id": chunk["chunk_id"], "point_id": chunk["point_id"],
                                     "embedding_text_sha256": digest(chunk["embedding_text"].encode()),
                                     "vector": vector}) + b"\n"
                    target.write(raw)
                    checksum.update(raw)
                    count += 1
                pending.clear()

            for chunk in chunk_records(chunks, manifest):
                pending.append(chunk)
                if len(pending) == batch_size:
                    flush()
            if pending:
                flush()
        if count == 0:
            raise IngestionError("No chunks to embed")
        if (implementation_identity() != implementation or
                read_manifest(chunks, manifest_sha256) != manifest or
                verify_model(model) != encoder.identity or
                any(digest(read_bytes(ROOT / name, 65536)) != checksum for name, checksum in locks.items())):
            raise IngestionError("Embedding inputs or implementation changed during run")
        report = {
            "schema_version": "1.0.0", "artifact_kind": "bge_embeddings",
            "chunk_manifest_sha256": manifest_sha256, "chunk_build_id": manifest["build_id"],
            "chunk_stream_sha256": manifest["output_sha256"]["chunks.jsonl"],
            "corpus_use": manifest["corpus_use"], "preview_limit_per_source": manifest["preview_limit_per_source"],
            "model": encoder.identity, "dimensions": 384, "dtype": "float32", "normalize": "l2",
            "pooling": "cls", "device": "cpu", "batch_size": batch_size, "threads": encoder.threads,
            "vectors": count, "vectors_sha256": checksum.hexdigest(),
            "inference_and_write_seconds": time.perf_counter() - started,
            "implementation_files": implementation, "dependency_files": locks, "git": git_state(),
            "environment": {"python": platform.python_version(), "system": platform.system(),
                            "packages": dict(sorted((d.metadata["Name"], d.version) for d in distributions()))},
        }
        report["build_id"] = digest(canonical(report))
        (stage / "manifest.json").write_bytes(canonical(report) + b"\n")
        if output.exists():
            raise IngestionError("Embedding output appeared during run")
        os.rename(stage, output)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunks", required=True, type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--batch-size", default=16, type=int)
    args = parser.parse_args()
    try:
        report = build(args.chunks, args.manifest_sha256, args.model, args.output, args.batch_size)
    except (IngestionError, OSError) as exc:
        parser.exit(1, f"Embedding build failed: {exc}\n")
    print(canonical(report).decode())


if __name__ == "__main__":
    main()

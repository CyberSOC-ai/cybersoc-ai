"""Verify paired chunk/vector artifacts, load separate collections, and read back."""

import argparse
from collections import Counter
import hashlib
from itertools import zip_longest
import os
from pathlib import Path
import tempfile

import httpx

from rag.ingestion.core import IngestionError, canonical, digest, parse_json, read_bytes
from .chunk import git_state, implementation_identity
from .chunking import SOURCES, TOKENIZER_REVISION, TOKENIZER_SHA256, filter_payload
from .embed import chunk_records, read_manifest
from .embedding import validate_vectors
from .model import WEIGHTS_SHA256
from .store import Qdrant, matches

SELECTION = Path(__file__).parent / "configs/selection-v1.json"
COLLECTIONS = ("knowledge", "soc_history")


def embedding_manifest(directory, expected, chunk_sha, chunks):
    raw = read_bytes(Path(directory) / "manifest.json", 4 * 1024**2)
    if digest(raw) != expected:
        raise IngestionError("Embedding manifest SHA-256 mismatch")
    value = parse_json(raw)
    if any(value.get(k) != v for k, v in {
        "schema_version": "1.0.0", "artifact_kind": "bge_embeddings", "dimensions": 384,
        "dtype": "float32", "normalize": "l2", "pooling": "cls", "device": "cpu",
        "chunk_manifest_sha256": chunk_sha, "chunk_build_id": chunks["build_id"],
        "chunk_stream_sha256": chunks["output_sha256"]["chunks.jsonl"],
        "vectors": chunks["chunks"], "corpus_use": chunks["corpus_use"],
        "preview_limit_per_source": chunks["preview_limit_per_source"],
    }.items()):
        raise IngestionError("Incompatible embedding/chunk release")
    model = value["model"]
    if (model["model_id"] != "BAAI/bge-small-en-v1.5" or model["revision"] != TOKENIZER_REVISION or
            model["sha256"]["model.safetensors"] != WEIGHTS_SHA256 or
            model["sha256"]["tokenizer.json"] != TOKENIZER_SHA256):
        raise IngestionError("Embedding model/tokenizer identity mismatch")
    return value


def vector_records(directory, manifest):
    checksum, count = hashlib.sha256(), 0
    with (Path(directory) / "vectors.jsonl").open("rb") as stream:
        while line := stream.readline(1024**2 + 1):
            if len(line) > 1024**2 or not line.endswith(b"\n"):
                raise IngestionError("Invalid or oversized vector line")
            checksum.update(line)
            value = parse_json(line)
            validate_vectors([value["vector"]], 1)
            count += 1
            yield value
    if count != manifest["vectors"] or checksum.hexdigest() != manifest["vectors_sha256"]:
        raise IngestionError("Vector stream hash/count mismatch")


def point_for(chunk, vector):
    if ((chunk["chunk_id"], chunk["point_id"]) != (vector["chunk_id"], vector["point_id"]) or
            digest(chunk["embedding_text"].encode()) != vector["embedding_text_sha256"]):
        raise IngestionError("Vector/chunk alignment mismatch")
    source = chunk["source"]
    if source not in SOURCES or chunk["collection"] != ("soc_history" if source == "soc_log" else "knowledge"):
        raise IngestionError("Source/collection boundary mismatch")
    filters = filter_payload(chunk)
    if filters != chunk["filters"]:
        raise IngestionError("Stored filter projection mismatch")
    if source == "soc_log" and (filters["split"] != "development" or type(filters["test_frozen"]) is not bool):
        raise IngestionError("Ineligible SOC payload")
    if (chunk["source"] != chunk["provenance"]["source"] or
            chunk["snapshot_ref"] != chunk["provenance"]["artifact_ref"]):
        raise IngestionError("Chunk citation provenance mismatch")
    # Explicit internal payload. This object is never a public evidence response.
    fields = ("chunk_id", "record_id", "collection", "content", "content_sha256",
              "parent_content_sha256", "parent_record_sha256", "ordinal", "start_char", "end_char",
              "token_count", "config_sha256", "quality_flags", "provenance", "metadata")
    payload = {**filters, **{key: chunk[key] for key in fields},
               "embedding_text_sha256": vector["embedding_text_sha256"]}
    return {"id": chunk["point_id"], "vector": vector["vector"], "payload": payload}


def check_collection(info, settings, indexes, metadata):
    if info is None:
        raise IngestionError("Collection missing after creation")
    config = info["config"]
    params = config["params"]
    for key, value in settings["vectors"].items():
        if params["vectors"].get(key) != value:
            raise IngestionError("Resolved vector configuration mismatch")
    if params.get("payload") != settings["payload"] or config.get("quantization_config") is not None:
        raise IngestionError("Resolved storage/quantization configuration mismatch")
    for key in ("shard_number", "replication_factor", "write_consistency_factor"):
        if params.get(key) != settings[key]:
            raise IngestionError("Resolved shard/replica configuration mismatch")
    for key, value in settings["hnsw_config"].items():
        if config["hnsw_config"].get(key) != value:
            raise IngestionError("Resolved HNSW configuration mismatch")
    if config.get("metadata") != metadata:
        raise IngestionError("Collection build metadata mismatch")
    for field, kind in indexes.items():
        if info["payload_schema"].get(field, {}).get("data_type") != kind:
            raise IngestionError("Payload index configuration mismatch")


def spool_points(chunks, vectors, cm, em, directory):
    counts, sources, hashes = Counter(), Counter(), {}
    # All input hashes/IDs are checked before the first database mutation.
    handles = {name: (directory / f"{name}.jsonl").open("xb") for name in COLLECTIONS}
    checksums = {name: hashlib.sha256() for name in COLLECTIONS}
    try:
        for chunk, vector in zip_longest(chunk_records(chunks, cm), vector_records(vectors, em)):
            if chunk is None or vector is None:
                raise IngestionError("Chunk/vector length mismatch")
            point = point_for(chunk, vector)
            name = chunk["collection"]
            raw = canonical(point) + b"\n"
            handles[name].write(raw)
            checksums[name].update(raw)
            counts[name] += 1
            sources[chunk["source"]] += 1
    finally:
        for handle in handles.values():
            handle.close()
    if sum(counts.values()) == 0:
        raise IngestionError("Cannot index an empty embedding release")
    hashes.update({key: value.hexdigest() for key, value in checksums.items()})
    return counts, sources, hashes


def batches(path, size=64):
    with path.open("rb") as stream:
        batch = []
        for line in stream:
            batch.append(parse_json(line))
            if len(batch) == size:
                yield batch
                batch = []
        if batch:
            yield batch


def verify_points(client, name, path, expected):
    if client.count(name) != expected:
        raise IngestionError("Stored point count mismatch")
    for batch in batches(path):
        actual = {p["id"]: p for p in client.points(name, [p["id"] for p in batch])}
        if len(actual) != len(batch):
            raise IngestionError("Missing points on readback")
        for point in batch:
            saved = actual.get(point["id"])
            if saved is None or saved["payload"] != point["payload"]:
                raise IngestionError("Stored payload differs from verified source")
            validate_vectors([saved["vector"]], 1)
            if max(abs(a - b) for a, b in zip(saved["vector"], point["vector"], strict=True)) > 1e-5:
                raise IngestionError("Stored vector differs from verified input")


def build(chunks, chunk_sha, vectors, embedding_sha, output, endpoint="http://127.0.0.1:6333"):
    output = Path(output)
    if output.exists():
        raise IngestionError("Use a new index receipt directory")
    cm = read_manifest(chunks, chunk_sha)
    em = embedding_manifest(vectors, embedding_sha, chunk_sha, cm)
    selection_bytes = read_bytes(SELECTION, 65536)
    store = parse_json(selection_bytes)["vector_store"]
    implementation = implementation_identity()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".index-", dir=output.parent) as tmp:
        stage = Path(tmp) / "release"
        stage.mkdir()
        counts, sources, spool_hashes = spool_points(chunks, vectors, cm, em, stage)
        identity = {"chunk_manifest_sha256": chunk_sha, "embedding_manifest_sha256": embedding_sha,
                    "selection_sha256": digest(selection_bytes), "point_spool_sha256": spool_hashes,
                    "implementation_files": implementation}
        build_id = digest(canonical(identity))
        names = {key: f"{key}_{build_id}" for key in COLLECTIONS}
        metadata = {"index_build_id": build_id, "state": "building",
                    "embedding_manifest_sha256": embedding_sha, "corpus_use": cm["corpus_use"]}
        client = Qdrant(endpoint)
        created = []
        try:
            server = client.server()
            if any(client.info(name) is not None for name in names.values()):
                raise IngestionError("Collection already exists; refusing to overwrite or resume")
            for key, name in names.items():
                client.create(name, store["create_collection_request"], metadata)
                created.append(name)
                for field, kind in store["planned_payload_indexes"].items():
                    client.field_index(name, field, kind)
                check_collection(client.info(name), store["create_collection_request"],
                                 store["planned_payload_indexes"], metadata)
                for batch in batches(stage / f"{key}.jsonl"):
                    client.upsert(name, batch)
                verify_points(client, name, stage / f"{key}.jsonl", counts[key])
                forbidden = "soc_log" if key == "knowledge" else "cve"
                if client.count(name, matches("source", forbidden)) != 0:
                    raise IngestionError("Collection boundary verification failed")
            if (implementation_identity() != implementation or read_bytes(SELECTION, 65536) != selection_bytes or
                    read_manifest(chunks, chunk_sha) != cm or
                    embedding_manifest(vectors, embedding_sha, chunk_sha, cm) != em):
                raise IngestionError("Index inputs changed during loading")
            ready_metadata = {**metadata, "state": "ready"}
            resolved = {}
            for key, name in names.items():
                client.ready(name, metadata)
                info = client.info(name)
                check_collection(info, store["create_collection_request"], store["planned_payload_indexes"], ready_metadata)
                resolved[key] = {"config": info["config"], "payload_schema": info["payload_schema"]}
            report = {"schema_version": "1.0.0", "artifact_kind": "qdrant_index_receipt", "state": "ready",
                      "build_id": build_id, "identity": identity, "collections": names,
                      "points_by_collection": {k: counts[k] for k in COLLECTIONS}, "points_by_source": dict(sources),
                      "server": server, "endpoint": endpoint, "image": store["image"],
                      "resolved": resolved, "corpus_use": cm["corpus_use"],
                      "preview_limit_per_source": cm["preview_limit_per_source"], "git": git_state()}
            (stage / "manifest.json").write_bytes(canonical(report) + b"\n")
            if output.exists():
                raise IngestionError("Index receipt output appeared during loading")
            os.rename(stage, output)
            return report
        except Exception as exc:
            if created:
                raise IngestionError("Index build not published; new collections retained for inspection: " +
                                     ", ".join(created)) from exc
            raise
        finally:
            client.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunks", required=True, type=Path)
    parser.add_argument("--chunk-manifest-sha256", required=True)
    parser.add_argument("--vectors", required=True, type=Path)
    parser.add_argument("--embedding-manifest-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--endpoint", default="http://127.0.0.1:6333")
    args = parser.parse_args()
    try:
        report = build(args.chunks, args.chunk_manifest_sha256, args.vectors, args.embedding_manifest_sha256,
                       args.output, args.endpoint)
    except (IngestionError, OSError, httpx.HTTPError) as exc:
        parser.exit(1, f"Index build failed: {exc}\n")
    print(canonical(report).decode())


if __name__ == "__main__":
    main()

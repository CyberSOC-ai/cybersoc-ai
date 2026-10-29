"""Offline index integrity/lifecycle tests; synthetic vectors are plumbing only."""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import httpx

from rag.ingestion.core import IngestionError, canonical, digest
from rag.vector.chunk import ROOT
from rag.vector.chunking import DEFAULT_CONFIG, TOKENIZER_REVISION, TOKENIZER_SHA256, filter_payload
from rag.vector.index import build, point_for, verify_points
from rag.vector.model import WEIGHTS_SHA256
from rag.vector.store import Qdrant, matches
from test_chunking import cve, soc


class FakeQdrant:
    def __init__(self):
        self.collections = {}
        self.data = {}
        self.writes = 0

    def close(self):
        pass

    def server(self):
        return {"version": "1.20.0", "commit": "synthetic"}

    def info(self, name):
        return deepcopy(self.collections.get(name))

    def create(self, name, config, metadata):
        self.collections[name] = {"config": {"params": {k: config[k] for k in
            ("vectors", "payload", "shard_number", "replication_factor", "write_consistency_factor")},
            "hnsw_config": config["hnsw_config"], "quantization_config": None,
            "metadata": metadata}, "payload_schema": {}}
        self.data[name] = {}

    def field_index(self, name, field, kind):
        self.collections[name]["payload_schema"][field] = {"data_type": kind}

    def upsert(self, name, points):
        self.writes += 1
        self.data[name].update({p["id"]: deepcopy(p) for p in points})

    def count(self, name, filters=None):
        values = self.data[name].values()
        if filters is None:
            return len(self.data[name])
        return sum(all(p["payload"].get(c["key"]) == c["match"]["value"] for c in filters["must"]) for p in values)

    def points(self, name, ids):
        return [deepcopy(self.data[name][identity]) for identity in ids if identity in self.data[name]]

    def ready(self, name, metadata):
        self.collections[name]["config"]["metadata"] = {**metadata, "state": "ready"}


class IndexTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.server = FakeQdrant()

    def inputs(self):
        config_raw = DEFAULT_CONFIG.read_bytes()
        config = json.loads(config_raw)
        chunks, vectors = [], []
        for index, record in enumerate([cve(), soc()]):
            digit = "a" if index == 0 else "b"
            chunk = dict(record, chunk_id="CHK-" + digit*64,
                         point_id=f"{digit*8}-{digit*4}-{digit*4}-{digit*4}-{digit*12}",
                         ordinal=0, start_char=0, end_char=len(record["content"]),
                         parent_content_sha256=record["content_sha256"], parent_record_sha256=digest(canonical(record)),
                         embedding_text=record["content"], token_count=3, config_sha256=digest(config_raw),
                         quality_flags=[], filters=filter_payload(record))
            chunks.append(chunk)
            vectors.append({"chunk_id": chunk["chunk_id"], "point_id": chunk["point_id"],
                            "embedding_text_sha256": digest(chunk["embedding_text"].encode()),
                            "vector": [1.0] + [0.0]*383})
        chunk_path, vector_path = self.root / "chunks", self.root / "vectors"
        chunk_path.mkdir()
        vector_path.mkdir()
        raw = b"".join(canonical(c) + b"\n" for c in chunks)
        (chunk_path / "chunks.jsonl").write_bytes(raw)
        (chunk_path / "chunking-config.json").write_bytes(config_raw)
        policies = [json.loads((ROOT / f"datasets/knowledge/{k}-policy.json").read_bytes()) for k in ("soc", "external")]
        cm = {"schema_version": "1.0.0", "artifact_kind": "chunks_no_embeddings", "build_id": "fixture",
              "config": config, "config_sha256": digest(config_raw), "chunks": 2,
              "output_sha256": {"chunks.jsonl": digest(raw)}, "corpus_use": "development_only",
              "preview_limit_per_source": 1,
              "splits_sha256": digest((ROOT / "datasets/evaluation/soc-eval-v1/splits.json").read_bytes()),
              "policy_sha256s": sorted(digest(canonical(p)) for p in policies)}
        (chunk_path / "manifest.json").write_bytes(canonical(cm))
        raw = b"".join(canonical(v) + b"\n" for v in vectors)
        (vector_path / "vectors.jsonl").write_bytes(raw)
        em = {"schema_version": "1.0.0", "artifact_kind": "bge_embeddings", "dimensions": 384,
              "dtype": "float32", "normalize": "l2", "pooling": "cls", "device": "cpu",
              "chunk_manifest_sha256": digest(canonical(cm)), "chunk_build_id": "fixture",
              "chunk_stream_sha256": cm["output_sha256"]["chunks.jsonl"], "vectors": 2,
              "vectors_sha256": digest(raw), "corpus_use": "development_only", "preview_limit_per_source": 1,
              "model": {"model_id": "BAAI/bge-small-en-v1.5", "revision": TOKENIZER_REVISION,
                        "sha256": {"model.safetensors": WEIGHTS_SHA256, "tokenizer.json": TOKENIZER_SHA256}}}
        (vector_path / "manifest.json").write_bytes(canonical(em))
        return dict(chunks=chunk_path, chunk_sha=digest(canonical(cm)), vectors=vector_path,
                    embedding_sha=digest(canonical(em)), output=self.root / "receipt"), chunks, vectors

    def test_load_preserves_payload_and_separates_collections(self):
        args, chunks, _ = self.inputs()
        with patch("rag.vector.index.Qdrant", return_value=self.server):
            report = build(**args)
        self.assertEqual(report["points_by_collection"], {"knowledge": 1, "soc_history": 1})
        for chunk in chunks:
            name = report["collections"][chunk["collection"]]
            point = self.server.data[name][chunk["point_id"]]
            self.assertEqual(point["payload"]["metadata"], chunk["metadata"])
            self.assertEqual(point["payload"]["provenance"], chunk["provenance"])
            self.assertNotIn("embedding_text", point["payload"])
            self.assertEqual(self.server.collections[name]["config"]["metadata"]["state"], "ready")
        self.assertTrue((args["output"] / "manifest.json").exists())

    def test_existing_collections_cannot_be_overwritten(self):
        args, _, _ = self.inputs()
        with patch("rag.vector.index.Qdrant", return_value=self.server):
            build(**args)
            previous = self.server.writes
            args["output"] = self.root / "second"
            with self.assertRaisesRegex(IngestionError, "already exists"):
                build(**args)
            self.assertEqual(self.server.writes, previous)
            self.assertFalse(args["output"].exists())

    def test_corrupt_tail_is_rejected_before_connecting(self):
        args, _, _ = self.inputs()
        path = args["vectors"] / "vectors.jsonl"
        path.write_bytes(path.read_bytes() + b"invalid\n")
        with patch("rag.vector.index.Qdrant") as client, self.assertRaises(IngestionError):
            build(**args)
        client.assert_not_called()
        self.assertFalse(args["output"].exists())

    def test_incompatible_manifest_rejected_before_connecting(self):
        args, _, _ = self.inputs()
        with patch("rag.vector.index.Qdrant") as client, self.assertRaises(IngestionError):
            build(**(args | {"embedding_sha": "0"*64}))
        client.assert_not_called()

    def test_alignment_filters_and_boundaries_rejected(self):
        _, chunks, vectors = self.inputs()
        for field, value in [("point_id", vectors[1]["point_id"]), ("embedding_text_sha256", "0"*64)]:
            with self.assertRaises(IngestionError):
                point_for(chunks[0], vectors[0] | {field: value})
        for changes in ({"collection": "soc_history"}, {"filters": {}}):
            with self.assertRaises(IngestionError):
                point_for(chunks[0] | changes, vectors[0])

    def test_failure_does_not_publish_receipt_or_delete_collections(self):
        args, _, _ = self.inputs()
        with patch("rag.vector.index.Qdrant", return_value=self.server), \
                patch.object(self.server, "upsert", side_effect=IngestionError("injected")):
            with self.assertRaisesRegex(IngestionError, "retained"):
                build(**args)
        self.assertFalse(args["output"].exists())
        self.assertTrue(self.server.collections)
        self.assertTrue(all(c["config"]["metadata"]["state"] == "building" for c in self.server.collections.values()))

    def test_readback_detects_payload_and_vector_changes(self):
        args, _, _ = self.inputs()
        with patch("rag.vector.index.Qdrant", return_value=self.server):
            report = build(**args)
        name = report["collections"]["knowledge"]
        point = next(iter(self.server.data[name].values()))
        point["payload"]["content"] = "changed"
        with self.assertRaisesRegex(IngestionError, "payload"):
            verify_points(self.server, name, args["output"] / "knowledge.jsonl", 1)

    def test_local_endpoint_validation(self):
        for url in ("http://example.org", "http://127.0.0.1.evil", "http://user:pass@localhost",
                    "https://localhost", "http://localhost/path", "http://localhost?x=1"):
            with self.assertRaises(IngestionError):
                Qdrant(url)
        with self.assertRaises(IngestionError):
            Qdrant.path("../wrong")

    def test_http_envelopes_versions_and_filter_encoding(self):
        calls = []
        def handler(request):
            calls.append(request)
            if request.url.path == "/":
                return httpx.Response(200, json={"version": "1.20.0"})
            if request.method == "GET":
                return httpx.Response(404, json={"status": "error"})
            return httpx.Response(200, json={"status": "ok", "result": {"count": 0}})
        client = Qdrant(transport=httpx.MockTransport(handler))
        self.addCleanup(client.close)
        name = "knowledge_" + "a"*64
        self.assertEqual(client.server()["version"], "1.20.0")
        self.assertIsNone(client.info(name))
        self.assertEqual(client.count(name, matches("test_frozen", False)), 0)
        self.assertIs(json.loads(calls[-1].content)["filter"]["must"][0]["match"]["value"], False)
        with patch.object(client.client, "get", return_value=httpx.Response(200, json={"version": "other"})):
            with self.assertRaises(IngestionError):
                client.server()

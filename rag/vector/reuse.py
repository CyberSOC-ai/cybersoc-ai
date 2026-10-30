"""Disk-backed caches of hash-pinned historical releases, never live query data."""

from itertools import zip_longest
from pathlib import Path
import sqlite3

from rag.ingestion.core import IngestionError, canonical, digest, parse_json, read_bytes


class ReuseCache:
    """Keep corpus-sized text/vectors on disk instead of in a Python dictionary."""

    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE chunks (record TEXT, ordinal INTEGER, data BLOB, seen INTEGER DEFAULT 0, "
                        "PRIMARY KEY(record, ordinal))")
        self.db.execute("CREATE TABLE vectors (text_sha TEXT PRIMARY KEY, tokens INTEGER, data BLOB)")

    def close(self):
        self.db.close()

    def load_chunks(self, directory, expected, config_sha256):
        from .embed import chunk_records, read_manifest
        manifest = read_manifest(directory, expected, check_eligibility=False)
        if manifest["config_sha256"] != config_sha256:
            raise IngestionError("Chunking configuration changed; use a fresh build")
        try:
            for chunk in chunk_records(directory, manifest):
                self.db.execute("INSERT INTO chunks(record, ordinal, data) VALUES (?, ?, ?)",
                                (chunk["record_id"], chunk["ordinal"], canonical(chunk)))
        except sqlite3.IntegrityError as exc:
            raise IngestionError("Duplicate cached record/ordinal") from exc
        self.db.commit()
        return manifest

    def chunks_for(self, record, prefix):
        self.db.execute("UPDATE chunks SET seen=1 WHERE record=?", (record["record_id"],))
        chunks = [parse_json(row[0]) for row in self.db.execute(
            "SELECT data FROM chunks WHERE record=? ORDER BY ordinal", (record["record_id"],))]
        if not chunks:
            return None
        if any(c["ordinal"] != i for i, c in enumerate(chunks)):
            raise IngestionError("Cached chunk ordinals are not contiguous")
        # A new acquisition may change provenance/metadata without changing text.
        # Rebind those fields and IDs, but reuse exact source spans/token counts.
        if all(c["parent_content_sha256"] == record["content_sha256"] and
               c["content"] == record["content"][c["start_char"]:c["end_char"]] and
               c["embedding_text"] == prefix + c["content"] for c in chunks):
            return chunks
        return None

    def removed_records(self):
        return self.db.execute("SELECT COUNT(DISTINCT record) FROM chunks WHERE seen=0").fetchone()[0]

    def load_vectors(self, chunks, chunk_sha, vectors, vector_sha, model, locks):
        from .embed import chunk_records, read_manifest
        from .index import embedding_manifest, point_for, vector_records
        cm = read_manifest(chunks, chunk_sha, check_eligibility=False)
        em = embedding_manifest(vectors, vector_sha, chunk_sha, cm)
        if em["model"] != model or em.get("dependency_files") != locks:
            raise IngestionError("Embedding model/runtime changed; use a fresh build")
        for chunk, vector in zip_longest(chunk_records(chunks, cm), vector_records(vectors, em)):
            if chunk is None or vector is None:
                raise IngestionError("Cached chunk/vector length mismatch")
            point_for(chunk, vector)  # Check IDs, text hashes and source boundary.
            self.put_vector(vector["embedding_text_sha256"], chunk["token_count"], vector["vector"])
        self.db.commit()
        return em

    def get_vector(self, text_sha, tokens):
        row = self.db.execute("SELECT tokens, data FROM vectors WHERE text_sha=?", (text_sha,)).fetchone()
        if row is None:
            return None
        if row[0] != tokens:
            raise IngestionError("Cached text/token count mismatch")
        return parse_json(row[1])

    def put_vector(self, text_sha, tokens, vector):
        previous = self.get_vector(text_sha, tokens)
        if previous is not None:
            if previous != vector:
                raise IngestionError("Conflicting cached vectors for identical embedding text")
            return
        self.db.execute("INSERT INTO vectors VALUES (?, ?, ?)", (text_sha, tokens, canonical(vector)))


def previous_release(path, expected):
    """Resolve a pinned READY -> receipt -> chunk/vector manifest chain offline."""
    raw = read_bytes(path, 4 * 1024**2)
    if digest(raw) != expected:
        raise IngestionError("Previous READY SHA-256 mismatch")
    ready = parse_json(raw)
    if ready.get("schema_version") != "1.0.0" or ready.get("state") != "ready":
        raise IngestionError("Previous preparation is not ready")
    receipt_raw = read_bytes(Path(ready["index"]) / "manifest.json", 4 * 1024**2)
    if digest(receipt_raw) != ready["index_manifest_sha256"]:
        raise IngestionError("Previous index receipt SHA-256 mismatch")
    receipt = parse_json(receipt_raw)
    if (receipt.get("schema_version") != "1.0.0" or
            receipt.get("artifact_kind") != "qdrant_index_receipt" or receipt.get("state") != "ready" or
            digest(canonical(receipt["identity"])) != receipt["build_id"] or
            receipt["collections"] != {k: f"{k}_{receipt['build_id']}" for k in ("knowledge", "soc_history")}):
        raise IngestionError("Previous index receipt is invalid")
    return ready, receipt

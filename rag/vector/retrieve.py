"""Query a verified local index and project hits into the closed v1 contract."""

import argparse
import hashlib
import math
from pathlib import Path

import httpx
from jsonschema import ValidationError

from backend.validation import validate
from rag.ingestion.core import IngestionError, canonical, digest, parse_json, read_bytes
from .embedding import BGEEncoder, validate_vectors
from .embed import read_manifest
from .index import COLLECTIONS, SELECTION, batches, check_collection, embedding_manifest
from .store import Qdrant


class RetrievalError(IngestionError):
    def __init__(self, code, message, retryable=False):
        super().__init__(message)
        self.code, self.retryable = code, retryable


def response(request, evidence=None, error=None):
    value = {"schema_version": "1.0.0", "request_id": request["request_id"],
             "trace_id": request["trace_id"], "status": "error" if error else "ok",
             "evidence": [] if evidence is None else evidence}
    if error:
        value["error"] = {"code": error.code, "message": str(error), "retryable": error.retryable}
    validate("retrieval-response", value)
    return value


def dependency_error(exc):
    if isinstance(exc, httpx.TimeoutException):
        return RetrievalError("timeout", "Local vector-store request timed out", True)
    return RetrievalError("dependency_unavailable", "Local vector store is unavailable", True)


def query_filter(filters, collection, frozen):
    must = []
    for public, field in (("sources", "source"), ("snapshot_refs", "snapshot_ref")):
        if filters.get(public):
            must.append({"key": field, "match": {"any": filters[public]}})
    if collection == "soc_history":
        must.extend([{"key": "split", "match": {"value": "development"}},
                     {"key": "test_frozen", "match": {"value": frozen}}])
    return {"must": must}


def evidence_for(hit, collection, proofs, filters, query):
    """Validate the returned point against verified local readback fingerprints."""
    try:
        payload, vector, score = hit["payload"], hit["vector"], hit["score"]
        proof = proofs.get(hit["id"])
        if proof != (digest(canonical(payload)), digest(canonical(vector))):
            raise IngestionError("Unrecognized or changed point")
        validate_vectors([vector], 1)
        if type(score) not in (int, float) or not math.isfinite(score):
            raise IngestionError("Invalid cosine score")
        expected = sum(a*b for a, b in zip(query, vector, strict=True)) / math.sqrt(
            sum(a*a for a in query) * sum(b*b for b in vector))
        if abs(score - expected) > 1e-5:
            raise IngestionError("Score differs from vector cosine")
        if payload["collection"] != collection:
            raise IngestionError("Wrong collection")
        if (filters.get("sources") and payload["source"] not in filters["sources"] or
                filters.get("snapshot_refs") and payload["snapshot_ref"] not in filters["snapshot_refs"]):
            raise IngestionError("Returned point violates requested filters")
        value = {"evidence_id": payload["chunk_id"], "source": payload["source"],
                 "source_record_id": payload["source_record_id"], "snapshot_ref": payload["snapshot_ref"],
                 "content": payload["content"], "score": score, "score_kind": "cosine",
                 "retrieval_method": "vector"}
        return value
    except (IngestionError, KeyError, TypeError, ValueError) as exc:
        raise RetrievalError("invalid_output", "Retrieved point failed integrity or filter validation") from exc


class Retriever:
    def __init__(self, index, index_sha256, chunks, vectors, model, endpoint="http://127.0.0.1:6333", *, exact=False):
        self.index, self.chunks, self.vectors = Path(index), Path(chunks), Path(vectors)
        raw = read_bytes(self.index / "manifest.json", 4 * 1024**2)
        if digest(raw) != index_sha256:
            raise IngestionError("Index receipt SHA-256 mismatch")
        self.receipt = parse_json(raw)
        r = self.receipt
        if (r.get("schema_version") != "1.0.0" or r.get("artifact_kind") != "qdrant_index_receipt" or
                r.get("state") != "ready" or digest(canonical(r["identity"])) != r["build_id"] or
                r["collections"] != {k: f"{k}_{r['build_id']}" for k in COLLECTIONS}):
            raise IngestionError("Invalid or incomplete index receipt")
        self.selection_bytes = read_bytes(SELECTION, 65536)
        if digest(self.selection_bytes) != r["identity"]["selection_sha256"]:
            raise IngestionError("Index selection settings differ from current settings")
        self.store = parse_json(self.selection_bytes)["vector_store"]
        self.cm = read_manifest(chunks, r["identity"]["chunk_manifest_sha256"])
        self.em = embedding_manifest(vectors, r["identity"]["embedding_manifest_sha256"],
                                     r["identity"]["chunk_manifest_sha256"], self.cm)
        if r["corpus_use"] != self.cm["corpus_use"] or r["preview_limit_per_source"] != self.cm["preview_limit_per_source"]:
            raise IngestionError("Index usage restriction mismatch")
        # Verify local spool identities before connecting, then verify remote data.
        for key in COLLECTIONS:
            checksum = hashlib.sha256()
            with (self.index / f"{key}.jsonl").open("rb") as stream:
                while block := stream.read(1024**2):
                    checksum.update(block)
            if checksum.hexdigest() != r["identity"]["point_spool_sha256"][key]:
                raise IngestionError("Index point spool SHA-256 mismatch")
        self.client = Qdrant(endpoint)
        self.proofs = {key: {} for key in COLLECTIONS}
        try:
            self.check_state()
            for key, name in r["collections"].items():
                for batch in batches(self.index / f"{key}.jsonl"):
                    actual = {p["id"]: p for p in self.client.points(name, [p["id"] for p in batch])}
                    if len(actual) != len(batch):
                        raise IngestionError("Missing stored points")
                    for expected in batch:
                        saved = actual.get(expected["id"])
                        if saved is None or saved["payload"] != expected["payload"]:
                            raise IngestionError("Stored payload mismatch")
                        validate_vectors([saved["vector"]], 1)
                        if max(abs(a-b) for a, b in zip(saved["vector"], expected["vector"], strict=True)) > 1e-5:
                            raise IngestionError("Stored vector mismatch")
                        self.proofs[key][expected["id"]] = (digest(canonical(saved["payload"])),
                                                            digest(canonical(saved["vector"])))
                if len(self.proofs[key]) != r["points_by_collection"][key]:
                    raise IngestionError("Duplicate or missing point spool IDs")
            self.encoder = BGEEncoder(model)
            if self.encoder.identity != self.em["model"]:
                raise IngestionError("Query model differs from indexed embedding model")
        except Exception:
            self.client.close()
            raise
        self.params = {**self.store["initial_search_params"], "exact": exact}
        # read_manifest above pins these exact split bytes to this corpus.
        from .chunk import ROOT
        self.frozen = parse_json(read_bytes(ROOT / "datasets/evaluation/soc-eval-v1/splits.json"))["test_frozen"]

    def close(self):
        self.client.close()

    def check_state(self):
        r = self.receipt
        if (read_manifest(self.chunks, r["identity"]["chunk_manifest_sha256"]) != self.cm or
                read_bytes(SELECTION, 65536) != self.selection_bytes):
            raise IngestionError("Index eligibility or settings changed; rebuild required")
        self.client.server()
        metadata = {"index_build_id": r["build_id"], "state": "ready", "corpus_use": r["corpus_use"],
                    "embedding_manifest_sha256": r["identity"]["embedding_manifest_sha256"]}
        for key, name in r["collections"].items():
            check_collection(self.client.info(name), self.store["create_collection_request"],
                             self.store["planned_payload_indexes"], metadata)
            if self.client.count(name) != r["points_by_collection"][key]:
                raise IngestionError("Live index point count changed")

    def retrieve(self, request):
        validate("retrieval-request", request)  # Invalid envelopes are caller errors.
        if request["mode"] != "vector":
            return response(request, error=RetrievalError("validation_error", "This retriever supports vector mode only"))
        try:
            self.check_state()
            try:
                query = self.encoder.query(request["query"])
                validate_vectors([query], 1)
            except IngestionError as exc:
                return response(request, error=RetrievalError("validation_error", str(exc)))
            filters, hits = request["filters"], []
            for key, name in self.receipt["collections"].items():
                result = self.client.request("POST", self.client.path(name) + "/points/query", {
                    "query": query, "filter": query_filter(filters, key, self.frozen),
                    "limit": request["top_k"], "with_payload": True, "with_vector": True, "params": self.params})
                candidates = result["points"]
                if not isinstance(candidates, list) or len(candidates) > request["top_k"]:
                    raise RetrievalError("invalid_output", "Unexpected number of retrieved candidates")
                seen = set()
                for hit in candidates:
                    if hit["id"] in seen:
                        raise RetrievalError("invalid_output", "Duplicate retrieved point")
                    seen.add(hit["id"])
                    hits.append(evidence_for(hit, key, self.proofs[key], filters, query))
            # Same encoder/metric across both collections: merge raw cosine scores.
            hits.sort(key=lambda value: (-value["score"], value["evidence_id"]))
            if len({h["evidence_id"] for h in hits}) != len(hits):
                raise RetrievalError("invalid_output", "Duplicate evidence identity across collections")
            self.check_state()
            return response(request, evidence=hits[:request["top_k"]])
        except RetrievalError as exc:
            return response(request, error=exc)
        except httpx.HTTPError as exc:
            return response(request, error=dependency_error(exc))
        except IngestionError:
            return response(request, error=RetrievalError("conflict", "Index state or eligibility changed; reload or rebuild required"))
        except (KeyError, TypeError, ValueError, ValidationError):
            return response(request, error=RetrievalError("invalid_output", "Retrieval returned invalid evidence"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("index", "chunks", "vectors", "model", "request", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--index-manifest-sha256", required=True)
    parser.add_argument("--endpoint", default="http://127.0.0.1:6333")
    parser.add_argument("--exact", action="store_true")
    args = parser.parse_args()
    try:
        request = parse_json(read_bytes(args.request, 65536))
        validate("retrieval-request", request)
        if args.output.exists():
            raise IngestionError("Use a new response output file")
    except (IngestionError, OSError, ValidationError):
        parser.exit(1, "Invalid request envelope or output path\n")
    reader = None
    try:
        reader = Retriever(args.index, args.index_manifest_sha256, args.chunks, args.vectors,
                           args.model, args.endpoint, exact=args.exact)
        result = reader.retrieve(request)
    except httpx.HTTPError as exc:
        result = response(request, error=dependency_error(exc))
    except (IngestionError, OSError, KeyError, TypeError, ValueError):
        result = response(request, error=RetrievalError("conflict", "Index or model verification failed; inspect the local build"))
    finally:
        if reader is not None:
            reader.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents accidental replacement of an earlier response.
    with args.output.open("xb") as target:
        target.write(canonical(result) + b"\n")
    print(canonical({"status": result["status"], "evidence": len(result["evidence"])}).decode())


if __name__ == "__main__":
    main()

"""Deterministic source slices with a verified, offline WordPiece tokenizer."""

from copy import deepcopy
from importlib.metadata import version
from pathlib import Path
import uuid

from tokenizers import Tokenizer

from rag.ingestion.core import IngestionError, canonical, digest, parse_json, read_bytes, validate

DEFAULT_CONFIG = Path(__file__).parent / "configs/chunking-v1.json"
TOKENIZER_SHA256 = "d241a60d5e8f04cc1b2b3e9ef7a4921b27bf526d9f6050ab90f9267a1f9e5c66"
TOKENIZER_REVISION = "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"
SOURCES = {"mitre_attack", "cve", "cwe", "detection_rule", "playbook", "soc_log"}


def load_config(path=DEFAULT_CONFIG):
    raw = read_bytes(path, 65536)
    config = parse_json(raw)
    expected = parse_json(read_bytes(DEFAULT_CONFIG, 65536))
    if not isinstance(config, dict) or set(config) != set(expected):
        raise IngestionError("Unknown or missing chunking configuration field")
    for key in ("version", "projection", "algorithm", "tokenizer"):
        if config[key] != expected[key]:
            raise IngestionError(f"Unsupported chunking {key}")
    if (config["tokenizer"]["revision"] != TOKENIZER_REVISION or
            config["tokenizer"]["sha256"] != "d241a60d5e8f04cc1b2b3e9ef7a4921b27bf526d9f6050ab90f9267a1f9e5c66"):
        raise IngestionError("Unsupported tokenizer identity")
    for key in ("max_tokens", "overlap_tokens", "max_characters", "short_text_characters"):
        if type(config[key]) is not int:
            raise IngestionError("Chunking limits must be integers")
    if not 4 <= config["max_tokens"] <= 512:
        raise IngestionError("Chunk token budget must fit BGE")
    if not 0 <= config["overlap_tokens"] < config["max_tokens"] - 2:
        raise IngestionError("Invalid chunk overlap")
    if not 1 <= config["max_characters"] <= 16000 or config["short_text_characters"] < 0:
        raise IngestionError("Invalid character limit")
    if config["placeholder_texts"] != expected["placeholder_texts"]:
        raise IngestionError("Changing the quality policy requires a new implementation version")
    return config, digest(raw), raw


class Chunker:
    def __init__(self, tokenizer_path, config_path=DEFAULT_CONFIG):
        self.config, self.config_sha256, self.config_bytes = load_config(config_path)
        raw = read_bytes(tokenizer_path, 2 * 1024**2)
        if digest(raw) != TOKENIZER_SHA256:
            raise IngestionError("Tokenizer SHA-256 mismatch")
        if version("tokenizers") != self.config["tokenizer"]["library_version"]:
            raise IngestionError("Tokenizer library version mismatch")
        # Loading a local JSON tokenizer does not fetch/execute repository code.
        self.tokenizer = Tokenizer.from_str(raw.decode("utf-8"))
        self.tokenizer.no_truncation()
        self.tokenizer.no_padding()
        if self.count("") != 2:
            raise IngestionError("Expected BGE CLS/SEP special tokens")

    def count(self, text):
        return len(self.tokenizer.encode(text, add_special_tokens=True).ids)

    def spans(self, text, prefix):
        """Yield original character slices; re-encode every candidate, never decode IDs.

        Subword boundaries and Unicode normalization can change tokenization when
        sliced. Counts therefore come from the exact final embedding text. Overlap
        targets up to the configured count in the current window's tokenization.
        """
        budget = self.config["max_tokens"]
        available = budget - self.count(prefix)
        if available <= self.config["overlap_tokens"]:
            raise IngestionError("Reference header leaves insufficient passage budget")
        character_budget = self.config["max_characters"] - len(prefix)
        if character_budget < 1:
            raise IngestionError("Reference header exceeds evidence character budget")
        start = 0
        while start < len(text):
            encoding = self.tokenizer.encode(text[start:], add_special_tokens=False)
            offsets = encoding.offsets
            if not offsets:
                # Whitespace/control tail is included in the last slice when possible.
                end = min(len(text), start + character_budget)
            elif len(offsets) <= available:
                end = min(len(text), start + character_budget)
            else:
                end = min(start + offsets[available - 1][1], start + character_budget)
            # Exact re-tokenization, including reference prefix and special tokens.
            while end > start and self.count(prefix + text[start:end]) > budget:
                candidates = [start + a for a, _ in offsets if start < start + a < end]
                end = candidates[-1] if candidates else end - 1
            if end <= start:
                raise IngestionError("Cannot fit a source character in passage budget")
            yield start, end, self.count(prefix + text[start:end])
            if end == len(text):
                break
            window = self.tokenizer.encode(text[start:end], add_special_tokens=False).offsets
            overlap = self.config["overlap_tokens"]
            next_start = end
            if overlap and len(window) > overlap:
                next_start = start + window[-overlap][0]
            # Pathological offsets (e.g. normalized Unicode) must still progress.
            start = next_start if start < next_start <= end else end

    def chunks(self, record, *, previous=None):
        """Return chunks plus quality decision; eligibility is enforced by the builder."""
        validate("record", record)
        source = record["source"]
        expected_collection = "soc_history" if source == "soc_log" else "knowledge"
        if source not in SOURCES or record["collection"] != expected_collection:
            raise IngestionError("Unsupported source or collection for vector chunking")
        if record["snapshot_ref"] != record["provenance"]["artifact_ref"]:
            raise IngestionError("Record snapshot/provenance mismatch")
        if source != record["provenance"]["source"]:
            raise IngestionError("Record source/provenance mismatch")
        if record["record_id"] != "DOC-" + digest(canonical([source, record["source_record_id"]])):
            raise IngestionError("Record identity mismatch")
        body = record["content"]
        if digest(body.encode("utf-8")) != record["content_sha256"]:
            raise IngestionError("Record text hash mismatch")
        clean = body.strip().strip("# ").casefold()
        reason = ("empty_or_nonlexical_text" if not any(c.isalnum() for c in body) else
                  "placeholder_text" if clean in self.config["placeholder_texts"] else None)
        if reason:
            return [], {"excluded": reason, "flags": []}
        flags = ["short_primary_text"] if len(body.strip()) <= self.config["short_text_characters"] else []
        prefix = reference_prefix(record)
        output = []
        spans = ([(c["start_char"], c["end_char"], c["token_count"]) for c in previous]
                 if previous else self.spans(body, prefix))
        record_sha = digest(canonical(record))
        for ordinal, (start, end, count) in enumerate(spans):
            content = body[start:end]
            # Full record digest binds metadata and supplemental provenance too.
            identity = digest(canonical(["chunk-v1", record_sha,
                                         self.config_sha256, ordinal, start, end, prefix, content]))
            item = {
                "schema_version": "1.0.0", "chunk_id": "CHK-" + identity,
                "point_id": str(uuid.UUID(hex=identity[:32])),
                "record_id": record["record_id"], "source": source,
                "source_record_id": record["source_record_id"],
                "collection": record["collection"], "snapshot_ref": record["snapshot_ref"],
                "ordinal": ordinal, "start_char": start, "end_char": end,
                "content": content, "content_sha256": digest(content.encode()),
                "embedding_text": prefix + content, "token_count": count,
                "parent_content_sha256": record["content_sha256"],
                "parent_record_sha256": record_sha,
                "config_sha256": self.config_sha256, "quality_flags": flags,
                "provenance": deepcopy(record["provenance"]),
                "metadata": deepcopy(record["metadata"]),
                "filters": filter_payload(record),
            }
            output.append(item)
        return output, {"excluded": None, "flags": flags}


def reference_prefix(record):
    if record["source"] == "soc_log":
        return ""  # No incident IDs, paths, titles, group membership or labels.
    metadata = record["metadata"]
    identity = (metadata["technique_id"] if record["source"] == "mitre_attack" else
                record["source_record_id"] if record["source"] in {"cve", "cwe"} else "")
    title = record["title"]
    body_start = record["content"].lstrip("# ").casefold()
    parts = [identity] if identity else []
    if title != identity and not body_start.startswith(title.casefold()):
        parts.append(title)
    return "\n".join(parts) + "\n" if parts else ""


def filter_payload(record):
    """Explicit internal filter projection; never append this to model evidence."""
    m = record["metadata"]
    result = {key: record[key] for key in ("source", "snapshot_ref", "source_record_id")}
    platforms = m.get("platforms")
    if record["source"] == "playbook":
        platforms = [m["platform"]]
    elif record["source"] == "detection_rule":
        product = m["logsource"].get("product")
        platforms = [product] if isinstance(product, str) else None
    if platforms:
        result["platforms"] = sorted({p.casefold() for p in platforms})
    status = m.get("status", m.get("vulnStatus"))
    if status:
        result["source_status"] = status
    if record["source"] == "soc_log":
        result.update(split=m["split"], incident_group_id=m["group_id"],
                      test_frozen=m["test_frozen"])
    return result

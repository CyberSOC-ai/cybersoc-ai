"""Bounded offline input, versioned validation and deterministic serialization."""

import hashlib
import json
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

SCHEMA_DIR = Path(__file__).with_name("schemas")
MAX_INPUT_BYTES = 128 * 1024 * 1024


class IngestionError(ValueError):
    """An input cannot be safely or reproducibly normalized."""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise IngestionError("Duplicate JSON object key")
        value[key] = item
    return value


def parse_json(data):
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=unique_object,
                          parse_constant=lambda _: invalid_constant())
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise IngestionError("Invalid UTF-8 JSON") from exc


def invalid_constant():
    raise IngestionError("Non-finite JSON value")


def read_bytes(path, limit=MAX_INPUT_BYTES):
    with Path(path).open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise IngestionError("Input exceeds byte limit")
    return data


@lru_cache(maxsize=8)
def validator_for(name):
    schema = json.loads((SCHEMA_DIR / f"{name}.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def validate(name, value):
    errors = list(validator_for(name).iter_errors(value))
    if errors:
        # Do not include raw document contents in errors/logs.
        path = "/".join(map(str, errors[0].absolute_path))
        raise IngestionError(f"Invalid {name} at /{path}: {errors[0].validator}")


def text(value):
    if not isinstance(value, str) or not value.strip():
        raise IngestionError("Required non-empty source text is missing")
    return " ".join(value.split())


def record(snapshot, source_id, title, content, metadata):
    source_id = text(source_id)
    result = {
        "schema_version": "1.0.0",
        "record_id": "DOC-" + digest(canonical([snapshot["source"], source_id])),
        "source": snapshot["source"],
        "source_record_id": source_id,
        "collection": ("soc_history" if snapshot["source"] == "soc_log" else
                       "relationships" if metadata.get("stix_type") == "relationship" else "knowledge"),
        "title": text(title),
        "content": text(content),
        "content_sha256": digest(text(content).encode("utf-8")),
        "snapshot_ref": snapshot["artifact_ref"],
        "provenance": dict(snapshot),
        "metadata": metadata,
    }
    validate("record", result)
    return result

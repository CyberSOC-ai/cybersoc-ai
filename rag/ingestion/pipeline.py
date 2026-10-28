"""Pure normalization plus atomic publication of a complete corpus directory."""

from collections import Counter
import os
from pathlib import Path
import tempfile

from . import VERSION, adapters
from .core import IngestionError, canonical, digest, parse_json, read_bytes, validate


def implementation_hash():
    root = Path(__file__).parent
    files = sorted([*root.glob("*.py"), *root.glob("schemas/*.json")])
    return digest(canonical({str(p.relative_to(root)): digest(p.read_bytes()) for p in files}))


def normalize(data, snapshot, *, policy=None, splits_data=None):
    validate("snapshot", snapshot)
    if digest(data) != snapshot["sha256"]:
        raise IngestionError("Snapshot hash mismatch")
    if snapshot["upstream_version"].lower() in {"latest", "main", "master", "head"}:
        raise IngestionError("An immutable snapshot version is required")
    if snapshot["source"] == "soc_log":
        if policy is None or splits_data is None:
            raise IngestionError("SOC policy and evaluation splits are required")
        iterator = adapters.soc(data, snapshot, policy, parse_json(splits_data), splits_data)
    else:
        if policy is not None or splits_data is not None:
            raise IngestionError("SOC policy is only valid for SOC snapshots")
        iterator = {"mitre_attack": adapters.attack, "cve": adapters.cve,
                    "cwe": adapters.cwe}[snapshot["source"]](data, snapshot)
    records, excluded, seen = [], Counter(), set()
    try:
        for value, reason in iterator:
            if value is None:
                excluded[reason] += 1
            else:
                if value["record_id"] in seen:
                    raise IngestionError("Duplicate normalized record identity")
                seen.add(value["record_id"])
                records.append(value)
    except (KeyError, TypeError, AttributeError, RecursionError) as exc:
        raise IngestionError("Malformed upstream record") from exc
    records.sort(key=lambda item: item["record_id"])
    output = b"".join(canonical(item) + b"\n" for item in records)
    report = {
        "schema_version": "1.0.0", "normalizer_version": VERSION,
        "implementation_sha256": implementation_hash(),
        "record_schema_sha256": digest((Path(__file__).parent / "schemas/record.schema.json").read_bytes()),
        "snapshot": snapshot, "accepted": len(records),
        "excluded": dict(sorted(excluded.items())),
        "considered": len(records) + sum(excluded.values()),
        "records_sha256": digest(output),
        "corpus_use": "development_only" if snapshot["source"] == "soc_log" and
        not parse_json(splits_data)["test_frozen"] else "retrieval",
    }
    if policy is not None:
        report["soc_policy_sha256"] = digest(canonical(policy))
        report["splits_sha256"] = digest(splits_data)
    return output, report


def ingest(input_path, snapshot_path, notice_path, output_dir, *, policy_path=None,
           splits_path=None):
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise IngestionError("Output directory already exists; use a new version")
    snapshot_data = read_bytes(snapshot_path, 1024 * 1024)
    snapshot = parse_json(snapshot_data)
    validate("snapshot", snapshot)
    notice = read_bytes(notice_path, 4 * 1024 * 1024)
    if digest(notice) != snapshot["notice_sha256"]:
        raise IngestionError("Source notice hash mismatch")
    policy_data = read_bytes(policy_path, 16 * 1024 * 1024) if policy_path else None
    splits_data = read_bytes(splits_path, 16 * 1024 * 1024) if splits_path else None
    output, report = normalize(read_bytes(input_path), snapshot,
                               policy=parse_json(policy_data) if policy_data else None,
                               splits_data=splits_data)
    report["snapshot_manifest_sha256"] = digest(snapshot_data)
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    # Publish only after every record validates. Preserve notice, manifest and
    # policy inputs alongside the derived corpus; raw snapshots stay external.
    with tempfile.TemporaryDirectory(prefix=".ingestion-", dir=output_dir.parent) as temporary:
        staging = Path(temporary) / "corpus"
        staging.mkdir()
        (staging / "records.jsonl").write_bytes(output)
        (staging / "manifest.json").write_bytes(canonical(report) + b"\n")
        (staging / "source-notice.txt").write_bytes(notice)
        (staging / "snapshot.json").write_bytes(snapshot_data)
        if policy_data is not None:
            (staging / "soc-policy.json").write_bytes(policy_data)
        if splits_data is not None:
            (staging / "splits.json").write_bytes(splits_data)
        os.rename(staging, output_dir)
    return report

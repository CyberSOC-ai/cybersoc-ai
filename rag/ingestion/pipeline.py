"""Pure normalization plus atomic publication of a complete corpus directory."""

from collections import Counter
import os
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET

import yaml

from . import VERSION, adapters
from .core import IngestionError, canonical, digest, parse_json, read_bytes, validate


def implementation_hash():
    root = Path(__file__).parent
    files = sorted([*root.glob("*.py"), *root.glob("schemas/*.json")])
    hashes = {str(p.relative_to(root)): digest(p.read_bytes()) for p in files}
    repository = root.parents[1]
    dependencies = [repository / "backend/validation.py", repository / "requirements.txt",
                    *sorted((repository / "backend/contracts/v1").glob("*.schema.json"))]
    hashes.update({"repository/" + str(p.relative_to(repository)): digest(p.read_bytes()) for p in dependencies})
    return digest(canonical(hashes))


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
        from . import extensions
        iterator = {"mitre_attack": adapters.attack, "cve": adapters.cve, "cwe": adapters.cwe,
                    "kev": extensions.kev, "detection_rule": extensions.sigma,
                    "playbook": extensions.playbook}[snapshot["source"]](data, snapshot)
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
    except IngestionError:
        raise
    except (KeyError, TypeError, AttributeError, RecursionError, ValueError, yaml.YAMLError, ET.ParseError) as exc:
        raise IngestionError("Malformed upstream record") from exc
    records.sort(key=lambda item: item["record_id"])
    output = b"".join(canonical(item) + b"\n" for item in records)
    report = build_report(snapshot, len(records), excluded, digest(output), policy, splits_data)
    return output, report


def build_report(snapshot, accepted, excluded, output_sha256, policy=None, splits_data=None):
    report = {
        "schema_version": "1.0.0", "normalizer_version": VERSION,
        "implementation_sha256": implementation_hash(),
        "record_schema_sha256": digest((Path(__file__).parent / "schemas/record.schema.json").read_bytes()),
        "snapshot": snapshot, "accepted": accepted,
        "excluded": dict(sorted(excluded.items())),
        "considered": accepted + sum(excluded.values()),
        "records_sha256": output_sha256,
        "corpus_use": "development_only" if snapshot["source"] == "soc_log" and
        not parse_json(splits_data)["test_frozen"] else "retrieval",
    }
    if policy is not None:
        report["soc_policy_sha256"] = digest(canonical(policy))
        report["splits_sha256"] = digest(splits_data)
    return report


def ingest(input_path, snapshot_path, notice_path, output_dir, *, policy_path=None,
           splits_path=None, stream_nvd=False):
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
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    # Publish only after every record validates. Preserve notice, manifest and
    # policy inputs alongside the derived corpus; raw snapshots stay external.
    with tempfile.TemporaryDirectory(prefix=".ingestion-", dir=output_dir.parent) as temporary:
        staging = Path(temporary) / "corpus"
        staging.mkdir()
        if stream_nvd:
            if snapshot["source"] != "cve" or policy_data is not None or splits_data is not None:
                raise IngestionError("Streaming NVD requires a CVE snapshot without SOC inputs")
            from .nvd_bulk import normalize_file
            accepted, excluded, checksum = normalize_file(input_path, snapshot, staging)
            report = build_report(snapshot, accepted, excluded, checksum)
        else:
            output, report = normalize(read_bytes(input_path), snapshot,
                                       policy=parse_json(policy_data) if policy_data else None,
                                       splits_data=splits_data)
            (staging / "records.jsonl").write_bytes(output)
        report["snapshot_manifest_sha256"] = digest(snapshot_data)
        (staging / "manifest.json").write_bytes(canonical(report) + b"\n")
        (staging / "source-notice.txt").write_bytes(notice)
        (staging / "snapshot.json").write_bytes(snapshot_data)
        if policy_data is not None:
            (staging / "soc-policy.json").write_bytes(policy_data)
        if splits_data is not None:
            (staging / "splits.json").write_bytes(splits_data)
        os.rename(staging, output_dir)
    return report

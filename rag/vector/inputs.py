"""Verify the composed ingestion handoff and recheck current SOC eligibility."""

from collections import Counter
import hashlib
from pathlib import Path

from rag.ingestion.adapters import split_guard
from rag.ingestion.core import IngestionError, canonical, digest, parse_json, read_bytes, validate


class CorpusInput:
    def __init__(self, directory, manifest_sha256, splits_path, policy_paths):
        self.directory = Path(directory)
        raw = read_bytes(self.directory / "manifest.json", 4 * 1024**2)
        if digest(raw) != manifest_sha256:
            raise IngestionError("Composed manifest SHA-256 mismatch")
        self.manifest_sha256 = manifest_sha256
        self.manifest = parse_json(raw)
        if self.manifest.get("schema_version") != "1.0.0":
            raise IngestionError("Unsupported corpus version")
        if self.manifest.get("corpus_use") not in {"development_only", "retrieval"}:
            raise IngestionError("Missing corpus usage restriction")
        split_bytes = read_bytes(splits_path, 16 * 1024**2)
        self.splits = parse_json(split_bytes)
        self.splits_sha256 = digest(split_bytes)
        self.policies = {}
        self.blocked_ids, self.blocked_groups, self.blocked_runs = set(), set(), set()
        for path in policy_paths:
            policy = parse_json(read_bytes(path, 16 * 1024**2))
            external = "source_record" in next(iter(policy.get("records", [])), {})
            checked = split_guard(policy, self.splits, split_bytes,
                                  schema="external-policy" if external else "soc-policy",
                                  identity_field="source_record" if external else "incident_id")
            key = digest(canonical(policy))
            if key in self.policies:
                raise IngestionError("Duplicate eligibility policy")
            self.policies[key] = (policy, checked[0])
            self.blocked_ids.update(checked[1])
            self.blocked_groups.update(checked[2])
            self.blocked_runs.update(checked[3])
        self.snapshots = {}
        for index, entry in enumerate(self.manifest["inputs"]):
            snapshot = entry["snapshot"]
            validate("snapshot", snapshot)
            key = snapshot["artifact_ref"]
            if key in self.snapshots:
                raise IngestionError("Ambiguous input snapshot")
            self.snapshots[key] = entry
            notice = read_bytes(self.directory / f"notice-{index:02d}.txt", 4 * 1024**2)
            if digest(notice) != snapshot["notice_sha256"]:
                raise IngestionError("Source notice digest mismatch")
            if snapshot["source"] == "soc_log":
                if (entry.get("splits_sha256") != self.splits_sha256 or
                        entry.get("soc_policy_sha256") not in self.policies):
                    raise IngestionError("SOC corpus needs rebuilding for current policy/splits")
        self.policy_sha256s = sorted(self.policies)

    def check_soc(self, record):
        if record["source"] != "soc_log":
            return
        m = record["metadata"]
        entry = self.snapshots[record["snapshot_ref"]]
        policy, assignments = self.policies[entry["soc_policy_sha256"]]
        identity = (m["provider"] + ":" + m["source_path"] if "provider" in m else m["incident_id"])
        assignment = assignments.get(identity)
        if assignment is None:
            raise IngestionError("SOC record has no current assignment")
        if (m["split"] != "development" or assignment["split"] != "development" or
                identity in self.blocked_ids or
                set(assignment["related_case_ids"]) & self.blocked_ids or
                m["group_id"] in self.blocked_groups or m["run_id"] in self.blocked_runs):
            raise IngestionError("Ineligible SOC record in prepared corpus; rebuild ingestion")
        if any(m[key] != assignment[key] for key in ("group_id", "run_id")):
            raise IngestionError("SOC assignment lineage mismatch")
        if (m["assignment_ref"] != policy["assignment_ref"] or
                m["dataset_version"] != self.splits["dataset_version"] or
                m["test_frozen"] != self.splits["test_frozen"]):
            raise IngestionError("SOC split metadata mismatch")
        if "provider" in m and (m["source_file_sha256"] != assignment["sha256"] or
                                 not 0 <= m["event_index"] < assignment["max_events"]):
            raise IngestionError("External SOC assignment content/selection mismatch")

    def records(self):
        """A bounded stream. Callers publish output only after full exhaustion."""
        checksum, counts, previous = hashlib.sha256(), Counter(), ""
        with (self.directory / "records.jsonl").open("rb") as stream:
            while line := stream.readline(8 * 1024**2 + 1):
                if len(line) > 8 * 1024**2 or not line.endswith(b"\n"):
                    raise IngestionError("Invalid or oversized composed corpus line")
                checksum.update(line)
                record = parse_json(line)
                validate("record", record)
                if record["record_id"] <= previous:
                    raise IngestionError("Corpus IDs must be unique and sorted")
                previous = record["record_id"]
                entry = self.snapshots.get(record["snapshot_ref"])
                if entry is None or record["provenance"] != entry["snapshot"]:
                    raise IngestionError("Unrecognized primary provenance")
                for snapshot in record["metadata"].get("provenance_chain", []):
                    known = self.snapshots.get(snapshot["artifact_ref"])
                    if known is None or snapshot != known["snapshot"]:
                        raise IngestionError("Unrecognized supplemental provenance")
                self.check_soc(record)
                counts[record["source"]] += 1
                yield record
        if (checksum.hexdigest() != self.manifest["records_sha256"] or
                sum(counts.values()) != self.manifest["accepted"] or
                dict(counts) != self.manifest["by_source"]):
            raise IngestionError("Composed corpus hash/count mismatch")

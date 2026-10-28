"""Source-format, provenance, deterministic replay and leakage boundary tests."""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from jsonschema import Draft202012Validator, ValidationError

from rag.ingestion.core import IngestionError, canonical, digest, parse_json, read_bytes
from rag.ingestion.pipeline import ingest, normalize

ROOT = Path(__file__).resolve().parents[2]
NOTICE = b"Synthetic fixtures for parser tests; not an upstream dataset.\n"


def snapshot(source, data):
    return {"schema_version": "1.0.0", "source": source, "owner": "fixture-owner",
            "source_url": "https://example.org/fixture", "upstream_version": "test-1",
            "acquired_at": "2026-10-28T00:00:00Z", "sha256": digest(data),
            "artifact_ref": "fixture:" + digest(data), "license_ref": "fixture-license",
            "notice_ref": "fixture-notice", "notice_sha256": digest(NOTICE),
            "usage_scope": "project-retrieval"}


def technique(identity="attack-pattern--one", **updates):
    value = {"type": "attack-pattern", "id": identity, "name": "Test technique",
             "description": "A synthetic technique description.", "modified": "2026-01-01T00:00:00Z",
             "external_references": [{"source_name": "mitre-attack", "external_id": "T1110"}]}
    value.update(updates)
    return value


def attack_data(*items):
    return canonical({"type": "bundle", "objects": list(items)})


def run_attack(data):
    return normalize(data, snapshot("mitre_attack", data))


class IngestionTests(unittest.TestCase):
    def test_schemas_are_valid(self):
        for path in (ROOT / "rag/ingestion/schemas").glob("*.json"):
            Draft202012Validator.check_schema(json.loads(path.read_text()))
        directory = ROOT / "rag/ingestion/schemas"
        snapshot_schema = json.loads((directory / "snapshot.schema.json").read_bytes())
        for key in ("$schema", "$id"):
            snapshot_schema.pop(key)
        record_schema = json.loads((directory / "record.schema.json").read_bytes())
        self.assertEqual(snapshot_schema, record_schema["properties"]["provenance"])

    def test_source_metadata_types_are_part_of_the_handoff_contract(self):
        data = attack_data(technique(modified={"unexpected": "object"}))
        with self.assertRaises(IngestionError):
            run_attack(data)

    def test_deterministic_sorted_records_and_identity_across_snapshots(self):
        data = attack_data(technique("b"), technique("a"))
        first, manifest = run_attack(data)
        self.assertEqual((first, manifest), run_attack(data))
        changed = attack_data(technique("b", description="Changed description"), technique("a"))
        second, _ = run_attack(changed)
        a = {r["source_record_id"]: r for r in map(json.loads, first.splitlines())}
        b = {r["source_record_id"]: r for r in map(json.loads, second.splitlines())}
        self.assertEqual(a["b"]["record_id"], b["b"]["record_id"])
        self.assertNotEqual(a["b"]["content_sha256"], b["b"]["content_sha256"])
        self.assertEqual(manifest["records_sha256"], digest(first))
        self.assertEqual([r["record_id"] for r in a.values()], sorted(r["record_id"] for r in a.values()))

    def test_attack_exclusions_and_relationships(self):
        data = attack_data(technique(), technique("revoked", revoked=True),
                           technique("deprecated", x_mitre_deprecated=True),
                           {"type": "identity", "id": "identity--one"},
                           {"type": "relationship", "id": "relationship--one",
                            "relationship_type": "uses", "source_ref": "actor--one",
                            "target_ref": "attack-pattern--one", "modified": "2026-01-01T00:00:00Z"})
        output, report = run_attack(data)
        self.assertEqual(len(output.splitlines()), 2)
        self.assertEqual(report["excluded"], {"revoked_or_deprecated": 2, "unsupported_stix_type": 1})
        records = list(map(json.loads, output.splitlines()))
        relationship = next(r for r in records if r["source_record_id"] == "relationship--one")
        self.assertEqual(relationship["metadata"]["target_ref"], "attack-pattern--one")

    def test_duplicate_ids_and_malformed_upstream_fail(self):
        for data in (attack_data(technique(), technique()),
                     attack_data(technique(external_references=[])), b"[]", b"{}",
                     attack_data({"type": "attack-pattern"})):
            with self.subTest(data=data[:80]), self.assertRaises(IngestionError):
                run_attack(data)

    def test_strict_json_and_byte_limit(self):
        for data in (b'{"a":1,"a":2}', b'{"a":NaN}', b'\xff', b'{'):
            with self.assertRaises(IngestionError):
                parse_json(data)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "input"
            path.write_bytes(b"1234")
            with self.assertRaises(IngestionError):
                read_bytes(path, 3)

    def test_provenance_is_required_and_hashes_are_checked(self):
        data = attack_data(technique())
        for field in ("source_url", "license_ref", "notice_sha256", "upstream_version", "acquired_at"):
            manifest = snapshot("mitre_attack", data)
            del manifest[field]
            with self.assertRaises(IngestionError):
                normalize(data, manifest)
        manifest = snapshot("mitre_attack", data)
        with self.assertRaises(IngestionError):
            normalize(data + b" ", manifest)
        manifest["upstream_version"] = "latest"
        with self.assertRaises(IngestionError):
            normalize(data, manifest)

    def test_cve_preserves_missing_fields_and_supplied_enrichment(self):
        item = {"id": "CVE-2026-1234", "published": "2026-01-01T00:00:00.000",
                "lastModified": "2026-01-02T00:00:00.000",
                "descriptions": [{"lang": "en", "value": "Synthetic vulnerability"}],
                "vulnStatus": "Received"}
        def feed(items):
            return canonical({"format": "NVD_CVE", "version": "2.0",
                              "vulnerabilities": [{"cve": i} for i in items]})
        data = feed([item])
        out, _ = normalize(data, snapshot("cve", data))
        normalized = json.loads(out)
        self.assertNotIn("metrics", normalized["metadata"])
        item["metrics"] = {"cvssMetricV31": [{"cvssData": {"baseScore": 7.5}}]}
        item["weaknesses"] = [{"description": [{"lang": "en", "value": "CWE-20"}]}]
        data = feed([item, dict(item, id="CVE-2026-1235", vulnStatus="Rejected"),
                     dict(item, id="CVE-2026-1236", descriptions=[])])
        out, report = normalize(data, snapshot("cve", data))
        self.assertEqual(json.loads(out)["metadata"]["metrics"], item["metrics"])
        self.assertEqual(report["accepted"], 1)
        self.assertEqual(report["excluded"], {"rejected_cve": 1, "missing_english_description": 1})

    def test_cwe_namespace_relationships_and_categories(self):
        data = b'''<Weakness_Catalog xmlns="http://cwe.mitre.org/cwe-7" Version="test-1">
        <Weaknesses><Weakness ID="20" Name="Input validation" Status="Stable" Abstraction="Class">
        <Description>Improper <b>input</b> validation.</Description>
        <Related_Weaknesses><Related_Weakness Nature="ChildOf" CWE_ID="707"/></Related_Weaknesses>
        </Weakness><Weakness ID="1" Status="Deprecated"/></Weaknesses>
        <Categories><Category ID="100"/></Categories><Views><View ID="200"/></Views></Weakness_Catalog>'''
        out, report = normalize(data, snapshot("cwe", data))
        item = json.loads(out)
        self.assertEqual(item["source_record_id"], "CWE-20")
        self.assertIn("Improper input validation.", item["content"])
        self.assertEqual(item["metadata"]["relationships"][0]["CWE_ID"], "707")
        self.assertEqual(report["excluded"], {"deprecated_cwe": 1, "cwe_category_or_view": 2})
        manifest = snapshot("cwe", data)
        manifest["upstream_version"] = "other"
        with self.assertRaises(IngestionError):
            normalize(data, manifest)

    def test_xml_entities_and_alternate_encodings_are_rejected(self):
        samples = [b'<!DOCTYPE x [<!ENTITY y "secret">]><x>&y;</x>',
                   '<!DOCTYPE x><x/>'.encode('utf-16'), b'<wrong/>']
        for data in samples:
            with self.assertRaises(IngestionError):
                normalize(data, snapshot("cwe", data))

    def test_cwe_8_namespace_and_groupings(self):
        data = b'''<Weakness_Catalog xmlns="http://cwe.mitre.org/cwe-8" Version="test-1">
        <Weaknesses><Weakness ID="20" Name="Input validation" Status="Stable" Abstraction="Class">
        <Description>Improper input validation.</Description></Weakness></Weaknesses>
        <Groupings><Grouping ID="100"/></Groupings></Weakness_Catalog>'''
        out, report = normalize(data, snapshot("cwe", data))
        self.assertEqual(json.loads(out)["metadata"]["xml_namespace"], "http://cwe.mitre.org/cwe-8")
        self.assertEqual(report["excluded"], {"cwe_category_or_view": 1})

    def test_inactive_relationship_targets_are_excluded(self):
        data = attack_data(technique(revoked=True),
                           {"type": "relationship", "id": "r", "relationship_type": "uses",
                            "source_ref": "actor--one", "target_ref": "attack-pattern--one",
                            "modified": "2026-01-01T00:00:00Z"})
        out, report = run_attack(data)
        self.assertEqual(out, b"")
        self.assertEqual(report["excluded"]["inactive_relationship_endpoint"], 1)

    def soc_inputs(self):
        incident = json.loads((ROOT / "tests/normalizer/fixtures/lab01-run01-incident.json").read_text())
        splits = canonical({"dataset_version": "fixture-1", "test_frozen": True,
                            "development": [], "test": [{"case_id": "TEST-1", "group_id": "HELDOUT"}]})
        assignment = {"incident_id": incident["incident_id"], "record_sha256": digest(canonical(incident)),
                      "group_id": "DEVELOPMENT", "run_id": "RUN-1", "split": "development",
                      "related_case_ids": [], "sanitization_ref": "fixture-reviewed-input"}
        policy = {"schema_version": "1.0.0", "dataset_version": "fixture-1",
                  "splits_sha256": digest(splits), "assignment_ref": "fixture-assignment",
                  "records": [assignment]}
        return incident, policy, splits

    def test_soc_requires_hashed_assignment_and_excludes_labels(self):
        incident, policy, splits = self.soc_inputs()
        data = canonical([incident])
        manifest = snapshot("soc_log", data)
        out, report = normalize(data, manifest, policy=policy, splits_data=splits)
        self.assertEqual(report["accepted"], 1)
        self.assertEqual(json.loads(out)["collection"], "soc_history")
        with self.assertRaises(IngestionError):
            normalize(data, manifest)
        incident["expected_verdict"] = "false_positive"
        data = canonical([incident])
        with self.assertRaises(ValidationError):
            normalize(data, snapshot("soc_log", data), policy=policy, splits_data=splits)

    def test_soc_group_related_case_unknown_split_and_hash_boundaries(self):
        incident, policy, splits = self.soc_inputs()
        data = canonical([incident])
        for changes in ({"group_id": "HELDOUT"}, {"related_case_ids": ["TEST-1"]},
                        {"split": "test"}, {"split": "quarantine"}):
            blocked = deepcopy(policy)
            blocked["records"][0].update(changes)
            out, report = normalize(data, snapshot("soc_log", data), policy=blocked, splits_data=splits)
            self.assertEqual(out, b"")
            self.assertEqual(report["excluded"], {"excluded_soc_split": 1})
        policy["records"] = []
        _, report = normalize(data, snapshot("soc_log", data), policy=policy, splits_data=splits)
        self.assertEqual(report["excluded"], {"unassigned_soc_record": 1})
        _, policy, _ = self.soc_inputs()
        for altered in (splits + b" ", splits.replace(b'fixture-1', b'fixture-2')):
            with self.assertRaises(IngestionError):
                normalize(data, snapshot("soc_log", data), policy=policy, splits_data=altered)
        policy["records"][0]["record_sha256"] = "0" * 64
        with self.assertRaises(IngestionError):
            normalize(data, snapshot("soc_log", data), policy=policy, splits_data=splits)

    def test_soc_sibling_run_and_duplicate_policy(self):
        incident, policy, splits = self.soc_inputs()
        sibling = deepcopy(policy["records"][0])
        sibling.update(incident_id="INC-other", group_id="OTHER", split="test")
        policy["records"].append(sibling)
        data = canonical([incident])
        out, _ = normalize(data, snapshot("soc_log", data), policy=policy, splits_data=splits)
        self.assertEqual(out, b"")
        sibling["incident_id"] = incident["incident_id"]
        with self.assertRaises(IngestionError):
            normalize(data, snapshot("soc_log", data), policy=policy, splits_data=splits)

    def test_unfrozen_split_is_explicitly_development_only(self):
        incident, policy, splits = self.soc_inputs()
        splits = splits.replace(b'true', b'false')
        policy["splits_sha256"] = digest(splits)
        data = canonical([incident])
        _, report = normalize(data, snapshot("soc_log", data), policy=policy, splits_data=splits)
        self.assertEqual(report["corpus_use"], "development_only")

    def test_soc_cannot_relabel_a_present_heldout_duplicate(self):
        incident, policy, splits = self.soc_inputs()
        heldout = dict(incident, incident_id="INC-heldout")
        assignment = dict(policy["records"][0], incident_id="INC-heldout", split="test",
                          group_id="OTHER-GROUP", run_id="OTHER-RUN",
                          record_sha256=digest(canonical(heldout)))
        policy["records"].append(assignment)
        for candidate in (heldout, dict(heldout, description="Different text, same source event")):
            policy["records"][1]["record_sha256"] = digest(canonical(candidate))
            data = canonical([incident, candidate])
            out, report = normalize(data, snapshot("soc_log", data), policy=policy, splits_data=splits)
            self.assertEqual(out, b"")
            self.assertEqual(report["excluded"], {"excluded_soc_duplicate": 1, "excluded_soc_split": 1})

    def test_atomic_cli_notice_and_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            data = attack_data(technique())
            (temp / "input.json").write_bytes(data)
            (temp / "snapshot.json").write_bytes(canonical(snapshot("mitre_attack", data)))
            (temp / "notice").write_bytes(NOTICE)
            args = [sys.executable, "-B", "-m", "rag.ingestion", "--input", str(temp / "input.json"),
                    "--snapshot", str(temp / "snapshot.json"), "--notice", str(temp / "notice"),
                    "--output", str(temp / "out")]
            result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["accepted"], 1)
            self.assertEqual((temp / "out/source-notice.txt").read_bytes(), NOTICE)
            before = (temp / "out/records.jsonl").read_bytes()
            self.assertNotEqual(subprocess.run(args, cwd=ROOT, capture_output=True).returncode, 0)
            self.assertEqual(before, (temp / "out/records.jsonl").read_bytes())
            (temp / "notice").write_bytes(b"changed")
            with self.assertRaises(IngestionError):
                ingest(temp / "input.json", temp / "snapshot.json", temp / "notice", temp / "failed")
            self.assertFalse((temp / "failed").exists())
            (temp / "notice").write_bytes(NOTICE)
            invalid = attack_data(technique(), {"type": "attack-pattern"})
            (temp / "input.json").write_bytes(invalid)
            (temp / "snapshot.json").write_bytes(canonical(snapshot("mitre_attack", invalid)))
            with self.assertRaises(IngestionError):
                ingest(temp / "input.json", temp / "snapshot.json", temp / "notice", temp / "failed")
            self.assertFalse((temp / "failed").exists())


if __name__ == "__main__":
    unittest.main()

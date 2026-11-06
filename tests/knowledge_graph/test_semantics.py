"""Graph consistency tests; no claim of source truth or ETL split enforcement."""
from copy import deepcopy
import hashlib
import json
import unittest

from rag.graph.validate import ASSETS, ONTOLOGY, node_uid, relationship_uid, validate_batch


class SemanticTests(unittest.TestCase):
    def setUp(self):
        self.batch = json.loads((ASSETS / "examples/minimal-graph.json").read_text(encoding="utf-8"))

    def find(self, label):
        return next(n for n in self.batch["nodes"] if n["label"] == label)

    def resign_edge(self, edge):
        edge["uid"] = relationship_uid(edge["type"], edge["from_uid"], edge["to_uid"], edge["source_record_uid"])

    def test_examples_are_consistent(self):
        for path in (ASSETS / "examples").glob("*.json"):
            with self.subTest(example=path.name):
                validate_batch(json.loads(path.read_text(encoding="utf-8")))

    def test_synthetic_fixture_covers_all_business_labels(self):
        self.assertEqual({n["label"] for n in self.batch["nodes"]}, set(ONTOLOGY["node_types"]))

    def test_source_bytes_match_fixture_hashes(self):
        source = self.find("SourceRecord")
        expected = hashlib.sha256((ASSETS / "examples/SYNTHETIC_SOURCE.txt").read_text(encoding="utf-8").rstrip("\n").encode()).hexdigest()
        self.assertEqual(source["properties"]["content_sha256"], expected)

    def test_duplicate_nodes_and_relationships_rejected(self):
        for field in ("nodes", "relationships"):
            with self.subTest(field=field):
                batch = deepcopy(self.batch)
                batch[field].append(deepcopy(batch[field][0]))
                with self.assertRaises(ValueError):
                    validate_batch(batch)

    def test_missing_endpoint_rejected(self):
        self.batch["nodes"].remove(self.find("Host"))
        with self.assertRaises(ValueError):
            validate_batch(self.batch)

    def test_missing_and_wrong_provenance_rejected(self):
        for missing in (True, False):
            with self.subTest(missing=missing):
                batch = deepcopy(self.batch)
                if missing:
                    batch["nodes"] = [n for n in batch["nodes"] if n["label"] != "SourceRecord"]
                else:
                    batch["relationships"][0]["source_record_uid"] = self.find("Host")["uid"]
                    self.resign_edge(batch["relationships"][0])
                with self.assertRaises(ValueError):
                    validate_batch(batch)

    def test_wrong_endpoint_type_rejected(self):
        edge = self.batch["relationships"][0]
        edge["to_uid"] = self.find("User")["uid"]
        self.resign_edge(edge)
        with self.assertRaises(ValueError):
            validate_batch(self.batch)

    def test_forged_identifiers_rejected(self):
        for field in ("nodes", "relationships"):
            with self.subTest(field=field):
                batch = deepcopy(self.batch)
                batch[field][0]["uid"] = "KG-" + "0" * 64
                with self.assertRaises(ValueError):
                    validate_batch(batch)

    def test_identity_is_stable_order_independent_and_scoped(self):
        props = {"scope": "lab:a", "username": "admin"}
        self.assertEqual(node_uid("User", props), node_uid("User", dict(reversed(list(props.items())))))
        self.assertNotEqual(node_uid("User", props), node_uid("User", {**props, "scope": "lab:b"}))
        self.assertNotEqual(node_uid("User", props), node_uid("User", {**props, "username": "Admin"}))

    def test_source_versions_have_distinct_identities(self):
        props = self.find("SourceRecord")["properties"]
        self.assertNotEqual(node_uid("SourceRecord", props),
                            node_uid("SourceRecord", {**props, "content_sha256": "1" * 64}))

    def test_multiple_sources_preserve_separate_assertions(self):
        source = deepcopy(self.find("SourceRecord"))
        source["properties"]["snapshot_ref"] = "synthetic:second-source"
        source["uid"] = node_uid("SourceRecord", source["properties"])
        self.batch["nodes"].append(source)
        edge = deepcopy(self.batch["relationships"][0])
        edge["source_record_uid"] = source["uid"]
        self.resign_edge(edge)
        self.batch["relationships"].append(edge)
        validate_batch(self.batch)

    def test_ip_indicator_must_match_target(self):
        self.find("ThreatIndicator")["properties"]["value"] = "192.0.2.11"
        with self.assertRaises(ValueError):
            validate_batch(self.batch)

    def test_ip_version_and_canonical_form(self):
        self.find("IPAddress")["properties"]["version"] = 6
        with self.assertRaises(ValueError):
            validate_batch(self.batch)

    def test_indicator_values_and_intervals(self):
        for kind, value in (("sha256", "bad"), ("domain", "https://example.com"), ("ipv6", "192.0.2.10")):
            with self.subTest(kind=kind):
                batch = deepcopy(self.batch)
                props = next(n for n in batch["nodes"] if n["label"] == "ThreatIndicator")["properties"]
                props.update(indicator_type=kind, value=value)
                with self.assertRaises(ValueError):
                    validate_batch(batch)
        self.find("ThreatIndicator")["properties"].update(
            valid_from="2026-11-06T12:00:00Z", valid_until="2026-11-05T12:00:00Z")
        with self.assertRaises(ValueError):
            validate_batch(self.batch)

    def test_subtechnique_parent_and_domain(self):
        parent = self.find("AttackTechnique")
        child = deepcopy(parent)
        child["properties"].update(technique_id="T1110.001", name="Password Guessing")
        child["uid"] = node_uid("AttackTechnique", child["properties"])
        self.batch["nodes"].append(child)
        source_uid = self.find("SourceRecord")["uid"]
        edge = {"type": "SUBTECHNIQUE_OF", "from_uid": child["uid"], "to_uid": parent["uid"],
                "source_record_uid": source_uid, "properties": {}}
        self.resign_edge(edge)
        self.batch["relationships"].append(edge)
        validate_batch(self.batch)
        edge["from_uid"], edge["to_uid"] = edge["to_uid"], edge["from_uid"]
        self.resign_edge(edge)
        with self.assertRaises(ValueError):
            validate_batch(self.batch)

    def test_lab_example_has_only_observed_mentions(self):
        batch = json.loads((ASSETS / "examples/lab-mentions.json").read_text(encoding="utf-8"))
        validate_batch(batch)
        self.assertEqual(len(batch["relationships"]), 5)
        self.assertEqual({e["type"] for e in batch["relationships"]},
                         {"MENTIONS_HOST", "MENTIONS_USER", "MENTIONS_IP"})
        self.assertEqual({n["properties"]["name"] for n in batch["nodes"] if n["label"] == "Host"},
                         {"linux-01", "linuxsoc"})

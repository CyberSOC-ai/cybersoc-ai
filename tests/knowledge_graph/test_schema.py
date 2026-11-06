"""Offline graph shape tests. No Neo4j, downloads or model required."""
from copy import deepcopy
import json
import unittest

from jsonschema import Draft202012Validator, ValidationError

from rag.graph.validate import ASSETS, ONTOLOGY, SCHEMA, VALIDATOR


class SchemaTests(unittest.TestCase):
    def setUp(self):
        self.batch = json.loads((ASSETS / "examples/minimal-graph.json").read_text(encoding="utf-8"))

    def test_schema_is_well_formed(self):
        Draft202012Validator.check_schema(SCHEMA)

    def test_examples_satisfy_schema(self):
        for path in (ASSETS / "examples").glob("*.json"):
            with self.subTest(example=path.name):
                VALIDATOR.validate(json.loads(path.read_text(encoding="utf-8")))

    def test_ontology_and_schema_agree(self):
        variants = SCHEMA["properties"]["nodes"]["items"]["oneOf"]
        actual = {v["properties"]["label"]["const"]: v["properties"]["properties"] for v in variants}
        self.assertEqual(set(actual), set(ONTOLOGY["node_types"]))
        for label, rule in ONTOLOGY["node_types"].items():
            self.assertEqual(actual[label], rule["property_schema"])
            self.assertEqual(actual[label]["required"], rule["required_properties"])
            self.assertTrue(set(rule["identity_fields"]) <= set(rule["required_properties"]))
        self.assertEqual(set(SCHEMA["properties"]["relationships"]["items"]["properties"]["type"]["enum"]),
                         set(ONTOLOGY["relationship_types"]))

    def test_unknown_fields_versions_labels_and_relationships(self):
        mutations = [lambda b: b.update(ontology_version="2.0.0"),
                     lambda b: b.update(unexpected=True),
                     lambda b: b["nodes"][1].update(label="Invented"),
                     lambda b: b["nodes"][1]["properties"].update(secret="forbidden"),
                     lambda b: b["relationships"][0].update(type="INVENTED"),
                     lambda b: b["relationships"][0]["properties"].update(confidence=2)]
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                batch = deepcopy(self.batch)
                mutate(batch)
                with self.assertRaises(ValidationError):
                    VALIDATOR.validate(batch)

    def test_all_required_properties_are_enforced(self):
        for index, node in enumerate(self.batch["nodes"]):
            fields = ONTOLOGY["node_types"][node["label"]]["required_properties"]
            for field in fields:
                with self.subTest(label=node["label"], field=field):
                    batch = deepcopy(self.batch)
                    del batch["nodes"][index]["properties"][field]
                    with self.assertRaises(ValidationError):
                        VALIDATOR.validate(batch)

    def test_invalid_ip_technique_cve_and_timestamp(self):
        invalid = {"IPAddress": ("address", "999.1.1.1"),
                   "AttackTechnique": ("technique_id", "T11"),
                   "Vulnerability": ("cve_id", "CVE-2024-x"),
                   "Alert": ("timestamp", "2026-02-30T12:00:00Z")}
        for label, (field, value) in invalid.items():
            with self.subTest(label=label):
                batch = deepcopy(self.batch)
                next(n for n in batch["nodes"] if n["label"] == label)["properties"][field] = value
                with self.assertRaises(ValidationError):
                    VALIDATOR.validate(batch)

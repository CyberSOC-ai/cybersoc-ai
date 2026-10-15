"""Verify S0-T06 fixture integration with the existing closed trace contract."""
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "experiments/examples"


def reject_network(uri):
    raise RuntimeError(f"Unregistered schema reference: {uri}")


class ExperimentExamplesTest(unittest.TestCase):
    def test_synthetic_manifest_resolves_a_compatible_trace(self):
        manifest = json.loads((EXAMPLES / "manifest.synthetic.json").read_text())
        trace_path = (EXAMPLES / manifest["trace_ref"]).resolve()
        self.assertTrue(trace_path.is_relative_to(EXAMPLES.resolve()))
        trace = json.loads(trace_path.read_text())
        schemas = [json.loads(p.read_text()) for p in
                   (ROOT / "backend/contracts/v1").glob("*.schema.json")]
        registry = Registry(retrieve=reject_network).with_resources(
            (s["$id"], Resource.from_contents(s)) for s in schemas)
        schema = next(s for s in schemas if s["title"] == "trace")
        Draft202012Validator(schema, registry=registry,
                             format_checker=FormatChecker()).validate(trace)
        self.assertEqual(manifest["trace_id"], trace["trace_id"])
        self.assertEqual(manifest["versions"], trace["versions"])
        self.assertTrue(manifest["synthetic_example"])
        self.assertEqual(manifest["execution_status"], "not_run")
        self.assertEqual(manifest["measured_metrics"], [])
        self.assertEqual(trace["workflow"], "baseline")
        self.assertEqual([s["step"] for s in trace["steps"]],
                         list(range(1, len(trace["steps"]) + 1)))
        self.assertLessEqual(trace["started_at"], trace["finished_at"])

    def test_templates_parse_without_claiming_executed_results(self):
        templates = {p.stem: json.loads(p.read_text()) for p in
                     (ROOT / "experiments/templates").glob("*.json")}
        self.assertEqual(set(templates), {"experiment", "environment", "results"})
        for name, value in templates.items():
            with self.subTest(template=name):
                self.assertEqual(value["record_kind"], "template")
                self.assertEqual(value["record_version"], "1.0.0")
        for name in ("experiment", "results"):
            self.assertEqual(templates[name]["execution_status"], "not_run")
        self.assertEqual(templates["results"]["metrics"], [])


if __name__ == "__main__":
    unittest.main()

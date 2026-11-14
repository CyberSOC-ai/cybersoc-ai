"""Shared-release isolation, integrity and recorded failure behavior; no model needed."""

from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import os
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from ai.no_rag import run as shared
from ai.runtime.contracts import InvalidOutput, RunnerTimeout, RunnerUnavailable, contract_validators


class Runtime:
    command = ["controlled-runtime"]

    def __init__(self, *args):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class Generator:
    last_formatted_prompt = "controlled-format"
    responses = []

    def __init__(self, **kwargs):
        self.calls = 0

    def generate(self, messages, schema, deadline):
        user = json.loads(messages[1]["content"])
        assert set(user) == {"untrusted_incident", "fixed_proposal_policy", "required_output"}
        self.calls += 1
        response = self.responses[self.calls - 1] if self.responses else json.dumps({
            "summary": "Controlled compatibility output, not a model judgment.",
            "triage_verdict": "undetermined", "risk_level": "low",
            "mitre_techniques": [], "recommended_actions": []})
        if isinstance(response, Exception):
            raise response
        return response, {"client_seconds": 0.1}


class SharedTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.release = self.root / "release"
        inputs = self.release / "incidents/inputs"
        inputs.mkdir(parents=True)
        assets = []
        for number in range(7):
            iid = "B0-LNX-SSH-001" if number == 0 else f"TEST-{number}"
            incident = {"schema_version": "1.0.0", "incident_id": iid,
                "timestamp": "2026-11-11T00:00:00Z", "source": "controlled-fixture",
                "source_event_id": iid, "description": "Controlled fixture observation.",
                "severity": "low", "entities": [], "ingestion_kind": "synthetic"}
            path = inputs / f"{iid}.json"
            shared.save(path, incident)
            assets.append({"path": path.relative_to(self.release).as_posix(), "sha256": shared.digest(path)})
        shared.save(self.release / "manifest.json", {"release_id": "shared-dev-v1", "assets": assets})
        # Intentionally invalid: the No-RAG path must never read either directory.
        for name in ("evaluation", "knowledge"):
            (self.release / name).mkdir()
            (self.release / name / "DO-NOT-LOAD.json").write_text("not json: EVALUATOR_SENTINEL")
        self.manifest_hash = shared.digest(self.release / "manifest.json")
        self.artifact = self.root / "fixture.bin"
        self.artifact.write_bytes(b"Controlled artifact; never executable")
        self.config = self.root / "config.json"
        shared.save(self.config, {"model_file": str(self.artifact), "runtime_executable": str(self.artifact),
            "model_sha256": shared.digest(self.artifact), "runtime_sha256": shared.digest(self.artifact),
            "runtime_version": "controlled", "port": 8087, "max_input_tokens": 3072,
            "max_output_tokens": 512, "context_tokens": 4096, "seed": 42, "timeout_seconds": 2})
        self.output = self.root / "run"
        self.policy = self.root / "policy.json"
        policy = json.loads(shared.POLICY.read_text())
        policy.pop("source_role_annotations", None)
        shared.save(self.policy, policy)

    def invoke(self, **kwargs):
        with patch.object(shared, "RELEASE_SHA256", self.manifest_hash), \
                patch.object(shared, "POLICY", self.policy), \
                patch.object(shared, "LocalRuntime", Runtime), \
                patch.object(shared, "LlamaServer", Generator), \
                patch.object(shared, "git_state", return_value=("a" * 40, True)), \
                redirect_stdout(StringIO()):
            return shared.run(self.config, self.release, self.output, **kwargs)

    def test_success_saves_correlated_trace_without_evaluator_or_historical_data(self):
        self.assertEqual(self.invoke(), 0)
        folder = self.output / "B0-LNX-SSH-001"
        result = json.loads((folder / "result.json").read_text())
        trace = json.loads((folder / "trace.json").read_text())
        contract_validators(shared.ROOT)["trace"].validate(trace)
        self.assertEqual(result["trace_id"], trace["trace_id"])
        self.assertEqual(result["evidence"], [])
        sources = json.loads((self.output / "source-manifest.json").read_text())
        self.assertFalse(any("evaluation" in p or "datasets/" in p for p in sources))
        for path in self.output.rglob("*.json"):
            self.assertNotIn("EVALUATOR_SENTINEL", path.read_text())
        hashes = json.loads((self.output / "artifact-manifest.json").read_text())
        for path, expected in hashes.items():
            self.assertEqual(shared.digest(self.output / path), expected)
        report = json.loads((self.output / "report.json").read_text())
        self.assertEqual(report["counts"]["selected"], 1)
        self.assertEqual(report["counts"]["valid"], 1)
        self.assertFalse(report["evaluator_loaded"])

    def test_changed_incident_rejected_before_runtime_or_output(self):
        path = self.release / "incidents/inputs/TEST-6.json"
        path.write_text("{}")
        with self.assertRaisesRegex(ValueError, "Incident checksum mismatch"):
            self.invoke()
        self.assertFalse(self.output.exists())

    def test_changed_manifest_is_rejected(self):
        (self.release / "manifest.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "manifest checksum mismatch"):
            self.invoke()

    def test_changed_model_rejected(self):
        self.artifact.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            self.invoke()
        self.assertFalse(self.output.exists())

    def test_preflight_does_not_start_runtime_or_create_run(self):
        with patch.object(Runtime, "__enter__", side_effect=AssertionError("started")):
            self.assertEqual(self.invoke(check=True), 0)
        self.assertFalse(self.output.exists())

    def test_unknown_case_and_existing_run_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown"):
            self.invoke(case="missing")
        self.invoke()
        before = (self.output / "report.json").read_bytes()
        with self.assertRaises(FileExistsError):
            self.invoke()
        self.assertEqual((self.output / "report.json").read_bytes(), before)

    def test_recognized_failures_have_valid_error_traces_and_batch_continues(self):
        responses = ["not json", InvalidOutput("bad response"), RunnerTimeout("timeout"),
                     RunnerUnavailable("unavailable")]
        valid = json.dumps({"summary": "Controlled", "triage_verdict": "undetermined",
                            "risk_level": "low", "mitre_techniques": [], "recommended_actions": []})
        with patch.object(Generator, "responses", responses + [valid] * 3):
            self.assertEqual(self.invoke(all_cases=True), 1)
        report = json.loads((self.output / "report.json").read_text())
        self.assertEqual(report["counts"], {"available": 7, "selected": 7, "attempted": 7,
                                         "valid": 3, "failed": 4, "not_attempted": 0})
        for path in self.output.glob("*/trace.json"):
            contract_validators(shared.ROOT)["trace"].validate(json.loads(path.read_text()))
        self.assertEqual(len(list(self.output.glob("*/failure.json"))), 4)

    def test_startup_failure_is_saved_without_attempted_success(self):
        with patch.object(Runtime, "__enter__", side_effect=RunnerUnavailable("controlled failure")):
            with self.assertRaises(RunnerUnavailable):
                self.invoke()
        report = json.loads((self.output / "report.json").read_text())
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["counts"]["attempted"], 0)
        self.assertEqual(report["counts"]["not_attempted"], 1)

    def test_incident_symlink_is_rejected(self):
        path = self.release / "incidents/inputs/TEST-6.json"
        other = self.root / "outside.json"
        other.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(other)
        with self.assertRaisesRegex(ValueError, "symlinks"):
            self.invoke()

    def test_launcher_identity_is_explicit_and_validated(self):
        with patch.dict(os.environ, {"CYBERSOC_RUN_COMMIT": "b" * 40, "CYBERSOC_RUN_DIRTY": "true"}):
            self.assertEqual(shared.git_state(), ("b" * 40, True))
        with patch.dict(os.environ, {"CYBERSOC_RUN_COMMIT": "unknown", "CYBERSOC_RUN_DIRTY": "false"}):
            with self.assertRaisesRegex(ValueError, "Git identity"):
                shared.git_state()

    def test_output_cannot_modify_frozen_release(self):
        self.output = self.release / "new-run"
        with self.assertRaisesRegex(ValueError, "frozen release"):
            self.invoke()
        self.assertFalse(self.output.exists())

    def test_source_annotations_bind_to_incident_hash_and_scope(self):
        incident = {"incident_id": "CASE", "entities": [{"type": "host", "value": "host"},
                    {"type": "ip", "value": "198.51.100.4"}, {"type": "ip", "value": "192.0.2.5"}]}
        role = {"incident_sha256": "a" * 64, "target": "host", "source_ip": "198.51.100.4",
                "destination_ip": "192.0.2.5", "service": "ssh"}
        policy = {"targets": ["host"], "source_role_annotations": {"CASE": role}}
        manifest = {"assets": [{"path": "incidents/inputs/CASE.json", "sha256": "a" * 64}]}
        scoped = shared.incident_policy(policy, incident, manifest)
        self.assertEqual(scoped["network_scope"]["source_ip"], "198.51.100.4")
        self.assertNotIn("source_role_annotations", scoped)
        self.assertEqual(policy["targets"], ["host"])
        role["incident_sha256"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "annotation"):
            shared.incident_policy(policy, incident, manifest)

    def test_unannotated_cases_have_no_eligible_targets(self):
        policy = json.loads(self.policy.read_text())
        scoped = shared.incident_policy(policy, {"incident_id": "UNANNOTATED"}, {})
        self.assertEqual(scoped["targets"], [])
        self.assertIsNone(scoped["network_scope"])


if __name__ == "__main__":
    unittest.main()

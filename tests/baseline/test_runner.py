"""Behavioral checks; controlled outputs are not model performance evidence."""

from copy import deepcopy
import json
from pathlib import Path
import time
import unittest

from ai.baseline.runner import BaselineRunner, InvalidOutput, RunnerTimeout, strict_json
from ai.baseline.api_adapter import APIAdapter

ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class Generator:
    def __init__(self, decision):
        self.text = json.dumps(decision)
        self.calls = []

    def generate(self, messages, schema, deadline):
        self.calls.append(deepcopy(messages))
        return self.text, {"input_tokens": 100, "output_tokens": 20}


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.incident = read("datasets/evaluation/soc-eval-v1/inputs/P01.json")
        self.policy = read("datasets/evaluation/soc-eval-v1/protocol/runner-policy.json")
        self.decision = {"summary": "Suspicious authentication activity; success not established.",
            "triage_verdict": "undetermined", "risk_level": "medium",
            "mitre_techniques": [], "recommended_actions": []}

    def core(self, decision=None):
        return BaselineRunner(Generator(decision or self.decision), ROOT)

    def proposal(self):
        return {"target": next(e["value"] for e in self.incident["entities"] if e["type"] == "host"),
                "source_ip": next(e["value"] for e in self.incident["entities"] if e["type"] == "ip"),
                "reason": "Repeated failures", "expected_effect": "Limit test-source SSH",
                "risks": "May block authorized traffic", "rollback_plan": "Expire test rule"}

    def test_success_contract_and_identity(self):
        runner = self.core()
        result, _ = runner.investigate(self.incident, self.policy,
            investigation_id="INV-known", trace_id="TRC-known")
        runner.checks["investigation-result"].validate(result)
        self.assertEqual(result["incident_id"], self.incident["incident_id"])
        self.assertEqual(result["investigation_id"], "INV-known")
        self.assertEqual(result["trace_id"], "TRC-known")
        self.assertEqual(result["mode"], "no_rag")
        self.assertEqual(result["evidence"], [])

    def test_prompt_is_input_only_and_does_not_mutate_input(self):
        runner = self.core()
        original = deepcopy(self.incident)
        runner(self.incident, self.policy)
        user = strict_json(runner.generator.calls[0][1]["content"])
        self.assertEqual(user["untrusted_incident"], original)
        self.assertNotIn("labels", user)
        self.assertNotIn("context", user)
        self.assertEqual(self.incident, original)

    def test_proposal_uses_policy_ids_and_no_execution(self):
        self.decision["recommended_actions"] = [self.proposal()]
        runner = self.core()
        a = runner(self.incident, self.policy)["recommended_actions"][0]
        b = runner(self.incident, self.policy)["recommended_actions"][0]
        self.assertNotEqual(a["idempotency_key"], b["idempotency_key"])
        self.assertEqual(a["status"], "proposed")
        self.assertTrue(a["requires_approval"])
        self.assertEqual(a["arguments"]["duration_seconds"], 300)
        self.assertNotIn("approval", a)

    def test_unobserved_source_and_target_rejected(self):
        for field, value in (("source_ip", "192.0.2.254"), ("target", "unseen-host")):
            with self.subTest(field=field):
                action = self.proposal()
                action[field] = value
                self.decision["recommended_actions"] = [action]
                with self.assertRaises(InvalidOutput):
                    self.core()(self.incident, self.policy)

    def test_model_cannot_supply_approval_ids_or_extra_fields(self):
        for field in ("status", "action_id", "requires_approval"):
            with self.subTest(field=field):
                action = self.proposal()
                action[field] = "approved"
                self.decision["recommended_actions"] = [action]
                with self.assertRaises(InvalidOutput):
                    self.core()(self.incident, self.policy)

    def test_duplicate_proposal_rejected(self):
        self.decision["recommended_actions"] = [self.proposal(), self.proposal()]
        with self.assertRaises(InvalidOutput):
            self.core()(self.incident, self.policy)

    def test_no_json_repair_or_synthetic_success(self):
        for text in ('not json', '```json\n{}\n```', '{"summary":"a","summary":"b"}',
                     '{}', '{"risk_level":NaN}', '[]'):
            with self.subTest(text=text):
                runner = self.core()
                runner.generator.text = text
                with self.assertRaises(InvalidOutput) as error:
                    runner(self.incident, self.policy)
                self.assertEqual(str(error.exception), "Model output failed validation")

    def test_policy_rejects_execution_and_expired_deadline_skips_inference(self):
        runner = self.core()
        self.policy["execution_enabled"] = True
        with self.assertRaises(ValueError):
            runner(self.incident, self.policy)
        self.assertEqual(len(runner.generator.calls), 0)
        with self.assertRaises(RunnerTimeout):
            runner.investigate(self.incident, self.policy, deadline=time.monotonic() - 1)

    def test_model_cannot_override_incident_identity(self):
        self.decision["incident_id"] = "INC-override"
        with self.assertRaises(InvalidOutput):
            self.core()(self.incident, self.policy)

    def test_api_adapter_constructs_without_unmerged_backend(self):
        adapter = APIAdapter(self.core(), self.policy, {
            **{k: "test" for k in ("model", "prompt", "dataset", "configuration")},
            "commit": "a" * 40})
        self.assertEqual(adapter.policy, self.policy)

    def test_api_adapter_preserves_backend_ids_and_maps_timeout(self):
        from types import ModuleType, SimpleNamespace
        from unittest.mock import patch

        module = ModuleType("backend.runner")
        module.RunnerTimeout = type("APITimeout", (Exception,), {})
        module.RunnerUnavailable = type("APIUnavailable", (Exception,), {})
        adapter = APIAdapter(self.core(), self.policy, {
            **{k: "test" for k in ("model", "prompt", "dataset", "configuration")},
            "commit": "a" * 40})
        request = SimpleNamespace(incident=self.incident, investigation_id="INV-api",
                                  trace_id="TRC-api", deadline_monotonic=time.monotonic()+10)
        with patch.dict("sys.modules", {"backend.runner": module}):
            result = adapter.run(request)
            self.assertEqual(result["investigation_id"], "INV-api")
            self.assertEqual(result["trace_id"], "TRC-api")
            request.deadline_monotonic = time.monotonic() - 1
            with self.assertRaises(module.RunnerTimeout):
                adapter.run(request)


if __name__ == "__main__":
    unittest.main()

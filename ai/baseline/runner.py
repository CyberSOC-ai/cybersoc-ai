"""Input-only baseline core, independent of evaluator labels and the HTTP API."""

from copy import deepcopy
import ipaddress
import json
from pathlib import Path
import time
from uuid import uuid4

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


class RunnerUnavailable(Exception):
    """Configured inference dependency is unavailable."""


class RunnerTimeout(Exception):
    """Inference exceeded its monotonic deadline."""


class InvalidOutput(Exception):
    """Candidate output is malformed or violates the contract/policy."""

    def __init__(self, message, *, stage="generation"):
        super().__init__(message)
        self.stage = stage


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result

    def constant(_):
        raise ValueError("Nonfinite JSON number")

    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)


def contract_validators(root):
    def reject(uri):
        raise ValueError("Unregistered schema reference")

    schemas = [json.loads(p.read_text(encoding="utf-8"))
               for p in (Path(root) / "backend/contracts/v1").glob("*.schema.json")]
    registry = Registry(retrieve=reject).with_resources(
        (s["$id"], Resource.from_contents(s)) for s in schemas)
    return {s["title"]: Draft202012Validator(s, registry=registry,
                                            format_checker=FormatChecker()) for s in schemas}


def decision_schema():
    """Model chooses findings; trusted code owns record identity and permissions."""
    action = {"type": "object", "properties": {
        name: {"type": "string", "minLength": 1, "maxLength": 2000}
        for name in ("target", "source_ip", "reason", "expected_effect", "risks", "rollback_plan")}}
    action.update(required=list(action["properties"]), additionalProperties=False)
    props = {
        "summary": {"type": "string", "minLength": 1, "maxLength": 8000},
        "triage_verdict": {"enum": ["true_positive", "false_positive", "undetermined"]},
        "risk_level": {"enum": ["informational", "low", "medium", "high", "critical"]},
        "mitre_techniques": {"type": "array", "maxItems": 100, "uniqueItems": True,
                             "items": {"type": "string", "pattern": r"^T[0-9]{4}(\.[0-9]{3})?$"}},
        "recommended_actions": {"type": "array", "items": action, "maxItems": 20},
    }
    return {"type": "object", "properties": props, "required": list(props),
            "additionalProperties": False}


class BaselineRunner:
    """Callable pilot interface; generator.generate returns text and measurements.

    No model, tokenizer or dataset downloads occur here. Configuration and model
    loading are explicit setup work outside request handlers.
    """

    def __init__(self, generator, root, *, timeout_seconds=180):
        if not 0 < timeout_seconds <= 3600:
            raise ValueError("Invalid timeout")
        self.generator = generator
        self.checks = contract_validators(root)
        self.prompt = (Path(__file__).with_name("prompt.txt")).read_text(encoding="utf-8")
        self.timeout_seconds = timeout_seconds
        self.last_measurement = None
        self.last_output = None
        self.last_messages = None

    def __call__(self, incident, policy):
        return self.investigate(incident, policy)[0]

    def investigate(self, incident, policy, *, investigation_id=None, trace_id=None, deadline=None):
        self.last_measurement = None
        self.last_output = None
        self.last_messages = None
        started = time.monotonic()
        deadline = min(deadline, started + self.timeout_seconds) if deadline is not None else started + self.timeout_seconds
        if time.monotonic() >= deadline:
            raise RunnerTimeout("Inference deadline exceeded")
        self.checks["incident"].validate(incident)
        policy = deepcopy(policy)
        self._check_policy(policy)
        messages = [
            {"role": "system", "content": self.prompt},
            {"role": "user", "content": json.dumps({"untrusted_incident": incident,
             "fixed_proposal_policy": policy, "required_output": decision_schema()}, ensure_ascii=False)},
        ]
        self.last_messages = deepcopy(messages)
        text, measurement = self.generator.generate(messages, decision_schema(), deadline)
        self.last_output = text
        self.last_measurement = deepcopy(measurement)
        if time.monotonic() >= deadline:
            raise RunnerTimeout("Inference deadline exceeded")
        stage = "json_parsing"
        try:
            if not isinstance(text, str) or len(text.encode("utf-8")) > 131072:
                raise ValueError("Output size")
            candidate = strict_json(text)
            stage = "decision_schema"
            Draft202012Validator(decision_schema()).validate(candidate)
            stage = "proposal_policy"
            result = {
                "schema_version": "1.0.0", "incident_id": incident["incident_id"],
                "investigation_id": investigation_id or "INV-" + uuid4().hex,
                "trace_id": trace_id or "TRC-" + uuid4().hex, "mode": "no_rag",
                "status": "ok", "evidence": [],
                **{k: candidate[k] for k in ("summary", "triage_verdict", "risk_level", "mitre_techniques")},
                "recommended_actions": [self._action(a, incident, policy)
                                        for a in candidate["recommended_actions"]],
            }
            keys = [(a["target"], a["arguments"]["source_ip"]) for a in result["recommended_actions"]]
            if len(keys) != len(set(keys)):
                raise ValueError("Duplicate proposal")
            stage = "result_contract"
            self.checks["investigation-result"].validate(result)
        except Exception as exc:
            # Do not disclose candidate output, incident text or schema error values.
            raise InvalidOutput("Model output failed validation", stage=stage) from exc
        measurement = {**measurement, "pipeline_seconds": time.monotonic() - started}
        return result, measurement

    @staticmethod
    def _check_policy(policy):
        if (policy.get("execution_enabled") is not False or policy.get("action_type") != "block_ip"
                or policy.get("response_defaults") != {"schema_version": "1.0.0", "revision": 1,
                    "requires_approval": True, "status": "proposed"}):
            raise ValueError("Only disabled-execution proposal policy is supported")
        for name in ("environment_id", "policy_version", "target_inventory_revision"):
            if not isinstance(policy.get(name), str) or not policy[name]:
                raise ValueError("Missing policy identity")
        if not isinstance(policy.get("targets"), list) or not all(isinstance(t, str) for t in policy["targets"]):
            raise ValueError("Invalid target policy")
        scope = policy["ssh_containment"]
        duration = scope["default_duration_seconds"]
        bounds = scope["duration_seconds"]
        if (type(duration) is not int or not 1 <= bounds["min"] <= duration <= bounds["max"] <= 3600
                or scope["port"] != 22 or scope["protocol"] != "tcp"):
            raise ValueError("Invalid containment scope")

    @staticmethod
    def _action(action, incident, policy):
        hosts = {e["value"] for e in incident["entities"] if e["type"] == "host"}
        ips = {str(ipaddress.ip_address(e["value"])) for e in incident["entities"] if e["type"] == "ip"}
        source = str(ipaddress.IPv4Address(action["source_ip"]))
        if action["target"] not in hosts or action["target"] not in policy["targets"] or source not in ips:
            raise ValueError("Unobserved or unregistered proposal target")
        return {
            **policy["response_defaults"], "action_id": "ACT-" + uuid4().hex,
            "incident_id": incident["incident_id"], "idempotency_key": "KEY-" + uuid4().hex,
            "action_type": "block_ip", "target": action["target"],
            **{k: policy[k] for k in ("environment_id", "target_inventory_revision", "policy_version")},
            "arguments": {"source_ip": source, "port": 22, "protocol": "tcp",
                          "duration_seconds": policy["ssh_containment"]["default_duration_seconds"]},
            **{k: action[k] for k in ("reason", "expected_effect", "risks", "rollback_plan")},
        }

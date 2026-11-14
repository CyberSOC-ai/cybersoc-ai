"""Shared strict decision/result contracts and sanitized inference exceptions."""

import json
from pathlib import Path

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

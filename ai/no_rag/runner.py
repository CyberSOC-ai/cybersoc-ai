"""Incident-only prompt composition and validated No-RAG investigations."""

from copy import deepcopy
import json
from pathlib import Path
import time
from uuid import uuid4

from jsonschema import Draft202012Validator

from ai.runtime.contracts import (InvalidOutput, RunnerTimeout, contract_validators,
                                  decision_schema, strict_json)
from ai.runtime.policy import ProposalPolicy


class BaselineRunner(ProposalPolicy):
    """Callable pilot interface; generator.generate returns text and measurements.

    No model, tokenizer or dataset downloads occur here. Configuration and model
    loading are explicit setup work outside request handlers.
    """

    def __init__(self, generator, root, *, timeout_seconds=180, require_source_roles=False):
        if not 0 < timeout_seconds <= 3600:
            raise ValueError("Invalid timeout")
        self.generator = generator
        self.checks = contract_validators(root)
        self.prompt = (Path(__file__).with_name("prompt.txt")).read_bytes().decode("utf-8")
        self.timeout_seconds = timeout_seconds
        self.require_source_roles = require_source_roles
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
            if self.require_source_roles:
                self._check_source_roles(candidate["recommended_actions"], incident, policy)
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

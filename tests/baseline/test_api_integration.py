"""Runs against actual S1-T04 when available; never vendors its implementation."""

import importlib.util
import json
import os
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from ai.baseline.api_adapter import compose_api
from ai.baseline.runner import BaselineRunner, RunnerTimeout, RunnerUnavailable

ROOT = Path(__file__).resolve().parents[2]
API_AVAILABLE = importlib.util.find_spec("backend.app") is not None


class ControlledGenerator:
    """Only software plumbing; real-model smoke evidence is recorded separately."""
    def __init__(self, mode="valid"):
        self.mode = mode

    def generate(self, messages, schema, deadline):
        if self.mode == "timeout":
            raise RunnerTimeout()
        if self.mode == "unavailable":
            raise RunnerUnavailable()
        if self.mode == "invalid":
            return "not JSON", {}
        return json.dumps({"summary": "Controlled integration test only",
            "triage_verdict": "undetermined", "risk_level": "low",
            "mitre_techniques": [], "recommended_actions": []}), {}


@unittest.skipUnless(API_AVAILABLE and hasattr(os, "getuid"),
                     "Requires S1-T04 backend and POSIX runtime; use the Linux integration environment")
class APIIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.incident = json.loads((ROOT / "datasets/evaluation/soc-eval-v1/inputs/P01.json").read_text())
        self.policy = json.loads((ROOT / "datasets/evaluation/soc-eval-v1/protocol/runner-policy.json").read_text())
        self.versions = {"model": "controlled-test", "prompt": "controlled-test",
                         "dataset": "not_applicable", "configuration": "controlled-test", "commit": "a"*40}

    def client(self, mode="valid"):
        from fastapi.testclient import TestClient

        core = BaselineRunner(ControlledGenerator(mode), ROOT)
        app = compose_api(core, self.policy, self.versions, self.temp.name)
        client = TestClient(app)
        client.__enter__()
        self.addCleanup(client.__exit__, None, None, None)
        return client

    def test_real_backend_persists_correlated_result_and_trace(self):
        from backend.repository import SQLiteRepository
        from backend.validation import validate

        client = self.client()
        self.assertEqual(client.post("/incidents", json=self.incident).status_code, 201)
        self.assertEqual(client.post("/incidents", json=self.incident).status_code, 200)
        response = client.post(f"/incidents/{self.incident['incident_id']}/investigate")
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        validate("investigation-result", result)
        repo = SQLiteRepository(Path(self.temp.name))
        with sqlite3.connect(repo.path) as db:
            stored_result, stored_trace = db.execute("SELECT result, trace FROM investigations").fetchone()
        self.assertEqual(json.loads(stored_result), result)
        trace = json.loads(stored_trace)
        validate("trace", trace)
        self.assertEqual(trace["trace_id"], result["trace_id"])
        self.assertEqual(trace["workflow"], "baseline")
        self.assertEqual(trace["versions"], self.versions)

    def test_error_mapping_and_failure_persistence(self):
        from backend.repository import SQLiteRepository

        for mode, expected in (("timeout", 504), ("unavailable", 503), ("invalid", 502)):
            with self.subTest(mode=mode):
                # Each client uses its own core but retains the same local repository.
                client = self.client(mode)
                client.post("/incidents", json=self.incident)
                response = client.post(f"/incidents/{self.incident['incident_id']}/investigate")
                self.assertEqual(response.status_code, expected, response.text)
                self.assertEqual(response.json()["status"], "error")
                self.assertEqual(response.json()["recommended_actions"], [])
        repo = SQLiteRepository(Path(self.temp.name))
        with sqlite3.connect(repo.path) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM investigations").fetchone()[0], 3)

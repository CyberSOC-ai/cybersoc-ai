"""Compatibility checks preserve evidence and reject changed local artifacts."""

import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from jsonschema import ValidationError

from ai.baseline import smoke


class Runtime:
    def __init__(self, *args):
        self.process = SimpleNamespace(poll=lambda: 0)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class Generator:
    value = '{"status":"ready"}'

    def __init__(self, **kwargs):
        pass

    def generate(self, messages, schema, deadline):
        return self.value, {"output_tokens": 5}


class SmokeTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        binary = self.root / "controlled.bin"
        binary.write_bytes(b"controlled fixture; never executed")
        self.config = self.root / "config.json"
        self.config.write_text(json.dumps({
            "model_file": str(binary), "runtime_executable": str(binary),
            "model_sha256": smoke.digest(binary), "runtime_sha256": smoke.digest(binary),
            "port": 8087, "max_input_tokens": 100, "context_tokens": 512, "seed": 42,
        }))

    def invoke(self, output):
        with patch.object(smoke, "LocalRuntime", Runtime), \
                patch.object(smoke, "LlamaServer", Generator), \
                patch.object(smoke.subprocess, "run", return_value=SimpleNamespace(
                    stdout="controlled version", stderr="")):
            return smoke.smoke(self.config, output)

    def test_changed_artifact_rejected_before_output_or_startup(self):
        (self.root / "controlled.bin").write_bytes(b"changed")
        with patch.object(smoke, "LocalRuntime") as runtime:
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                smoke.smoke(self.config, self.root / "run")
            runtime.assert_not_called()
        self.assertFalse((self.root / "run").exists())

    def test_invalid_output_remains_a_failure_and_run_is_not_overwritten(self):
        output = self.root / "run"
        with patch.object(Generator, "value", '{"status":"wrong"}'):
            with self.assertRaises(ValidationError):
                self.invoke(output)
        report = json.loads((output / "report.json").read_text())
        self.assertEqual(report["status"], "failed")
        self.assertTrue(report["runtime_process_stopped"])
        before = (output / "report.json").read_bytes()
        with self.assertRaises(FileExistsError):
            self.invoke(output)
        self.assertEqual((output / "report.json").read_bytes(), before)

    def test_success_is_a_smoke_not_an_incident_result(self):
        report = self.invoke(self.root / "run")
        self.assertEqual(report["output"], {"status": "ready"})
        self.assertFalse(report["data_release_evaluated"])
        self.assertEqual(report["configuration"]["max_output_tokens"], 32)


if __name__ == "__main__":
    unittest.main()

"""Exercise artifact persistence and all-attempted counting without real models."""

from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from ai.baseline import run


class FakeRuntime:
    command = ["controlled-test-runtime"]

    def __init__(self, *args):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def peak_memory_bytes(self):
        return None


class FakeGenerator:
    text = json.dumps({"summary": "Controlled software fixture, not a model run.",
        "triage_verdict": "undetermined", "risk_level": "low", "mitre_techniques": [],
        "recommended_actions": []})
    last_formatted_prompt = "controlled-test-prompt"

    def __init__(self, **kwargs):
        pass

    def generate(self, messages, schema, deadline):
        if "labels" in json.loads(messages[1]["content"]):
            raise AssertionError("Evaluator labels leaked into runner")
        return self.text, {"client_seconds": 1, "output_tokens": 10}


class CLITests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        artifact = self.folder / "controlled.bin"
        artifact.write_bytes(b"not executable: controlled test only")
        self.config = self.folder / "config.json"
        self.config.write_text(json.dumps({
            "model_file": str(artifact), "model_sha256": run.sha(artifact),
            "runtime_executable": str(artifact), "runtime_sha256": run.sha(artifact),
            "runtime_version": "controlled-test", "artifact_repo": "controlled-test",
            "artifact_revision": "test-v1", "publisher_id": "controlled-test",
            "upstream_revision": "test-v1", "port": 8087, "context_tokens": 4096,
            "max_input_tokens": 3072, "max_output_tokens": 512, "seed": 42,
            "quantization": "controlled-test", "timeout_seconds": 2}), encoding="utf-8")
        self.output = self.folder / "run"

    def invoke(self):
        argv = ["run", "--config", str(self.config), "--output", str(self.output), "--limit", "1"]
        with patch("sys.argv", argv), patch.object(run, "LocalRuntime", FakeRuntime), \
                patch.object(run, "LlamaServer", FakeGenerator), \
                patch.object(run, "git_state", return_value=("a" * 40, True)), \
                redirect_stdout(StringIO()):
            return run.main()

    def test_partial_run_counts_and_saved_hashes(self):
        self.assertEqual(self.invoke(), 0)
        scores = json.loads((self.output / "scores.json").read_text())
        self.assertEqual(scores["counts"]["attempted"], 1)
        self.assertEqual(scores["counts"]["not_attempted"], 13)
        self.assertEqual(scores["counts"]["valid"], 1)
        artifacts = json.loads((self.output / "artifact-manifest.json").read_text())
        for name, digest in artifacts.items():
            self.assertEqual(run.sha(self.output / name), digest)
        self.assertIn("model-outputs.json", artifacts)
        self.assertIn("rendered-prompts.json", artifacts)
        with self.assertRaises(FileExistsError):
            self.invoke()

    def test_failed_output_is_preserved_and_counted(self):
        with patch.object(FakeGenerator, "text", "not JSON"):
            self.assertEqual(self.invoke(), 1)
        scores = json.loads((self.output / "scores.json").read_text())
        self.assertEqual(scores["counts"]["attempted"], 1)
        self.assertEqual(scores["counts"]["failed"], 1)
        self.assertIn("not JSON", (self.output / "model-outputs.json").read_text())
        values = json.loads((self.output / "measurements.json").read_text())
        self.assertEqual(next(iter(values.values()))["rejection_stage"], "json_parsing")

    def test_checksum_mismatch_prevents_loading(self):
        config = json.loads(self.config.read_text())
        Path(config["model_file"]).write_bytes(b"changed artifact")
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            self.invoke()
        self.assertFalse(self.output.exists())

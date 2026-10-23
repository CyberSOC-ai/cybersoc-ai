"""Dirty evaluator changes must be reproducible, not just the inference code."""

import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from ai.baseline.provenance import snapshot_sources


class ProvenanceTests(unittest.TestCase):
    def test_locally_changed_evaluator_is_copied_and_hashed(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            evaluator = root / "ai/evaluation/scoring.py"
            evaluator.parent.mkdir(parents=True)
            evaluator.write_bytes(b"# locally modified evaluator\r\nvalue = 42\r\n")
            output = Path(temporary) / "run"
            output.mkdir()
            manifest = snapshot_sources(root, output)
            copied = output / "source/ai/evaluation/scoring.py"
            self.assertEqual(copied.read_bytes(), evaluator.read_bytes())
            self.assertEqual(manifest["ai/evaluation/scoring.py"], hashlib.sha256(copied.read_bytes()).hexdigest())
            evaluator.write_bytes(b"# changed after snapshot")
            self.assertIn(b"value = 42", copied.read_bytes())

    def test_unrelated_credentials_and_ignored_artifacts_are_not_copied(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            root.mkdir()
            (root / ".env").write_text("synthetic secret placeholder")
            (root / ".local").mkdir()
            (root / ".local/private.json").write_text("{}")
            output = Path(temporary) / "run"
            output.mkdir()
            self.assertEqual(snapshot_sources(root, output), {})
            self.assertEqual(list((output / "source").iterdir()), [])

"""Prevent investigation modes from acquiring each other's private dependencies."""

from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]


class PackageBoundaryTests(unittest.TestCase):
    def assert_isolated_import(self, module, forbidden):
        script = ("import importlib,sys; importlib.import_module(" + repr(module) + "); "
                  "assert not any(name == prefix or name.startswith(prefix+'.') "
                  "for prefix in " + repr(forbidden) + " for name in sys.modules)")
        subprocess.run([sys.executable, '-B', '-c', script], cwd=ROOT, check=True,
                       capture_output=True, text=True, timeout=15)

    def test_rag_does_not_import_no_rag_or_evaluation(self):
        self.assert_isolated_import('rag.vector.generation', ['ai.no_rag', 'ai.evaluation'])

    def test_no_rag_does_not_import_retrieval_or_evaluation(self):
        self.assert_isolated_import('ai.no_rag.run', ['rag', 'ai.evaluation'])

    def test_runtime_does_not_import_either_investigation_mode(self):
        self.assert_isolated_import('ai.runtime.smoke', ['ai.no_rag', 'rag', 'ai.evaluation'])

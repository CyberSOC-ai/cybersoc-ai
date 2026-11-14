"""Menu behavior and pipeline delegation with controlled outputs; no model execution."""

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from ai.no_rag import run as shared, terminal


class TerminalTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.output = Path(temp.name) / "session"
        self.inputs = [{"incident_id": "B0-TEST-001", "description": "Observed failures only."},
                       {"incident_id": "B0-TEST-002", "description": "Other observations."}]

    def invoke(self, commands, run=None):
        buffer = StringIO()
        with patch.object(shared, "release_inputs", return_value=(self.inputs, {})), \
                patch.object(shared, "run", side_effect=run) as pipeline, \
                patch("builtins.input", side_effect=commands), redirect_stdout(buffer):
            status = terminal.session("config.json", "release", self.output)
        return status, buffer.getvalue(), pipeline

    def successful_run(self, config, release, output, *, case):
        folder = output / case
        folder.mkdir(parents=True)
        shared.save(output / "report.json", {"status": "completed"})
        shared.save(folder / "result.json", {"summary": "No successful access established.",
            "triage_verdict": "undetermined", "risk_level": "medium", "mitre_techniques": [],
            "recommended_actions": []})
        shared.save(folder / "raw-output.json", "controlled raw answer")
        shared.save(folder / "trace.json", {"trace_id": "TRC-test"})
        return 0

    def test_browse_back_invalid_selection_and_quit_do_not_start_model(self):
        status, text, pipeline = self.invoke(["invalid", "0", "1", "i", "j", "t", "unknown", "b", "q"])
        self.assertEqual(status, 0)
        pipeline.assert_not_called()
        self.assertIn("Observed failures only.", text)
        self.assertIn("Run analysis first.", text)
        self.assertIn("Choose one of the listed numbers.", text)
        self.assertFalse(self.output.exists())

    def test_selected_case_runs_and_results_raw_answer_trace_can_be_read(self):
        status, text, pipeline = self.invoke(["2", "r", "j", "t", "q"], self.successful_run)
        self.assertEqual(status, 0)
        self.assertEqual(pipeline.call_args.kwargs, {"case": "B0-TEST-002"})
        self.assertIn("No successful access established.", text)
        self.assertIn("controlled raw answer", text)
        self.assertIn("TRC-test", text)
        self.assertIn("nothing executed", text)

    def test_repeated_analysis_uses_fresh_output_directories(self):
        self.invoke(["1", "r", "r", "q"], self.successful_run)
        self.assertEqual(len(list(self.output.glob("attempt-*"))), 2)

    def test_failed_inference_shows_failure_and_allows_return_to_menu(self):
        def failed(config, release, output, *, case):
            folder = output / case
            folder.mkdir(parents=True)
            shared.save(output / "report.json", {"status": "completed_with_failures"})
            shared.save(folder / "failure.json", {"code": "timeout"})
            return 1
        status, text, _ = self.invoke(["1", "r", "b", "q"], failed)
        self.assertEqual(status, 0)
        self.assertIn("timeout", text)
        self.assertNotIn("Assessment (contract-valid", text)

    def test_startup_failure_does_not_crash_menu(self):
        status, text, _ = self.invoke(["1", "r", "b", "q"], OSError("controlled details"))
        self.assertEqual(status, 0)
        self.assertIn("Analysis stopped: OSError", text)
        self.assertNotIn("controlled details", text)

    def test_eof_and_interrupt_exit_cleanly(self):
        self.assertEqual(self.invoke([EOFError()])[0], 0)
        self.assertEqual(self.invoke([KeyboardInterrupt()])[0], 0)
        self.assertEqual(self.invoke(["1", "r"], KeyboardInterrupt())[0], 130)

    def test_terminal_control_sequences_are_escaped(self):
        buffer = StringIO()
        with redirect_stdout(buffer):
            terminal.display("untrusted\x1b[2J\x07")
        self.assertNotIn("\x1b", buffer.getvalue())
        self.assertIn("\\u001b", buffer.getvalue())

    def test_cli_dispatch_and_incompatible_flags(self):
        with patch.object(terminal, "session", return_value=0) as session:
            self.assertEqual(shared.main(["--interactive", "--output", str(self.output)]), 0)
            session.assert_called_once()
        with patch("sys.stderr", StringIO()):
            for flags in (["--interactive", "--check"], ["--interactive", "--all"],
                          ["--interactive", "--case", "TEST"], ["--interactive"]):
                with self.assertRaises(SystemExit):
                    shared.main(flags)


if __name__ == "__main__":
    unittest.main()

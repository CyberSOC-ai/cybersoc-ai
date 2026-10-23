"""Real local HTTP transport bounds; no model/download involved."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import Thread
import time
import unittest
from unittest.mock import patch

from ai.baseline.llama_server import LlamaServer
from ai.baseline.runner import InvalidOutput, RunnerTimeout, RunnerUnavailable


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    mode = "ok"

    def log_message(self, *args):
        pass

    def handle(self):
        try:
            super().handle()
        except ConnectionError:
            pass  # Expected when a deadline test closes its client connection.

    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"]))
        if self.mode == "unavailable":
            self.send_error(503)
            return
        if self.path == "/apply-template":
            payload = {"prompt": "formatted prompt"}
        elif self.path == "/tokenize":
            payload = {"tokens": [1, 2, 3]}
        else:
            events = [{"content": "{}", "stop": False},
                      {"content": "", "stop": True, "stop_type": "limit" if self.mode == "limit" else "eos",
                       "timings": {"predicted_n": 2}}]
            body = b"".join(b"data: " + json.dumps(e).encode() + b"\n\n" for e in events)
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if self.mode == "stall":
                time.sleep(0.3)
            try:
                self.wfile.write(body)
            except OSError:
                pass
            return
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class TransportTests(unittest.TestCase):
    def setUp(self):
        Handler.mode = "ok"
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.client = LlamaServer(port=self.server.server_port)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def test_streamed_measurement_has_no_false_ttft(self):
        content, metrics = self.client.generate([], {}, time.monotonic() + 2)
        self.assertEqual(content, "{}")
        self.assertEqual(metrics["input_tokens"], 3)
        self.assertIsNone(metrics["ttft_seconds"])
        self.assertIsNotNone(metrics["time_to_first_content_chunk_seconds"])

    def test_generation_limit_is_failure(self):
        Handler.mode = "limit"
        with self.assertRaises(InvalidOutput):
            self.client.generate([], {}, time.monotonic() + 2)

    def test_unavailable_is_not_a_success(self):
        Handler.mode = "unavailable"
        with self.assertRaises(RunnerUnavailable):
            self.client.generate([], {}, time.monotonic() + 2)

    def test_deadline_bounds_stalled_response(self):
        Handler.mode = "stall"
        with self.assertRaises(RunnerTimeout):
            self.client.generate([], {}, time.monotonic() + 0.1)

    def test_input_budget_rejects_no_silent_truncation(self):
        self.client.max_input_tokens = 1
        with self.assertRaises(InvalidOutput):
            self.client.generate([], {}, time.monotonic() + 2)


class ResponseShapeTests(unittest.TestCase):
    def generate(self, path, record):
        responses = {"/apply-template": {"prompt": "controlled"}, "/tokenize": {"tokens": [1]},
                     "/completion": {"content": "{}", "stop": True, "timings": {"predicted_n": 2}}}
        responses[path] = record
        client = LlamaServer()
        with patch.object(client, "_request", side_effect=lambda p, *a, **k: iter([responses[p]])):
            return client.generate([], {}, time.monotonic() + 2)

    def test_malformed_completion_events_raise_recognized_failure(self):
        records = [[], None, "text", 1, {}, {"content": []}, {"stop": "true"},
            {"content": "{}", "stop": True, "timings": []},
            {"content": "{}", "stop": True, "timings": {"predicted_n": "2"}},
            {"content": "{}", "stop": True, "timings": {"predicted_n": True}},
            {"content": "{}", "stop": True, "timings": {"predicted_ms": float("nan")}},
            {"content": "{}", "stop": True, "truncated": "false"}]
        for record in records:
            with self.subTest(record=record), self.assertRaises(InvalidOutput):
                self.generate("/completion", record)

    def test_malformed_template_responses_raise_recognized_failure(self):
        for record in ([], None, {}, {"prompt": []}):
            with self.subTest(record=record), self.assertRaises(InvalidOutput):
                self.generate("/apply-template", record)

    def test_malformed_token_responses_raise_recognized_failure(self):
        for record in ([], None, {}, {"tokens": None}, {"tokens": "text"},
                       {"tokens": [True]}, {"tokens": [1.5]}, {"tokens": [-1]}):
            with self.subTest(record=record), self.assertRaises(InvalidOutput):
                self.generate("/tokenize", record)

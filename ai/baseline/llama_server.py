"""Bounded llama.cpp CPU/GPU server client using only loopback HTTP."""

import http.client
import json
import math
import socket
import time

from .runner import InvalidOutput, RunnerTimeout, RunnerUnavailable, strict_json


class LlamaServer:
    def __init__(self, *, port=8087, max_input_tokens=3072, max_output_tokens=512,
                 seed=42, context_tokens=4096):
        if (type(port) is not int or not 1024 <= port <= 65535
                or not 0 < max_input_tokens or not 0 < max_output_tokens
                or max_input_tokens + max_output_tokens > context_tokens):
            raise ValueError("Invalid inference bounds")
        self.port = port
        self.max_input_tokens = max_input_tokens
        self.max_output_tokens = max_output_tokens
        self.seed = seed
        self.last_formatted_prompt = None

    def _request(self, path, payload, deadline, *, stream=False):
        conn = http.client.HTTPConnection("127.0.0.1", self.port)
        try:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RunnerTimeout("Inference deadline exceeded")
            conn.timeout = remaining
            conn.request("POST", path, json.dumps(payload).encode("utf-8"),
                         {"Content-Type": "application/json"})
            connection_socket = conn.sock
            response = conn.getresponse()
            if response.status != 200:
                raise RunnerUnavailable("Inference server returned an error")
            buffer, total = b"", 0
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise RunnerTimeout("Inference deadline exceeded")
                # Deadlines bound each read, not only initial connection setup.
                if connection_socket is not None:
                    connection_socket.settimeout(remaining)
                chunk = response.read1(8192)
                if not chunk:
                    break
                total += len(chunk)
                if total > 2 * 1024 * 1024:
                    raise InvalidOutput("Inference response exceeds byte limit")
                buffer += chunk
                if stream:
                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        if line.startswith(b"data: "):
                            yield strict_json(line[6:].decode("utf-8"))
            if stream:
                if buffer.strip():
                    raise InvalidOutput("Incomplete inference stream")
            else:
                yield strict_json(buffer.decode("utf-8"))
        except (TimeoutError, socket.timeout) as exc:
            raise RunnerTimeout("Inference deadline exceeded") from exc
        except (OSError, http.client.HTTPException) as exc:
            raise RunnerUnavailable("Local inference server unavailable") from exc
        except (ValueError, UnicodeError) as exc:
            raise InvalidOutput("Invalid inference response") from exc
        finally:
            conn.close()

    def generate(self, messages, schema, deadline):
        self.last_formatted_prompt = None
        started = time.monotonic()
        try:
            template_record = next(self._request("/apply-template", {"messages": messages}, deadline), None)
            if not isinstance(template_record, dict) or not isinstance(template_record.get("prompt"), str):
                raise InvalidOutput("Invalid template response")
            template = template_record["prompt"]
            self.last_formatted_prompt = template
            token_record = next(self._request("/tokenize", {"content": template, "add_special": True}, deadline), None)
            tokens = token_record.get("tokens") if isinstance(token_record, dict) else None
            if not isinstance(tokens, list) or any(type(token) is not int or token < 0 for token in tokens):
                raise InvalidOutput("Invalid tokenization response")
            if len(tokens) > self.max_input_tokens:
                raise InvalidOutput("Input exceeds token budget; no silent truncation")
            payload = {"prompt": template, "json_schema": schema, "stream": True,
                       "n_predict": self.max_output_tokens, "temperature": 0,
                       "seed": self.seed, "cache_prompt": False, "n_keep": 0}
            content, final, first = [], None, None
            for event in self._request("/completion", payload, deadline, stream=True):
                if not isinstance(event, dict):
                    raise InvalidOutput("Invalid completion event")
                part = event.get("content", "")
                if not isinstance(part, str) or type(event.get("stop", False)) is not bool:
                    raise InvalidOutput("Invalid completion fields")
                if "truncated" in event and type(event["truncated"]) is not bool:
                    raise InvalidOutput("Invalid completion fields")
                if part and first is None:
                    first = time.monotonic() - started
                content.append(part)
                if event.get("stop"):
                    final = event
            if not final or final.get("stop_type") == "limit" or final.get("truncated"):
                raise InvalidOutput("Generation incomplete or token limit reached")
            elapsed = time.monotonic() - started
            timings = final.get("timings", {})
            if not isinstance(timings, dict):
                raise InvalidOutput("Invalid completion timings")
            predicted = timings.get("predicted_n", final.get("tokens_predicted"))
            if predicted is not None and (type(predicted) is not int or predicted < 0):
                raise InvalidOutput("Invalid output token count")
            if any(type(value) not in (int, float) or not math.isfinite(value) or value < 0
                   for value in timings.values()):
                raise InvalidOutput("Invalid completion timings")
            return "".join(content), {
                "client_seconds": elapsed, "time_to_first_content_chunk_seconds": first,
                "ttft_seconds": None, "input_tokens": len(tokens), "output_tokens": predicted,
                "output_tokens_per_client_second": predicted / elapsed if predicted is not None else None,
                "server_timings": timings, "cache_prompt": False,
            }
        except (KeyError, TypeError, OverflowError) as exc:
            raise InvalidOutput("Incomplete server response") from exc

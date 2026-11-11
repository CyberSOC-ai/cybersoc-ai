"""Check a pinned local model/runtime without loading incident or evaluation data."""

import argparse
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import file_digest
from importlib.metadata import version
import json
from pathlib import Path
import platform
import subprocess
import time

from jsonschema import Draft202012Validator

from .llama_server import LlamaServer
from .runner import strict_json
from .runtime import LocalRuntime

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = {"type": "object", "properties": {"status": {"enum": ["ready"]}},
          "required": ["status"], "additionalProperties": False}
MESSAGES = [
    {"role": "system", "content": "Respond only with the requested JSON object."},
    {"role": "user", "content": "Return an object with status set to ready."},
]


def digest(path):
    with Path(path).open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def verified_config(config_path):
    config = strict_json(Path(config_path).read_text(encoding="utf-8"))
    for key in ("model_file", "runtime_executable"):
        path = Path(config[key])
        if not path.is_absolute():
            path = ROOT / path
        expected = config["model_sha256" if key == "model_file" else "runtime_sha256"]
        if digest(path) != expected:
            raise ValueError(f"{key} checksum mismatch")
        config[key] = str(path.resolve())
    # This compatibility check deliberately uses a small CPU/output budget.
    config["threads"] = 2
    config["max_output_tokens"] = 32
    return config


def smoke(config_path, output):
    config = verified_config(config_path)
    # Check bounds before creating output or starting a child process.
    generator = LlamaServer(port=config["port"], max_input_tokens=config["max_input_tokens"],
                            max_output_tokens=32, context_tokens=config["context_tokens"],
                            seed=config["seed"])
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    report = {
        "purpose": "runtime_model_structured_output_smoke_only",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "configuration": config, "configuration_sha256": digest(config_path),
        "environment": {"python": platform.python_version(), "system": platform.system(),
                        "packages": {p: version(p) for p in ("httpx", "jsonschema")}},
        "messages": deepcopy(MESSAGES), "required_schema": deepcopy(SCHEMA),
        "data_release_evaluated": False, "status": "running",
    }
    started = time.monotonic()
    runtime = None
    try:
        checked = subprocess.run([config["runtime_executable"], "--version"], check=True,
                                 capture_output=True, text=True, timeout=10)
        (output / "runtime-version.txt").write_text(checked.stdout + checked.stderr,
                                                   encoding="utf-8")
        with LocalRuntime(config, output / "runtime.log") as runtime:
            report["startup_seconds"] = time.monotonic() - started
            raw, measurements = generator.generate(deepcopy(MESSAGES), deepcopy(SCHEMA),
                                                   time.monotonic() + 60)
            value = strict_json(raw)
            Draft202012Validator(SCHEMA).validate(value)
            report.update(status="passed", output=value, measurements=measurements)
    except Exception as exc:
        report.update(status="failed", failure_type=type(exc).__name__)
        raise
    finally:
        report["elapsed_seconds"] = time.monotonic() - started
        if runtime is not None:
            report["runtime_process_stopped"] = runtime.process.poll() is not None
        (output / "report.json").write_text(json.dumps(report, indent=2) + "\n",
                                            encoding="utf-8")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True,
                        help="New private run directory; never overwritten")
    args = parser.parse_args(argv)
    report = smoke(args.config, args.output)
    print(f"Qwen/runtime smoke: {report['status']} (no incident evaluation)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Explicit real-model smoke through the optional S1-T04 ASGI API and SQLite.

Run inside a POSIX environment with the backend available. No ports are published
and no HTTP client or model text can choose the configuration or imported code.
"""

import argparse
import hashlib
import json
from pathlib import Path
import platform
import shutil
import sqlite3
import sys
from tempfile import TemporaryDirectory

from .api_adapter import compose_api
from .llama_server import LlamaServer
from .runner import BaselineRunner
from .runtime import LocalRuntime


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend-root", type=Path, required=True)
    parser.add_argument("--backend-commit", required=True)
    parser.add_argument("--project-commit", required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    # A trusted, explicit local code snapshot only; this is not an API parameter.
    sys.path.insert(0, str(args.backend_root.resolve()))
    from fastapi.testclient import TestClient
    from backend.repository import SQLiteRepository
    from backend.validation import validate

    root = Path(__file__).resolve().parents[2]
    config = json.loads(args.config.read_text())
    if sha(config["model_file"]) != config["model_sha256"] or sha(config["runtime_executable"]) != config["runtime_sha256"]:
        raise ValueError("Configured model/runtime checksum mismatch")
    args.output.mkdir(parents=True, exist_ok=False)
    dataset = root / "datasets/evaluation/soc-eval-v1"
    incident = json.loads((dataset / "inputs/P01.json").read_text())
    policy = json.loads((dataset / "protocol/runner-policy.json").read_text())
    versions = {"model": config["artifact_repo"] + "@" + config["artifact_revision"],
        "prompt": "PRM-soc-triage-v1-" + sha(Path(__file__).with_name("prompt.txt")),
        "dataset": json.loads((dataset / "manifest.json").read_text())["dataset_version"],
        "configuration": "CFG-S1T03-" + sha(args.config), "commit": args.project_commit}
    record = {"kind": "local integration smoke, not benchmark", "synthetic_incident": True,
        "backend_commit": args.backend_commit, "versions": versions,
        "configuration": config, "python": sys.version, "platform": platform.platform(),
        "http_scope": "in-process ASGI TestClient; real model uses container loopback",
        "timeout_seconds": config["timeout_seconds"], "execution_status": "running"}
    save(args.output / "record.json", record)
    with TemporaryDirectory(prefix="s1t03-api-") as state:
        with LocalRuntime(config, args.output / "model-server.log"):
            core = BaselineRunner(LlamaServer(port=config["port"],
                max_input_tokens=config["max_input_tokens"], max_output_tokens=config["max_output_tokens"],
                seed=config["seed"], context_tokens=config["context_tokens"]), root,
                timeout_seconds=config["timeout_seconds"])
            app = compose_api(core, policy, versions, state, timeout_seconds=config["timeout_seconds"])
            with TestClient(app) as client:
                record["health"] = client.get("/health").json()
                created = client.post("/incidents", json=incident)
                repeated = client.post("/incidents", json=incident)
                result = client.post(f"/incidents/{incident['incident_id']}/investigate")
                record["http_statuses"] = {"ingest": created.status_code,
                    "duplicate": repeated.status_code, "investigate": result.status_code}
                save(args.output / "result.json", result.json())
                save(args.output / "record.json", record)
                if created.status_code != 201 or repeated.status_code != 200 or result.status_code != 200:
                    raise RuntimeError("Integration smoke failed; inspect saved local evidence")
                validate("investigation-result", result.json())
                with sqlite3.connect(SQLiteRepository(Path(state)).path) as db:
                    rows = db.execute("SELECT result, trace FROM investigations").fetchall()
                if len(rows) != 1:
                    raise RuntimeError("Unexpected persisted attempt count")
                stored, trace = map(json.loads, rows[0])
                validate("trace", trace)
                assert stored == result.json() and stored["trace_id"] == trace["trace_id"]
                assert trace["versions"] == versions and trace["workflow"] == "baseline"
                save(args.output / "trace.json", trace)
                save(args.output / "measurement.json", core.last_measurement)
                save(args.output / "model-output.json", core.last_output)
            shutil.copyfile(SQLiteRepository(Path(state)).path, args.output / "state.sqlite3")
    record["execution_status"] = "passed"
    save(args.output / "record.json", record)
    save(args.output / "artifact-manifest.json", {p.name: sha(p) for p in args.output.iterdir() if p.is_file()})
    print(json.dumps({"status": "passed", "http_statuses": record["http_statuses"],
                      "trace_persisted": True, "actions_executed": False}))


if __name__ == "__main__":
    main()

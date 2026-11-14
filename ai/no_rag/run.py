"""Incident-only No-RAG runs against the frozen shared-dev-v1 release."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import time
from uuid import uuid4

from ai.runtime.configuration import configuration
from ai.runtime.contracts import InvalidOutput, RunnerTimeout, RunnerUnavailable, strict_json
from ai.runtime.lifecycle import LocalRuntime
from ai.runtime.llama_server import LlamaServer
from ai.runtime.policy import incident_policy
from ai.runtime.provenance import ROOT, IMPLEMENTATION_ID, digest, git_state, save, utc
from ai.runtime.provenance import SOURCES as RUNTIME_SOURCES
from .runner import BaselineRunner

RELEASE_SHA256 = "8376256e0d5bfa6733fc6d045ffa42f23be779fe51a1d23a8fae0a79315ef88e"
POLICY = ROOT / "ai/runtime/configs/shared-dev-v1-policy.json"
SOURCES = RUNTIME_SOURCES + tuple(str(p.relative_to(ROOT)) for p in sorted(Path(__file__).parent.glob('*.py')))
SOURCES += ("ai/no_rag/prompt.txt", "infrastructure/run-no-rag.sh")


def release_inputs(release, checks):
    release = Path(release)
    manifest_path = release / "manifest.json"
    if manifest_path.is_symlink() or digest(manifest_path) != RELEASE_SHA256:
        raise ValueError("shared-dev-v1 manifest checksum mismatch")
    manifest = strict_json(manifest_path.read_text(encoding="utf-8"))
    paths = [a for a in manifest["assets"] if a["path"].startswith("incidents/inputs/")]
    if manifest["release_id"] != "shared-dev-v1" or len(paths) != 7:
        raise ValueError("Unexpected release or incident inventory")
    inputs, seen = [], set()
    for asset in sorted(paths, key=lambda a: a["path"]):
        relative = asset["path"]
        if not re.fullmatch(r"incidents/inputs/[A-Za-z0-9._-]+\.json", relative):
            raise ValueError("Invalid incident asset path")
        path = release / relative
        if path.resolve().parent != (release.resolve() / "incidents/inputs") or path.is_symlink():
            raise ValueError("Incident assets cannot follow symlinks")
        if digest(path) != asset["sha256"]:
            raise ValueError("Incident checksum mismatch")
        incident = strict_json(path.read_text(encoding="utf-8"))
        checks["incident"].validate(incident)
        iid = incident["incident_id"]
        if iid in seen or path.stem != iid:
            raise ValueError("Duplicate or mismatched incident identity")
        seen.add(iid)
        inputs.append(incident)
    return inputs, manifest


def snapshot(output):
    paths = [ROOT / p for p in SOURCES]
    paths.extend(sorted((ROOT / "backend/contracts/v1").glob("*.schema.json")))
    hashes = {}
    for path in paths:
        if path.is_symlink():
            raise ValueError("Execution sources cannot be symlinks")
        relative = path.relative_to(ROOT)
        target = output / "source" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
        hashes[relative.as_posix()] = digest(target)
    save(output / "source-manifest.json", hashes)


def run(config_path, release, output, *, case="B0-LNX-SSH-001", all_cases=False, check=False):
    config = configuration(config_path)
    generator = LlamaServer(port=config["port"], max_input_tokens=config["max_input_tokens"],
        max_output_tokens=config["max_output_tokens"], context_tokens=config["context_tokens"],
        seed=config["seed"])
    runner = BaselineRunner(generator, ROOT, timeout_seconds=config["timeout_seconds"], require_source_roles=True)
    inputs, manifest = release_inputs(release, runner.checks)
    selected = inputs if all_cases else [i for i in inputs if i["incident_id"] == case]
    if not selected:
        raise ValueError("Unknown shared-dev-v1 case ID")
    policy = strict_json(POLICY.read_text(encoding="utf-8"))
    runner._check_policy(policy)
    policies = {i["incident_id"]: incident_policy(policy, i, manifest) for i in inputs}
    commit, dirty = git_state()
    if check:
        print(f"Preflight passed: {len(inputs)} verified incidents; {len(selected)} selected; no model started.")
        return 0
    output = Path(output)
    if output.resolve().is_relative_to(Path(release).resolve()):
        raise ValueError("Run output cannot be inside the frozen release")
    output.mkdir(parents=True, exist_ok=False)
    report = {"run_id": "RUN-" + uuid4().hex, "implementation_id": IMPLEMENTATION_ID, "mode": "no_rag", "release": "shared-dev-v1",
        "release_manifest_sha256": RELEASE_SHA256, "started_at": utc(), "status": "running",
        "code": {"commit": commit, "dirty": dirty},
        "environment": {"python": platform.python_version(), "platform": platform.platform(),
                        "runtime": config["runtime_version"]},
        "selected_ids": [i["incident_id"] for i in selected],
        "counts": {"available": len(inputs), "selected": len(selected), "attempted": 0,
                   "valid": 0, "failed": 0, "not_attempted": len(selected)},
        "quality": "Not scored: development expectations are not accepted gold labels.",
        "execution_image": os.environ.get("CYBERSOC_EXECUTION_IMAGE", "not_recorded"),
        "knowledge_used": False, "evaluator_loaded": False, "execution_enabled": False}
    versions = {"model": config["model_sha256"], "prompt": digest(Path(__file__).with_name("prompt.txt")),
                "dataset": RELEASE_SHA256, "configuration": "", "commit": commit}
    save(output / "report.json", report)
    try:
        save(output / "configuration.json", config)
        save(output / "policy.json", policy)
        save(output / "release-manifest.json", manifest)
        snapshot(output)
        versions["configuration"] = hashlib.sha256(
            (digest(output / "configuration.json") + digest(output / "policy.json")).encode()).hexdigest()
        with LocalRuntime(config, output / "runtime.log") as runtime:
            report["loading_command"] = runtime.command
            for incident in selected:
                iid, started, begin = incident["incident_id"], utc(), time.monotonic()
                folder = output / iid
                folder.mkdir()
                save(folder / "input.json", incident)
                save(folder / "policy.json", policies[iid])
                trace_id, investigation_id = "TRC-" + uuid4().hex, "INV-" + uuid4().hex
                error, result, measurement = None, None, None
                report["counts"]["attempted"] += 1
                report["counts"]["not_attempted"] -= 1
                try:
                    result, measurement = runner.investigate(incident, policies[iid],
                        investigation_id=investigation_id, trace_id=trace_id)
                    save(folder / "result.json", result)
                    report["counts"]["valid"] += 1
                except (InvalidOutput, RunnerTimeout, RunnerUnavailable) as exc:
                    code = {InvalidOutput: "invalid_output", RunnerTimeout: "timeout",
                            RunnerUnavailable: "dependency_unavailable"}[type(exc)]
                    error = {"code": code, "message": "No-RAG inference failed validation or availability checks.",
                             "retryable": isinstance(exc, (RunnerTimeout, RunnerUnavailable))}
                    save(folder / "failure.json", {**error, "stage": getattr(exc, "stage", None)})
                    report["counts"]["failed"] += 1
                step = {"step": 1, "component": "inference", "input_ref": f"{iid}/input.json",
                        "status": "error" if error else "ok", "latency_ms": (time.monotonic()-begin)*1000}
                if error:
                    step["error"] = error
                else:
                    step["output_ref"] = f"{iid}/result.json"
                trace = {"schema_version": "1.0.0", "trace_id": trace_id, "incident_id": iid,
                         "workflow": "baseline", "mode": "no_rag", "versions": versions,
                         "started_at": started, "finished_at": utc(), "status": step["status"],
                         "steps": [step]}
                if error:
                    trace["error"] = error
                runner.checks["trace"].validate(trace)
                save(folder / "trace.json", trace)
                save(folder / "messages.json", runner.last_messages)
                save(folder / "raw-output.json", runner.last_output)
                save(folder / "formatted-prompt.json", generator.last_formatted_prompt)
                save(folder / "measurements.json", measurement or runner.last_measurement)
                save(output / "report.json", report)
                print(f"{iid}: {'failed (' + error['code'] + ')' if error else 'contract-valid'}", flush=True)
        report["status"] = "completed_with_failures" if report["counts"]["failed"] else "completed"
    except BaseException as exc:
        report.update(status="failed", failure_type=type(exc).__name__)
        raise
    finally:
        report["finished_at"] = utc()
        save(output / "report.json", report)
        hashes = {p.relative_to(output).as_posix(): digest(p)
                  for p in sorted(output.rglob("*")) if p.is_file()}
        save(output / "artifact-manifest.json", hashes)
    print(json.dumps(report["counts"]))
    return 1 if report["counts"]["failed"] else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "ai/runtime/configs/qwen-cpu-linux.json")
    parser.add_argument("--release", type=Path, default=ROOT / "datasets/releases/shared-dev-v1")
    parser.add_argument("--output", type=Path, help="New private directory; existing runs are never overwritten")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--case", default="B0-LNX-SSH-001")
    selection.add_argument("--all", action="store_true", dest="all_cases")
    selection.add_argument("--interactive", action="store_true", help="Choose incidents and inspect results in a terminal")
    parser.add_argument("--check", action="store_true", help="Verify inputs and local artifacts without inference")
    args = parser.parse_args(argv)
    if args.interactive and args.check:
        parser.error("--interactive and --check cannot be combined")
    if not args.check and args.output is None:
        parser.error("--output is required unless --check is used")
    try:
        if args.interactive:
            from .terminal import session

            return session(args.config, args.release, args.output)
        return run(args.config, args.release, args.output, case=args.case,
                   all_cases=args.all_cases, check=args.check)
    except Exception as exc:
        print(f"No-RAG run stopped: {type(exc).__name__}. Inspect configuration and any saved report.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

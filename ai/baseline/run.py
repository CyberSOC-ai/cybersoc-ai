"""Exploratory synthetic-pilot run; model code never receives evaluator labels."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
from uuid import uuid4

from ai.evaluation.hashing import read_json
from ai.evaluation.loader import load_model_inputs, load_evaluator_cases
from ai.evaluation.scoring import score_cases
from ai.evaluation.validation import validate_dataset, validators

from .llama_server import LlamaServer
from .runtime import LocalRuntime
from .runner import BaselineRunner, InvalidOutput, RunnerTimeout, RunnerUnavailable


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save(path, record):
    Path(path).write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def utc():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def git_state(root):
    """Read real checkout identity; tests inject this external dependency."""
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True).strip())
    return commit, dirty


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--limit", type=int, default=14)
    args = parser.parse_args()
    if not 1 <= args.limit <= 14:
        parser.error("limit must be 1–14 development cases")
    root = Path(__file__).resolve().parents[2]
    config = read_json(args.config)
    # LocalRuntime loads this exact artifact; configuration is trusted local input.
    if sha(config["model_file"]) != config["model_sha256"]:
        raise ValueError("Model artifact digest mismatch")
    if sha(config["runtime_executable"]) != config["runtime_sha256"]:
        raise ValueError("Runtime executable digest mismatch")
    dataset = root / "datasets/evaluation/soc-eval-v1"
    validate_dataset(root, dataset)
    inputs = load_model_inputs(dataset)[:args.limit]
    policy = read_json(dataset / "protocol/runner-policy.json")
    output = args.output
    output.mkdir(parents=True, exist_ok=False)  # Never overwrite run evidence.
    run_id = "RUN-" + uuid4().hex
    experiment = read_json(root / "experiments/templates/experiment.json")
    started = utc()
    commit, dirty = git_state(root)
    save(output / "configuration.json", config)
    source = {}
    source_dir = output / "source"
    source_dir.mkdir()
    for file in sorted(Path(__file__).parent.glob("*")):
        if file.suffix not in (".py", ".txt"):
            continue
        target = source_dir / file.name
        target.write_bytes(file.read_bytes())
        source[file.name] = sha(file)
    save(output / "source-manifest.json", source)
    environment = {"os": platform.platform(), "cpu": platform.processor(),
                   "python": sys.version, "execution": "local llama.cpp CPU; exploratory",
                   "peak_gpu_memory": None, "gpu_null_reason": "CPU run; no NVIDIA GPU",
                   "runtime": config["runtime_version"], "hardware": config.get("hardware"),
                   "loading_command": config.get("loading_command"),
                   "peak_process_memory_bytes": None,
                   "peak_memory_null_reason": "Not instrumented by this client; external measurement required",
                   "cold_warm": "preloaded model; no warmup; per-request prompt cache disabled"}
    save(output / "environment.json", environment)
    prompt_file = Path(__file__).with_name("prompt.txt")
    save(output / "inputs.json", inputs)
    save(output / "policy.json", policy)
    prompt_record = {"system_template": prompt_file.read_text(encoding="utf-8"),
                     "version": "PRM-soc-triage-v1", "sha256": sha(prompt_file)}
    save(output / "prompt.json", prompt_record)
    experiment.update(record_kind="exploratory", synthetic_example=False,
                      experiment_id="EXP-S1T03-pilot-baseline-v1", run_id=run_id, task_id="S1-T03",
                      question="Can the pinned model produce contract-valid No-RAG pilot decisions?",
                      changed_variable="model artifact (comparison only under matched configuration)",
                      execution_status="running", started_at=started)
    experiment["code"].update(git_commit=commit, dirty=dirty,
                              patch_ref="source/ and source-manifest.json (runner source snapshot)")
    experiment["model"].update(publisher_id=config["artifact_repo"], revision=config["artifact_revision"],
                               sha256=config["model_sha256"], tokenizer_id=config["artifact_repo"],
                               tokenizer_revision=config["artifact_revision"],
                               quantization_source_revision=config["artifact_revision"])
    experiment["model"]["upstream_model_id"] = config["publisher_id"]
    experiment["model"]["upstream_head_at_inspection"] = config["upstream_revision"]
    experiment["model"]["lineage_limit"] = "Conversion's exact upstream checkpoint revision not established"
    experiment["prompt"].update(version="PRM-soc-triage-v1", template_ref="prompt.json",
                                sha256=sha(prompt_file), rendered_inputs_ref="rendered-prompts.json")
    experiment["dataset"].update(version=read_json(dataset / "manifest.json")["dataset_version"],
        manifest_ref="dataset-manifest.json", manifest_sha256=sha(dataset / "manifest.json"),
        split="development", split_manifest_sha256=sha(dataset / "splits.json"),
        case_ids_ref="inputs.json", incident_groups_ref="dataset-splits.json",
        leakage_check_ref="preflight validated hashes; model received input-only loader")
    (output / "dataset-manifest.json").write_bytes((dataset / "manifest.json").read_bytes())
    (output / "dataset-splits.json").write_bytes((dataset / "splits.json").read_bytes())
    experiment["inference"].update(quantization=config["quantization"], kv_cache=True,
        flash_attention=False, prefix_cache=False, serving_engine="llama.cpp",
        serving_version=config["runtime_version"], temperature=0, seed=config["seed"],
        max_input_tokens=config["max_input_tokens"], max_output_tokens=config["max_output_tokens"],
        batch_size=1, concurrency=1)
    for section in ("embedding", "chunking", "retrieval", "graph"):
        experiment[section]["applicability_reason"] = "No-RAG baseline; not used"
    experiment["retrieval"]["mode"] = "no_rag"
    experiment["workflow"].update(kind="baseline", version="S1T03-local-v1",
        configuration_ref="configuration.json", configuration_sha256=sha(output / "configuration.json"))
    experiment["environment"].update(environment_id="local-cpu-exploratory",
        record_ref="environment.json", sha256=sha(output / "environment.json"))
    experiment["evaluation"]["applicability_reason"] = "Pilot scorer only; no judge or human claim annotations"
    experiment["artifacts"].update(input_manifest_ref="dataset-manifest.json", results_ref="scores.json",
        output_manifest_ref="artifact-manifest.json", access_retention_owner="Soulaiman; local only",
        sanitization_version="synthetic-pilot-inputs; output inspection pending before sharing")
    experiment["remaining_null_reasons"] = {"all_unfilled_fields":
        "Exploratory pilot: no official comparison, judge, tracking deployment or runtime trace adapter; see environment limitations"}
    save(output / "experiment.json", experiment)
    generator = LlamaServer(port=config["port"], max_input_tokens=config["max_input_tokens"],
        max_output_tokens=config["max_output_tokens"], seed=config["seed"], context_tokens=config["context_tokens"])
    runner = BaselineRunner(generator, root, timeout_seconds=config["timeout_seconds"])
    predictions, measurements, failures, model_outputs, rendered_prompts = {}, {}, {}, {}, {}
    with LocalRuntime(config, output / "server.log") as runtime:
        environment["loading_command"] = runtime.command
        save(output / "environment.json", environment)
        experiment["environment"]["sha256"] = sha(output / "environment.json")
        for incident in inputs:
            iid, begin = incident["incident_id"], time.monotonic()
            try:
                result, measurement = runner.investigate(incident, policy)
                predictions[iid], measurements[iid] = result, measurement
            except (InvalidOutput, RunnerTimeout, RunnerUnavailable) as exc:
                predictions[iid] = None
                failures[iid] = type(exc).__name__
                measurements[iid] = {"elapsed_seconds": time.monotonic() - begin,
                                 "generation": runner.last_measurement,
                                 "rejection_stage": getattr(exc, "stage", None)}
            save(output / "predictions.json", predictions)
            save(output / "measurements.json", measurements)
            save(output / "failures.json", failures)
            model_outputs[iid] = runner.last_output
            save(output / "model-outputs.json", model_outputs)
            rendered_prompts[iid] = {"messages": runner.last_messages,
                                     "formatted": generator.last_formatted_prompt}
            save(output / "rendered-prompts.json", rendered_prompts)
            print(f"{iid}: {'failed: ' + failures[iid] if iid in failures else 'valid'}", flush=True)
        environment["peak_process_memory_bytes"] = runtime.peak_memory_bytes()
        environment["peak_memory_scope"] = "Server lifetime peak working set, including model loading; bytes"
        if environment["peak_process_memory_bytes"] is not None:
            environment.pop("peak_memory_null_reason", None)
        save(output / "environment.json", environment)
        experiment["environment"]["sha256"] = sha(output / "environment.json")
    # Labels are loaded only after inference, in this evaluator entry point.
    cases = load_evaluator_cases(dataset)
    manifest = read_json(dataset / "manifest.json")
    scores = score_cases(cases, predictions, manifest["severity_universe"], manifest["mitre_universe"],
                         validators(root, dataset)["investigation-result"])
    save(output / "scores.json", scores)
    experiment.update(finished_at=utc(), execution_status="completed_with_failures" if failures else "completed")
    experiment["remaining_null_reasons"]["faithfulness_and_quality"] = "Not measured; no validated judge or human labels"
    save(output / "experiment.json", experiment)
    artifact_hashes = {str(p.relative_to(output)): sha(p) for p in sorted(output.rglob("*")) if p.is_file()}
    save(output / "artifact-manifest.json", artifact_hashes)
    print(json.dumps(scores["counts"]))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

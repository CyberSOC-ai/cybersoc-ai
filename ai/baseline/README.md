# S1-T03 — Local No-RAG baseline runner

Owner: Soulaiman · Reviewer: Anas · [Issue #11](https://github.com/CyberSOC-ai/cybersoc-ai/issues/11).

Implementation on `feature/11-baseline-slm-runner`, authorized by Soulaiman for branch publication and PR review. Review: [PR #81](https://github.com/CyberSOC-ai/cybersoc-ai/pull/81); Soulaiman will request Anas's review. Task completion is not claimed. See the [S1 journal](../../docs/sprints/sprint-01/README.md) for actual validation and remaining work.

## What runs

`BaselineRunner` takes a validated incident and a fixed proposal policy. It builds a versioned prompt, calls an injected generator, parses strict JSON and validates the result against the existing v1 contract. There is no RAG, agent orchestration, fine-tuning or action execution.

The model supplies only summary, triage verdict, assessed risk, MITRE mappings and optional block proposals. Trusted code supplies incident/investigation/trace identities, action IDs, idempotency keys, approval requirements and fixed SSH containment scope. It rejects extra fields, duplicate proposals, unobserved source addresses and unregistered/unobserved hosts. This validates proposal structure and scope, not analyst correctness or operational authorization.

`LlamaServer` is the model-family-independent inference interface. It applies the loaded GGUF's embedded chat template, tokenizes the complete prompt, rejects over-budget inputs and requests schema-constrained streaming output. It fails explicitly on incomplete generation, invalid output, unavailability or deadline. `LocalRuntime` explicitly loads a local model and terminates only the server process it created, including on exceptions. Models are never loaded on import or downloaded by request handlers.

CPU inference was chosen for this Windows Ryzen 5 5625U / Radeon integrated machine. Quantized weights are a practical development configuration, not the S5 quantization study or a selected final serving architecture. Both input and output budgets are recorded. No remote Python checkpoint code is executed.

## Local setup

The shared project convention remains Python 3.12/Docker. The current machine's exploratory environment uses Python 3.14.3 because Docker's engine was stopped. Those pilot runs do not establish Docker/CI validation. A subsequent [backend integration exercise](API_INTEGRATION.md) passed 103 tests in a separate Python 3.12 Linux image; hosted CI remains unrun.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -B -m unittest discover -s tests/baseline -v
.\.venv\Scripts\ruff.exe check --no-cache .
```

Use the [official llama.cpp binaries](https://github.com/ggml-org/llama.cpp/releases), selecting the appropriate CPU build. The locally tested build is `b11827`, commit `970b51ce7c9ba5fff0726c5e9994f1c2f0e4eedc`. Its Windows CPU archive SHA-256 is `2740eeac6ed9b727a3a1002f5a42e74defa3c4cbb9a8b42b11356a07f969cb13`. Record the executable hash too. Retain bundled license notices. Downloads and extracted binaries stay in ignored `.local/runtime/`.

Model artifacts:

| Artifact | Immutable repository revision | File / SHA-256 |
|---|---|---|
| Publisher [Qwen GGUF](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF), Apache-2.0 | `91cad51170dc346986eccefdc2dd33a9da36ead9` | `qwen2.5-1.5b-instruct-q4_k_m.gguf` / `6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e` |
| Community [Phi conversion by bartowski](https://huggingface.co/bartowski/microsoft_Phi-4-mini-instruct-GGUF), derived from [Microsoft Phi](https://huggingface.co/microsoft/Phi-4-mini-instruct) | `7ff82c2aaa4dde30121698a973765f39be5288c0` | `microsoft_Phi-4-mini-instruct-Q4_K_M.gguf` / `01999f17c39cc3074afae5e9c539bc82d45f2dd7faa3917c66cbef76fce8c0c2` |

Retain source cards and upstream license notices with local artifacts; Microsoft publishes the upstream model under MIT. Phi is a third-party conversion, not an official Microsoft GGUF. The exact upstream checkpoint used by a conversion is not established merely by looking up the upstream repository's current revision. The immutable GGUF revision, checksum, embedded tokenizer/template and conversion source identify what actually ran; lineage limitations must be reported.

## Run command and configuration

Place a trusted JSON config in `.local/qwen-config.json` or `.local/phi-config.json` with these fields:

```json
{
  "publisher_id": "Qwen/Qwen2.5-1.5B-Instruct",
  "upstream_revision": "record the inspected source revision; conversion lineage must be verified separately",
  "artifact_repo": "Qwen/Qwen2.5-1.5B-Instruct-GGUF",
  "artifact_revision": "91cad51170dc346986eccefdc2dd33a9da36ead9",
  "model_file": ".local/models/qwen2.5-1.5b-instruct-q4_k_m.gguf",
  "model_sha256": "6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e",
  "runtime_executable": ".local/runtime/b11827/llama-server.exe",
  "runtime_sha256": "fill from the verified extracted executable",
  "runtime_version": "b11827",
  "quantization": "Q4_K_M",
  "port": 8087,
  "context_tokens": 4096,
  "max_input_tokens": 3072,
  "max_output_tokens": 512,
  "seed": 42,
  "threads": 6,
  "timeout_seconds": 180
}
```

The example contains placeholders. The checked-in [Qwen config](configs/qwen-cpu.json) and [Phi config](configs/phi-cpu.json) contain portable paths and actual pinned hashes for the tested Windows CPU build; copy one into `.local/` and adjust paths/hardware as necessary. Download the matching artifacts separately. Paths resolve from the working directory; run from the repository root. The config is trusted deployment input, never model/HTTP input. It selects only local artifacts and loopback serving. The CLI verifies artifact hashes, launches a preloaded single-slot CPU server, and stops it after the run. Do not launch another server on that port first.

```powershell
.\.venv\Scripts\python.exe -B -m ai.baseline.run --config .local/qwen-config.json --output .local/runs/qwen-new --limit 14
```

Choose a new output directory for every attempt. `--limit 1` runs the first case and records the other 13 as not attempted. The pilot has only 14 development cases; no test split is available. Every attempted failure remains in the denominator. There is no automatic output repair or retry. Startup/configuration errors fail the run rather than manufacturing predictions; an interrupted run retains its `running` marker and partial outputs for diagnosis.

## Evaluation and evidence

`run.py` is the evaluator, separate from the runner core. It validates the dataset, passes input-only incidents and the same fixed policy to the runner, then loads gold labels only after predictions exist. It reuses Anas's scorer without changing labels, case groups, prompts used by the judge, or dataset hashes. Model failures produce explicit `None` predictions and sanitized failure classes.

Run directories retain configuration, policy, system prompt, exact rendered prompts, raw model answers, input records, predictions, failures, per-case timings, dataset/split manifests, source snapshot, code SHA/dirty state, environment, portable experiment metadata and SHA-256 artifact manifest. Raw runtime logs stay local; inspect outputs/logs before sharing. Schema-constrained decoding is part of the recorded baseline setup; it is not evidence of factual correctness or injection resistance.

Client timings include template application and tokenization. First content chunk is recorded separately; token-level TTFT is null because it is not established. Server-reported prompt/decode timings are retained with separate scope. Cold model load is excluded from per-case latency. On Windows the client records the server's lifetime peak working set, including loading, through GetProcessMemoryInfo; this is neither per-case memory nor GPU allocation. Unsupported/unavailable memory counters are null with a reason. GPU memory is not applicable for CPU runs. No human quality, faithfulness or hallucination scores are claimed without annotations/judge validation.

Scores are development-pilot observations on unreviewed synthetic labels, not held-out benchmark results. A seed/temperature zero does not guarantee identical results across platforms. One pass without repeated trials does not establish a speed ranking. Upstream source revision and conversion revision are separate provenance fields; conversion lineage remains a limitation.

## Handoffs

- Anas's pilot: `runner(incident, policy)` returns a contract-valid result; the callable core implements it.
- Oussama's unmerged PR #79: `APIAdapter.run(request)` preserves backend-issued investigation/trace IDs and its deadline, maps timeout/unavailability to backend exception types and leaves persistence to the backend. Backend imports are deferred, so pilot use works on `main` without merging the API branch. Local composition, actual-backend integration tests and one real Qwen API smoke passed against a pinned snapshot; see [integration evidence](API_INTEGRATION.md). Owner agreement and verification against the approved merged backend revision remain pending.
- Deadline limits are cooperative on the client socket. The runtime is a separate process and the CLI stops it on exit. The future API pool must still reconcile timeout/cancellation before reusing server capacity; closing an HTTP connection is not a universal guarantee that computation has stopped.
- ADR-002 remains Proposed until model evidence and team review support a selection. Do not turn these early pilot observations into a final model decision.

The [llama.cpp server documentation](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md) describes `/apply-template`, `/tokenize`, streaming `/completion` and JSON-schema constraints. Runtime behavior is additionally checked against the pinned build locally.

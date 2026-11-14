# No RAG baseline

This folder contains the incident-only investigation baseline for CyberSOC AI.
It analyses one normalized incident with a local compact model, a fixed proposal
policy and a strict JSON output contract. It does not retrieve reference documents,
query a vector or graph database, train the model or execute response actions.

The baseline serves two purposes: establishing a reproducible investigation path
and providing the reference against which later Vector, Graph and Hybrid RAG
modes can be compared on the same incidents. It is an explicitly selected mode;
it must not silently replace a failed retrieval pipeline.

## Start here

1. Read this guide for architecture, configuration and execution.
2. Use [EVALUATION.md](EVALUATION.md) to review all seven incidents, exact prompts,
   expected labels, real outputs, completed ratings and claim annotations.
3. Use [IMPROVEMENTS.md](IMPROVEMENTS.md) for known gaps, controlled experiments
   and the conditions for moving to RAG comparison.

These are the three active documentation files for this phase. Pipeline code and its prompt remain here; shared model/policy configuration
is owned by [the runtime](../runtime/README.md); raw runs, models and archived working notes
remain outside the source tree under local artifact storage.
The evaluation record is self-contained for reading and manual scoring. The
local archive is only needed to audit the original evaluator bundle byte-for-byte.

## Current state

The active implementation is `local-layout-v2`, reorganized on 14 November 2026.
The earlier model/prompt/policy settings and input data are preserved. Runtime
extraction and source-path changes are recorded as a new implementation identity.

The active source dataset is the immutable `shared-dev-v1` release. Its seven
synthetic incidents cover SSH failures, approved account creation, a file change,
Windows login, administrator-group membership, approved PowerShell maintenance
and a client vulnerability finding. These are development cases, not held-out
final-test data. The reference documents and evaluator judgments are not model
inputs in No-RAG.

The latest frozen experiment is `shared-no-rag-aligned-v1`, recorded on
13 November 2026. All seven outputs passed contract/policy validation, with
verdict-field agreement of 4/7 and accepted-risk-set agreement of 5/7. Several
answers remain incomplete or overlook approval context. The completed technical
review retains this weak baseline as the reference for a small Vector RAG
comparison. This is not an overall reasoning-quality pass or independent
reproduction acceptance.

The previous RAG code, pilot datasets and prepared indexes were retired. They are
not dependencies of this entry point. The backend foundation remains, but the
standalone CLI is not automatically a served API deployment. The default API has
no model runner and returns 503 for investigations. The fresh standalone [Vector RAG CLI](../../rag/vector/README.md) is separate;
its backend integration remains unavailable.

## Folder map

```text
ai/no_rag/
  README.md          Local execution and handoff guide
  EVALUATION.md      Preserved seven-case evidence and scoring
  IMPROVEMENTS.md    Known gaps and future experiments
  prompt.txt         Incident-only system instructions
  run.py             Pinned incident loader, case selection and run recording
  terminal.py        Interactive incident inspection
  runner.py          No-RAG message composition and result validation
  api_adapter.py     Optional backend adapter; not a deployment
  configs/           Original historical lock and new layout lock
```

Shared lifecycle, transport, contracts, permissions and model configuration now
live in `ai/runtime/`. Historical source snapshots and experiments retain their
original `ai/baseline/` paths; their hashes are not rewritten.

Tests live in `tests/no_rag/` and `tests/backend/`. The launcher is
`infrastructure/run-no-rag.sh`. The backend owns the versioned contracts in
`backend/contracts/v1/`; no separate model-only result format replaces them.
Earlier Windows configuration examples and historical reports are retained in
`docs/history/reset-2026-11-13/ai/baseline/`, outside the active workflow.

## Execution flow

1. Verify the selected release manifest and every incident input hash/schema.
2. Verify the local model and runtime binaries against their configured hashes.
3. Derive the incident-specific proposal policy from verified observations.
4. Start a bounded local model server; build system/user messages and apply the
   model's embedded chat template.
5. Count tokens and reject an oversized input rather than truncate it. Generate
   schema-constrained JSON within the output and time budgets.
6. Validate JSON, decision fields, allowed proposals and the final v1 result.
   Trusted code supplies investigation/trace/action identities and approval fields.
7. Save input, actual policy, messages, rendered prompt, raw answer, result or
   failure, measurements, trace and source/artifact hashes. Stop the owned server.

The model supplies summary, maliciousness verdict, assessed risk, optional ATT&CK
IDs and optional response proposals. No evaluator answer is inserted into the
prompt. A valid schema proves structure and policy compliance, not factual or
operational correctness.

## Prerequisites and artifact restoration

First complete [runtime setup steps 1–4](../runtime/README.md): obtain the reviewed
source revision, restore data, obtain/hash-check the model/server and prepare a
verified inference image. The launcher uses a content-addressed image or the full
`NO_RAG_IMAGE` override. It never builds, downloads or substitutes missing artifacts.

Required local artifacts:

- Frozen release at `datasets/releases/shared-dev-v1`, restored using the
  [shared release guide](../../datasets/SHARED_DEV_V1.md).
- Qwen2.5-1.5B-Instruct Q4_K_M GGUF and llama.cpp b11827 at the paths in
  [the Linux configuration](../runtime/configs/qwen-cpu-linux.json), with matching hashes.
- Existing image and permission to run local Docker containers.

Model licenses, notices and acquisition receipts remain with the local artifacts.
The repository does not contain weights or imply permission to download, execute
or redistribute additional resources. Do not substitute a synthetic runner for
an unavailable model in deployment.

## Commands

Run from the repository root. Preflight verifies the release, incidents and
configured model/runtime files without starting inference:

```sh
bash infrastructure/run-no-rag.sh --check
```

Run one case, all seven sequentially, or the interactive incident menu:

```sh
bash infrastructure/run-no-rag.sh --case B0-LNX-SSH-001
bash infrastructure/run-no-rag.sh --all
bash infrastructure/run-no-rag.sh --interactive
```

The menu lets you inspect input, run a selected incident, read the assessment or
failure, and inspect raw output and trace. Each analysis uses a fresh attempt
folder and model context. Browsing alone does not start the model. It is not a
free-form conversational assistant.

The launcher uses a read-only checkout, no external network or published ports,
a 3 GiB/no-swap limit and two CPUs. Inference uses container loopback only. The
server starts and stops within that container. Run only one model invocation at
a time on this setup; do not terminate an unrelated owner session to free resources.

If an appropriate existing Python/runtime environment is already available,
the same module can be called directly:

```sh
python3 -B -m ai.no_rag.run --case B0-LNX-SSH-001 \
  --config ai/runtime/configs/qwen-cpu-linux.json \
  --output artifacts/local-inference/runs/shared-manual-01
```

`--release PATH` selects another restored directory containing the same pinned
release, not arbitrary data. `--config PATH` selects trusted local settings, not
HTTP/model input. New source contents require a new release and explicit integration.

## Configuration and frozen reproduction

The current configuration uses 4,096 context tokens, a 3,072-token input limit,
512 output tokens, temperature 0, seed 42, one model slot and a 180-second incident
inference deadline. Runtime startup has a separate 120-second bound. Temperature 0
and a seed improve control but do not guarantee identical answers across platforms.

The baseline lock identifies the exact source/configuration files, model/runtime,
image, generation settings and evaluator identity used in the recorded experiment.
The ordinary launcher does not automatically load or enforce that lock. Verify
its hashes before claiming reproduction of this frozen experiment, then compare
saved execution snapshots afterward. A changed prompt, model, policy or setting
requires a new baseline identity and new output directory; never overwrite a run.

The historical `shared-no-rag-aligned-v1.lock.json` records the pre-refactor paths
and hashes and is retained unchanged. It does not match the reorganized source.
`local-layout-v2.lock.json` identifies the new source layout; its mapping records
the predecessor. Recorded seven-case scores belong to the historical experiment,
not a new post-refactor inference run. The model's original general knowledge remains available; deleting datasets does not erase it
or alter model weights.

## Proposal boundary

The only structured proposal type is `block_ip` for SSH. The shared policy limits
eligible targets to a verified scope for the SSH incident. Literal originating
peer, destination, host and service annotations are tied to the incident hash.
Other cases receive no eligible targets; missing scope fails closed for proposals.
An empty action list is valid. No response executor exists here.

The shared entry point enables strict source-role validation: the destination IP
cannot be substituted for the originating peer, even if both occur in entities.
All proposals remain approval-required with execution disabled. Entity membership
and correct source roles still do not prove malicious intent or justify blocking.

The optional API adapter does not automatically inherit the shared entry point's
release selection, incident-specific policy or strict-role configuration. Trusted
application composition must supply those deliberately and manage model lifecycle.
See the [backend runner interface](../../backend/RUNNER_INTERFACE.md).

## Output files and failures

The launcher prints a unique folder under `artifacts/local-inference/runs/`.
Each run contains a report, configuration/policy, release identity, execution-source
snapshot and artifact manifest. Each attempted case contains:

- `input.json` and `policy.json` for the exact supplied observations and scope.
- `messages.json` and `formatted-prompt.json` for actual model input.
- `raw-output.json` and either `result.json` or `failure.json`.
- `measurements.json` and a correlated `trace.json`.

No repair, automatic retry, hidden fallback or removal of invalid actions occurs.
Failures remain recorded. Output directories must be new. Exit 0 means selected
outputs are contract-valid or preflight passed; exit 1 means recognized inference
failures; exit 2 means preflight/startup/unexpected failure. None is a model-quality
acceptance signal. Partial runs retain available evidence.

The latest run is
`artifacts/local-inference/runs/shared-no-rag-20261113T161333-408799/`.
Preflight, freeze and post-run review evidence are under
`artifacts/local-inference/baseline-freezes/shared-no-rag-aligned-v1/`.
Older working documents and the original evaluator bundle are preserved in a
single local archive identified in [EVALUATION.md](EVALUATION.md).

## Verification and limits

Focused checks for the alignment task passed: 49 baseline tests, 21 backend tests,
Ruff, repository/link checks, Bash syntax and whitespace. The real seven-case run
also passed artifact, source/input, template, token and result/trace integrity
checks. These are distinct from human scoring, hosted CI and clean-image or
independent teammate reproduction, which remain unverified for this phase.

Use the existing development image for offline checks when available:

```sh
docker compose run --rm -T dev python -B -m unittest discover -s tests/no_rag -v
docker compose run --rm -T dev python -B -m unittest discover -s tests/runtime -v
docker compose run --rm -T dev python -B -m unittest discover -s tests/backend -v
docker compose run --rm -T dev ruff check --no-cache .
python3 -B infrastructure/ci/check_repository.py
```

The seven-case review is complete: 21 facts assessed, 27 claims annotated and
all four quality dimensions rated for every case. Whole-answer claim support is
23/27 (85.19%), while only 9/21 required facts are fully conveyed. These measures
answer different questions. Independent paired validation remains unfinished.
No new inference was needed for this scoring. Broader
exposure, new downloads, deployments or model experiments require their own scope.
For future data growth, follow the [release workflow](../../datasets/README.md):
stage changes separately, publish the next immutable source release and bind new
artifacts/runs to its identity without overwriting earlier data.

## Fresh-machine handoff checklist

1. Use the reviewed source revision and complete the runtime setup guide.
2. Restore and verify shared-dev-v1 using the data-folder release guide.
3. Run `--check`; it must report seven verified incidents without model startup.
4. Run one case, inspect its input/messages/raw output/result-or-failure/trace,
   then run `--all`. Keep the reported output directory and all intended cases.
5. Compare the recorded source/model/configuration identities before comparing
   results. A different layout, image or runtime is a new experiment; do not
   relabel it as the historical seven-case run.
6. Record actual commands, platform, exit status and output hashes for the
   reviewer. Any external artifact sharing needs reviewed usage/access rights.

For future source releases, this No-RAG entry point deliberately remains pinned
to the reviewed seven-case v1 manifest. New narratives require an explicit loader
selection/version update and reviewed source-role policy; changing `--release`
only changes the location of the same frozen release. Arbitrary runtime paths or
files copied beside v1 do not activate new data. The complete source-addition
workflow belongs to [datasets/README.md](../../datasets/README.md).

## Layout verification — 14 November 2026

The reorganized checkout passed 144 offline tests: contracts 20, evaluation 21,
backend 21, normalizer 16, No-RAG 38, shared runtime 14 and Vector 14. Runtime tests
include import-isolation checks: neither investigation mode imports the other or
the evaluator. The real No-RAG `--check` passed against all seven frozen inputs
and existing model/server bytes without starting the model.

Recorded-output replay through the new No-RAG core reproduced all seven exact
messages and validated results. RAG's actual tokenizer/template preflight matched
all seven original rendered prompts; retrieval matched all 21 query rankings/scores
to six decimals while reusing 718 embeddings and computing none. These are layout
compatibility checks, not new incident-generation or model-quality measurements.
The new layout's native Qdrant snapshot was also restored into a separate
collection, with all 21 query rankings/scores matching to six decimals.
Original source/evaluation bytes and verification records are retained locally
under `artifacts/local-inference/layout-migrations/layout-v2-20261114`.
Fresh-image builds, hosted CI, cloud execution and teammate reproduction remain
unverified. Follow the new setup guides and record their outcomes on another host.

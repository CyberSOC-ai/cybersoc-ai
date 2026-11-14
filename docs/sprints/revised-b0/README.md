# B0 — Ahmed: foundation, No-RAG and small Vector RAG

## Sprint information

Status: Local No-RAG and standalone Vector RAG implemented and reviewed; complete B0 acceptance pending. Schedule by readiness; no invented dates. Deadline 1 January 2027; feature freeze 28 December 2026.

B0 is assigned to Ahmed; every downstream owner and all reviewers are unassigned for Ahmed to choose. Headings below record contributions only.

## Deliverables

| Issue | Deliverable | Owner | Reviewer | Status |
|---|---|---|---|---|
| [#95](https://github.com/CyberSOC-ai/cybersoc-ai/issues/95) | Deliver shared foundation, No-RAG and small reusable Vector RAG | Ahmed | Unassigned | Planned |

# 1. Ahmed

## Assigned tasks

B0 initial delivery.

## Work and learning evidence

### Shared-release No-RAG implementation — 2026-11-11

Added `ai.baseline.shared`, an incident-only entry point for the pinned
`shared-dev-v1` manifest, reusing the existing bounded runner/runtime. It verifies
all seven incident hashes/contracts, supports one case or all cases, and records
correlated v1 results/traces, raw answers/prompts, timings, failures, source bytes
and hashes. Historical pilot/evaluator/knowledge contents are excluded. The fixed
policy permits only proposed SSH blocks on synthetic `b0-linux-a`; empty actions
are valid. No execution or fine-tuning occurs.

[Local test instructions](../../../ai/no_rag/README.md) use the existing
Python 3.12 Docker image with no downloads/external network and explicit CPU/RAM
limits. Preflight passed against actual local model/runtime and all seven frozen
inputs without starting the model. All 41 baseline tests passed offline in that
image; focused Ruff, shell syntax, repository integrity and whitespace checks
passed. Tests use controlled model outputs, not SOC-quality evidence. No real
incident inference, hosted CI, cloud cycle or independent reproduction was run;
B0 acceptance remains pending. Changes are local, uncommitted and unpublished.

Follow-up: added `--interactive` incident selection, input viewing, bounded
pipeline invocation, assessment/failure display and raw-answer/trace inspection.
Each analysis uses a fresh output directory and no conversation history. Terminal
control sequences in displayed data are escaped. Real offline Docker browsing
and clean exit passed without inference; 49 baseline tests and focused Ruff
passed. Interactive model analysis remains for the owner to exercise locally.

### First real seven-case No-RAG run — 2026-11-11

Owner authorized `bash infrastructure/run-no-rag.sh --all`. Offline CPU Qwen2.5
1.5B Q4_K_M / llama.cpp b11827 attempted all seven shared-dev-v1 cases: one
contract-valid, six rejected at proposal-policy validation. Median client
inference was 45.21 seconds; total batch wall time about 315 seconds. All 70 saved
artifact hashes and seven trace contracts passed independent checks. The 49
baseline software tests passed again. Evidence remains local/ignored under
`artifacts/local-inference/runs/shared-no-rag-20261111T224040-273041/`.

The contract-valid SSH answer proposed blocking the server IP instead of the
originating peer. Other answers used invalid `undetermined` IPs or an unrelated
policy host. These expose weak action selection and a source-role validation gap;
contract validity does not establish action correctness. No prompt/config change,
retry, output repair or action execution occurred. Evaluator/knowledge contents
were not loaded; no accuracy score, held-out benchmark or B0 acceptance is claimed.
Future improvements require a new development run preserving this evidence.

### Source-role checks, abstention and second run — 2026-11-11

Owner authorized improvements and rerun. Policy v2 binds literal input-derived SSH
source/destination/host/service annotations to the frozen incident hash. Shared
CLI uses incident-specific scopes, no eligible targets without roles and opt-in
strict source-role validation. Prompt defaults to empty actions; permissions are
not requests. Frozen release unchanged; no evaluator labels, repair or filtering.
Legacy callers retain existing default behavior outside the shared entry point.

All 55 baseline tests and 107 offline Vector tests passed; focused Ruff, repository
integrity and whitespace checks passed. Real offline Qwen rerun at
`artifacts/local-inference/runs/shared-no-rag-20261111T225131-274868/`: seven attempted,
seven contract-valid, zero failed, seven empty action lists. Median client
inference 38.83s, total wall time about 270s. All 77 artifact hashes and seven
trace/result contracts passed verification; initial run's 70 hashes unchanged.

This improves action abstention/validation, not established assessment accuracy.
Account summary still invents unauthorized creation; SSH/Windows logon label
false_positive without supplied benign explanation; PowerShell remains
undetermined/medium despite approved context. Prompt/policy/validation changed
together; no isolated causal comparison, frozen-test score or B0 acceptance.

### Incremental data/RAG reset — 2026-11-13

Ahmed authorized retiring old prepared data/RAG and rebuilding from shared-v1.
The [cleanup record](../../data/cleanup-reset.md) lists boundaries and verification.
Obsolete preparation bundles, old pilot/retrieval datasets, knowledge configs,
RAG code/adapter, implementation-specific tests/CLI and generated corpora/indexes
were removed. Relevant baseline/API tests now use explicit synthetic fixtures;
independent scoring/contract checks remain. Historical reports and model packages
were preserved separately. The stopped old Qdrant container/volume were removed;
other running services and local inference artifacts were untouched.

127 retained offline tests passed in the existing Python 3.12 image; Ruff,
repository integrity, shell syntax, whitespace and frozen release checks passed.
No-RAG preflight passed without inference. Hosted CI/new image reproduction were
not run. RAG is explicitly unavailable (503 with no fallback), not reimplemented.
The [active data workflow](../../data/workflow.md) defines new immutable releases.
B0 quality/reproduction acceptance remains open. No commit or remote write.

### General-prompt alignment and fresh frozen No-RAG run — 2026-11-13

Owner authorized aligning general label definitions before a fresh recorded pass.
[Report](../../../ai/no_rag/EVALUATION.md) records the frozen baseline,
real template/tokenization audit and seven-case run. Seven attempted/valid, zero
failures; all 77 hashes and seven result/trace contracts verified. Source/evaluator
unchanged, no case-specific answer leakage, no truncation or post-output tuning.
49 baseline and 21 backend tests and focused static checks passed.

Verdict field agreement 4/7 and risk-in-set 5/7 do not establish full reasoning
quality: approval context is still missed, some malicious verdicts unsupported,
and several summaries incomplete. Median client 125.16s, wall 834.93s; no isolated
causal quality/speed claim or B0 acceptance. Model/policy/settings unchanged;
no download, fine-tuning, action execution, commit or remote write.

### No-RAG documentation consolidation — 2026-11-13

Consolidated the active phase into [the No-RAG guide](../../../ai/no_rag/README.md),
[complete evaluation record](../../../ai/no_rag/EVALUATION.md) and
[improvement plan](../../../ai/no_rag/IMPROVEMENTS.md). Exact incidents, received
prompts and outputs for seven cases are included with definitions and blank
review/metric worksheets. Redundant working documents were archived before
removal; historical notes/config examples moved out of the active folder.
Code/configuration paths and frozen run/source identities are unchanged.
Documentation integrity/completeness checks passed; no new inference or quality
acceptance was performed. Manual review and scoring remain the next step.

### Completed No-RAG development review — 2026-11-13

Completed [the seven-case review](../../../ai/no_rag/EVALUATION.md) with all
21 fact criteria, 28 quality ratings and 27 evidence-bound claim judgments.
Results: facts nine met/four partial/eight missing; verdict4/7; risk-in-set5/7.
Whole-answer support23/27 (85.19%), three unsupported interpretations and one
unjudged temporal qualifier. Mean correctness2.86, evidence use3.86,
actionability2.29, safety3.71 /5; full seven-case coverage for every dimension.

The baseline is retained as a measured experimental reference for the requested
small Vector RAG comparison, not accepted as a high-quality investigator. No new
inference or output repair. Independent paired human validation, positive-class
coverage and B0 reproduction/handoff remain open. Arithmetic, evidence identities,
source/output preservation, links and whitespace checks passed. No commit/remote
write. Next work is a fresh small Vector RAG on the agreed source release.

# 2. Soulaiman

## Assigned tasks

No assignment made by this roadmap.

## Work and learning evidence

Record actual work, changed components, commands/results, artifact versions, failures, limitations, issue/PR links and the walkthrough/reproduction evidence here. Do not prefill completion.

# 3. Anas

## Assigned tasks

No assignment made by this roadmap.

## Work and learning evidence

Record actual work, changed components, commands/results, artifact versions, failures, limitations, issue/PR links and the walkthrough/reproduction evidence here. Do not prefill completion.

# 4. Achraf

## Assigned tasks

No assignment made by this roadmap.

## Work and learning evidence

Record actual work, changed components, commands/results, artifact versions, failures, limitations, issue/PR links and the walkthrough/reproduction evidence here. Do not prefill completion.

# 5. Oussama

## Assigned tasks

No assignment made by this roadmap.

## Work and learning evidence

Record actual work, changed components, commands/results, artifact versions, failures, limitations, issue/PR links and the walkthrough/reproduction evidence here. Do not prefill completion.

# Shared sprint integration

## Integration and acceptance

Pending actual dependency checks, real integration and independent reproduction.

## Experiments, security and reproducibility

Link run/trace/artifact identities, failed cases and scope limits when observed.

## Report checkpoint and retrospective

Record the R2/R3 consolidation checkpoints and lessons when applicable.

### Fresh local Vector RAG — 2026-11-13

Explicit owner selection: Qdrant + existing verified BGE-small. The
[standalone pipeline](../../../rag/vector/README.md) verifies 21 documents, produces
718 passages, maintains immutable index/run identities, supports compatible
embedding reuse and native snapshot restore, and runs bounded local Qwen with
verified source context. The [evaluation](../../../rag/vector/EVALUATION.md)
retains actual prompts/outputs and scores all 7 cases:6 valid,1 policy rejection,
verdict4/7,delivered risk-field agreement5/7. No answer-quality gain accepted.
All 18 answerable queries find known references; incomplete judgments prevent
full precision claims. Local restore reproduces21 query ranks/scores.

141 offline tests and Ruff/repository/shell/whitespace checks pass. Source release
and No-RAG frozen control unchanged. Store stopped with persistent data retained.
No fresh-image build, hosted CI, cloud cycle, independent validation or teammate
reproduction performed. Backend integration remains pending; this evidence does
not close all B0 acceptance gates or assign downstream owners.

### Pipeline layout and local handoff guides — 2026-11-14

Owner approved four clear ownership areas: `ai/no_rag`, `rag/vector`, `datasets`
and `ai/runtime`. Shared lifecycle/transport/contracts/policy/provenance were
extracted from the old No-RAG package. Both modes use the runtime directly;
No-RAG and RAG do not import each other. Tests moved to `tests/no_rag` and
`tests/runtime`; hosted workflow commands updated without claiming a CI run.

The [runtime guide](../../../ai/runtime/README.md) documents official pinned
model/server acquisition, image preparation, checks and limits. Both pipeline
guides contain local execution/inspection/restore instructions. The
[data guide](../../../datasets/README.md) owns source acceptance, extraction,
rights/provenance, stable IDs/deduplication, evaluator separation, new complete
releases, explicit activation, embedding reuse and source-format limitations.

New identity `local-layout-v2`; historical locks/runs preserved. All 144 offline
tests and Ruff/repository/shell/whitespace checks pass. No-RAG real preflight
passes; recorded-output replay reproduces seven messages/results. RAG actual
template preflight matches seven original prompts; 21 retrieval rankings/scores
match to six decimals. Compatible build reuses 718 embeddings, creates zero new
ones, retains vector bytes. Native snapshot export/restore into a distinct
collection preserves all 21 query rankings/scores. Original 80 source payload hashes and 185 historical
run artifacts verified unchanged. Original source/evaluation files archived before
moves under local layout-migration artifacts. No new quality inference, install,
download, fresh-image build, API integration, Kaggle work, commit/push or upload.
The owned store was stopped; full B0 cloud/independent-handoff gates remain open.

### Publication preparation — 2026-11-14

The shared baseline checkpoint retains incomplete B0/cloud/independent-reproduction
gates. Publisher passages were omitted from the distributable RAG prompt views
because source records retain unresolved redistribution status. Full original
prompts/report remain in local run and migration artifacts; incidents, raw model
outputs, scores, reference IDs/offsets and passage hashes remain reviewable in Git.
The public views are explicitly distinguished from the exact model inputs.

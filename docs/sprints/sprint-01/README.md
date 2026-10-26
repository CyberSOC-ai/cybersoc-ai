# Sprint 1 — Platform Baseline, SOC Lab MVP & No-RAG Baseline

## Sprint Information
- Dates: 2026-10-13 → 2026-10-25
- Main objective: Produce the first reproducible, end-to-end baseline without RAG.
- Main dependencies: S0-T01, S0-T03, S0-T04, S0-T05, S0-T06, S0-T07
- Exit criteria:
  - Project starts reproducibly
  - Lab generates at least one valid incident
  - Normalized incident reaches the backend
  - Baseline SLM produces a structured result
  - Baseline metrics are recorded
  - `soc-eval-v1` and its evaluation protocol (faithfulness, quality rubric, dev / test split) are versioned and reviewed

## Sprint Tasks

| Task | Owner | Reviewer | Domain | Status |
|---|---|---|---|---|
| S1-T01 — Reproducible local environment + Docker + basic CI | Ahmed | Achraf | devops | In progress |
| S1-T02 — Evaluation dataset v1 and evaluation protocol | Anas | Oussama | ai-slm | Ready (pilot; S1-T02 incomplete) |
| S1-T03 — Baseline SLM runner | Soulaiman | Anas | ai-slm | In review |
| S1-T04 — FastAPI core + incident ingestion | Oussama | Soulaiman | backend | In progress |
| S1-T05 — SOC Lab MVP | Achraf | Ahmed | soc | Backlog |
| S1-T06 — SOC alert normalizer | Ahmed | Oussama | soc | In progress (implemented locally; PR/review pending) |
| S1-T07 — No-RAG end-to-end baseline | Anas | Ahmed | ai-slm | Backlog |

# 1. Ahmed
## Assigned tasks

S1-T01, S1-T06

## Work completed

2026-10-15 — S1-T01: Implemented and locally validated the development foundation on `feature/9-reproducible-local-environment`. PR, assigned-reviewer request, hosted CI and merge remain pending. S1-T01 is not yet Done.

- Recorded Python 3.12 and Node.js 24 conventions. Built a Python development image with pinned Python packages, a regular `dev` user and a read-only project bind mount through Compose.
- Centralized Python dependencies in root `requirements.txt`; added Ruff configuration, a comment-only `.env.example`, build-context exclusions and a [development setup guide](../../development.md) linked from the root README.
- Updated the existing required `repository-checks` CI job to use checkout v6, the Gitleaks v3 Action, Docker build, Ruff and contract tests. Removed the standalone whitespace gate at Ahmed's request. Existing repository integrity checks remain.

2026-10-26 — **S1-T06:** Implemented the [SOC alert normalizer](../../../backend/normalizer/README.md)
for raw Wazuh alerts and OpenSearch exports. Added a file/stdin CLI, offline
incident v1 validation, deterministic identity, explicit severity mapping,
normalized fixtures for both of Achraf's real alerts and dedicated CI tests.
Local implementation does not claim a live collector or full lab-to-model run.
PR, hosted CI and Oussama's assigned review remain pending; S1-T06 is not Done.

## Technical approach

Use Docker as the shared Python environment, without requiring a local virtual environment. Install dependencies during image build, then run checks as user ID 1000 with source files mounted read-only at `/workspace`. Code edits are visible on the next run; dependency or Dockerfile changes require rebuilding.

Keep CI commands explicit: build the image, run Ruff, then run the existing contract suite. Gitleaks runs through its official GitHub Action with the license supplied through GitHub Secrets; automatic PR comments are disabled. Local pre-commit scanning uses the separately installed CLI documented in the setup guide.

**S1-T06:** Unwrap `_source` when present, validate required Wazuh fields,
normalize timestamps to UTC, preserve event identity and observed address/user
roles, then validate the completed incident against the existing offline schema.
Keep mapping independent from API transport, database storage and inference.

## Files / components modified

Added `.python-version`, `.nvmrc`, `requirements.txt`, `pyproject.toml`, `.env.example`, `.dockerignore`, `compose.yaml`, `infrastructure/docker/Dockerfile.dev` and `docs/development.md`.

Updated `.github/workflows/ci.yml`, root `README.md`, `backend/contracts/README.md` and this task row/member section. Removed `tests/contracts/requirements.txt` after moving its dependency into the root requirements file.

**S1-T06:** Added `backend/normalizer/`, `tests/normalizer/` and two expected
incident fixtures. Updated `backend/README.md`, `.github/workflows/ci.yml` and
Ahmed's journal/status row. Existing contracts and original lab evidence are unchanged.

## Tests / validation

Local Linux x86_64 validation during 2026-10-14/15:

- Compose configuration parsed and the development image built successfully. Default execution reported Python 3.12.15; `id` confirmed `uid=1000(dev)` and `gid=1000(dev)`.
- `docker compose run --rm -T dev python -m pip --no-cache-dir check` reported no broken requirements after pinning all 19 installed Python packages.
- `docker compose run --rm -T dev ruff check --no-cache .` passed, and `docker compose run --rm -T dev python -B -m unittest discover -s tests/contracts -v` passed all 17 test methods through the read-only mount.
- Workflow YAML parsed after the CI changes. GitHub metadata confirmed the `GITLEAKS_LICENSE` secret name exists; its value was not read or displayed. This is not evidence that the hosted Gitleaks Action has passed.
- The setup guide/root README check verified balanced code fences and 21 existing local Markdown link targets before this journal update.
- Final pre-commit checks passed for all 77 staged/tracked text files. Gitleaks 8.30.1 found no suspected secrets in the staged changes. The Compose build, Ruff and all 17 contract tests were rerun successfully before committing.

Fresh-checkout reproduction, hosted CI and other-platform validation remain pending. No model-quality, lab-detection or performance benchmark was run.

**S1-T06 local validation (2026-10-26):** Shared Python 3.12 development image
built successfully. All 15 normalizer tests passed, covering both real exports,
raw/wrapped equivalence, stable replay identity and separate deployments,
all 16 severity levels, UTC conversion, malformed inputs, IPv6, strict JSON/CLI
behavior and real FastAPI/SQLite ingestion (201 new, 200 replay, 409 conflict).
Ruff passed. All 109 existing contract/evaluation/backend/baseline tests also
passed (124 tests total including the normalizer suite). Repository integrity,
including the new source/test/documentation files, and changed whitespace checks
passed. A standalone Docker CLI run also produced the first normalized incident.
Gitleaks 8.30.1 scanned the staged implementation diff and found no leaks.
No model inference or live collection is claimed by this task.

## Results / metrics

One Python development service builds and runs locally; 19 package versions are recorded in one requirements file; Ruff and all 17 contract test methods pass. The CI configuration includes secret scanning, repository integrity, Docker build, lint and tests under the existing required job name.

**S1-T06:** Both real alert exports produce contract-valid replay incidents.
Same-event replay retains identity; the second observed event remains distinct.
Wazuh level 5 maps to `low` under documented project policy `wazuh-level-v1`.
This is detector-severity translation, not an AI risk assessment or benchmark.

## Problems encountered

The host Python environment initially lacked the project's pinned format-checking dependencies and local virtual-environment support. Running the checks in the Python 3.12 Docker environment resolved the contract-test dependency mismatch.

The initial draft introduced more setup layers than Ahmed wanted. It was discarded and rebuilt through small explained changes. Gitleaks' organization Action required a license key; Ahmed obtained it and stored it in GitHub Secrets, allowing removal of the temporary manual installer.

**S1-T06:** Existing source exports have OpenSearch wrappers, timezone offsets
and differently scoped IP addresses. The adapter handles wrapped/raw input and
preserves roles explicitly. Host Docker access required sandbox escalation for
local test execution. The earlier observed evidence-manifest line-ending mismatch
is outside the normalizer's changes; original source evidence was preserved.

## Decisions made

Use a Docker-first workflow, one central Python requirements file, a non-root runtime user and a restricted build context. Keep Python and future Node tooling separate. Do not invent environment variables before a component needs them.

Prefer readable direct CI steps over a custom check-runner wrapper. Keep functional/security checks and remove the cosmetic whitespace gate. Use the official Gitleaks Action once its organization license is available.

The Python base image tag can receive updates and is not digest-pinned. Node.js is a version convention only and is not installed in the Python image. The full project bind mount includes local files even when `.dockerignore` excludes them from builds; read-only mounting prevents writes, not reads.

**S1-T06:** Use deployment namespace `wazuh:lab` by default, original Wazuh `id`
as `source_event_id` and UUIDv5-derived incident identity. Require explicit
deployment namespaces for independent installations. Saved files default to
`replay`. Severity ranges 0–3 / 4–6 / 7–9 / 10–12 / 13–15 map to informational /
low / medium / high / critical; Oussama reviews this project policy. Missing
required fields and malformed values fail rather than inventing facts. No verdict,
MITRE ground truth, new contract fields or automated actions are added.

## Related Issues / Pull Requests

[S1-T01 / Issue #9](https://github.com/CyberSOC-ai/cybersoc-ai/issues/9). Branch: `feature/9-reproducible-local-environment`. Assigned reviewer: Achraf (`Eachr4f`). Ahmed authorized commit and branch publication on 2026-10-15. PR creation remains pending; add the actual PR link and hosted validation evidence before completion. S1-T06 remains tracked separately in [issue #14](https://github.com/CyberSOC-ai/cybersoc-ai/issues/14).

**S1-T06:** [Issue #14](https://github.com/CyberSOC-ai/cybersoc-ai/issues/14);
input evidence from [Achraf's merged PR #80](https://github.com/CyberSOC-ai/cybersoc-ai/pull/80).
Branch: `feature/14-soc-alert-normalizer`. Assigned reviewer: Oussama (`Ossel14`).
No PR or approval is claimed. Keep issue #14 open pending the remaining workflow.

## Learning outcome

A Dockerfile builds an image; Compose records how to build and run it; a bind mount makes local code visible without rebuilding for each edit. Requirements record installed packages, while Ruff configuration selects code checks. GitHub Actions reruns the shared checks on PRs; local success does not prove hosted CI passed. Secrets belong in protected configuration, not source files. A documented local implementation becomes Done only after the remaining project workflow requirements are satisfied.

**S1-T06:** An alert reports an observation; normalization arranges the same
facts into the shared incident form. Validation checks that form; tests check
conversion behavior. A user account differs from a hostname, detector severity
differs from AI risk, and replaying an event must preserve its identity.


# 2. Soulaiman
## Assigned tasks

S1-T03 — Baseline SLM runner; reviewer Anas. [Issue #11](https://github.com/CyberSOC-ai/cybersoc-ai/issues/11).

## Work completed

2026-10-22: Started implementation locally on `feature/11-baseline-slm-runner`. Added an input-only No-RAG inference core, explicit local model loading, bounded llama.cpp HTTP generation, strict result/proposal validation, a development-pilot CLI, reproducibility records and behavioral tests. See the [runner guide](../../../ai/baseline/README.md). Soulaiman authorized committing, branch publication and PR creation after the local review. Task completion and reviewer approval are not claimed.

## Technical approach

Reuse the merged v1 contracts and Anas's pilot loader/scorer. Keep model decisions separate from trusted record identity and policy-controlled action fields. Use CPU llama.cpp with immutable GGUF artifacts on this Ryzen/Radeon machine. The initial runtime configuration uses Q4_K_M for practical local inference, not a controlled S5 optimization benchmark. Keep the callable pilot interface and optional adapter for Oussama's proposed API interface around the same core. The API branch is not merged by this task.

## Files / components modified

`ai/baseline/`, `tests/baseline/`, `.github/workflows/ci.yml`, `.gitignore`, draft `docs/adr/ADR-002.md` and this member section/status row. Downloaded runtimes, model weights, local configuration and generated runs stay in ignored `.local/`; a repository-local `.venv` is also ignored. Existing dataset labels, protocol files and contracts are unchanged.

## Tests / validation

Local Python 3.14.3 environment installed the existing pinned requirements. Contract tests: 19 passed. Evaluation tests: 43 passed after sandbox restrictions on temporary files were removed for the test command. Baseline suite: 19 tests passed, including core behavior, real loopback transport, API adapter identities/deadlines and CLI artifact persistence/failure counting. Ruff and repository/local Markdown-link checks passed. Completed Qwen/Phi run artifact hashes were independently rechecked. Subsequent local integration: Docker Desktop started; 103 combined baseline/backend/contract/evaluation tests passed in a non-root Python 3.12 Linux image. One real Qwen request returned HTTP 200 and persisted its correlated result/trace. Native Windows backend storage failed on POSIX ownership APIs; these checks were preserved by testing in Linux. [Integration evidence](../../../ai/baseline/API_INTEGRATION.md) records the pinned backend, image and scope. Pre-publication checks also passed in the shared Docker dev image: Ruff, 19 baseline tests (2 optional API tests skipped), 19 contract tests and 43 evaluation tests. Hosted CI is tracked on the PR; no hosted pass is claimed here.

## Results / metrics

First actual Qwen Q4_K_M development case produced a contract-valid result on CPU: 1 attempted, 1 valid, 13 not attempted. Client latency was 14.728 seconds, excluding cold model load; server reported 188 output tokens and approximately 25.02 decode tokens/second. The triage verdict was undetermined; schema validity does not prove correct analysis. Initial full Qwen pass: 14 attempted, 8 valid and 6 rejected outputs; all failures remain in scoring. The follow-up Qwen pass again had 8 valid/6 rejected; Phi had 13 valid/1 rejected across 14 attempted. Correct triage verdicts across all attempts were 3/14 for Qwen and 1/14 for Phi. These weak pilot observations do not justify a model winner. Full timing/memory and limitations are in the [local results note](../../../ai/baseline/LOCAL_RESULTS.md); source/raw artifacts stay in `.local/runs/`. Judge-based faithfulness and human quality scores are not measured. These are synthetic development observations, not frozen-test benchmarks.

2026-10-23 review fixes: Anas reproduced an unhandled malformed completion event. Added response-shape validation and a CLI regression proving the failed attempt is counted, the next case runs and final scores/status are saved. Aligned prompt references with exact file hashes and expanded source snapshots to include locally edited evaluation dependencies. Native validation: 25 baseline tests passed with two optional API skips, plus 19 contract and 43 evaluation tests; Ruff and repository integrity passed. One real Qwen smoke completed successfully and its artifact hashes checked. Historical runs were dirty and their narrower snapshots do not establish the exact evaluator code; detailed artifacts remain local at the owner's request. See [review fixes](../../../ai/baseline/REVIEW_FIXES.md). Reviewer approval is not claimed.

## Problems encountered

This machine has approximately 14 GiB RAM and integrated Radeon graphics; Oussama's documented NVIDIA GPU is not this environment. Native Python is 3.14.3 rather than the project's Docker/Python 3.12 convention. Some sandboxed tests failed on local socket/temp-directory permissions; the same tests passed when rerun with the necessary permissions. Baseline outputs can fail validation and remain failures rather than repaired or synthetic successes. Phi's GGUF is a community conversion, with exact conversion-to-upstream-checkpoint lineage not established.

## Decisions made

Soulaiman authorized publication on the isolated task branch and requested Anas's review. On 2026-10-23 he authorized fixing the review findings and merging after verification, with no ZIP or external artifact sharing. This is owner authorization, not reviewer approval or independent verification of model results. No agent/RAG/response execution is introduced. Preserve input-only model access, use the same fixed policy for every case, bound tokens and deadlines, reject unobserved proposal targets and leave approval state to trusted code. Do not tune on pilot labels or declare ADR-002 accepted from early pilot evidence. Local API composition and a Qwen-through-API smoke passed against the pinned PR #79 snapshot; owner agreement and rechecking the approved merged backend remain pending.

## Related Issues / Pull Requests

[S1-T03 / #11](https://github.com/CyberSOC-ai/cybersoc-ai/issues/11); input pilot [PR #78](https://github.com/CyberSOC-ai/cybersoc-ai/pull/78), part of [#10](https://github.com/CyberSOC-ai/cybersoc-ai/issues/10). Coordination target: Oussama's open [PR #79](https://github.com/CyberSOC-ai/cybersoc-ai/pull/79). [S1-T03 PR #81](https://github.com/CyberSOC-ai/cybersoc-ai/pull/81) is open from `feature/11-baseline-slm-runner` into `main`. Soulaiman will request Anas's review. No merge or review approval is claimed; #11 remains open.

## Learning outcome

A model runner combines loading, prompt formatting, generation and validated output. A successful JSON/schema check differs from a correct triage decision. Pilot labels and evaluator metadata must stay outside model inputs. Reproducible runs identify the exact executed artifact/configuration, failures, timing scope and limitations; converting a model does not automatically establish its upstream checkpoint provenance.


# 3. Anas
## Assigned tasks

S1-T02 (evaluation dataset and protocol), S1-T07 (No-RAG end-to-end baseline).
S1-T07 runner/lab integration has not been executed in this work.

## Work completed

2026-10-22 — Delivered the synthetic pilot dataset, scoring tools and protocol
drafts. Released soc-eval-v1-pilot.3 after Anas reviewed and approved all 14 cases.
Set label_author to Anas; Oussama's peer review is still pending. Every label keeps
pending_review / needs_review=true. Applied the approved template-family merges:
P11/P13/P14 into G-SSH and P12 into G-FIM. Incident inputs and gold decisions,
actions and evidence are unchanged.

S1-T02 is NOT done: the frozen test split, two-person claim labelling and peer
review are NOT done. Status: Ready for baseline integration (pilot only); the full
S1-T02 task remains incomplete. No judge model, human claim annotations or measured
model performance is claimed. PR #78 is Part of #10. Anas authorized merging the
pilot without waiting for Oussama's review due to time constraints. This owner
decision does not constitute peer approval or completion of the project Definition
of Done. All labels retain pending_review / needs_review=true.

### Remaining work and dependencies

- Anas: prepare separate test cases, keep template families disjoint from development,
  obtain label review, then freeze test membership and record versioned hashes.
- Soulaiman (#11): produce baseline answers on the development incidents using the
  documented runner interface; this pilot is ready for that integration.
- Two independent annotators: label all baseline development answers and their claims,
  covering at least 50 claims. Extend with more answers if needed; preserve original
  ratings, calculate agreement and adjudicate disagreements.
- Oussama: review the 14 labels, protocol drafts and scoring; resolve findings before
  claiming peer-reviewed benchmark readiness.
- Team: choose and record judge model/provider/revision/decoding/retry policy, then
  validate the judge against the adjudicated human annotations.

Do not close #10 or publish pilot scores as final benchmark results.

## Technical approach

Reference [METRICS.md](../../../experiments/METRICS.md) for scoring authority.
Retain nominal Cohen's kappa and raw agreement; implement owner-selected quadratic
weighted Cohen's kappa for ordinal 1–5 scores, null for zero expected disagreement.
Hash metadata changes and all protocol/validation assets with existing tooling.
Keep candidate text in quoted untrusted prompt blocks and labels out of model code.
Execute the README's 15-line baseline-runner example with a contract-valid dummy
predictor; no model is involved.

## Files / components modified

- [Dataset README](../../../datasets/evaluation/soc-eval-v1/README.md), approved
  author/group/version metadata, [guidelines](../../../datasets/evaluation/soc-eval-v1/guidelines/labeling.md),
  [manifest](../../../datasets/evaluation/soc-eval-v1/manifest.json) and split hashes.
- [Protocol](../../../datasets/evaluation/soc-eval-v1/protocol/README.md) agreement
  documentation and [validation templates](../../../datasets/evaluation/soc-eval-v1/validation/README.md).
- [Scorer](../../../ai/evaluation/scoring.py) and [evaluation tests](../../../tests/evaluation/).
- Only this member section and the S1-T02 status row in the sprint journal.

## Tests / validation

Cloud sandbox, no Docker: installed pinned requirements; evaluation discovery:
43 tests passed; contracts discovery: 19 tests passed. Ruff passed. Repository
integrity and local Markdown links passed: 158 tracked text files checked.
Real output and hosted CI are recorded in PR #78. New tests check a hand-computed
weighted-kappa example, invalid and degenerate ratings, and the actual README
example using incident-ID predictions. Existing integrity, oracle, shortcut,
faithfulness, nominal-kappa and prompt-boundary tests also passed. Mutations use
temporary copies, never the dataset. Software tests are not peer review or human
claim-validation evidence.

## Results / metrics

Composition: 14 synthetic development cases, 6 true positives, 8 false positives,
four template-family groups, no test split. Gold severity: informational 8,
medium 4, high 2. Shortcut verdict accuracy: ticket 7/14, wording 8/14; detector
severity accuracy 5/14; action exact match: never-act 11/14, always-block 9/14.
The 0.80 line is a local data-quality check, not a project metric or acceptance
threshold. The arithmetic fixture [1,2,3] versus [1,3,3] gives quadratic weighted
kappa 0.8 and raw agreement 2/3; these are software fixtures, not human results.

## Problems encountered

The pilot has no frozen test split, collected lab evidence, real baseline answer
set or independent claim annotations. Shared template families limit independence.
Peer review remains outstanding. Empty templates and prompt boundary tests do not
establish judge validity or model-level injection resistance.

## Decisions made

Apply the rule that cases sharing a scenario template family or describing the
same episode share a group_id; preserve other groups. Anas approved all cases;
Oussama has not reviewed them, so nothing is accepted. Label ALL baseline answers
on development cases with no sampling seed. If their claims total fewer than the
CDC minimum of 50, extend with more answers; never reduce the minimum. Preserve
original independent ratings before adjudication. Use quadratic weighted Cohen's
kappa for ordinal scores. Judge model/provider/revision/decoding/retry policy:
TBD - team decision. Configuration remains null/not_selected. Proposal scoring
does not establish execution safety. Git does not enforce evaluator-only access.

## Related Issues / Pull Requests

[Issue #10 / S1-T02](https://github.com/CyberSOC-ai/cybersoc-ai/issues/10),
[PR #78](https://github.com/CyberSOC-ai/cybersoc-ai/pull/78), branch
feature/10-soc-eval-v1. Owner Anas; peer reviewer Oussama (@Ossel14).
The [S1-T03 handoff](../../../datasets/evaluation/soc-eval-v1/README.md#for-s1-t03-baseline-runner)
lets Soulaiman (@soulaimane-22) use this pilot for [#11](https://github.com/CyberSOC-ai/cybersoc-ai/issues/11).
Labels await peer review; do not tune on these cases or publish scores as final
benchmark results. Issue #10 remains open. Anas authorized PR #78 to be merged
for pilot integration without waiting for peer review; the review request remains
outstanding.

## Learning outcome

Owner approval, peer review and two-person claim annotation are distinct evidence.
Grouping records construction dependence; hashes establish identity, not truth.
Contextual support differs from correctness. Claims within an answer are not
independent samples. Quadratic weighting makes ordinal disagreement explicit,
while a zero expected disagreement gives no usable kappa estimate.


# 4. Achraf
## Assigned tasks

S1-T05

## Work completed

S1-T05: On 2026-10-22, prepared [setup](../../../infrastructure/soc-lab/SETUP.md), [results/handoff](../../../infrastructure/soc-lab/S1-T05-RESULTS.md), two user-supplied raw alert exports and screenshot. Actual central deployment uses Windows Docker Desktop and two Ubuntu VMs. Review, CI, credential rotation and merge pending; not Done.

## Technical approach

Use Wazuh 4.14.9 central containers on Windows / WSL 2, endpoint agent on Ubuntu and separate internal-network simulation. Journald collects SSH. This documents an adaptation of the S0-T07 central VM plan.

## Files / components modified

Added infrastructure/soc-lab/SETUP.md, S1-T05-RESULTS.md and evidence/. Updated Achraf section only. No private runtime Compose, credentials, keys or VM images shipped.

## Tests / validation

User evidence confirms agent connected, active-response disabled locally, and two indexed rule-5760/level-5 alerts at 13:43:25.130Z and 13:46:26.157Z. Package checks verify JSON fields, original bytes, SHA-256 and links; hosted CI and full lab isolation/rebuild checks remain pending. No automated secret scanner or runtime benchmark claimed.

## Results / metrics

Two distinct live SSH-failure observations, one dashboard screenshot. Correlated brute force, performance metrics and full original run metadata are not established. Detector firedtimes is not an attempt counter.

## Problems encountered

Initial 11-failure attempt coincided with disconnected manager and is not validated detection. Docker disk-full error observed with about 1 GB free; user cleanup restored 22.7 GB. Credential mismatches fixed during setup; disclosed passwords require rotation before final acceptance.

## Decisions made

Use actual Docker Desktop topology and validate repeatable single-failure behavior without claiming correlation. Preserve failed attempts and missing metadata. User retains merge control.

## Related Issues / Pull Requests

S1-T05: confirm issue number before adding closing keyword. Branch feature/s1-t05-soc-lab-mvp; reviewer Ahmed (@ElrhAhmed). Add actual PR link and CI evidence before Done. Normalization is S1-T06 / issue #14.

## Learning outcome

Raw endpoint events, manager alerts and OpenSearch exports differ. Unwrap _source for normalizer input, preserve provenance and normalize timestamps explicitly. Storage readiness and consistent service credentials affect repeatability.


# 5. Oussama
## Assigned tasks

S1-T04 — FastAPI core + incident ingestion / [Issue #12](https://github.com/CyberSOC-ai/cybersoc-ai/issues/12). Reviewer: Soulaiman (`soulaimane-22`).

## Work completed

2026-10-22: Implemented the independent S1-T04 backend on `feature/12-fastapi-incident-ingestion`, based on latest `origin/main` at `e801410` (including the merged evaluation pilot, PR #78). Added GET `/health`, POST `/incidents`, POST `/incidents/{incident_id}/investigate`, strict v1 validation, SQLite persistence, OpenAPI documentation and backend tests. Actual application returns 503 when no real runner is configured. Controlled successful runners exist only in tests. No model, RAG, training or response execution was implemented.

Documented the [runner interface](../../../backend/RUNNER_INTERFACE.md) before implementing dispatch. On 2026-10-23, Soulaiman formally approved PR #79 and merged it at `7e4bdb2533541a1cc52feff43b3c72d48280d14f`. His reported Qwen integration agrees the synchronous Linux No-RAG adapter; Issue #11 does not formally block independent backend work.

2026-10-23 — documentation follow-up: Updated only the backend guide/interface and this member section to record approval, scoped integration evidence, Linux support/native Windows limitation and the existing 180-second CPU setting alongside the unchanged 30-second API default. Re-read Issue #12's exact criteria and CDC §14: technical acceptance is satisfied, with no additional blocking code requirement identified. Formal Done/closure awaits this follow-up's approved publication/check/review/merge workflow and explicit issue-closure approval.

## Technical approach

Validate raw JSON against the unchanged offline Draft 2020-12 registry with format checking, without Pydantic coercion. Use a repository protocol and private file-backed SQLite outside the source tree. Atomic transactions and uniqueness constraints enforce incident/event identity; preserve original events and record delivery metadata separately.

Inject a trusted synchronous baseline adapter at application construction. Bound execution off the event loop to one call and a 30-second deadline by default, with no waiting queue. A timed-out/cancelled call retains capacity until it actually exits; late output is discarded. Persist validated result and baseline trace together before reporting success. API/storage health and model configuration are separate.

## Files / components modified

Added `backend/app.py`, `repository.py`, `runner.py`, `validation.py`, `__init__.py`, `backend/README.md`, `backend/RUNNER_INTERFACE.md` and `tests/backend/test_api.py`. Updated root dependency pins, Compose, development Dockerfile, `.env.example`, CI test discovery, root/development guides, the S1-T04 row and this member section. Existing interchange schemas, evaluation assets, other member sections and shared integration sections are unchanged.

## Tests / validation

Python 3.12 Docker development image built with the pinned API dependencies; `pip check` passed. Backend tests cover strict inputs and untrusted outputs, malformed/oversized/streamed JSON, sanitized failures, local OpenAPI references, duplicate/conflicting events, concurrent atomic ingestion, persistence, timeout/late-result/cancellation behavior, responsive health and durable result/trace records. Final Python 3.12 Docker results: 20 backend tests, 19 unchanged contract tests and 43 evaluation tests passed (82 total). Docker Ruff and dependency consistency checks passed. Tracked-file integrity/link checks passed for 166 files, staged whitespace checks passed, and Gitleaks 8.30.1 found no leaks in staged changes. Compose configuration parsed successfully. Those initial local results preceded PR publication; subsequent hosted evidence is recorded below.

Actual loopback container smoke checks passed for health, incident ingestion, OpenAPI and default 503 dependency errors. After restarting the isolated API, the same incident returned 200 with `created: false`, demonstrating persisted identity. The smoke service was stopped; its private synthetic-data volume was retained. These original backend-only smoke checks performed no real inference, GPU measurement or live lab ingestion; they are distinct from Soulaiman's later Qwen ASGI integration.

2026-10-23 — hosted and reviewer evidence: [PR #79 final-head CI](https://github.com/CyberSOC-ai/cybersoc-ai/actions/runs/40011091986) passed at head `38e5fcaecead21e4cac46588af50ccb43f1dd299`; [merge/main CI](https://github.com/CyberSOC-ai/cybersoc-ai/actions/runs/40011328644) passed at merge `7e4bdb2533541a1cc52feff43b3c72d48280d14f`. Both ran backend, baseline, contract and evaluation tests, image build, lint, integrity and secret scanning. Soulaiman's [formal approval](https://github.com/CyberSOC-ai/cybersoc-ai/pull/79#pullrequestreview-5633412190) is separate from his [reported integration results](https://github.com/CyberSOC-ai/cybersoc-ai/pull/79#issuecomment-6353520974).

His [integration record](../../../ai/baseline/API_INTEGRATION.md) reports 103 tests passing in Python 3.12/Linux and one actual Qwen in-process ASGI request returning 200 with matching SQLite result/trace, plus 201 new ingestion and 200 duplicate handling against backend snapshot `d1957f7`. Backend files were unchanged at the final approved PR head. This is historical owner-reported smoke evidence with an uncommitted runner checkout and local detailed artifacts, not independently reproduced benchmark evidence. Real-model Uvicorn/external-client deployment, Phi-through-API, authentication and live Wazuh integration remain unverified. No new inference is performed in this documentation follow-up.

2026-10-23 — follow-up checks: repository integrity/local file links passed for 194 tracked text files; whitespace and balanced code-fence checks passed. Both existing controlled API-adapter integration tests passed in Python 3.12 Docker (2 tests, no model inference). Verified that only the three authorized documentation files changed and other members/shared sections are untouched. Original PR and merge CI evidence above was rechecked; this local follow-up has no hosted CI run yet.

## Results / metrics

Three API operations, one repository abstraction/SQLite implementation and one documented runner protocol. Defaults: 65536-byte request body, five-second body receipt deadline, 131072-byte serialized candidate limit, batch/concurrency admission of one inference call and 30-second inference deadline. The backend test suite uses controlled inference fixtures; Soulaiman separately reports the single successful Qwen ASGI smoke. Neither is a model-quality benchmark.

## Problems encountered

Sandbox Docker-socket and package-network restrictions required approved tool access. The first deep-nesting test exposed a parser-dependent difference (valid nested JSON could reach schema validation); explicit nesting bounds now reject it consistently. The initial isolated Compose smoke start lacked its project-specific image tag; a cached project build resolved it. No failed attempt is counted as passed.

Python threads cannot guarantee hard inference cancellation; a real runner must honor the monotonic deadline or use a supervised process/service. An abruptly terminated process or cancelled HTTP handler is not a recoverable job queue. The loopback development API has no authentication; identity/access controls are required before exposure beyond loopback. Native Windows Python is unsupported because ownership/runtime checks use POSIX APIs; use Linux, Docker/Linux containers or an appropriate Linux environment without bypassing those checks.

## Decisions made

Keep the default application unconfigured (503); real inference requires explicit trusted composition through the supplied S1-T03 adapter. Use controlled runners only in tests; missing dependency is 503, busy is 503, timeout is 504, invalid output is 502, conflicting event identity is 409. Never echo raw exceptions or model text in errors. Preserve source severity separately from AI risk; proposals remain inert data.

Use a writable, private named volume at `/runtime` with source mounted read-only. Default host storage is a private directory under `/tmp`, overridable outside the checkout. Only one Uvicorn worker is supported for the laptop concurrency budget. The adapter contract is agreed for the tested Linux scope. The backend default remains 30 seconds; existing `compose_api(..., timeout_seconds=180)` supplies the bounded CPU setting and one-call concurrency. Phi may need that larger budget, but Phi-through-API is not demonstrated. Model loading/quality work stays with #11; live normalization/full lab integration stays with #14/#15.

## Related Issues / Pull Requests

[Issue #12](https://github.com/CyberSOC-ai/cybersoc-ai/issues/12) remains open. Implementation [PR #79](https://github.com/CyberSOC-ai/cybersoc-ai/pull/79) was approved and merged by Soulaiman on 2026-10-23 at 19:25:40 UTC. Declared prerequisites [#3](https://github.com/CyberSOC-ai/cybersoc-ai/issues/3) and [#9](https://github.com/CyberSOC-ai/cybersoc-ai/issues/9) are completed. The S1-T03 adapter merged via [PR #81](https://github.com/CyberSOC-ai/cybersoc-ai/pull/81); this does not imply [Issue #11](https://github.com/CyberSOC-ai/cybersoc-ai/issues/11) is complete. [#14](https://github.com/CyberSOC-ai/cybersoc-ai/issues/14)/[#15](https://github.com/CyberSOC-ai/cybersoc-ai/issues/15) own remaining live pipeline integration. Documentation follow-up branch: `docs/12-integration-evidence-followup`, based on synchronized main `7e4bdb2`. Only a local commit is authorized for this follow-up; push, PR, merge and closure require further approval. See the [acceptance/DoD assessment](../../../backend/README.md#issue-12-acceptance-and-closure-assessment--2026-10-23).

## Learning outcome

JSON Schema validation and OpenAPI documentation are separate concerns: HTTP models must not silently coerce invalid contract data. Event uniqueness must be enforced transactionally, rather than with an unprotected check-then-insert. A response timeout is not cancellation of compute, and a passing fake-adapter test is not evidence of a working real-model baseline.

# Shared Sprint Integration

## Integrated components

> To be completed by the sprint coordinator or explicitly assigned person.

## Architecture changes

> To be completed by the sprint coordinator or explicitly assigned person.

## Shared experiments

> To be completed by the sprint coordinator or explicitly assigned person.

## Security considerations

> To be completed by the sprint coordinator or explicitly assigned person.

## Known limitations

> To be completed by the sprint coordinator or explicitly assigned person.

## Exit criteria verification

> To be completed by the sprint coordinator or explicitly assigned person.

## Sprint retrospective

> To be completed by the sprint coordinator or explicitly assigned person.

Individual work is edited only in the named member section. Shared sections are maintained by the sprint coordinator or explicitly assigned person. Each task entry links its Issue and PR before Done.

# S0-T06 — Experiment and version-tracking convention

Owner: Anas · Reviewer: Ahmed · Date: 2026-10-15 · [Issue #6](https://github.com/CyberSOC-ai/cybersoc-ai/issues/6)

Status: implemented documentation proposal; review, hosted CI and merge pending.
Authority: [CDC §§6.5, 8, 9.8, 11.4, 14](../docs/CDC.md), [contracts](../backend/contracts/README.md), [inventory](../datasets/README.md), and [security policy](../security/README.md).
This task defines conventions and templates. Dataset construction / executable scoring belong to S1-T02, official environment freeze to S5-T01, tracing/dashboard deployment to S5-T03. No model, dataset, tracking server or GPU benchmark has been run here.

## Start here

1. Write the question and the single variable being changed; use CDC §9.6 staged ablations.
2. Copy [experiment.json](templates/experiment.json) and [environment.json](templates/environment.json) outside Git for real runs. Fill nulls before an official run; use explicit applicability reasons for unused components.
3. Pin every input using the identity rules below. Verify the frozen split and exclude held-out incident groups from training and retrieval.
4. Keep per-case outputs, claims, scores and traces in authorized artifact storage. Store a small sanitized record / manifest in Git only when safe and appropriately licensed.
5. Copy [results.json](templates/results.json), record failures as well as successes, and complete [REPORT.md](templates/REPORT.md). Do not treat the tracking UI as the sole copy.
6. Use the [metric protocol](METRICS.md), review the [worked examples](examples/README.md), and check the acceptance table below before reporting a comparison.

The JSON files are fill-in templates, not new service contracts or schema validators. Null means unfilled/unavailable, never zero. A completed record must explain every remaining null. Retain unknown, error, unsupported and not-applicable outcomes distinctly. Synthetic fixtures must say `synthetic_example: true` and must never be counted as measured results.

## Identity and version rules

| Item | Convention / required evidence |
|---|---|
| Experiment definition | `EXP-S0T06-example-v1` illustrates the pattern `EXP-<task>-<slug>-v<integer>`. Stable across repetitions of one question; new version for changed design. |
| Run | `RUN-<UTC YYYYMMDDTHHMMSSZ>-<unique suffix>`; unique per attempt, including retries and failures. Never overwrite a previous run. |
| Protocol / record / environment | Separate `protocol_version`, `record_version`, `environment_id` and environment digest. Version record structure independently from workflow contracts. |
| Model / tokenizer | Publisher ID plus immutable upstream revision, tokenizer revision and artifact SHA-256 where acquired; record quantization format, producer and revision separately. A family name or mutable branch is insufficient. |
| Prompt | `PRM-<purpose>-v<integer>` plus SHA-256 of the exact UTF-8 template and reference to the sanitized rendered input. Record template variables and decoding settings. Do not normalize line endings silently. |
| Dataset | `soc-eval-v1` release plus immutable manifest SHA-256, split manifest SHA-256, case IDs, incident-group IDs and source snapshots. A changed label, split or included record creates a new manifest/release. |
| Retrieval / graph | Immutable corpus snapshot refs, embedding model/revision, chunk size/overlap/unit, index build/config digest, graph snapshot/schema, query/fusion settings and K. `not_applicable` with a reason for No-RAG. |
| Code / configuration | Full Git commit SHA plus SHA-256 of the exact saved configuration bytes. Official runs require a clean checkout; exploratory dirty runs record dirty state and a protected patch reference and cannot masquerade as official results. |
| Judge | Model/provider revision, extraction and judging prompt revisions/digests, rubric version, generation settings, raw sanitized decisions and human-validation subset version. |
| Trace | Preserve `schema_version: 1.0.0`, opaque `trace_id`, and required version keys from the existing trace schema. Stable names in `versions` resolve through the experiment manifest to immutable revisions/digests. |

SHA-256 identifies bytes, not permission, truth or safety. Store checksum manifests alongside artifacts and verify on acquisition/use. Use immutable references in official records; mutable aliases such as `latest` may be convenience labels only. Never replace an upstream revision with the Git commit of this project.

Dataset and split manifest hashes must cover every case's content (inputs, expected labels and evaluator context), directly or through recorded per-case content hashes, not only IDs or paths. Verify the manifests and all referenced case content against those hashes before scoring.

## Experiment record and environment

The experiment template covers all CDC §11.4 fields, including model, tokenizer, prompt, dataset/split, embedding/chunking, retrieval/graph, inference, workflow, judge, trace references, UTC time and code SHA. Official records identify the input/output artifacts, their hashes, execution status, case counts and comparison baseline.

The environment template records CPU/GPU/RAM/VRAM, OS, Python, driver/runtime/library versions, dependency lock/container digest, determinism, seeds, concurrency, context/output limits and timing configuration. Keep `exploratory` distinct from `official`; S5-T01 authorizes the final reference environment. A laptop experiment does not freeze it.

Compare latency only under the same documented hardware, workload and timing boundary. Record warmup/repetition counts, cold versus warm cache, batch size/concurrency, streaming behavior and instrumentation state. Separate model-only timing from end-to-end timing. Synchronize accelerator timing where needed; report units and measured peak-memory scope. A fixed seed or temperature zero is not a guarantee of cross-platform determinism; see [research notes](RESEARCH.md).

## Dataset and artifact boundaries

Interpret CDC §9.3's training data as a subset of §9.8's development partition; S1-T02 records train/tuning membership inside development and freezes the independent test set. This interpretation is proposed for review, not an unreviewed rewrite of the CDC. Do not tune prompts, thresholds, judge rubrics or retrieval using reported test results. A subsequent design change needs a new preregistered evaluation plan and honest disclosure of test reuse.

Split at incident-group level before generating chunks, replay records or paraphrases. Keep all near-duplicates/derived records from one incident in the same partition. A reusable scenario type may occur in both partitions only when distinct executions are independent and the limitation is reported. Record group overlap and exact/near-duplicate checks; exact hashes alone cannot find semantic duplicates. Exclude test incidents, labels and derived records from vector/graph indexes and fine-tuning data. Public general knowledge about a technique remains eligible; a test incident's answer does not.

Store large/private outputs under ADR-006's eventual access-controlled artifact policy. ADR-010 does not select that provider. Redact before logging/export; references must resolve for authorized reviewers without exposing credentials, signed URLs or sensitive raw logs. Record sanitization version and access/retention owner. Use synthetic secret canaries for security tests, never real credentials.

## Trace compatibility and tracking

Use [trace.schema.json](../backend/contracts/v1/trace.schema.json) unchanged, including `baseline`, `single_agent` and `multi_agent`. A baseline cannot claim agent steps. Link `run_id` to `trace_id` in the experiment manifest rather than adding forbidden fields to closed contract objects. Record per-step tools, sanitized I/O refs, failures and latency. Check step order, references and workflow consistency beyond schema validation.

[ADR-010](../docs/adr/ADR-010.md) proposes MLflow. Keep the project experiment ID separate from MLflow's experiment ID (a grouping), and save the MLflow run ID alongside the project run ID. Link native tracking trace IDs to project trace IDs explicitly. Logging run metrics alone does not create a trace. Export project records and traces in documented JSON forms so later tool changes do not erase provenance. S5-T03 implements the adapter and proves export/reload behavior.

## Acceptance and verification

| Issue #6 requirement | Deliverable | Verification / handoff |
|---|---|---|
| Experiment and version conventions | Identity table; [experiment template](templates/experiment.json) | Resolve required revisions and digests; unique attempts; label synthetic examples. |
| Benchmark/environment format | [Environment](templates/environment.json), [results](templates/results.json), [report](templates/REPORT.md) | Confirm same environment and case set; preserve denominator, failures, units, conclusion and limits. |
| Trace convention | Compatibility section; existing trace schema | Validate synthetic trace against v1; verify project run/trace mapping without schema changes. |
| Metrics and split rule | [METRICS.md](METRICS.md), dataset boundaries | Hand-check worked values and N/A cases; S1-T02 implements tests and real split checks. |
| Tracking tool | [ADR-010](../docs/adr/ADR-010.md) | Review documented tradeoffs; deployment/export validation deferred to S5-T03. |
| Evidence / DoD | [VALIDATION.md](VALIDATION.md); Anas sprint section | Local checks, PR CI and Ahmed review; no task closure before applicable DoD evidence. |

Before acceptance, a teammate should fill a record using these instructions and resolve its artifacts. This usability check and real dataset overlap checks remain pending; a synthetic walkthrough cannot prove either. CDC §11.4 mentions Sprint 1 for ADR-010 whereas task #6 / §23 say Sprint 0; this delivery follows the issue and records the inconsistency without altering shared planning.

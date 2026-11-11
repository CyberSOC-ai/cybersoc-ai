# Baseline-first project roadmap

Authorized by Ahmed on 11 November 2026. This replaces the execution order, future ownership and dependency mapping of the original Sprint 0–8 plan; all brief/CDC technical and experimental requirements remain. Historical contribution records are preserved.

GitHub tracking: [roadmap #94](https://github.com/CyberSOC-ai/cybersoc-ai/issues/94) · [project board](https://github.com/orgs/CyberSOC-ai/projects/1).

## Initial delivery and ownership

**Ahmed (@ElrhAhmed) owns only B0, [#95](https://github.com/CyberSOC-ai/cybersoc-ai/issues/95): fresh shared foundation → complete No-RAG → complete small reusable Vector RAG → independent reproduction and walkthrough.** These ordered checkpoints are one initial task, delivered through small PRs. Downstream implementation starts after the complete B0 handoff is accepted. Teammates may support labels, source/license checks, review and planning earlier.

**All downstream owners and reviewers are unassigned for Ahmed to choose.** Historical journal names are not future assignments. No teammate or reviewer is assigned by this roadmap beyond Ahmed’s B0 ownership.

B0 establishes correct execution, reusability, one local/cloud artifact persistence cycle and basic evaluation. It does not require perfect model answers, a whole-corpus build, larger-scale optimization or fine-tuning. Bigger datasets and expanded implementations follow the handoff. Existing code can be reused, changed or replaced; prior completed tasks do not block the fresh implementation.

## Sprint / stage mapping

Stages are delivery gates rather than invented calendar commitments. Estimate B0 first, then schedule remaining work against **feature freeze 28 December 2026**, buffer **29–31 December**, and submission **1 January 2027**. Hardware availability and the remaining capacity must be checked before promising dates. No requirement becomes optional because of scheduling pressure.

| Stage | Deliverables | Ownership | Journal |
|---|---|---|---|
| B0 | [#95](https://github.com/CyberSOC-ai/cybersoc-ai/issues/95) Deliver shared foundation, No-RAG and small reusable Vector RAG | Ahmed; reviewer TBD | [Journal](sprints/revised-b0/README.md) |
| R1 | [#96](https://github.com/CyberSOC-ai/cybersoc-ai/issues/96) Expand shared data and deliver threat-intelligence ingestion/lookup; [#97](https://github.com/CyberSOC-ai/cybersoc-ai/issues/97) Deliver complete reproducible Graph RAG; [#98](https://github.com/CyberSOC-ai/cybersoc-ai/issues/98) Integrate investigation modes and reproducible API deployment; [#99](https://github.com/CyberSOC-ai/cybersoc-ai/issues/99) Deliver reviewed evaluation release and common comparison harness | Unassigned; Ahmed selects owner/reviewer | [Journal](sprints/revised-r1/README.md) |
| R2 | [#100](https://github.com/CyberSOC-ai/cybersoc-ai/issues/100) Deliver Hybrid RAG and four-mode development comparison | Unassigned; Ahmed selects owner/reviewer | [Journal](sprints/revised-r2/README.md) |
| R3 | [#101](https://github.com/CyberSOC-ai/cybersoc-ai/issues/101) Deliver single-agent and six-agent LangGraph investigation; [#102](https://github.com/CyberSOC-ai/cybersoc-ai/issues/102) Deliver reference SOC lab and human-approved sandbox response; [#103](https://github.com/CyberSOC-ai/cybersoc-ai/issues/103) Deliver React/TypeScript analyst dashboard and workflow tests; [#104](https://github.com/CyberSOC-ai/cybersoc-ai/issues/104) Extend LLMOps tracking, agent traces and quality monitoring | Unassigned; Ahmed selects owner/reviewer | [Journal](sprints/revised-r3/README.md) |
| R4 | [#105](https://github.com/CyberSOC-ai/cybersoc-ai/issues/105) Complete SLM comparison and inference/serving optimization study; [#106](https://github.com/CyberSOC-ai/cybersoc-ai/issues/106) Run required QLoRA experiment and Base vs Fine-tuned comparison; [#107](https://github.com/CyberSOC-ai/cybersoc-ai/issues/107) Evaluate all nine LLM security threats with mitigations off/on | Unassigned; Ahmed selects owner/reviewer | [Journal](sprints/revised-r4/README.md) |
| R5 | [#108](https://github.com/CyberSOC-ai/cybersoc-ai/issues/108) Validate release candidate and freeze final integrated benchmarks | Unassigned; Ahmed selects owner/reviewer | [Journal](sprints/revised-r5/README.md) |
| R6 | [#109](https://github.com/CyberSOC-ai/cybersoc-ai/issues/109) Finalize Markdown report, contribution journals and five-minute demo | Unassigned; Ahmed selects owner/reviewer | [Journal](sprints/revised-r6/README.md) |

R1 data, graph, API and evaluation work can run in parallel after B0. R2 Hybrid acceptance requires real retrievers. R3 agent, response, UI and tracing work can overlap once their interfaces are stable. R4 experiment preparation begins after B0 as inputs become ready; official evaluation needs the reviewed frozen test protocol and recorded reference environment. R5 is final integration acceptance, not the first time tests are written. Reports are written continuously, with consolidation checkpoints after R2 and R3.

## Complete deliverables and acceptance

### B0: Deliver shared foundation, No-RAG and small reusable Vector RAG — [#95](https://github.com/CyberSOC-ai/cybersoc-ai/issues/95)

Owner: Ahmed (@ElrhAhmed). Reviewer: unassigned. Dependencies: None; this is the initial delivery.

- [ ] Define the fresh small knowledge corpus and normalized incident release; inspect source licenses, provenance and available ground truth. Include representative MITRE ATT&CK, CVE/CWE, threat-intelligence and eligible historical SOC examples.
- [ ] Publish separate knowledge, incident and evaluator-label artifacts. Reserve final-test scenarios/groups; never put labels or held-out incidents into retrieval/model inputs. Extend reviewed evaluation later rather than blocking this small baseline on a final benchmark.
- [ ] Inventory old artifacts and references for the planned reset; explicitly identify disposable paths, database collections/volumes and shared objects before deletion. Preserve code, historical evidence and credentials. No blanket cleanup is authorized by this roadmap issue.
- [ ] Choose and document one shared artifact store, pinned dependencies, model/tokenizer references and local/cloud setup. GitHub owns source/configuration; notebooks launch reusable repository modules.
- [ ] Implement the common model runtime/Python interface with bounded generation, structured output validation, deadlines and sanitized errors.
- [ ] Deliver No-RAG first: incident -> model -> validated result/trace; save inputs, outputs, failures and basic quality/latency observations.
- [ ] Implement complete small Vector RAG: normalization consumption, tokenizer-aware chunking, embeddings, persistent index, filtered retrieval, provenance/citations, generation, validation and independent retrieval checks.
- [ ] Establish lightweight LLMOps: portable run IDs/JSON records, model/prompt/corpus/index/config/code versions, checksums and a small tested tracking integration (MLflow is the existing proposal, not an already-deployed service).
- [ ] Demonstrate one cloud execution and persistence cycle; save and restore the index plus all supporting manifests/artifacts without recomputing document embeddings. Record cloud/local runtime compatibility and hardware limits.
- [ ] Publish fetch/start/test/restore commands, a walkthrough explaining the technologies and artifacts, and a fresh-checkout reproduction by a teammate selected later.

**Acceptance evidence:**

- [ ] Foundation, No-RAG and Vector RAG checkpoints are delivered in that order, through small reviewable PRs under this single initial task.
- [ ] A second member can fetch the release, run both modes on common small incidents, inspect recorded results and restore prepared artifacts without Ahmed's intervention.
- [ ] Relevant tests and hosted CI pass; malformed inputs, dependency failures, empty retrieval, invalid output and deadline behavior are explicit; recommendations remain proposals.
- [ ] Correct execution/reusability and measured limitations are demonstrated. No perfect model quality, whole-corpus build, final fine-tuning or large-scale optimization is required for B0.
- [ ] Ahmed presents the workflow, and reproduction evidence is recorded. Only then is the initial handoff accepted and downstream implementation opened.

### R1: Expand shared data and deliver threat-intelligence ingestion/lookup — [#96](https://github.com/CyberSOC-ai/cybersoc-ai/issues/96)

Owner: Unassigned. Reviewer: unassigned. Dependencies: [#95](https://github.com/CyberSOC-ai/cybersoc-ai/issues/95).

- [ ] Expand the small B0 release into versioned development and comparison releases with source licenses, acquisition commands, checksums and access rules.
- [ ] Include MITRE ATT&CK, CVE/CWE, SOC history and at least one real approved threat-intelligence IOC snapshot; normalize IP/domain/hash, malware/tags/confidence where supported.
- [ ] Deliver structured IOC lookup and supported vector/graph projections; preserve provenance and source identity without inventing relationships.
- [ ] Split related scenario/group records together; exclude held-out incidents and near copies from retrieval and later training.
- [ ] Publish sanitized exports and artifact release instructions; verify one local and one cloud consumer. Large acquisition/index builds are later work, not retroactive B0 acceptance.

**Acceptance evidence:**

- [ ] Expanded release is reproducible by another member and consumed by Vector/Graph with coverage differences reported.
- [ ] IOC lookup and ingest rejection/provenance tests pass; source availability is independent of an individual's PC.

### R1: Deliver complete reproducible Graph RAG — [#97](https://github.com/CyberSOC-ai/cybersoc-ai/issues/97)

Owner: Unassigned. Reviewer: unassigned. Dependencies: [#95](https://github.com/CyberSOC-ai/cybersoc-ai/issues/95).

- [ ] Own ontology, extraction, ETL, Neo4j deployment/population, constraints, bounded parameterized queries, retrieval, generation and packaging end to end.
- [ ] Represent User, Host, IPAddress, Alert, Vulnerability, Malware, AttackTechnique and ThreatIndicator with source-record provenance and deterministic identity.
- [ ] Use the B0 common source release initially and expanded releases later. Reuse, modify or replace prior code on merit; PR #91 is historical/in-progress input, not an automatic acceptance gate.
- [ ] Reuse the shared model interface and result/evidence contracts. Preserve supported claims, permissions, error handling and citations.
- [ ] Publish source-coverage report, restore/export instructions, tests and an independent reproduction.

**Acceptance evidence:**

- [ ] A common incident produces a schema-valid, source-traceable graph-grounded investigation through a real populated Neo4j instance.
- [ ] Query/extraction tests and fresh-checkout reproduction pass; observations are distinguished from inferred or unsupported relationships.

### R1: Integrate investigation modes and reproducible API deployment — [#98](https://github.com/CyberSOC-ai/cybersoc-ai/issues/98)

Owner: Unassigned. Reviewer: unassigned. Dependencies: [#95](https://github.com/CyberSOC-ai/cybersoc-ai/issues/95).

- [ ] Integrate the accepted baseline using explicit trusted composition; expose No-RAG/Vector first and add Graph/Hybrid/agent adapters as they become ready.
- [ ] Preserve strict contracts, event deduplication, transactional persistence, correlated traces, limits, deadlines, shared capacity and explicit dependency failures.
- [ ] Verify model/database networking for local and cloud-supported deployments; do not assume separate containers share localhost.
- [ ] Provide authentication/authorization before exposure beyond trusted loopback and before approval decisions; protect service credentials.
- [ ] Publish OpenAPI, typed-client handoff and reproducible startup/backup/restore/health instructions. Prior merged API work can be reused or replaced without declaring the new baseline already accepted.

**Acceptance evidence:**

- [ ] A real model plus prepared vector index works through a served API; controlled tests alone are not claimed as live integration.
- [ ] A teammate can start the supported topology; new modes use the shared result contracts and no failed retrieval silently becomes No-RAG.

### R1: Deliver reviewed evaluation release and common comparison harness — [#99](https://github.com/CyberSOC-ai/cybersoc-ai/issues/99)

Owner: Unassigned. Reviewer: unassigned. Dependencies: [#95](https://github.com/CyberSOC-ai/cybersoc-ai/issues/95).

- [ ] Review labels for verdict, severity, MITRE mappings and expected actions independently of detector annotations; retain uncertain/unavailable labels explicitly.
- [ ] Define development/training-eligible data and a frozen final test split grouped by scenario/run; prohibit test-driven tuning and retrieval leakage.
- [ ] Evaluate retrieval independently with Precision@K, Recall@K and MRR (default K=5); document relevance-pool completeness and document/passage units.
- [ ] Use common decision/output expectations across No-RAG/Vector/Graph/Hybrid; keep retrieval and generation failures in intended/attempted/valid counts.
- [ ] Implement claim-level faithfulness/hallucination, four-criterion quality rubric, action correctness and judge validation with at least 50 claims double-labelled by two members and agreement reported.
- [ ] Define the reference benchmark environment early; pin its actual identity before official measurements and document hardware/runtime support and fair comparison budgets.

**Acceptance evidence:**

- [ ] A second member reproduces metric calculations and detects changed hashes, leakage and missing/failed cases.
- [ ] Reviewed frozen test release and judge-validation evidence are ready before final results; no exhaustive-recall or blind-test claim is made for development samples.

### R2: Deliver Hybrid RAG and four-mode development comparison — [#100](https://github.com/CyberSOC-ai/cybersoc-ai/issues/100)

Owner: Unassigned. Reviewer: unassigned. Dependencies: [#95](https://github.com/CyberSOC-ai/cybersoc-ai/issues/95), [#97](https://github.com/CyberSOC-ai/cybersoc-ai/issues/97), [#99](https://github.com/CyberSOC-ai/cybersoc-ai/issues/99).

- [ ] Implement vector/graph evidence fusion, ranking, deduplication, provenance and grounded generation using the shared model interface.
- [ ] Document incomparable score handling, source coverage, context budgets and dependency-failure policy.
- [ ] Compare No-RAG, Vector, Graph and Hybrid on common development incidents/model/source releases/environment; report retrieval metrics where applicable and answer quality for all modes.
- [ ] Persist configuration and outputs; expose the Hybrid adapter to API and future tools.

**Acceptance evidence:**

- [ ] Hybrid uses real retrievers and returns source-resolvable evidence; development scores, resource costs and limitations are saved.
- [ ] Final acceptance requires real Vector and Graph integration; controlled adapters may support preparation after B0.

### R3: Deliver single-agent and six-agent LangGraph investigation — [#101](https://github.com/CyberSOC-ai/cybersoc-ai/issues/101)

Owner: Unassigned. Reviewer: unassigned. Dependencies: [#95](https://github.com/CyberSOC-ai/cybersoc-ai/issues/95), [#100](https://github.com/CyberSOC-ai/cybersoc-ai/issues/100), [#96](https://github.com/CyberSOC-ai/cybersoc-ai/issues/96).

- [ ] Deliver state schema, typed node/tool contracts, bounded Hybrid/graph/IOC adapters, deadlines, budgets, tool allowlists and versioned trajectories.
- [ ] Deliver the single orchestrated agent first; then Triage, Investigation, RAG, Knowledge Graph, Threat Intelligence and Response roles with supervisor routing.
- [ ] Preserve the same evidence, output-validation, approval and audit rules in both architectures; agents cannot approve or directly execute response actions.
- [ ] Measure task/action correctness, tool failures, latency and trace complexity on common incidents/model/retrieval configuration.
- [ ] Prepare against stable interfaces after B0; real integration acceptance waits for the tools. A reduced topology is a reported CDC deviation, not a silent substitute.

**Acceptance evidence:**

- [ ] Both required architectures run real investigation tools and publish reproducible development comparisons and complete failure traces.
- [ ] Six-role target and any declared deviation are visible in ADRs/report; no unrestricted infrastructure access exists.

### R3: Deliver reference SOC lab and human-approved sandbox response — [#102](https://github.com/CyberSOC-ai/cybersoc-ai/issues/102)

Owner: Unassigned. Reviewer: unassigned. Dependencies: [#95](https://github.com/CyberSOC-ai/cybersoc-ai/issues/95), [#98](https://github.com/CyberSOC-ai/cybersoc-ai/issues/98).

- [ ] Maintain one reproducible Wazuh reference lab with repeatable scenarios, saved sanitized alerts and live ingestion; a full lab on every PC is not required.
- [ ] Implement authenticated authorized approval/rejection and append-only audit bound to exact immutable proposal/action/target/environment/policy revision and expiry.
- [ ] Implement restricted executor with allowlisted targets/actions, least privilege, disabled-by-default dispatch, single-use/atomic claims and replay protection.
- [ ] Validate expiry, changed proposal, rejection, out-of-inventory targets, audit failure, duplicate dispatch, timeout/unknown outcomes and reconciliation/approved rollback.
- [ ] Record live lab -> normalizer -> application integration and sandbox execution; public dataset replay supports development but does not replace lab/execution proof.

**Acceptance evidence:**

- [ ] Real approved sandbox action succeeds with correlated audit; unapproved/changed/replayed actions and missing audit are denied.
- [ ] Another member can recreate the lab/executor and replay scenarios; no response targets teammates' everyday hosts or production.

### R3: Deliver React/TypeScript analyst dashboard and workflow tests — [#103](https://github.com/CyberSOC-ai/cybersoc-ai/issues/103)

Owner: Unassigned. Reviewer: unassigned. Dependencies: [#95](https://github.com/CyberSOC-ai/cybersoc-ai/issues/95), [#98](https://github.com/CyberSOC-ai/cybersoc-ai/issues/98).

- [ ] Build the typed API client and incident list/detail/investigation views against agreed contracts.
- [ ] Provide explanations, risk, citations/evidence and graph exploration; add recommendation, approval/rejection and audit/execution-history views.
- [ ] Use fixture responses for preparation after B0; integrate real Graph/Hybrid/agent/approval paths as available.
- [ ] Keep database/model/executor credentials server-side and approver identity authenticated by the backend.
- [ ] Automate the analyst's main and denied/failure journeys; prepare the demo storyboard and later report checkpoint.

**Acceptance evidence:**

- [ ] An analyst completes the real investigation/approval/audit workflow through the UI; final acceptance depends on agents/response integration.
- [ ] Typed client and frontend/backend integration tests pass; no browser-supplied approved flag grants authority.

### R3: Extend LLMOps tracking, agent traces and quality monitoring — [#104](https://github.com/CyberSOC-ai/cybersoc-ai/issues/104)

Owner: Unassigned. Reviewer: unassigned. Dependencies: [#95](https://github.com/CyberSOC-ai/cybersoc-ai/issues/95), [#101](https://github.com/CyberSOC-ai/cybersoc-ai/issues/101).

- [ ] Build on B0's portable run records, shared release process and tested tracking choice; do not introduce competing stores for the same authority.
- [ ] Version models, prompts, corpus/index/graph settings, code, environments, workflows and agent trajectories with explicit run/trace mappings.
- [ ] Capture sanitized spans/tool calls, latency, errors, capacity failures and sampled faithfulness/quality assessments on live/replayed incidents.
- [ ] Verify protected storage/access, retention, backups and export/reload before shared exposure; tracking outages must not silently erase run records.
- [ ] Publish dashboard examples, local/cloud recording instructions and reusable artifacts outside ephemeral notebook disks.

**Acceptance evidence:**

- [ ] A teammate finds/reproduces a recorded run and follows its investigation/tool trajectory; failed calls and quality samples remain visible.
- [ ] Sanitized export/reload and backup recovery are demonstrated; monitoring is distinct from the mandatory approval audit ledger.

### R4: Complete SLM comparison and inference/serving optimization study — [#105](https://github.com/CyberSOC-ai/cybersoc-ai/issues/105)

Owner: Unassigned. Reviewer: unassigned. Dependencies: [#95](https://github.com/CyberSOC-ai/cybersoc-ai/issues/95), [#99](https://github.com/CyberSOC-ai/cybersoc-ai/issues/99).

- [ ] Compare Qwen and Phi on common incidents with verdict/severity/MITRE, faithfulness, quality/action correctness and latency/throughput/memory.
- [ ] Run staged comparisons for FP16 vs INT8 vs INT4, KV cache off/on, single vs batched requests, FlashAttention off/on, prefix caching off/on and baseline serving vs vLLM.
- [ ] Record TTFT, tokens/second, total latency, peak memory and quality degradation; separate cold startup, warm execution and workload boundaries.
- [ ] Pin the actual reference hardware/runtime and verify cloud access early after B0; do not treat cross-hardware timings as model rankings.
- [ ] Preserve unsupported-hardware/runtime evidence only where the CDC permits it; no silent feature deletion or giant Cartesian product. Development runs select configurations; official held-out results are finalized in R5.

**Acceptance evidence:**

- [ ] Every required model/runtime comparison has reproducible evidence or an explicitly permitted evidenced support limitation.
- [ ] Source/model/configuration/environment identities and failed cases are included; no performance win is inferred from unlike hardware.

### R4: Run required QLoRA experiment and Base vs Fine-tuned comparison — [#106](https://github.com/CyberSOC-ai/cybersoc-ai/issues/106)

Owner: Unassigned. Reviewer: unassigned. Dependencies: [#95](https://github.com/CyberSOC-ai/cybersoc-ai/issues/95), [#99](https://github.com/CyberSOC-ai/cybersoc-ai/issues/99), [#100](https://github.com/CyberSOC-ai/cybersoc-ai/issues/100).

- [ ] Use development error analysis of the RAG-enabled baseline to choose one SLM, one triage task and one QLoRA adapter.
- [ ] Prepare approved training-eligible examples and explicit split/group exclusions; never use frozen test incidents/labels for training or prompt tuning.
- [ ] Run the minimal three-working-day cloud training time-box after data/runtime preparation; persist the adapter, base-model identity, configuration and run artifacts.
- [ ] Compare Base vs Fine-tuned under the same prompts, retrieval setting and reference environment for verdict/severity/MITRE, faithfulness, latency and memory.
- [ ] Report improvement, degradation or no change honestly; export/reload the adapter and finalize held-out results in R5. No separate adapter per retrieval pipeline is required.

**Acceptance evidence:**

- [ ] Training was actually run and versioned artifacts plus reproducible comparison exist; an unexecuted plan is not completion.
- [ ] Negative/neutral outcomes are valid with analysis; the required experiment remains independent of product functionality.

### R4: Evaluate all nine LLM security threats with mitigations off/on — [#107](https://github.com/CyberSOC-ai/cybersoc-ai/issues/107)

Owner: Unassigned. Reviewer: unassigned. Dependencies: [#95](https://github.com/CyberSOC-ai/cybersoc-ai/issues/95), [#101](https://github.com/CyberSOC-ai/cybersoc-ai/issues/101), [#102](https://github.com/CyberSOC-ai/cybersoc-ai/issues/102), [#103](https://github.com/CyberSOC-ai/cybersoc-ai/issues/103).

- [ ] Version at least five cases for each of prompt injection, indirect injection, jailbreaking, data leakage, RAG poisoning, insecure tool use, excessive agency, output validation and auditability (at least 45 cases total).
- [ ] Include role-play, instruction override, multi-turn and system-prompt extraction attempts plus a benign control set.
- [ ] Run mitigations-off/on only in a controlled test harness; report per-class ASR, block/detection rate, false-refusal rate and secret leaks.
- [ ] Test untrusted logs/documents/IOCs, schema/argument limits, tool permissions, approval binding, sandbox boundaries and audit failures.
- [ ] Prepare fixtures after B0 alongside implementation; complete real backend/UI integration later and create concrete issues for residual failures.

**Acceptance evidence:**

- [ ] Per-class results, benign controls and versioned evidence exist; no critical secret leak, unapproved execution or forbidden tool call succeeds.
- [ ] Residual failures are visible and assessed; a planned mitigation or green unit suite is not claimed as measured security effectiveness.

### R5: Validate release candidate and freeze final integrated benchmarks — [#108](https://github.com/CyberSOC-ai/cybersoc-ai/issues/108)

Owner: Unassigned. Reviewer: unassigned. Dependencies: [#96](https://github.com/CyberSOC-ai/cybersoc-ai/issues/96), [#97](https://github.com/CyberSOC-ai/cybersoc-ai/issues/97), [#98](https://github.com/CyberSOC-ai/cybersoc-ai/issues/98), [#99](https://github.com/CyberSOC-ai/cybersoc-ai/issues/99), [#100](https://github.com/CyberSOC-ai/cybersoc-ai/issues/100), [#101](https://github.com/CyberSOC-ai/cybersoc-ai/issues/101), [#102](https://github.com/CyberSOC-ai/cybersoc-ai/issues/102), [#103](https://github.com/CyberSOC-ai/cybersoc-ai/issues/103), [#104](https://github.com/CyberSOC-ai/cybersoc-ai/issues/104), [#105](https://github.com/CyberSOC-ai/cybersoc-ai/issues/105), [#106](https://github.com/CyberSOC-ai/cybersoc-ai/issues/106), [#107](https://github.com/CyberSOC-ai/cybersoc-ai/issues/107).

- [ ] Run complete lab/normalizer/API/model/retrieval/agent/approval/executor/UI regression on fixed scenarios.
- [ ] Repeat final Qwen/Phi, four retrieval modes, Base/Fine-tuned, single/multi-agent, inference/serving and security comparisons with the agreed reference environment and untouched test protocol.
- [ ] Report intended/attempted/valid/failed cases, sample counts, quality/faithfulness/action metrics, latency/resource costs and uncertainty/limitations.
- [ ] Have a second member start from a fresh checkout, fetch artifacts, restore stores/models and reproduce the supported deployment and benchmark procedures.
- [ ] Resolve critical bugs, preserve failure/decision evidence, verify CI/secrets/backup recovery and freeze result identities. Prepare tests and benchmark harnesses earlier; R5 is acceptance, not first implementation.

**Acceptance evidence:**

- [ ] Release candidate completes the required real analyst workflow and clean-machine reproduction; no known critical security issue remains.
- [ ] All required experimental outcomes and support limitations are traceable; final result changes require documented correction.

### R6: Finalize Markdown report, contribution journals and five-minute demo — [#109](https://github.com/CyberSOC-ai/cybersoc-ai/issues/109)

Owner: Unassigned. Reviewer: unassigned. Dependencies: [#108](https://github.com/CyberSOC-ai/cybersoc-ai/issues/108).

- [ ] Write evidence continuously; first report checkpoint after R2 and second after R3. Finalize rather than reconstruct history in R6.
- [ ] Consolidate architecture, data/cloud workflow, lab, models, all retrieval modes, agents, security, controlled response, optimization, fine-tuning and LLMOps into root README.
- [ ] Preserve historical Sprint 0-8 member journals; maintain revised-stage journals with the same five member sections and linked PR/evidence records.
- [ ] Publish final figures/comparisons, limitations, setup/API/restore instructions, licenses and artifact access.
- [ ] Rehearse and record a demo of at most five minutes covering method, lab-to-assistant workflow, retrieval/agents, approved execution, experiment results and lessons.
- [ ] Freeze features by 28 December 2026; reserve 29-31 December for critical corrections and submission checks; submit by 1 January 2027.

**Acceptance evidence:**

- [ ] Every brief/CDC requirement is linked to implementation or allowed documented limitation, experiment evidence and final report location.
- [ ] All five members can explain the global system; final Markdown report, journals, usable artifact instructions and <=5-minute video are delivered.

## Shared data, compute and LLMOps contract

- Publish separate knowledge corpus, normalized incident inputs and evaluator-only labels. Vector and Graph use the same source release with documented representation/coverage differences; No-RAG sees the same incident without retrieved context.
- Preserve source licensing/provenance and group/run boundaries. Held-out incidents, labels and close scenario copies stay out of retrieval, prompt tuning and training.
- GitHub stores code/configuration/notebooks/small sanitized fixtures. One selected shared artifact store contains larger releases, models/adapters, index/graph exports and run bundles; do not create a dependency on one person’s PC.
- Save exact code, model/tokenizer, prompt, data, retrieval/graph, runtime and environment identities plus hashes. A database snapshot alone is insufficient if linked chunk/vector/manifests are required.
- Notebooks are compute launchers, not independent pipeline copies. Owners may have separate notebooks. Demonstrate cloud output persistence and compatible local restore before handoff.
- Use existing portable run records, pinned local/cloud setup, Docker where supported and GitHub Actions. MLflow remains the existing tracking proposal until B0 demonstrates the chosen integration; shared storage is selected and documented during B0. DVC is optional if it materially simplifies artifact version management.
- Do not compare timings across unlike hardware as model performance. Large-corpus embedding/indexing is distinct from language-model training.

## Requirements coverage

| Brief / CDC requirement | Active delivery |
|---|---|
| Architecture, contracts, workflow, environment, security policy, source/model inventory and version conventions | [#95](https://github.com/CyberSOC-ai/cybersoc-ai/issues/95), [#98](https://github.com/CyberSOC-ai/cybersoc-ai/issues/98), [#99](https://github.com/CyberSOC-ai/cybersoc-ai/issues/99) |
| Fresh normalized Wazuh/public replay data and shared releases; SOC-history and test leakage controls | [#95](https://github.com/CyberSOC-ai/cybersoc-ai/issues/95), [#96](https://github.com/CyberSOC-ai/cybersoc-ai/issues/96), [#99](https://github.com/CyberSOC-ai/cybersoc-ai/issues/99) |
| Qwen/Phi models, reusable runtime and complete No-RAG | [#95](https://github.com/CyberSOC-ai/cybersoc-ai/issues/95), [#105](https://github.com/CyberSOC-ai/cybersoc-ai/issues/105) |
| Complete Vector RAG, retrieval-only checks, citations and replayable artifacts | [#95](https://github.com/CyberSOC-ai/cybersoc-ai/issues/95), [#99](https://github.com/CyberSOC-ai/cybersoc-ai/issues/99), [#108](https://github.com/CyberSOC-ai/cybersoc-ai/issues/108) |
| Neo4j: users, hosts, IPs, alerts, vulnerabilities, malware, ATT&CK and threat indicators; complete Graph RAG | [#97](https://github.com/CyberSOC-ai/cybersoc-ai/issues/97) |
| MITRE ATT&CK, CVE/CWE, threat intelligence and SOC logs; real IOC feed/lookup | [#96](https://github.com/CyberSOC-ai/cybersoc-ai/issues/96), [#97](https://github.com/CyberSOC-ai/cybersoc-ai/issues/97), [#101](https://github.com/CyberSOC-ai/cybersoc-ai/issues/101) |
| Hybrid fusion and No-RAG/Vector/Graph/Hybrid comparison | [#100](https://github.com/CyberSOC-ai/cybersoc-ai/issues/100), [#99](https://github.com/CyberSOC-ai/cybersoc-ai/issues/99), [#108](https://github.com/CyberSOC-ai/cybersoc-ai/issues/108) |
| Stateful LangGraph single agent and six roles: Triage, Investigation, RAG, KG, TI and Response | [#101](https://github.com/CyberSOC-ai/cybersoc-ai/issues/101) |
| Authenticated human approval, immutable binding, append-only audit and sandbox-only execution | [#102](https://github.com/CyberSOC-ai/cybersoc-ai/issues/102), [#98](https://github.com/CyberSOC-ai/cybersoc-ai/issues/98) |
| Reference SOC lab, repeated scenarios, live normalizer path and end-to-end proof | [#102](https://github.com/CyberSOC-ai/cybersoc-ai/issues/102), [#108](https://github.com/CyberSOC-ai/cybersoc-ai/issues/108) |
| React/TypeScript dashboard: incidents, evidence/explanations, graph, risk, approvals and audit/execution history | [#103](https://github.com/CyberSOC-ai/cybersoc-ai/issues/103), [#98](https://github.com/CyberSOC-ai/cybersoc-ai/issues/98) |
| Qwen vs Phi; verdict accuracy/precision/recall/F1; severity/MITRE macro-F1 | [#105](https://github.com/CyberSOC-ai/cybersoc-ai/issues/105), [#99](https://github.com/CyberSOC-ai/cybersoc-ai/issues/99), [#108](https://github.com/CyberSOC-ai/cybersoc-ai/issues/108) |
| Faithfulness, hallucination, four-criterion quality rubric and action correctness; at least 50 double-labelled claims with agreement | [#99](https://github.com/CyberSOC-ai/cybersoc-ai/issues/99), [#108](https://github.com/CyberSOC-ai/cybersoc-ai/issues/108) |
| Retrieval Precision@K, Recall@K, MRR; independent retrieval before generation evaluation | [#99](https://github.com/CyberSOC-ai/cybersoc-ai/issues/99), [#100](https://github.com/CyberSOC-ai/cybersoc-ai/issues/100), [#108](https://github.com/CyberSOC-ai/cybersoc-ai/issues/108) |
| Required Base vs Fine-tuned: error analysis + one minimal QLoRA model/task/adapter, three-working-day training time-box, frozen-test comparison | [#106](https://github.com/CyberSOC-ai/cybersoc-ai/issues/106), [#108](https://github.com/CyberSOC-ai/cybersoc-ai/issues/108) |
| FP16 vs INT8/INT4, KV cache, batching, FlashAttention, prefix caching, baseline serving vs vLLM; TTFT/tokens-per-second/latency/memory/quality | [#105](https://github.com/CyberSOC-ai/cybersoc-ai/issues/105), [#108](https://github.com/CyberSOC-ai/cybersoc-ai/issues/108) |
| Single vs multi-agent correctness, tool failures, action correctness, latency and trace complexity | [#101](https://github.com/CyberSOC-ai/cybersoc-ai/issues/101), [#108](https://github.com/CyberSOC-ai/cybersoc-ai/issues/108) |
| All nine LLM threat classes; at least 45 cases, mitigations off/on ASR/block/false-refusal metrics and zero critical successes | [#107](https://github.com/CyberSOC-ai/cybersoc-ai/issues/107), [#108](https://github.com/CyberSOC-ai/cybersoc-ai/issues/108) |
| LLMOps model/prompt/data/retrieval/workflow versioning, trajectories, latency/quality/hallucination/tool-failure monitoring | [#95](https://github.com/CyberSOC-ai/cybersoc-ai/issues/95), [#104](https://github.com/CyberSOC-ai/cybersoc-ai/issues/104) |
| Git/PR/CI, secret scans, reproducible deployment, independent restore and final benchmark | [#98](https://github.com/CyberSOC-ai/cybersoc-ai/issues/98), [#108](https://github.com/CyberSOC-ai/cybersoc-ai/issues/108) |
| Living root Markdown report, member journals, setup/architecture/security/results docs, <=5-minute demo and all-member understanding | [#109](https://github.com/CyberSOC-ai/cybersoc-ai/issues/109) |

## Original task and issue migration

Closed completed issues remain unchanged. Open original fragments are consolidated and closed with the reason **not planned / superseded**, never marked completed by the migration. Their bodies, PRs and evidence remain historical; the replacements carry acceptance. Previous project items are archived reversibly. Open PRs remain open and can contribute to the new capability without automatically closing its replacement.

| Original task / issue | Historical state before migration | Replacement delivery |
|---|---|---|
| [[S0-T01] GitHub governance and workflow](https://github.com/CyberSOC-ai/cybersoc-ai/issues/1) | CLOSED | [#95](https://github.com/CyberSOC-ai/cybersoc-ai/issues/95) |
| [[S0-T02] Architecture and component boundaries](https://github.com/CyberSOC-ai/cybersoc-ai/issues/2) | CLOSED | [#95](https://github.com/CyberSOC-ai/cybersoc-ai/issues/95) |
| [[S0-T03] Incident, retrieval, response and trace contracts](https://github.com/CyberSOC-ai/cybersoc-ai/issues/3) | CLOSED | [#95](https://github.com/CyberSOC-ai/cybersoc-ai/issues/95), [#98](https://github.com/CyberSOC-ai/cybersoc-ai/issues/98) |
| [[S0-T04] Security, secrets and HITL policy](https://github.com/CyberSOC-ai/cybersoc-ai/issues/4) | CLOSED | [#95](https://github.com/CyberSOC-ai/cybersoc-ai/issues/95), [#102](https://github.com/CyberSOC-ai/cybersoc-ai/issues/102), [#107](https://github.com/CyberSOC-ai/cybersoc-ai/issues/107) |
| [[S0-T05] Data, knowledge-source and benchmark inventory](https://github.com/CyberSOC-ai/cybersoc-ai/issues/5) | CLOSED | [#95](https://github.com/CyberSOC-ai/cybersoc-ai/issues/95), [#96](https://github.com/CyberSOC-ai/cybersoc-ai/issues/96) |
| [[S0-T06] Experiment and version-tracking convention](https://github.com/CyberSOC-ai/cybersoc-ai/issues/6) | CLOSED | [#95](https://github.com/CyberSOC-ai/cybersoc-ai/issues/95), [#99](https://github.com/CyberSOC-ai/cybersoc-ai/issues/99), [#104](https://github.com/CyberSOC-ai/cybersoc-ai/issues/104) |
| [[S0-T07] SOC Lab architecture and scenario plan](https://github.com/CyberSOC-ai/cybersoc-ai/issues/7) | CLOSED | [#95](https://github.com/CyberSOC-ai/cybersoc-ai/issues/95), [#102](https://github.com/CyberSOC-ai/cybersoc-ai/issues/102) |
| [[S0-T08] Initialize sprint documentation structure](https://github.com/CyberSOC-ai/cybersoc-ai/issues/8) | CLOSED | [#95](https://github.com/CyberSOC-ai/cybersoc-ai/issues/95), [#109](https://github.com/CyberSOC-ai/cybersoc-ai/issues/109) |
| [[S1-T01] Reproducible local environment + Docker + basic CI](https://github.com/CyberSOC-ai/cybersoc-ai/issues/9) | CLOSED | [#95](https://github.com/CyberSOC-ai/cybersoc-ai/issues/95), [#98](https://github.com/CyberSOC-ai/cybersoc-ai/issues/98) |
| [[S1-T02] Evaluation dataset v1 and evaluation protocol](https://github.com/CyberSOC-ai/cybersoc-ai/issues/10) | CLOSED | [#95](https://github.com/CyberSOC-ai/cybersoc-ai/issues/95), [#99](https://github.com/CyberSOC-ai/cybersoc-ai/issues/99) |
| [[S1-T03] Baseline SLM runner](https://github.com/CyberSOC-ai/cybersoc-ai/issues/11) | CLOSED | [#95](https://github.com/CyberSOC-ai/cybersoc-ai/issues/95), [#105](https://github.com/CyberSOC-ai/cybersoc-ai/issues/105) |
| [[S1-T04] FastAPI core + incident ingestion](https://github.com/CyberSOC-ai/cybersoc-ai/issues/12) | CLOSED | [#95](https://github.com/CyberSOC-ai/cybersoc-ai/issues/95), [#98](https://github.com/CyberSOC-ai/cybersoc-ai/issues/98) |
| [[S1-T05] SOC Lab MVP](https://github.com/CyberSOC-ai/cybersoc-ai/issues/13) | CLOSED | [#102](https://github.com/CyberSOC-ai/cybersoc-ai/issues/102) |
| [[S1-T06] SOC alert normalizer](https://github.com/CyberSOC-ai/cybersoc-ai/issues/14) | CLOSED | [#95](https://github.com/CyberSOC-ai/cybersoc-ai/issues/95) |
| [[S1-T07] No-RAG end-to-end baseline](https://github.com/CyberSOC-ai/cybersoc-ai/issues/15) | OPEN | [#95](https://github.com/CyberSOC-ai/cybersoc-ai/issues/95) |
| [[S2-T01] Cybersecurity knowledge normalization / ingestion](https://github.com/CyberSOC-ai/cybersoc-ai/issues/16) | CLOSED | [#95](https://github.com/CyberSOC-ai/cybersoc-ai/issues/95), [#96](https://github.com/CyberSOC-ai/cybersoc-ai/issues/96) |
| [[S2-T02] Chunking, embeddings and vector index](https://github.com/CyberSOC-ai/cybersoc-ai/issues/17) | CLOSED | [#95](https://github.com/CyberSOC-ai/cybersoc-ai/issues/95) |
| [[S2-T03] Retriever evaluation](https://github.com/CyberSOC-ai/cybersoc-ai/issues/18) | CLOSED | [#95](https://github.com/CyberSOC-ai/cybersoc-ai/issues/95), [#99](https://github.com/CyberSOC-ai/cybersoc-ai/issues/99) |
| [[S2-T04] Vector-RAG generation pipeline](https://github.com/CyberSOC-ai/cybersoc-ai/issues/19) | OPEN | [#95](https://github.com/CyberSOC-ai/cybersoc-ai/issues/95) |
| [[S2-T05] RAG API integration](https://github.com/CyberSOC-ai/cybersoc-ai/issues/20) | CLOSED | [#98](https://github.com/CyberSOC-ai/cybersoc-ai/issues/98) |
| [[S2-T06] No-RAG vs Vector-RAG experiment](https://github.com/CyberSOC-ai/cybersoc-ai/issues/21) | OPEN | [#99](https://github.com/CyberSOC-ai/cybersoc-ai/issues/99), [#100](https://github.com/CyberSOC-ai/cybersoc-ai/issues/100) |
| [[S2-T07] SOC Lab scenario set v1](https://github.com/CyberSOC-ai/cybersoc-ai/issues/22) | OPEN | [#96](https://github.com/CyberSOC-ai/cybersoc-ai/issues/96), [#102](https://github.com/CyberSOC-ai/cybersoc-ai/issues/102) |
| [[S2-T08] Threat-intelligence ingestion](https://github.com/CyberSOC-ai/cybersoc-ai/issues/23) | OPEN | [#96](https://github.com/CyberSOC-ai/cybersoc-ai/issues/96) |
| [[S3-T01] Knowledge Graph ontology / schema](https://github.com/CyberSOC-ai/cybersoc-ai/issues/24) | OPEN | [#97](https://github.com/CyberSOC-ai/cybersoc-ai/issues/97) |
| [[S3-T02] Graph ingestion / ETL](https://github.com/CyberSOC-ai/cybersoc-ai/issues/25) | OPEN | [#97](https://github.com/CyberSOC-ai/cybersoc-ai/issues/97) |
| [[S3-T03] Neo4j population + Cypher validation](https://github.com/CyberSOC-ai/cybersoc-ai/issues/26) | OPEN | [#97](https://github.com/CyberSOC-ai/cybersoc-ai/issues/97) |
| [[S3-T04] Graph retrieval service](https://github.com/CyberSOC-ai/cybersoc-ai/issues/27) | OPEN | [#97](https://github.com/CyberSOC-ai/cybersoc-ai/issues/97) |
| [[S3-T05] Graph-RAG pipeline](https://github.com/CyberSOC-ai/cybersoc-ai/issues/28) | OPEN | [#97](https://github.com/CyberSOC-ai/cybersoc-ai/issues/97) |
| [[S3-T06] Hybrid RAG orchestration](https://github.com/CyberSOC-ai/cybersoc-ai/issues/29) | OPEN | [#100](https://github.com/CyberSOC-ai/cybersoc-ai/issues/100) |
| [[S3-T07] Retrieval comparison experiment](https://github.com/CyberSOC-ai/cybersoc-ai/issues/30) | OPEN | [#99](https://github.com/CyberSOC-ai/cybersoc-ai/issues/99), [#100](https://github.com/CyberSOC-ai/cybersoc-ai/issues/100) |
| [[S4-T01] Agent state model + structured agent contracts (LangGraph)](https://github.com/CyberSOC-ai/cybersoc-ai/issues/31) | OPEN | [#101](https://github.com/CyberSOC-ai/cybersoc-ai/issues/101) |
| [[S4-T02] RAG / KG / threat-intel tool adapters](https://github.com/CyberSOC-ai/cybersoc-ai/issues/32) | OPEN | [#101](https://github.com/CyberSOC-ai/cybersoc-ai/issues/101) |
| [[S4-T03] Single orchestrated investigation baseline](https://github.com/CyberSOC-ai/cybersoc-ai/issues/33) | OPEN | [#101](https://github.com/CyberSOC-ai/cybersoc-ai/issues/101) |
| [[S4-T04] Prompt-injection, jailbreak, tool-validation and output-validation controls](https://github.com/CyberSOC-ai/cybersoc-ai/issues/34) | OPEN | [#107](https://github.com/CyberSOC-ai/cybersoc-ai/issues/107) |
| [[S4-T05] Human approval state + audit model](https://github.com/CyberSOC-ai/cybersoc-ai/issues/35) | OPEN | [#102](https://github.com/CyberSOC-ai/cybersoc-ai/issues/102) |
| [[S4-T06] Response sandbox action execution](https://github.com/CyberSOC-ai/cybersoc-ai/issues/36) | OPEN | [#102](https://github.com/CyberSOC-ai/cybersoc-ai/issues/102) |
| [[S4-T07] Multi-agent LangGraph workflow](https://github.com/CyberSOC-ai/cybersoc-ai/issues/37) | OPEN | [#101](https://github.com/CyberSOC-ai/cybersoc-ai/issues/101) |
| [[S4-T08] Agent / action correctness benchmark (single vs multi-agent)](https://github.com/CyberSOC-ai/cybersoc-ai/issues/38) | OPEN | [#101](https://github.com/CyberSOC-ai/cybersoc-ai/issues/101), [#108](https://github.com/CyberSOC-ai/cybersoc-ai/issues/108) |
| [[S5-T01] Official benchmark environment freeze](https://github.com/CyberSOC-ai/cybersoc-ai/issues/39) | OPEN | [#99](https://github.com/CyberSOC-ai/cybersoc-ai/issues/99), [#105](https://github.com/CyberSOC-ai/cybersoc-ai/issues/105), [#108](https://github.com/CyberSOC-ai/cybersoc-ai/issues/108) |
| [[S5-T02] Inference optimization benchmark A: quantization, KV cache, batching](https://github.com/CyberSOC-ai/cybersoc-ai/issues/40) | OPEN | [#105](https://github.com/CyberSOC-ai/cybersoc-ai/issues/105) |
| [[S5-T03] Advanced tracing / experiment tracking incl. agent trajectories](https://github.com/CyberSOC-ai/cybersoc-ai/issues/41) | OPEN | [#104](https://github.com/CyberSOC-ai/cybersoc-ai/issues/104) |
| [[S5-T04] Runtime metrics and logging pipeline](https://github.com/CyberSOC-ai/cybersoc-ai/issues/42) | OPEN | [#104](https://github.com/CyberSOC-ai/cybersoc-ai/issues/104) |
| [[S5-T05] Error analysis and fine-tuning target selection](https://github.com/CyberSOC-ai/cybersoc-ai/issues/43) | OPEN | [#106](https://github.com/CyberSOC-ai/cybersoc-ai/issues/106) |
| [[S5-T06] QLoRA fine-tuning experiment (minimal, required)](https://github.com/CyberSOC-ai/cybersoc-ai/issues/44) | OPEN | [#106](https://github.com/CyberSOC-ai/cybersoc-ai/issues/106) |
| [[S5-T07] Documentation checkpoint #1 — consolidate Sprint 0–5 evidence into root report](https://github.com/CyberSOC-ai/cybersoc-ai/issues/45) | OPEN | [#109](https://github.com/CyberSOC-ai/cybersoc-ai/issues/109) |
| [[S5-T08] Serving-stack benchmark B: FlashAttention, prefix caching, vLLM](https://github.com/CyberSOC-ai/cybersoc-ai/issues/46) | OPEN | [#105](https://github.com/CyberSOC-ai/cybersoc-ai/issues/105) |
| [[S6-T01] Frontend architecture + typed API client](https://github.com/CyberSOC-ai/cybersoc-ai/issues/47) | OPEN | [#98](https://github.com/CyberSOC-ai/cybersoc-ai/issues/98), [#103](https://github.com/CyberSOC-ai/cybersoc-ai/issues/103) |
| [[S6-T02] Incident list/detail and investigation view](https://github.com/CyberSOC-ai/cybersoc-ai/issues/48) | OPEN | [#103](https://github.com/CyberSOC-ai/cybersoc-ai/issues/103) |
| [[S6-T03] Evidence / RAG / KG visualization](https://github.com/CyberSOC-ai/cybersoc-ai/issues/49) | OPEN | [#103](https://github.com/CyberSOC-ai/cybersoc-ai/issues/103) |
| [[S6-T04] Risk / recommendation / approval UI](https://github.com/CyberSOC-ai/cybersoc-ai/issues/50) | OPEN | [#103](https://github.com/CyberSOC-ai/cybersoc-ai/issues/103) |
| [[S6-T05] Audit / execution status UI](https://github.com/CyberSOC-ai/cybersoc-ai/issues/51) | OPEN | [#103](https://github.com/CyberSOC-ai/cybersoc-ai/issues/103) |
| [[S6-T06] Frontend/backend integration tests](https://github.com/CyberSOC-ai/cybersoc-ai/issues/52) | OPEN | [#103](https://github.com/CyberSOC-ai/cybersoc-ai/issues/103), [#108](https://github.com/CyberSOC-ai/cybersoc-ai/issues/108) |
| [[S6-T07] Documentation checkpoint #2 — consolidate later technical sections + demo storyboard](https://github.com/CyberSOC-ai/cybersoc-ai/issues/53) | OPEN | [#103](https://github.com/CyberSOC-ai/cybersoc-ai/issues/103), [#109](https://github.com/CyberSOC-ai/cybersoc-ai/issues/109) |
| [[S7-T01] End-to-end SOC Lab regression suite](https://github.com/CyberSOC-ai/cybersoc-ai/issues/54) | OPEN | [#102](https://github.com/CyberSOC-ai/cybersoc-ai/issues/102), [#108](https://github.com/CyberSOC-ai/cybersoc-ai/issues/108) |
| [[S7-T02] LLM security / abuse-case testing](https://github.com/CyberSOC-ai/cybersoc-ai/issues/55) | OPEN | [#107](https://github.com/CyberSOC-ai/cybersoc-ai/issues/107), [#108](https://github.com/CyberSOC-ai/cybersoc-ai/issues/108) |
| [[S7-T03] RAG / KG regression](https://github.com/CyberSOC-ai/cybersoc-ai/issues/56) | OPEN | [#108](https://github.com/CyberSOC-ai/cybersoc-ai/issues/108) |
| [[S7-T04] Final SLM / retrieval / agent / fine-tuning / security benchmark](https://github.com/CyberSOC-ai/cybersoc-ai/issues/57) | OPEN | [#108](https://github.com/CyberSOC-ai/cybersoc-ai/issues/108) |
| [[S7-T05] Release CI + clean reproducible deployment](https://github.com/CyberSOC-ai/cybersoc-ai/issues/58) | OPEN | [#98](https://github.com/CyberSOC-ai/cybersoc-ai/issues/98), [#108](https://github.com/CyberSOC-ai/cybersoc-ai/issues/108) |
| [[S7-T06] Final critical bug / security fixes](https://github.com/CyberSOC-ai/cybersoc-ai/issues/59) | OPEN | [#108](https://github.com/CyberSOC-ai/cybersoc-ai/issues/108) |
| [[S8-T01] Root README finalization (full project report in Markdown)](https://github.com/CyberSOC-ai/cybersoc-ai/issues/60) | OPEN | [#109](https://github.com/CyberSOC-ai/cybersoc-ai/issues/109) |
| [[S8-T02] Architecture / API / setup documentation](https://github.com/CyberSOC-ai/cybersoc-ai/issues/61) | OPEN | [#109](https://github.com/CyberSOC-ai/cybersoc-ai/issues/109) |
| [[S8-T03] Experimental results / figures / conclusions](https://github.com/CyberSOC-ai/cybersoc-ai/issues/62) | OPEN | [#109](https://github.com/CyberSOC-ai/cybersoc-ai/issues/109) |
| [[S8-T04] Security / DevSecOps / LLMOps documentation](https://github.com/CyberSOC-ai/cybersoc-ai/issues/63) | OPEN | [#109](https://github.com/CyberSOC-ai/cybersoc-ai/issues/109) |
| [[S8-T05] Demo scenario + rehearsal (recorded 5-minute demo)](https://github.com/CyberSOC-ai/cybersoc-ai/issues/64) | OPEN | [#109](https://github.com/CyberSOC-ai/cybersoc-ai/issues/109) |

## Execution workflow

Backlog → Ready → implementation → PR → tests/hosted CI and review handling → artifact publication + documentation → Done. Request the assigned reviewer once Ahmed chooses one; approvals remain advisory under CDC §11.3. No unselected reviewer is an invented approval gate.

A capability owner owns its end-to-end implementation, integration, tests, instructions and evidence. Use internal checklists and small PRs rather than a new issue for every implementation step. Split a deliverable only when independent ownership or acceptance genuinely helps.

No downstream issue is Ready merely because it has a milestone. It requires accepted B0, its specific stable inputs, access and an owner/reviewer chosen by Ahmed. Before B0 acceptance, only supporting review, labels and planning proceed.

Report checkpoint 1: after R2. Checkpoint 2 and demo storyboard: after R3. Preserve historical member contributions; record new work under the revised-stage journals.

## Artifact reset boundary

The user intends existing data artifacts to be replaced. This roadmap does not execute deletion. B0 inventories exact disposable paths/collections/volumes, removes or updates stale references through a scoped reset, and publishes fresh releases. No broad deletion of code, historical evidence, secrets, models or shared resources is inferred. Previous artifact availability is not a completion gate for the new work.

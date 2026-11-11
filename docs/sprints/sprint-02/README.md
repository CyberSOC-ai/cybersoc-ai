# Sprint 2 — Vector RAG & Threat-Intelligence Ingestion

> Historical Sprint 0-8 journal. Original assignments, dates and task statuses below are preserved as evidence, not current instructions. Use [the baseline-first roadmap](../../ROADMAP.md) and [current stage journals](../README.md) for new work.

## Sprint Information
- Dates: 2026-10-26 → 2026-11-08
- Main objective: Add evidence-grounded semantic retrieval, ingest real threat-intelligence data, and prove that retrieval quality is measurable.
- Main dependencies: S0-T05, S1-T02, S1-T03, S1-T04, S1-T05, S1-T06
- Exit criteria:
  - Ingestion is reproducible (knowledge and threat intelligence)
  - Retriever quality is measured separately
  - Vector RAG works through the backend
  - No-RAG vs Vector-RAG results are recorded

## Sprint Tasks

| Task | Owner | Reviewer | Domain | Status |
|---|---|---|---|---|
| S2-T01 — Cybersecurity knowledge normalization / ingestion | Ahmed | Soulaiman | rag | In review (PR #86; merge pending) |
| S2-T02 — Chunking, embeddings and vector index | Soulaiman | Ahmed | rag | Backlog |
| S2-T03 — Retriever evaluation | Ahmed | Anas | rag | Development evaluation delivered ([PR #89](https://github.com/CyberSOC-ai/cybersoc-ai/pull/89); formal state tracked on GitHub) |
| S2-T04 — Vector-RAG generation pipeline | Anas | Oussama | rag | Backlog |
| S2-T05 — RAG API integration | Oussama | Anas | backend | Backlog |
| S2-T06 — No-RAG vs Vector-RAG experiment | Achraf | Soulaiman | rag | Backlog |
| S2-T07 — SOC Lab scenario set v1 | Oussama | Ahmed | soc | Backlog |
| S2-T08 — Threat-intelligence ingestion | Ahmed | Oussama | soc | Backlog |

# 1. Ahmed
## Assigned tasks

S2-T01, S2-T03, S2-T08. S2-T03 transferred from Achraf to Ahmed on 2026-11-04;
Anas remains reviewer. The earlier update below covers S2-T01 and source expansion;
S2-T08 IOC-feed ingestion remains Backlog.

## Work completed

2026-11-04 — S2-T03: completed the first bounded development retrieval evaluation
on `codex/18-retriever-evaluation`. Added the hash-pinned
[replay release](../../../datasets/evaluation/retrieval-dev-v1/README.md),
[technical audit](../../../datasets/evaluation/retrieval-dev-v1/AUDIT.md), reusable
`ai.evaluation.retrieval` scorer/CLI and regression tests. The same pinned CPU
BGE/Qdrant index supplied 100 passage candidates per query; document deduplication
precedes K=5. All ten revised development queries succeeded: Precision@5 0.18,
Recall@5 over known labeled references 0.90, MRR 0.8625. Eight references ranked
first, Q02 second and Q01 eighth. Model, corpus, environment, run and label identities
are recorded in the release manifest; no answer-generation evaluation is claimed.

Ahmed validated the reference-answer note/35 existing decisions; 26 additional
technical labels were reviewed with AI assistance. Independent Anas approval is
not claimed. Queries are corpus-informed, judgments are pooled/incomplete and the
index covers 340 source records, not the full acquired corpus. Public replay uses
source identities only; large/private source/model/index artifacts stay local.
All 248 project tests passed locally, including 16 new retrieval checks; Ruff,
repository integrity and the staged secret scan passed.
[PR #89](https://github.com/CyberSOC-ai/cybersoc-ai/pull/89) publishes the release
and requests Anas's review. Ahmed authorized the technical audit, branch publication
and finalization if checks pass. Hosted CI, review handling, merge and linked issue
closure are tracked on that PR; no independent Anas approval is claimed.

2026-10-29 — Completed the expanded local [knowledge-ingestion implementation](../../../rag/ingestion/README.md)
on `feature/16-knowledge-ingestion`. The user approved including bulk CVE/NVD,
CISA KEV, Sigma, playbooks and selected OTRF/Splunk examples alongside ATT&CK,
CWE and existing lab history. The user subsequently authorized adding the 2025
and 2026 annual NVD feeds alongside 2024; the selection now covers all three
identifier years through their acquisition snapshots. [PR #86](https://github.com/CyberSOC-ai/cybersoc-ai/pull/86) is the publication
and review target. Ahmed authorized pushing the completed work; review and merge
remain with him. No merge, issue closure or independent peer approval is claimed.

## Technical approach

Stream annual NVD JSON into a disk-backed identity/sort stage; verify compressed
feed acquisition against NVD META size/SHA-256 and detect concurrent feed changes.
Acquire only named public files at pinned official-repository commits, retaining
licenses/notices, Git LFS identity, ZIP checks and receipts. Normalize with typed
schemas; reject unsafe YAML and XML, duplicate identities and changed source bytes.
Join NVD/CVE Program records and KEV by exact CVE ID. Keep ATT&CK relationships
separate from searchable prose. Compose a reproducible offline release with
structured CVE/KEV lookup. No models, embeddings, rule deployment or notebook
execution occur.

## Files / components modified

Extended `rag/ingestion/`, versioned ingestion schemas, offline tests and source/
assignment/validation records in `datasets/knowledge/`. Added pinned ijson/PyYAML
dependencies. Extended the draft backend evidence source enum with `detection_rule`
and `playbook`, retaining existing examples/fields; consumers with frozen enums
must refresh them. Other members' journals and shared sprint sections are unchanged.

## Tests / validation

Python 3.12.15 development image rebuilt. All 169 tests passed: 19 contracts,
43 evaluation, 20 backend, 16 normalizer, 27 baseline and 44 ingestion/acquisition.
Ruff passed. Expanded tests cover streaming bounds/counts/duplicate keys, NVD META
integrity, exact vulnerability joins, input-corpus tampering, source revision pins,
Git LFS identity, safe YAML and real external event formats/split exclusion.
The 44 ingestion tests passed again for the three-year selection update; its
code/schemas are unchanged. Full-source replay and final check details are in the
[validation record](../../../datasets/knowledge/VALIDATION.md). CI for the previously
published draft does not validate later commits; use PR #86 checks for the
final published head.

## Results / metrics

The updated local collection contains 164,201 prepared documents/excerpts:
162,499 CVEs across 2024 (38,494), 2025 (43,642) and 2026 (80,363),
706 ATT&CK techniques, 956 CWE weaknesses, three Linux Sigma rules, two Windows
playbooks and 35 SOC excerpts/observations. Exported 21,660 ATT&CK relationships
separately. Five official CVE records join existing documents; 544 CVEs gain KEV
context from a 1,762-record catalog, with 1,218 unmatched entries retained for
structured lookup. Two independent full builds reproduced 28 JSONL/report files
byte-for-byte, and exact CVE-year counts were checked in SQLite.

These are collection counts, not retrieval/model-quality results. The three-year
selection is not an all-years mirror; 2026 covers records available at acquisition.
The official CVE supplement is five records, and the external event selection is
33 excerpts rather than independent incidents. Data lives on this PC under
`.local/ingestion/`; the container mount is the same host directory. Git excludes
these datasets. S2-T02 will build the vector index from the prepared records.

## Problems encountered

The initially selected external logs were auditd text and Sysmon XML, so added
format-aware observation parsing instead of treating them as JSONL or inventing
backend incident fields. Some selected Sigma rules have upstream `test` status;
retain it rather than claiming production readiness. The selected playbooks are
Windows reference content, not deployed Windows-lab evidence. Existing dependency
stack emits an HTTP-client deprecation warning; tests pass.

## Decisions made

Use [the explicit source plan](../../../datasets/knowledge/sources.json) and
[coverage rationale](../../../datasets/knowledge/SOURCE_SELECTION.md). Preserve
NVD/CNA/ADP/KEV provenance separately and cite claims to the correct snapshot.
Keep source text as untrusted data. Both local SSH observations and the selected
external SSH run share `G-SSH`; network-discovery examples share their own family.
Unknown/unassigned files are quarantined. Changed split/source hashes invalidate
eligibility. The current pilot is unfrozen; all SOC material and the combined
release remain development-only. Manual prose-sensitivity and near-duplicate
review are still required. Retain source-specific notices; resolve OTRF's differing
README/root-license labels before external redistribution. Raw/generated artifacts
stay ignored locally; shared storage remains unresolved under ADR-006. Vector
store/embedding choices remain S2-T02/ADR-001 work.

## Related Issues / Pull Requests

[S2-T01 / #16](https://github.com/CyberSOC-ai/cybersoc-ai/issues/16).
Reviewer: Soulaiman (`soulaimane-22`). Branch: `feature/16-knowledge-ingestion`.
[Draft PR #86](https://github.com/CyberSOC-ai/cybersoc-ai/pull/86) tracks this
implementation and includes `Closes #16` for closure when Ahmed merges. Publication
is authorized. Final-head hosted CI, assigned review handling, merge and issue
closure remain required before formal Done. No merge or new reviewer notification
was performed by the assistant.

## Learning outcome

A large vulnerability reference needs bounded acquisition, incremental parsing
and exact identity joins. Reference knowledge, event examples and evaluator labels
have different roles. Preserving provenance and separating relationship exports
helps downstream retrieval; corpus size alone does not demonstrate answer quality.


# 2. Soulaiman
## Assigned tasks

S2-T02 — Chunking, embeddings and vector index. Reviewer: Ahmed.

## Work completed

2026-10-29 — Local implementation and validation completed on
`codex/17-chunking-embeddings-vector-index`, ready for review. Implemented pinned
model acquisition, token-aware chunking, CPU embeddings, persistent separate
knowledge/SOC collections, metadata filters and query-to-cited-evidence retrieval.
The implementation was validated using a documented development corpus; formal
Done still requires the PR/CI/review/closure workflow.

2026-10-30 — Local follow-up on `codex/incremental-vector-index`: added versioned
incremental preparation, preserving the previous index and reusing unchanged
passage spans and embedding text. Corpus additions, edits and omissions produce
a new verified release with parent hashes and work counters. Added the
[incremental guide](../../../rag/vector/INCREMENTAL.md) and
[local validation record](../../../rag/vector/INCREMENTAL_VALIDATION.md).
Publication and CI are tracked in
[PR #88](https://github.com/CyberSOC-ai/cybersoc-ai/pull/88). The original S2-T02
implementation remains in PR #87.

## Technical approach

Use the hash-pinned BGE-small model/tokenizer on CPU with CLS pooling, normalized
384-value float32 vectors and cosine search. Chunk exact source slices at 384 total
tokens with up to 48 overlap and a 16,000-character cap. Preserve deterministic
IDs, citation provenance, notices, source status and SOC split/group/run lineage.
Verify eligibility/hashes before publishing artifacts. Store vectors in pinned
local Qdrant on a named volume with typed payload indexes. Query filters apply
before global top-K; only closed evidence-contract fields cross the model boundary.

## Files / components modified

Added `rag/vector/` acquisition/chunking/embedding/index/retrieval modules,
configuration and guide, `tests/vector/`, optional CPU embedding requirements and
Dockerfile. Updated regular dependency pins, Compose's optional Qdrant profile,
CI, ADR-001 and contract documentation/tests. Corrected the draft request source
enum/bound to match the existing eight evidence sources. Added the evaluator
preparation command and S2-T03 setup guide for rebuilding an index from approved
inputs without private local artifacts.

## Tests / validation

Validation covers real tokenizer bounds/coverage, model/file integrity, finite
normalized embeddings, CLS pooling and batch agreement, repeatable saved vectors,
artifact tampering, atomic failure, source separation, typed filters, persistence,
readback, snapshot recovery, query/error behavior and closed citation projection.
The final 406-point development index is the review target. Source data, model
weights and large/generated evidence remain ignored locally. Hosted CI and peer
review have not been claimed from local tests.
All 220 project tests passed, including 50 vector tests. All 380 filter-value checks
passed before/after container recreation; snapshot recovery reproduced all 406
points and settings. Six real query cases and reader reload passed. See the
[final validation record](../../../rag/vector/VALIDATION.md).

## Results / metrics

Validation selection: 340 records -> 406 passages/vectors: 369 knowledge points
and 37 SOC points. It contains 100 CVEs, 100 CWEs, 100 ATT&CK techniques, all three
selected Sigma rules, both playbooks and all 35 prepared SOC records. The selection
limit is explicit in manifests; this is not full knowledge-corpus coverage.

Additional evidence: fresh ingestion replay contained 164,793 records and 21,660
separate relationships. Complete chunking produced 174,883 passages in 868 seconds,
about 65 MiB peak process RSS. The 406-passage CPU encoding build took about 136
seconds total, 114 seconds inference/write, about 735 MiB peak RSS. These are
exploratory measurements; no gold-label retrieval-quality or full-index scale
benchmark is claimed.

## Problems encountered

Normalized text has flattened whitespace; splitting uses actual tokenizer offsets.
Distinct CVE identities with shared descriptions remain separate. One heading-only
placeholder is excluded explicitly and ten short descriptions retain flags.
SOC data remains development-only with no frozen test split. Copied source-enum
validators must refresh for detection-rule/playbook request filters.

## Decisions made

[Issue #17](https://github.com/CyberSOC-ai/cybersoc-ai/issues/17) does not explicitly
mandate GPU execution or indexing every acquired record. A full-corpus run was
an expanded validation proposal and is not treated as a completion gate. Corpus
coverage is disclosed for Ahmed to assess against downstream needs. Keep CPU
configuration reproducible and ADR-001 Proposed until reviewed. Publish code and
sanitized validation records; keep acquired data/model/index artifacts outside Git.

## Related Issues / Pull Requests

[S2-T02 / #17](https://github.com/CyberSOC-ai/cybersoc-ai/issues/17).
[PR #87](https://github.com/CyberSOC-ai/cybersoc-ai/pull/87), ready for review on
`codex/17-chunking-embeddings-vector-index`. Reviewer: Ahmed (`ElrhAhmed`), review
requested. Hosted checks are tracked on the PR; merge/issue closure remain pending.
Achraf can start S2-T03 integration using the
[evaluator setup guide](../../../rag/vector/EVALUATOR_SETUP.md).

## Learning outcome

The embedding model turns source passages into vectors; Qdrant persists and filters
them. Query encoding must match the indexed model, and retrieved source slices
need explicit citations. Passing pipeline checks does not establish retrieval
relevance, independent test eligibility or complete source coverage.


# 3. Anas
## S2-T04 — Vector-RAG generation ([#19](https://github.com/CyberSOC-ai/cybersoc-ai/issues/19))

Delivery review: [PR #90](https://github.com/CyberSOC-ai/cybersoc-ai/pull/90),
assigned reviewer Oussama (@Ossel14). Current implementation and three complete
live records address the focused attribution investigation; acceptance and final
published-revision CI remain pending. Unsupported T1078, wrong destination-as-source
blocking and inadequate action reasoning remain explicit failures. The direction
definitions produced no observed decision correction. Historical plans below are
superseded by the executed records and authorize no additional model attempt.
Final historical packaging scans returned exit 1: boundary 17 tree findings,
direction 26 tree findings, plus the separately retained history finding. Saved
adjudications identify non-credentials; no scanner pass or exclusion is claimed.


The pipeline reuses the existing retriever and model client. The internal decision selects one pipeline-owned quotation catalogue ID. Code copies the supplied incident report with an unverified-input label, resolves the exact source span and citation, and retains the model verdict, risk, MITRE and action fields through existing #11 validation. Empty retrieval and invalid selections fail explicitly. Oussama is the assigned reviewer; semantic support and action correctness require separate assessment.

### Catalogue-owned attribution, 2026-11-09

Current generation selects a deterministic catalogue ID; code owns the exact
160-character-or-shorter source span, evidence pairing and supplied incident
report (explicitly labelled unverified input). No P01-specific catalogue rules
or report paraphrasing are used. Public summary size, including escaping and
attribution, is checked before inference without truncation. Model verdict/risk,
MITRE and proposed action fields remain unchanged and visible through #11.
Source/destination validation remains a separate shared-contract/validator gap;
no directional guard or binding inference was added. The initially planned live
investigation is now recorded in the execution entry below. Selection integrity
alone does not establish grounding or complete #19. Prior trials are preserved.
Local fake validation: 98 vector regressions (including 21 generation tests),
20 contract tests and Ruff passed. No model was loaded or run.

### Single approved live P01 execution, 2026-11-09

Internal direction-definition follow-up (2026-11-10): clarified the vector-only
schema descriptions for target and source_ip, including event-relative origin
versus destination and abstention if the incident does not establish direction.
Verified delivery path through required_output/user-message, apply-template and
completion.prompt in the existing adapter; the previous actual template retained
that whole user message. A fake HTTP regression checks generated request delivery
through the real pipeline/adapter, not model interpretation or semantic correctness.
Public schemas, shared validators and the completed boundary correction are
unchanged. No real-model call occurred at definition implementation time. The
later approved single-run result below retains unsupported mapping, wrong-source
proposal and action-reasoning limitations.

Definition-only live comparison (2026-11-10): verified before inference that actual
incident/policy/request, live retrieval, catalogue/exclusions, system prompt and
settings matched the boundary run. Removing only the two descriptions made schema,
user message and formatted prompt identical. Actual input2,462 tokens (+84) fit
cap3,072. One retrieval/completion produced a complete result in141.804s including
roughly71s inspection,175 output tokens/EOS/not truncated. No abstention: source
remained destination10.77.0.20. Quotation remained the relevant SSH definition;
unsupported T1078 and all action text remained byte-identical. No observed decision
correction; no general causal or accuracy claim. No repairs or retries.
[Source-first assessment and reproduction](../../../rag/generation/evidence/P01-direction-20261110-01/README.md)
and [complete packet](../../../rag/generation/evidence/P01-direction-20261110-01/evidence.json)
preserve comparisons and every field. The checked definition snapshot's154 scoped
tests/Ruff/integrity/whitespace passed; final docs/artifact checks are separate.
All prior failures remain. No further implementation, model attempt, commit,
push or merge followed. Reviewer acceptance and #19 remain pending.

Boundary follow-up (2026-11-10): approved a single-call candidate-only correction.
`sentence-boundaries-v1` omits uncertain leading units, unfinished tails, known
abbreviation ambiguity, unbalanced protected syntax and whole units over160
characters. It records exact offsets/exclusions and preserves full evidence;
it does not prove relevance or fix mappings/action direction. Required tests and
a live catalogue/token inspection precede the sole separately recorded completion.
No preferred quotation or answer is inserted. The frozen checklist and complete
artifacts are under `.local/P01-boundary-20261110-01/`; actual outcome follows in
the boundary review record. Earlier failures remain unchanged.

Actual boundary result: catalogue6 eligible sentences/5 exclusions inspected
before completion; old fragment ineligible and complete SSH sentences available.
Real token count2378, unchanged input cap3072/output512/context4096. One live
retrieval and one completion finished the pipeline in89.281s, including the
pre-inference inspection pause;175 output tokens, EOS/not truncated. Selected
exact88-character SSH definition is relevant general knowledge. Boundary and
quotation outcomes passed for this case; decision quality failed: T1078 remains
unsupported and destination10.77.0.20 remains the proposed source IP. Every field
was retained unchanged. true_positive/medium does not establish successful access.

Clean-export checks:292 tests passed, including106 vector/29 generation and all27
baseline tests; actual integrity/Ruff/whitespace passed. The same nine adjudicated
non-credential scanner findings retain failure exits, without suppressions.
[Every-field assessment and reproduction](../../../rag/generation/evidence/P01-boundary-20261110-01/README.md)
and [complete packet](../../../rag/generation/evidence/P01-boundary-20261110-01/evidence.json)
preserve before/after evidence. Semantic relevance generally, correct mappings,
role-aware action validation, final CI and assigned review remain unresolved.
No further experiment, answer repair, commit, push or merge occurred.

Completed the current VectorPipeline with real #17 retrieval and pinned Phi
Q4_K_M / Linux b11827: one retrieval, one completion, unchanged full P01 query,
MITRE-only K=2, exact search, 300-second diagnostic budget, 3072/512 token caps,
4096 context, seed 42, temperature 0, six CPU threads and one slot. Verified the
existing 340-record/406-vector preview and full live point readback; no rebuild.
Suitable evidence was defined before inference as support for relevant general
reference knowledge, not independent verification of the incident. The retrieved
SSH passage qualified; no query/filter/K adjustment was made.

Pipeline completion passed in 109.531 seconds, with 3042 input and 236 output
tokens, EOS, no truncation. Quotation integrity passed but relevance failed: the
model selected an incomplete ESXi/citation fragment. Report copying/attribution
worked, while T1078/T1098 and destination-as-source blocking remained unsupported
or wrong; undetermined abstains on the attack attempt and medium risk is defensible.
No answer repair or shared-validator change followed. No response was executed.

The [review record](../../../rag/generation/evidence/P01-live-catalogue-20261109-01/README.md)
and [complete synthetic evidence packet](../../../rag/generation/evidence/P01-live-catalogue-20261109-01/evidence.json)
preserve inputs, actual passages/IDs, raw and structured outputs, recorder source,
versions and every-field assessment. Full snapshot/logs remain at
`.local/P01-live-catalogue-20261109-01/`. Previous P01 failures remain unchanged,
including the 223.069-second Phi completion rejected for quotation integrity and
its invented hosts/reversed IP. Different environments/retrieval modes prevent a
controlled performance comparison. No retry, model change, commit, push or reviewer
message occurred. Judgment/action quality failed; reviewer acceptance and #19 Done
remain pending. Applicable fresh-check outcomes are recorded with the evidence.

Fresh checks: 98/98 vector tests, 20/20 contract tests and Ruff passed. Baseline:
24 passed, three CLI errors from the unchanged pinned policy digest/CRLF mismatch.
The dev-image integrity command and harness failed because Git is absent; logs
are retained. Host CRLF-aware whitespace passed; supplemental text/link checking
uses the actual host Git file list. No full-suite or dirty-head hosted-CI pass.

### Quotation integrity implementation, 2026-11-09

Changed only the internal decision and summary rendering; the public schema and
pipeline-owned evidence are unchanged. Invalid excerpts fail explicitly, and the
shared deadline remains in use. Offline fake-component validation passed: 11
generation tests and 15 deadline regressions; Ruff passed on the changed Python
files. No real model ran. These checks do not prove relevance, claim support or
correct triage, and do not complete #19. The single fixed-evidence P01 generation
replay is documented in rag/generation/README.md and awaits approval. It will
review every claim, including observations, mappings, verdict/risk and actions;
it will not measure live retrieval or the complete live pipeline.

### Bounded quotation follow-up, 2026-11-09

Internal quotations are capped at 160 characters without truncation or repair.
Ordinary Markdown brackets are allowed only in exact source quotations;
double-bracket marker injection remains rejected. Final summary validation uses
the already validated excerpt/selected ID, with no quotation-boundary parser.
Public contracts and pipeline-owned evidence are unchanged. Phi completion-02
reached an exact source prefix but timed out before analysis; no Phi reasoning
failure is inferred. One new 512-output-token/300-second CPU feasibility trial is
prepared only. Both quotation rules and deadline change, so it is not a clean
model-only comparison. All earlier runs remain preserved; #19 remains unresolved.
Validation: all 97 vector regressions (including 20 generation cases) and Ruff
passed. Baseline regressions: 24 passed, three CLI cases blocked by the untouched
CRLF policy file's pinned raw-byte digest mismatch. No normalization was made.

### Development evidence reported by Anas, 2026-11-06

On revision `fe9c9ab`, the two-order LSASS/SSH probe selected the LSASS passage in both orders and correctly attributed the single-sign-on explanation. Earlier P01 attempts omitted the inline citation or reached the 512-token limit with a decoding pattern. Those failures were retained.

Full run `P01-selection-f40eaf64ad59` used Qwen 1.5B Q4_K_M, llama.cpp CPU b11827, exact MITRE-only retrieval and K=2 on the 406-passage preview. The result passed structural and citation-ID validation. The incident supports the summary of eight failed passwords in 57 seconds. The selected passage about throttled password spraying does not substantiate that host, account, count or timing. No P01 claim-support pass is claimed.

Verdict and risk match the pending-review pilot label (true positive, medium). Returned T1078 and T1098 differ from expected T1110.001. The preview had zero dedicated T1110.001 passages among 138 MITRE passages. The proposed approval-required block on linux-01 for 192.0.2.10, TCP/22, 300 seconds matches the required action and permitted duration. The rollback text describes SSH configuration rather than removing the proposed block. No execution was reported.

At the source-selection revision, 70 vector and 27 baseline tests passed locally, along with Ruff and repository integrity. Raw real-run artifacts remain on Anas's PC. These are exploratory development observations. General accuracy, hosted CI and peer approval require separate evidence. Follow-up for Oussama: exposing structured claim-to-source links publicly would require contract review.

# 4. Achraf
## Assigned tasks

S2-T06. S2-T03 transferred to Ahmed on 2026-11-04; Anas remains reviewer.

## Work completed

> To be completed from validated sprint evidence.

## Technical approach

> To be completed from validated sprint evidence.

## Files / components modified

> To be completed from validated sprint evidence.

## Tests / validation

> To be completed from validated sprint evidence.

## Results / metrics

> To be completed from validated sprint evidence.

## Problems encountered

> To be completed from validated sprint evidence.

## Decisions made

> To be completed from validated sprint evidence.

## Related Issues / Pull Requests

> To be completed from validated sprint evidence.

## Learning outcome

> To be completed from validated sprint evidence.


# 5. Oussama
## Assigned tasks

S2-T05, S2-T07. This entry covers only S2-T05 / Issue #20.

## Work completed

2026-11-10 — Implemented Vector-RAG dispatch through the existing FastAPI
investigation endpoint on `feature/20-rag-api-integration`. Empty-body and
explicit `no_rag` calls retain the No-RAG behavior. Explicit `vector_rag` calls
use the merged experimental VectorPipeline. Results and correlated traces are
validated and stored in SQLite before a success response.

2026-11-11 — [PR #92](https://github.com/CyberSOC-ai/cybersoc-ai/pull/92)
merged into `main` at `cdf3f4ae6574c8f1f59baa5863d8913d06cf459b`.
[Anas approved the final head](https://github.com/CyberSOC-ai/cybersoc-ai/pull/92#pullrequestreview-5861259037)
after reproducing the citation fix. Required PR CI and post-merge main CI
passed. Issue #20 implementation and technical acceptance criteria are
complete; the linked issue and Project record formal closure.

## Technical approach

A trusted `VectorAPIAdapter` receives a preinitialized pipeline, fixed disabled-
execution policy, trace versions, K and filters. The backend creates the retrieval
request, investigation/trace IDs and one monotonic deadline. Both modes share the
same bounded worker pool. Strict v1 schemas and relational checks reject malformed
results, duplicate vector evidence IDs and unknown or malformed terminal
`[[evidence_id]]` citation markers while preserving ordinary brackets and
Markdown links in source text. The API never executes proposed actions. Missing dependencies, expired deadlines and invalid
outputs receive sanitized, typed errors with failed result/trace persistence once
a run starts. The HTTP `vector_rag` name maps to v1 `mode: vector` without changing
public contracts. Query text is capped at the retrieval contract's 4,000-character
limit; the full incident reaches generation.

## Files / components modified

`backend/app.py`, `backend/runner.py`, new `backend/vector_adapter.py`, new
`tests/backend/test_vector_api.py`, `backend/README.md`,
`backend/RUNNER_INTERFACE.md`, this named sprint section and the scoped
`.gitattributes` CRLF whitespace rule. Repository, public
schemas, Anas's RAG generation/retrieval and grounding behavior remain unchanged.

## Tests / validation

Controlled API tests cover both modes, legacy empty bodies, strict mode rejection,
missing/unavailable or changed retrieval dependencies, empty evidence, invalid
model output, deadline forwarding and expiry, shared concurrency, result/trace
persistence and evidence integrity. The final pre-merge local offline suite
passed 305 tests (contracts 20, evaluation 59, backend 32, normalizer 16,
ingestion 44, vector/generation 107, baseline 27). Ruff, repository integrity
(284 tracked text files), staged whitespace and Gitleaks 8.30.1 staged secret
scanning passed with zero leaks. Tests used the existing Python 3.12
development image offline with controlled retrieval and inference; no model
download, real inference or index rebuild was performed.
[PR CI](https://github.com/CyberSOC-ai/cybersoc-ai/actions/runs/43044656976)
passed on the final head; [post-merge main CI](https://github.com/CyberSOC-ai/cybersoc-ai/actions/runs/43060146180)
passed on the merge commit, including backend, contract, vector, baseline,
repository integrity, lint and secret-scanning checks.

## Results / metrics

The tests demonstrate contract-valid Vector-RAG API wiring with controlled
retrieval/generation, not semantic grounding or measured model quality. PR #90
merged as experimental baseline at `f6d84db0d5c1c4913d79a6d965d7e99805c9c75f`;
its required and post-merge CI passed. Issue #19 stays open. Unsupported T1078,
incorrect source/destination IP, incomplete semantic grounding and potentially
incorrect proposed response actions remain known limitations documented in
`rag/generation/README.md` and the P01 evidence packets. Actions remain
proposals only and are never executed by this API. No live SLM/Qdrant
Vector-RAG API run, live Wazuh/SOC ingest or external model deployment has
been verified for Issue #20. Controlled API integration tests do not establish
semantic support for generated claims or real-world action correctness.

## Problems encountered

The default Compose API has no model runner, and its separate Qdrant container is
not reachable through the API container's localhost. Trusted deployment must
prepare the pinned index/encoder/model and a shared loopback environment before
real-model validation. A timed-out Python worker is not forcibly cancelled; its
pool slot stays occupied until it exits. The source/destination and grounding
failures from #19 are intentionally not corrected by API integration.

Anas found that the API applied broad citation validation to the entire
rendered summary, so ordinary square brackets in incident observations and
Markdown links in exact retrieved quotations caused HTTP 502. Commit
`1cd34242abd7532b996e4ab77920291fe00047ed` checks the pipeline's one
terminal citation marker against the returned evidence IDs. Controlled
endpoint regressions now accept both ordinary bracketed incident text and
Markdown links in quotations with HTTP 200 and matching persisted result/trace,
while unknown, malformed, trailing and duplicate markers remain rejected.

## Decisions made

Keep one endpoint and a single mode-routed worker pool. Keep retrieval parameters
trusted configuration rather than HTTP inputs. Preserve v1 result/trace `vector`
mode and proposal-only actions. Do not treat a structurally valid result as proof
of evidence-grounded claims.

## Related Issues / Pull Requests

[Issue #20](https://github.com/CyberSOC-ai/cybersoc-ai/issues/20) technical
acceptance is complete; [PR #92](https://github.com/CyberSOC-ai/cybersoc-ai/pull/92)
merged at `cdf3f4ae6574c8f1f59baa5863d8913d06cf459b`. The upstream
[PR #90](https://github.com/CyberSOC-ai/cybersoc-ai/pull/90) remains an
experimental baseline, and [Issue #19](https://github.com/CyberSOC-ai/cybersoc-ai/issues/19)
is open for its unmet grounding criterion.

## Learning outcome

The backend selects a mode, owns the deadline and IDs, and validates/persists the
outcome. The VectorPipeline owns retrieval/generation and evidence provenance.
This boundary lets #20 expose the experimental pipeline without presenting the
known model-quality defects as resolved.

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

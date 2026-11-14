# Vector generation — issue #19

`VectorPipeline(retriever, generator, root).investigate(incident, policy, request)`
returns `(investigation_result, measurements)`, using #17's retriever and #11's
runner/model adapter. Public v1 contracts and API scope are unchanged. No #20 API
integration or #21 benchmark is implemented here.

## Delivery status and evidence guide — 2026-11-10

This delivery addresses the focused [review on PR #90](https://github.com/CyberSOC-ai/cybersoc-ai/pull/90#pullrequestreview-5819222237).
The implementation and saved evidence are ready for acceptance assessment;
Issue #19 is not declared Done. Exact quotations and valid JSON do not establish
correct judgments or safe action arguments. No further model experiment is part
of this delivery.

| Review request | Evidence and outcome |
|---|---|
| Complete real-model investigation | Three preserved P01 live retrieval/generation records below; each returned a full structured result. |
| Reproducible inputs, passages/IDs, output, versions and claim assessment | Each evidence packet contains actual inputs, full retrieval, raw/structured output, recorder and configuration. Each companion README distinguishes supplied observations from retrieved knowledge and assesses every substantive field. |
| Address unsupported attribution and retain before/after | Code labels the copied report as unverified input and renders a paired exact quotation. Conservative boundaries replaced arbitrary fragments; the boundary run selected relevant SSH knowledge. Unsupported T1078 and destination-as-source action arguments remain failures. Direction descriptions reached the prompt but produced no observed correction. |
| Regression tests | Deterministic tests cover ownership, exact spans, pairing, boundaries, failures and delivery of direction descriptions through the real adapter. They do not verify semantic correctness. |
| Documentation and limitations | Current results appear first; historical plans below are explicitly superseded. Reviewer feedback disposition and final published-revision CI remain pending. |

Read the direction assessment for the latest result, the boundary assessment for
the quotation correction, and the original catalogue assessment for the preserved
fragment failure. Original run packets, raw outputs and failed attempts are not
rewritten by this delivery. Local paths identify artifacts held by Anas, not
public downloads: independent reproduction requires the saved snapshots plus
preview/index, model and runtime bytes. The published HEAD alone cannot reproduce
the uncommitted implementation. Model conversion lineage remains unverified.

Historical scanner results must retain their scope: the first clean export had
8 tree findings and 1 history finding; final boundary packaging had 17 tree
findings; final direction packaging had 26 tree findings, with the prior history
finding retained separately. Saved adjudications identify file digests, synthetic
proposal keys and historical prose as non-credentials. These scans exited 1;
none is a passing secret scan. No scanner exclusions were added. Final delivery
validation is separate from these historical records and from hosted CI.

## Current generation handling: pipeline-owned report and quotation catalogue

`quotation_catalogue` visits every retrieved entry in retrieval order and uses
`sentence-boundaries-v1`, a conservative deterministic punctuation scanner.
The first unit is always omitted because retrieved chunks do not prove their
leading sentence boundary. Later units must end at top-level `.`, `!` or `?`
followed by whitespace or end of content. Balanced immediately attached
`(Citation: ...)` blocks belong to that unit. Parentheses, Markdown brackets,
double quotes and matching backtick runs protect internal punctuation. Decimal
and IP dots are not boundaries because they are not followed by whitespace.
Known abbreviations (the explicit ABBREVIATIONS set), letter initials and
ellipses make the entire unit ineligible rather than splitting at that point.
Unbalanced markup can make the remainder ineligible. Single-word headings,
unfinished tails, forged double-bracket markers and units longer than 160 Unicode
characters are omitted whole. There is no fallback to fixed-width slicing.

Each entry retains quotation_id, evidence_id, exact original start/end offsets
and excerpt. Only inter-unit whitespace is outside those offsets; text inside
the span is neither normalized nor rewritten. Exclusions can be recorded with
the same exact offsets/text and a deterministic reason. All full retrieved
passages remain unchanged. No eligible unit means explicit
PipelineError(code='invalid_output', stage='quotation_catalogue') before inference.
No P01 rules, source ranking, preferred quotation or manual candidate selection
are used. Token and final-rendering limits remain strict, without truncation or
catalogue pruning to force a request to fit.

These rules establish source boundaries under this limited grammar, not universal
English sentence detection, grammatical independence, informativeness or semantic
relevance. Unknown abbreviations and unsupported source markup may be misread;
pronouns may require context; complete but irrelevant units remain possible.
The conservative exclusions deliberately lose some useful source content. Full
passages remain available to the model and reviewer. The original 160-character
slicer and its failed real-model output remain preserved as before evidence.

The model selects only `summary.quotation_id` from the catalogue enum. It cannot
supply an excerpt, evidence ID, incident observations or replacement evidence.
Code resolves the exact source/evidence pairing, rechecks its offsets and exact
membership, then renders the reference quotation and code-owned citation marker.
Malformed/unknown selections fail at source_selection; span integrity failures
remain quotation_integrity. Final rendering is compared with the trusted fields;
there is no parser that rediscovers quotation boundaries from arbitrary text.

Code copies incident.description as a JSON-quoted literal labelled
**Supplied incident report (unverified input)**. This attributes the description
to the input; it does not independently verify its claims or reinterpret endpoint
roles. Policy-listed hosts never become observed hosts through report rendering.
Original whitespace, Unicode and escaping are preserved in the copied value.
Ordinary brackets in copied data are literal; double-bracket sequences in the
report fail explicitly at incident_report_markers rather than introducing forged
citations or being silently rewritten.

Before inference, every possible report-plus-quotation rendering is checked
against the existing summary limit (8000 characters, including JSON escaping,
labels and citation). If any selection would exceed it, incident_report_size
fails explicitly. No oversized incident description is silently truncated. This
is stricter than accepting an 8000-character description that cannot fit in the
public summary once its necessary attribution is added.

Verdict, risk, MITRE predictions and every model-provided action field remain
visible and unchanged through the existing #11 parsing/policy/result validation.
Trusted code still supplies action IDs, approval state, SSH scope and duration.
No action is silently removed, repaired or direction-corrected. Empty retrieval,
invalid output and shared deadlines retain their existing typed behavior. The
normal deadline remains 180 seconds; explicit 300-second diagnostics remain
possible, with any earlier caller deadline taking precedence.

Catalogue selection proves quotation integrity only. It does not prove relevance,
claim support, correct incident interpretation, mappings, triage or action safety.
The model still receives the full incident, policy and retrieved evidence as
untrusted input, plus the deterministic catalogue. Their combined input-token
budget remains enforced without truncation.

## Internal directional definitions

The vector-only internal decision schema now defines `target` as the observed
endpoint on which containment would apply; policy permission alone is not an
observation. It defines `source_ip` as the originating IPv4 peer for the activity
being contained relative to that target, not the destination merely because its
address appears among entities. Missing directional evidence permits abstaining
from the proposal. Definitions contain no case IDs or incident addresses.

These descriptions reach both model-input channels: ContextGenerator serializes
the schema into user-message `required_output`; LlamaServer sends those messages
to `/apply-template`, tokenizes the returned text and sends it as
`/completion.prompt`. The schema also goes separately to `json_schema` for
grammar conversion. The saved boundary run's actual template retained the entire
user message. A new fake-HTTP regression exercises the real pipeline/adapter and
checks the definitions in template messages, tokenization input and completion
prompt, as well as the grammar schema. Its simulated template/tokenizer/model
establish instruction delivery, not a real token count or semantic correctness.

Only annotations on a deep-copied internal schema changed. Public contracts,
shared validation, quotation boundaries and model judgment/action fields are
unchanged. Membership validation still does not prove direction. The last
real-model boundary evidence below predates these definitions. The subsequent
single approved comparison also retained unsupported T1078, the wrong blocking
IP and inadequate action reasoning; no improved behavior is established.

## Executed direction-definition comparison — 2026-11-10

The [source-first and every-field assessment](evidence/P01-direction-20261110-01/README.md)
and [complete synthetic packet](evidence/P01-direction-20261110-01/evidence.json)
record one live P01 completion. Before inference, actual inputs, live retrieval,
catalogue/exclusions, system prompt, launch and decoding settings matched the
boundary run. Removing only target/source_ip descriptions made schema, user
message and formatted prompt identical. Actual input was 2,462 tokens (+84),
within cap 3,072; output512/context4096 and shared deadline300s were unchanged.

**Source direction failed again:** one proposal used destination10.77.0.20 as
source. No abstention occurred. Quotation relevance passed for the same complete
SSH definition, but unsupported T1078 and weak action reasoning persisted. The
entire raw answer was byte-identical to the boundary run; all fields were kept
without repair. This case shows no observed correction from the definitions,
not a universal conclusion. Pipeline141.804s includes a roughly71s inspection
pause;175 output tokens/EOS/not truncated. It is not a speed comparison.

The frozen definitions export's154 scoped tests passed; they are not model-quality
evidence. Full source, comparison receipts, prompt/token records, raw/structured
outputs and prior failures remain under `.local/P01-direction-20261110-01/`.
Source direction, unsupported mapping, action reasoning and reviewer acceptance
remain unresolved. No additional experiment, code change, commit, push or merge
followed this assessment.

## Executed boundary correction — 2026-11-10

The [boundary review and every-field assessment](evidence/P01-boundary-20261110-01/README.md)
and [complete synthetic evidence packet](evidence/P01-boundary-20261110-01/evidence.json)
record the sole approved pinned live P01 attempt after `sentence-boundaries-v1`.
Before inference, all six actual candidates and five exclusions were inspected;
the prior incomplete ESXi fragment was absent, complete source sentences remained,
and actual input2378 tokens fit cap3072. No preferred candidate or answer was
inserted, and query/MITRE-only K=2/exact retrieval and prompt were unchanged.

Boundary/integrity and quotation relevance passed for this case: the model chose
the exact88-character complete SSH protocol sentence at source[201:289]. Pipeline
completed in89.281s, one retrieval and one completion,175 output tokens, EOS and
no truncation. The300s shared diagnostic deadline included a roughly20s inspection
pause; production default180 is unchanged. No general speed/quality claim follows.

Decision quality **failed**: unsupported T1078 persisted and destination10.77.0.20
was again proposed as source. Neither was repaired or hidden. true_positive/medium
is defensible for the reported attempt, not proof of successful compromise or
independent risk reasoning. Generic risks and vague rollback remain limitations.
The better quotation does not fix these decision/action errors or complete #19.
Reviewer acceptance and hosted CI remain pending. All previous failures remain.

Frozen clean-export checks passed292 tests (including106 vector/29 generation),
actual integrity, Ruff and whitespace. Secret scans retain the same adjudicated
non-credential findings/exit1; no all-checks-green claim. Exact source snapshots,
exclusions, tokenizer response, gate hashes, raw output and complete results are
preserved under `.local/P01-boundary-20261110-01/`. No additional model attempt,
commit, push, merge or reviewer message followed.

## Executed live P01 investigation — 2026-11-09

The approved single live-retrieval investigation completed using the current
catalogue implementation. See the [review record and field-by-field assessment](evidence/P01-live-catalogue-20261109-01/README.md)
and [sanitized complete evidence packet](evidence/P01-live-catalogue-20261109-01/evidence.json).
They include actual passages/IDs, raw output, complete structured result, exact
configuration/provenance, recorder source and before/after limitations.

Pipeline completion passed: one real retrieval, one completion, status=ok in
109.531 seconds (3.523 retrieval; 105.826 generation client), 3042 input tokens,
236 output tokens, EOS and no truncation. Query, MITRE-only filters, K=2 and exact
search were unchanged. The approved diagnostic budget was 300 seconds; the normal
default is still 180. No retries, repairs, model swaps or response execution occurred.

Before inference the recorder defined suitable evidence as support for a relevant
general reference statement, without requiring independent verification of incident
facts. The actual full SSH passage met that rule. The model nevertheless selected
Q-000-00480-00640: an exact but irrelevant, incomplete ESXi/citation fragment.
Quotation integrity passed; relevance failed. Code copied and attributed the
incident report correctly, but undetermined/T1078/T1098 and a block proposal using
destination 10.77.0.20 as source remain visible. Action quality failed; medium risk
is defensible without a supplied rationale. The shared role-blind validator was
not changed. Every substantive field is assessed in the review record.

Historical P01 failures, including the 223.069-second Phi quotation rejection,
invented host/IP claims and reversed-IP proposal, are preserved. This run differs
from that fixed-evidence Kaggle trial in generation handling, retrieval mode and
environment; it is not a controlled speed or model comparison. Reviewer acceptance
and applicable CDC completion remain pending. No perfect-accuracy claim or #19
closure follows from structural completion. The plans below describe their state
when written; this section records the actual approved execution.

Fresh applicable checks: 98 vector and 20 contract tests passed; Ruff passed.
Baseline had 24 passes and the same three policy-digest CLI errors. The dev image
lacks Git, so its repository-integrity command/check harness failed; this is
retained rather than described as passing. CRLF-aware host whitespace checking
passed; supplemental conflict/link checking uses the real host Git file list.
Exact logs and check summary accompany the evidence. No full-suite or latest
hosted-CI pass is claimed.

## Separate shared source/destination validation limitation

The v1 incident entity contains type/value but no structured directional role or
host/IP binding. #11's _action checks the IP is observed, not that it is the source.
The normalizer retains role wording in description text but flattens entities.
This task does not infer roles, parse P01-specific prose, hardcode IPs, add a guard,
or alter shared contracts/validators. A reversed observed IP can still pass the
existing policy check. Track authoritative role preservation and role-aware
validation as a separate shared-contract/validator issue. Policy/schema validity
and proposed/approval-required status do not establish correct action arguments.

## Deterministic checks and historical live-investigation plan

Run deterministic generation checks with:
`python -B -m unittest discover -s tests/vector -p test_generation.py -v`.
These verify catalogue ownership/pairing, report attribution, limits, unchanged
judgments/actions, marker validation and typed failures, not model quality.

Historical plan: executed by the 2026-11-09 live run and superseded by the
boundary and direction records above. This text grants no new run authorization.
At the time, the proposed acceptance example was **LIVE retrieval plus generation**, not
another saved-response replay: instantiate #17's exact Retriever against the
verified existing 340-record/406-vector preview, use the unchanged P01 request
(MITRE-only, top_k=2), and call this complete VectorPipeline once with #11's
verified Phi/Linux runtime. Do not rebuild embeddings/indexes or substitute the
full corpus. If pinned corpus/model/index receipts or sufficient compute are
unavailable, stop and record the missing prerequisite; do not describe a replay
as live retrieval. No environment setup or model run is authorized by this plan.

Before that separately approved attempt, freeze the dirty source snapshot and
hashes, prompt, internal schema/catalogue algorithm, incident/policy/query,
retriever/model/index/runtime identities and environment. Keep the current
512-output-token, 3072-input-token, 4096-context settings, temperature 0, seed 42,
cache_prompt=false, n_keep=0, six CPU threads and one slot. An explicitly recorded
300-second diagnostic budget is permitted by the current runner; it is not the
production default or a clean model-only comparison. Token-budget failures remain
failures rather than triggering catalogue pruning or silent truncation.

Use a fresh run directory and exclusive marker. Capture actual live retrieval,
passage order/IDs, catalogue/spans, request/schema/messages, raw/partial generation,
endpoint/chained-exception/process logs, before/after health, timings and result or
typed failure. Keep labels outside model input; preserve all earlier attempts.
At most one completion, no repair, retry or fallback, and export on failure.

Assess separately: complete structural execution; exact report/quote attribution;
quotation relevance; and every verdict/risk/MITRE/action claim, including negative
evidence, source/destination roles, containment risks and rollback. Identify
unsupported and uncertain claims explicitly. A valid quotation or JSON alone is
not a grounding pass. Publish a sanitized reproducible before/after assessment
for Oussama, retain remaining failures, and complete applicable CDC checks/review.
Issue #19 remains unresolved until the resulting evidence and feedback disposition are assessed. This historical plan has since been executed; see the records above.

## Historical evidence and handoff

The following records describe earlier implementations and trials, not the current
catalogue-selection request shape. Earlier artifacts remain unchanged.

## Reviewer and data handoff

Oussama can review [PR #90](https://github.com/CyberSOC-ai/cybersoc-ai/pull/90) now using the preview. Task #20 consumes the reviewed generation interface. Ahmed can prepare a separately versioned full-data release in parallel as agreed by the team. Keep the preview and its receipts available so the original run can be reproduced.

Anas's [Sprint 2 journal](../../../../sprints/sprint-02/README.md#3-anas) records the outcome and limitations. Detailed evidence lives under the local bundle root `.local/preview-index-340-v1/`:

| Local path relative to the bundle | Purpose |
|---|---|
| `runs/P01-selection-f40eaf64ad59/` | Full P01 run. Compare `raw-answer.txt`, `retrieval-response.json` and `result.json` to inspect the model selection, cited passage and proposed action. Consult `request.json`, `run-config.json`, `ready.json` and `measurements.json` for settings and provenance. |
| `runs/selection-23bad1ed6de742e5baf4ba6a40f19d5d/` | Two-order LSASS/SSH diagnostic; each order has its own raw answer and outcome. |
| `runtime/READY.json` | Paths and identities of Anas's restored index inside the container. Restore the preview on the reviewer's machine for a rerun. |

The full P01 call passed structural validation; its incident-specific summary came from the alert and its selected spraying passage did not support those details. The two MITRE predictions differed from the pilot label. Review claim support separately from marker validity.

Keep raw run files, models, Docker volumes and the handoff archive outside Git. A local path is a locator on Anas's PC; for independent inspection, Anas can provide a sanitized evidence extract privately to the reviewer. Follow the [experiment conventions](../../../../../experiments/README.md) for access and provenance. Windows line-ending adjustments made during restoration are workstation setup and should not be committed with #19.


## Retrieval deadline follow-up

Previously the pipeline checked its deadline only before and after retrieval.
Each Qdrant call independently received the client's 60-second timeout, so a
sequence of state checks and collection searches could exceed the investigation
budget before generation even began.

`VectorPipeline.investigate(..., deadline=...)` now passes the earlier of the
supplied monotonic deadline and its own configured limit to
`Retriever.retrieve(request, deadline=...)`. That optional keyword does not alter
JSON contracts; existing `retrieve(request)` callers still work. Custom injected
retrievers used by VectorPipeline must accept the deadline keyword rather than
silently ignoring it.

Retrieval checks the remaining time before/after local manifest reads and query
encoding, both state-verification passes and the collection searches. Qdrant
version, collection-info, count and query calls all use the same absolute deadline.
Immediately before each HTTP request, the REST adapter calculates
`min(60, deadline - time.monotonic())` and passes it through HTTPX's supported
per-request timeout setting for connect/read/write/pool phases. It never changes
the shared client's defaults. Expiry prevents further operations and partial or
late evidence is discarded. HTTPX timeouts and retrieval deadline expiry produce
the existing `timeout` retrieval error; the pipeline reports
`PipelineError(code='timeout', stage='retrieval')` and does not generate.

This is cooperative deadline enforcement, not hard cancellation. A local file
read or CPU embedding already in progress cannot be interrupted; overrun is
detected when it returns. [HTTPX timeouts](https://www.python-httpx.org/advanced/timeouts/) bound transport phases/inactivity, not an
atomic total wall-clock duration for the entire exchange: scheduling, multiple
phases or a continuously progressing response can exceed the remaining budget.
A request already sent does not cancel server-side Qdrant work. Post-operation
checks reject late responses and no subsequent operation receives a fresh full
budget. There are no added background threads, automatic retries, model downloads
or index builds. Startup artifact/model verification is outside an individual
investigation's deadline.

Regression tests in `tests/vector/test_deadlines.py` use a fake monotonic clock,
HTTPX MockTransport and synthetic index fixtures; no sleeps, live Qdrant or models
are needed. They cover successful shared-budget retrieval, expired deadlines,
slow operations, transport errors, multiple calls, sanitized pipeline error mapping
and unchanged no-deadline behavior.

## Historical — grounding status at the accepted timeout revision

The following status applies to 96f29f0 before the catalogue, boundary and
direction follow-ups. Current evidence and unresolved failures are recorded above.

The timeout fix does **not** change the prompt, citation validation, model selection
or grounding behavior. Citation IDs are validated for membership in the retrieved
set. The pipeline does **not** establish that the selected passages semantically
support the generated claims. The previously reported full-incident P01 run
contained unsupported claim-to-passage attribution even though its citation ID
and result structure were valid. No grounding fix or new real-model grounding
validation was performed in this change.

Further investigation and full-incident grounding evaluation are required;
[Issue #21](https://github.com/CyberSOC-ai/cybersoc-ai/issues/21) is a potential
follow-up, not an authorized transfer or waiver of Issue #19's acceptance criteria.
Treat this as an unresolved known limitation. Neither green tests nor a successful
source-selection diagnostic proves that the evidence-grounded-generation
acceptance criterion is satisfied.

## Historical — model-written quotation integrity change

The internal decision separates incident observations from an exact reference
excerpt and selected evidence ID. Empty/whitespace-only excerpts are rejected;
substring membership is checked against that selected passage without trimming,
case folding or whitespace normalization. A mismatch raises InvalidOutput at
quotation_integrity; malformed decisions retain source_selection failures.
Excerpts are limited to 160 Unicode characters. Ordinary Markdown brackets are
allowed in exact excerpts; double-bracket sequences remain forbidden. Evidence remains
pipeline-owned and the public v1 schema and shared deadline are unchanged.
Quotation integrity establishes neither relevance, claim support nor correct
triage. Incident observations remain model-generated and require review.
Issue #19 grounding acceptance remains unresolved.

### Historical replay plan (superseded by the feasibility trial below)

Replay P01-review-separated-ced3e0104ccf's saved incident, policy, request and
retrieval-response through generation with a fixed-response retriever.
This tests generation with fixed retrieved evidence, not live retrieval or the
complete live pipeline. Preserve evidence order, model artifact, seed 42,
4096 context, 3072 input/512 output token limits and 180-second budget.
Record actual runtime identity, source/input hashes, dirty state, exact settings,
raw output, result or typed failure and timings in a new private run directory.
Do not install, restore an index, rebuild embeddings, retry or vary prompts.

Review every output claim against its appropriate source: incident observations,
reference quotation and its relevance, MITRE mappings, verdict/risk, and all
proposed action fields (including justification, effects, risks and rollback).
Success requires a valid full result, exact relevant quotation, no unsupported
attribution or fabricated observations, and justified mappings/verdict/actions;
uncertainty must remain explicit. Any violation or typed failure fails this run.
If an exact valid quotation still produces misleading incident attribution,
abandon this approach rather than starting another prompt sweep. Passing this
single development replay cannot establish general grounding or close #19.

## Historical — bounded model-written quotation and CPU feasibility trial

The 160-character internal excerpt limit admits short source sentences (the P01
SSH passage has an 88-character plain sentence and a 133-character Markdown
sentence), while reserving more of the unchanged 512-token allowance for analysis.
Characters are not tokens; this cannot guarantee a complete result. Oversized,
empty, whitespace-only and nonexact excerpts fail; nothing is truncated/repaired.

After exact membership validation, ContextGenerator retains the observations,
excerpt and selected ID. The final summary must equal their trusted rendering.
Strict citation parsing then checks observations plus the code-owned marker;
no arbitrary string parser is used to rediscover quotation boundaries. Ordinary
Markdown in the already verified excerpt is literal source text. Forged/malformed
markers remain rejected. Evidence ownership, typed errors and public v1 contracts
are unchanged. Exact membership still proves neither relevance nor claim support.

The inspected Phi completion-02 attempt emitted an exact 697-character prefix,
then timed out at 180 seconds before decision fields. This is not reasoning
failure evidence. The next prepared run changes BOTH quotation rules and the
explicit diagnostic budget to 300 seconds: a CPU feasibility trial, not a clean
model-only comparison. The normal pipeline default remains 180 seconds; any
earlier supplied deadline still wins. No CDC/contract mandatory 180-second limit
was found; the #11 runner already accepts explicit budgets up to 3600 seconds.

Prepare a fresh code snapshot, request/schema/prompt hashes and a separate run
and marker. Keep all previous artifacts unchanged. Reuse the pinned Phi/Linux
runtime, P01 inputs, evidence/order, validators, 3072 input cap, 4096 context,
512 output cap, temperature 0, seed 42 and existing decoding settings. Use one
orchestrated server/client-child lifecycle with endpoint/traceback/process logs,
child health checks, at most one completion, no retries, and export on failure.
No live retrieval, model substitution, labels in input or embeddings/index build.
Success requires a complete defensible result under full claim review; structural
validity and exact quotations alone do not complete #19. Timeout/truncation stays
failed. That prepared trial subsequently ran; its failure and later live before/after evidence are preserved in the records above.

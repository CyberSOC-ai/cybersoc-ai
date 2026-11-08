# Vector generation — issue #19

`VectorPipeline(retriever, generator, root).investigate(incident, policy, request)`
returns `(investigation_result, measurements)`. Supply the existing
`rag.vector.retrieve.Retriever` and `ai.baseline.llama_server.LlamaServer` instances;
loading verified artifacts remains explicit setup. The request must satisfy the
existing retrieval-request contract and use vector mode. No API route is added.

The pipeline composes BaselineRunner's existing decision parsing, proposal-policy
checks and result validation through a context generator. Each invocation creates
its own runner, overrides its prompt, then validates citations before returning a
vector envelope. The internal baseline envelope is never exposed as a fallback.
No teammate runner or retriever code is modified.

Markers are exactly `[[evidence_id]]`. IDs use the contract's ASCII identifier
alphabet; `rag/vector/chunking.py` generates CHK- plus a digest. Neither allows
square brackets. A strict regex extracts markers; all remaining square brackets
are rejected to reject malformed/nested markers. At least one marker is required,
and every marker must match retrieved evidence. Pipeline-owned evidence is copied
from the validated retriever response; model-supplied evidence is forbidden by
the existing decision schema. All retrieved entries are retained, including any
not cited. This checks reference validity only, not claim support or completeness.

Empty retrieval raises PipelineError(code='invalid_output', stage='empty_retrieval')
before inference. Retrieval errors preserve their code; malformed responses fail
with invalid_output. Invalid generation and citations raise existing InvalidOutput.
No repair, retry, truncation or No-RAG fallback is performed. Retrieved content is
JSON data in the user message and never part of the trusted system instructions.
Prompt separation does not establish resistance to all prompt injection attacks.
The investigation's shared monotonic deadline is passed to retrieval and its
Qdrant reads; see the timeout follow-up below. Existing no-deadline retrieval
callers retain their original behavior.

Run synthetic integration tests with:
`python -B -m unittest discover -s tests/vector -p test_generation.py -v`.
Anas also ran the Linux CPU model locally on revision `fe9c9ab`. See the handoff below.

Runtime prerequisites absent from this checkout at implementation time:
- `.local/models/qwen2.5-1.5b-instruct-q4_k_m.gguf` and the configured llama.cpp runtime;
- acquired embedding model, chunk/vector artifacts, verified index receipt/spools;
- Qdrant at the default localhost:6333 endpoint (connection refused).
See the existing vector evaluator setup and baseline configuration documentation.

Follow-up for Oussama: a structured claim-to-evidence field requires a reviewed
contract change. The current v1 schema remains unchanged. API integration (#20)
and the formal comparison experiment (#21) remain separate tasks.

## Source selection

The internal model decision uses summary.claim and summary.evidence_id. The
latter is a required enum generated from this retrieval. Code strictly parses and
validates the entire decision before formatting the claim and selected ID as a
public summary. No default selection, guessing or automatic repair is allowed.
A valid selection identifies a passage; assess support separately.

The P01 and LSASS prompt-only attempts omitted required inline markers. A summary
regex in the decoding schema caused repetition in the b11827 A/B probe.
The selection probe (python -m rag.generation.selection_probe --help) uses the
existing LSASS and SSH retrieval responses, runs both passage orders, and saves
raw model decisions and outcomes. This diagnostic does not count as a full
incident run. Both passage orders selected the supporting LSASS source in Anas's run.

## Reviewer and data handoff

Oussama can review [PR #90](https://github.com/CyberSOC-ai/cybersoc-ai/pull/90) now using the preview. Task #20 consumes the reviewed generation interface. Ahmed can prepare a separately versioned full-data release in parallel as agreed by the team. Keep the preview and its receipts available so the original run can be reproduced.

Anas's [Sprint 2 journal](../../docs/sprints/sprint-02/README.md#3-anas) records the outcome and limitations. Detailed evidence lives under the local bundle root `.local/preview-index-340-v1/`:

| Local path relative to the bundle | Purpose |
|---|---|
| `runs/P01-selection-f40eaf64ad59/` | Full P01 run. Compare `raw-answer.txt`, `retrieval-response.json` and `result.json` to inspect the model selection, cited passage and proposed action. Consult `request.json`, `run-config.json`, `ready.json` and `measurements.json` for settings and provenance. |
| `runs/selection-23bad1ed6de742e5baf4ba6a40f19d5d/` | Two-order LSASS/SSH diagnostic; each order has its own raw answer and outcome. |
| `runtime/READY.json` | Paths and identities of Anas's restored index inside the container. Restore the preview on the reviewer's machine for a rerun. |

The full P01 call passed structural validation; its incident-specific summary came from the alert and its selected spraying passage did not support those details. The two MITRE predictions differed from the pilot label. Review claim support separately from marker validity.

Keep raw run files, models, Docker volumes and the handoff archive outside Git. A local path is a locator on Anas's PC; for independent inspection, Anas can provide a sanitized evidence extract privately to the reviewer. Follow the [experiment conventions](../../experiments/README.md) for access and provenance. Windows line-ending adjustments made during restoration are workstation setup and should not be committed with #19.


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

## UNRESOLVED — citation grounding

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

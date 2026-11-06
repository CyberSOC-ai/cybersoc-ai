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
The shared deadline is checked around retrieval; it does not interrupt a running
retriever call. Existing retriever transport timeouts still apply.

Run synthetic integration tests with:
`python -B -m unittest discover -s tests/vector -p test_generation.py -v`.
These tests make no model-quality claim. Real model execution: not run.

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
incident run. Real-model validation of this revision is pending.

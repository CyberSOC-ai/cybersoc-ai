# Incremental preparation: local validation

Date: 2026-10-30. Local branch: `codex/incremental-vector-index`.
Publication and hosted CI are tracked on the follow-up PR. This document records
local evidence; it does not claim independent peer approval.

## Automated checks

232 tests passed locally: 62 vector, 20 contract, 43 evaluation, 20 backend,
16 normalizer, 44 ingestion and 27 baseline. Ruff, repository/link integrity
(including new files), whitespace checks and source/test secret scans passed.

The 12 incremental tests cover unchanged work with no encoder loading or token
splitting, additions/edits/deletions, metadata-only acquisition changes, updated
reference headers, corrupt historical streams/receipts, incompatible model or
chunking settings, failure isolation, full validation of new input, inherited
preview limits, explicit expansion of coverage and CLI selection semantics.

## Real-model / real-Qdrant check

Used the existing pinned BGE-small CPU image and persistent Qdrant 1.20.0 with the
previous 340-record / 406-point development release. The original corpus, vectors
and collections were preserved. New test data was a **controlled synthetic
derivative**, marked with its own provenance/notice; it is not upstream CVE data
or a new acquisition to be used for relevance evaluation.

The update kept the desired record count at 340: add one real source record from
outside the previous selection, edit one selected CVE with an explicit synthetic
validation note, remove another selected CVE and refresh CVE provenance. Results:

| Work | Result |
|---|---:|
| Records reusing source spans | 338 |
| Records requiring chunking | 2 |
| Previously chunked records absent from new selection | 1 |
| Reused spans / vectors | 404 |
| Unique embedding texts encoded | 2 |
| New index points | 406 (369 knowledge + 37 SOC) |

Preparation took approximately 38 seconds in this small test, including cache
checks, model loading, inference, full collection loading and readback. This is
not a full-corpus performance estimate. Incremental chunk bytes exactly matched a
fresh chunking control. New and old readers both returned the same unaffected
playbook query results. Reopening the original reader after publication still
worked, confirming that the original collections were retained.

A second update with no corpus changes reused all 406 spans/vectors, encoded zero
texts, performed no token splitting, loaded no inference model, and inherited
full selection rather than silently falling back to the preview default. Both
updates published independent READY receipts and separate collection names.

Detailed artifacts/logs remain outside Git under `.local/s2t02/incremental-proof/`
and `.local/s2t02/incremental-*.txt`. The original 406-point index receipt and
original chunk/vector files were not replaced. No full-corpus embedding run,
GPU run, gold-label relevance evaluation or storage-level delta index update is
claimed. Each new index version still loads all selected points.

## Checkout stability

The real check first detected that Windows checkout had changed new vector
configuration/dependency files from LF to CRLF, invalidating raw-byte receipt
hashes. Restoring their verified LF bytes made the original index queryable again.
The repository attributes now enforce LF for vector JSON configurations,
`requirements-embeddings.txt` and the CPU embedding Dockerfile. The existing
baseline prompt attribute is retained. Runtime dependency reuse still requires
the recorded file identities; actual dependency changes require a fresh build.

See [INCREMENTAL.md](INCREMENTAL.md) for input, version switching and failure rules.

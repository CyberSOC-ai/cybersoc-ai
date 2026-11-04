# S2-T03 technical audit — 4 November 2026

Scope: code, replay artifacts, protocol compliance and the recorded local development
experiment. Responsible owner: Ahmed. Assigned reviewer: Anas. Audit actor: AI
assistant, at Ahmed's request. No independent human/Anas sign-off is asserted.

## Findings and resolutions

| Finding | Resolution / evidence |
|---|---|
| Work only under ignored `.local`; another checkout could not inspect or replay it. | Added a versioned, text-free public evidence projection, hashes, scores and regular evaluation module. Replays offline without model/data downloads. |
| Critical runner checks used `assert`, disabled by optimized Python. | Replaced with explicit exceptions; a subprocess regression verifies `python -O` still rejects changed input hashes. |
| Unknown labels could easily be confused with negatives. | Explicit nulls and eligibility counts; tests cover unknown top-five and unknown documents before the first positive. |
| Passage duplication and finite candidate depth could distort document metrics. | Deduplicate by snapshot + source record before K. Insufficient candidate depth is null unless ranking exhaustion is known; tests cover both cases. |
| No relevant result was not distinguished from a proven miss. | RR=0 for a proven miss in a fully judged exhausted ranking; otherwise null. Empty success, missing slots, no-positive queries and failures have distinct tests. |
| Local scripts assumed exactly ten complete successes. | Reusable evaluator counts all intended queries, rejects missing/duplicate run IDs and reports failures and metric-specific exclusions. |
| Relevance/query choices followed prior corpus inspection. | Explicit development-only classification and history; Q03/Q04 rerun; no blind-test or retriever-improvement claim. |
| Strict lookup questions have one known positive. | Precision ceiling and incomplete recall denominator are explained alongside results. |
| Ownership swap only existed on GitHub. | S2-T03 owner updated to Ahmed in the Sprint 2 table and his work journal; older historical member journals are preserved. The CDC table remains the older baseline until a dedicated governance update. |

## Acceptance assessment

Issue #18 requires retrieval measured independently before generation, with
Precision@K, Recall@K and MRR, test evidence and reproducibility. This release
provides an inspectable **bounded development evaluation** and does not claim
held-out accuracy or full-corpus coverage. No output-generation code runs.
Both upstream issues #10 and #17 were confirmed closed during the audit.

The real results replay as Precision@5=0.18, known-reference Recall@5=0.90,
MRR=0.8625 over 10/10 queries, with zero retrieval failures. The source-response
projection was compared field-for-field to local saved evidence. Publication
contains source identities and judgment rationales, not source passage content,
model weights, raw SOC logs or the private corpus/index. Full model-search replay
requires the pinned external artifacts documented in the manifest/setup guide.

## Verification before publication

The focused suite includes independent arithmetic, end-of-ranking/duplicate/snapshot
cases, error and incomplete-label behavior, hash tampering, invalid labels, duplicate
JSON keys, mismatched queries/filters, omitted cases, symlinks and output replacement.
The saved real ranking is a regression fixture, not a claim that test coverage
validates the truth of all labels. The PR records full project checks and hosted CI.

## Improvements recommended after this release

- Add diverse SOC investigation queries, multi-document positives and explicit
  corpus-coverage questions; report lookup and investigation tasks separately.
- Have a different human review labels, especially context-versus-direct relevance.
- Reserve independent evaluation queries before adjusting retrieval parameters.
- Keep Q01 as a regression; evaluate any source filtering/reranking changes on a
  versioned development set before an untouched test.
- Reevaluate relevance and resource costs on the expanded/full index. No GPU or
  complete-corpus build is established by this small run.

These are limits on generalization and future work, not concealed claims of a final
benchmark. Formal repository completion still requires the PR/CI/review-handling/
merge/issue workflow in CDC §14. This audit alone does not close an issue.

Local publication checks: all 248 project tests passed (20 contracts, 59 evaluation,
20 backend, 16 normalizer, 44 ingestion, 62 vector, 27 baseline); Ruff and tracked
Markdown/conflict integrity passed. Gitleaks found no secrets in the staged patch.
Two initial scanner alerts were verified as public tokenizer-file digests; redundant
per-file model metadata was replaced by the acquisition-receipt hash and the model/
weights/tokenizer pins, without disabling any scanner rule. JSON replay assets are
forced to LF in `.gitattributes` to keep hashes stable on Windows/Linux checkouts.

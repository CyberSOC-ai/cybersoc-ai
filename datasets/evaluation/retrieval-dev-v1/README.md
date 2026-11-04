# Retriever development evaluation v1 — S2-T03

Owner: Ahmed. Assigned reviewer: Anas. This is a **10-query development evaluation**,
not an independent test benchmark. It evaluates retrieval before answer generation.
The implementation and sanitized observed rankings are published together so another
member can reproduce the metrics without Ahmed's private `.local` artifacts.

## Replay the observed results

From the repository root, with Python 3.12 and the regular project dependencies:

```sh
python -B -m ai.evaluation.retrieval \
  --bundle datasets/evaluation/retrieval-dev-v1 \
  --manifest-sha256 4fae58e74a61784b62a7ffeb9e3d79080bfb19446304f26e950a2aa725f10ac6 \
  --output /tmp/retrieval-dev-results-new.json
```

The output path must be new. The same command works with `docker compose run --rm -T dev`
prefixed and `/tmp/...` inside the disposable container; the CLI prints the summary.
For retention, bind-mount a private artifact directory and use an output there.
The external manifest hash pins the release; all three input assets are checked
before scoring. Validations also run under `python -O`. The separate
[results](results.json) file is derived, not a trusted input; rerun to verify it.

## Files

| File | Purpose |
|---|---|
| [queries.json](queries.json) | Actual questions and source filters, with Q03/Q04 clarified. |
| [judgments.json](judgments.json) | 61 judged query–document pairs, rationales, content hashes and annotation provenance. Other pairs remain unknown. |
| [rankings.json](rankings.json) | Actual order of 100 passage identities returned for each query; contains no passage text, vectors, model answers or private SOC events. |
| [manifest.json](manifest.json) | Input hashes, corpus/index/model identities, environment and scope. |
| [results.json](results.json) | Recomputed per-query scores, failures, null reasons and aggregate denominators. |
| [AUDIT.md](AUDIT.md) | Technical audit, changes made and remaining limitations. |

Passage identity lists retain duplicates so the evaluator's document grouping is
itself replayable. The public projection was checked against the saved responses.
Each document is identified by `(snapshot_ref, source_record_id)`, not by its title
or its individual chunk ID. Content hashes in judgments link to source records in
the original corpus; they cannot independently prove an annotation is correct.

## Method and results

The [project protocol](../../../experiments/METRICS.md) defines K=5 and document
identity. The same verified S2-T02 BGE-small CPU/Qdrant index was used for all queries:
340 source records, 406 vectors, with separate knowledge/SOC collections. Filters
restrict this run to 305 knowledge documents (369 passages). No SOC events or pilot
incident families are retrieved. No LLM generates an answer during this evaluation.

Queries were authored after inspecting the corpus. Initial pooling combined vector
search and a simple document BM25 search; selected labels were completed after
reviewing candidates, before scoring. Q03/Q04 were clarified after the first trial
and all ten questions were rerun. These are retrospective development judgments,
not pre-registered independent test results. The retriever/index itself was unchanged.

| Measure | Observed result | Eligibility |
|---|---:|---:|
| Successful retrieval | 10/10 | 10 intended |
| Mean Precision@5 | 0.18 | 10/10 queries |
| Mean Recall@5 over **known labeled references** | 0.90 | 10/10 queries |
| MRR over judged prefixes | 0.8625 | 10/10 queries |

Eight reference documents are first, Q02's is second, and Q01's is eighth after
document deduplication. Q01 therefore has zero Precision/Recall at K=5 but RR=1/8.
MRR is not cut off at five. All documents before the first relevant result must
be labeled; otherwise RR is null. All top-five documents are labeled for this run.
A missing relevant hit only earns RR=0 when absence is established in an exhausted,
fully judged ranking; a truncated/unjudged candidate window instead returns null.

Precision uses K as its denominator; genuine missing slots count as nonrelevant
only if the ranking is exhausted. If 100 passage candidates do not establish five
distinct documents, the evaluator does not silently pretend the remaining slots
are absent. Unknown judgments never default to negatives. Failed retrieval stays
in the intended/failed counts, with null quality metrics and explicit eligibility.

There is **one known relevant document per question** under the strict direct-answer
policy. Thus Precision@5 is capped at 0.20 for these annotations. The 0.18 is not
18% answer accuracy. Recall's denominator is incomplete: these numbers do not prove
that 90% of all relevant knowledge in the corpus was retrieved. Related context
was graded nonrelevant if it did not directly answer the specific question.

## Review provenance and next use

Ahmed validated the reference-answer note and its 35 binary decisions in the chat.
Another 26 labels/clarifications were technically reviewed with AI assistance,
including three documents newly surfaced by the clarified queries. This technical
review is **not Anas's personal approval**, and the same assistance contributed
to both drafting and auditing. Assigned peer review is requested on the PR.
The ten-query sample is small and lookup-heavy; no population quality, uncertainty
estimate, answer faithfulness, No-RAG ablation or full-index scalability is claimed.

To reproduce **search**, rebuild the matching corpus/model/index with the
[evaluator setup](../../../rag/vector/EVALUATOR_SETUP.md), retain the same source
snapshots and recorded selection, instantiate `Retriever(..., exact=True)` and
submit each query using the v1 retrieval request contract. Fetch 100 passages,
retain their actual order, and export the four identity fields used by
`rankings.json`. Use a new version of all evaluation artifacts for a changed
corpus, labels, queries or filters. The exact original large artifacts remain local;
fresh acquisition may change contents/counts and is not the same release.

The immediate next use is the S2-T04 handoff: preserve Q01 as a regression case,
expand representative development queries and positive coverage, obtain independent
annotation review, and reserve a separate query set before claiming held-out quality.
A full-corpus index is not a completion claim of this release.

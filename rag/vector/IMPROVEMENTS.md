# Vector RAG improvements

## Observed limits

The frozen seven-case run produced six valid results and one policy rejection.
Verdict agreement stayed at 4/7. Account labeling improved, SSH labeling regressed,
and PowerShell approval/artifact/completion evidence remained underused. The group
case asserted maliciousness, emitted an unqualified technique and proposed an
action with no eligible target. Validation rejected it; the model response was
not corrected. All six accepted answers selected IDs, but none explained a
reference-derived technical fact. These are measured generation limitations.

- Draft retrieval judgments list known supporting and selected non-answering
  documents; unlisted documents remain unjudged. Expand adjudicated relevance
  before making full precision or final benchmark claims.
- Topic similarity does not establish answerability of approval, attribution or
  exploitation questions. Keep reference knowledge separate from host observations.
- First-event query extraction is deliberately simple. It can miss relevant later
  configuration details or choose a broad platform document. Evaluate alternatives
  on new reviewed examples rather than hand-coding these seven case identities.
- Two context passages constrain token use but can omit needed complementary facts.
  Compare context sizes under measured budgets with separate experiment identities.
- Source ID membership and exact passage provenance are structural checks, not
  entailment. Review reference-supported statements and citation usefulness.
- A compact generator may restate incidents, ignore approval context or select
  decorative references. Retrieval is not assumed to fix reasoning failures about
  information already present in the input.

## Future work

1. Finish independent relevance/answer review, broader positive/negative incident
   coverage and paired human claim validation. The current development set is not
   an untouched test benchmark.
2. First test one general generation change that requests explicit evidence-based
   rationale and useful analyst verification in the summary. Keep required input
   facts separate from reference explanations, and preserve unknown intent. A
   scope-dependent action schema could prevent structurally ineligible proposals,
   but would need a separately recorded comparison configuration; it would not fix
   the underlying maliciousness/approval reasoning. Do not silently constrain or
   repair this frozen run. Then compare one retrieval or generation change at a
   time: query construction,
   passage size, document diversity, context budget or an approved model variant.
   Preserve failures and do not rewrite earlier source/run artifacts.
3. Validate fresh-image and teammate/cloud reproduction, native snapshot portability
   and performance at larger corpus sizes. Local restore is not a cloud cycle.
4. Add a reviewed API composition only after the standalone pipeline is accepted.
   Keep model/index initialization outside request handlers, retain bounded shared
   execution and fail explicitly without falling back to No-RAG.
5. Consider reranking, lexical/identifier-aware retrieval or later Graph/Hybrid
   integration only as separately evaluated scope. The present delivery is dense
   Vector RAG, not an agent or Hybrid implementation.

## Data growth

Create a new source release for accepted changes. Retain predecessor identities,
stable document IDs, source notices and hashes; never index evaluator labels or
held-out incidents. Reuse embeddings only for identical inputs under a compatible
encoder/model/tokenizer environment. Give indexes, packets and runs new identities.

The No-RAG reference and its scored record remain unchanged. A RAG comparison must
report source coverage, context changes, failure counts and actual latency boundaries
before claiming an improvement. Independent reproduction and the complete B0
handoff remain separate gates under the project roadmap.

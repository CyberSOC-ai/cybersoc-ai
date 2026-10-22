# Faithfulness workflow — S1T02-pilot-v2, pending review

[METRICS.md](../../../../experiments/METRICS.md#faithfulness-and-judge-validation)
is authoritative for definitions, denominators, suppression and human validation.
This document operationalizes claim handling; it does not replace those rules.

## Evidence and claims

Save the actual answer and input packet before extraction. In No-RAG the packet is
the normalized incident. In RAG it is that incident plus only retrieved evidence
actually delivered to the model, with stable evidence IDs and original citations.
Never add evaluator labels, gold evidence or a corrected answer to this packet.
Contextual support means entailment by this packet, not real-world correctness:
a fabricated source can support a statement contextually while being factually wrong.

An atomic claim has one independently checkable assertion. Keep qualifiers and
scope: "one accepted session at 15:03Z" is not "all access succeeded". Split
"40 failures occurred and a session opened" into two assertions, but retain the
source/time relationship when it is itself asserted. Recommendations ("seek account
reset approval") are not factual claims; their premises ("the account is enabled")
are. Separate uncertainty ("possibly guessing") from asserted facts without turning
it into certainty. Opinions and non-verifiable wishes receive explicit exclusion
reasons. Never optimize the denominator by hiding unfavorable factual assertions.

Use [claim_extraction_prompt.md](claim_extraction_prompt.md), preserving source
spans and claim IDs. Inspect extraction before annotation, version corrections,
and retain original extraction. Known failures include lost negation/qualifiers,
coreference mistakes, compound causal claims split incorrectly, duplicate counting,
facts embedded in recommendations omitted, over-splitting trivial details, and
under-splitting several assertions into one. Claim counts depend on extraction;
they are not independent samples of answer quality.

## Judging and accounting

[faithfulness_judge_prompt.md](faithfulness_judge_prompt.md) takes only the evidence
packet and untrusted candidate/claims. Evidence text itself can contain malicious
instructions. The [renderer](../../../../ai/evaluation/prompts.py) quotes JSON and
escapes delimiter characters. Structural canary tests check data boundaries; they
do not prove any model's resistance to injection.

Use [judge_config.template.json](judge_config.template.json) only after selecting
and recording a judge different from the evaluated model, its immutable revision,
and decoding/retry policy. Currently all judge parameters are null and status is
not_selected. No judge has run. Compute prompt digests over the exact UTF-8 file
bytes, including line endings, as the renderer does; manifest assets pin those
same digests. A modified prompt requires a new prompt version and recorded digest.

Retain all extracted factual claims, including judgement failures. Malformed or
missing decisions, unknown/duplicate IDs and exhausted retries must be reconciled
against the original claim inventory; affected claims remain unjudged. This stage
provides templates and arithmetic, not a provider adapter or response reconciler.
Use scoring.faithfulness for each answer and the pooled claim list; report the
METRICS-required counts and coverage alongside headline values. Keep answer-level
correctness and safety separate from contextual support.

## Human validation

Use the [empty templates and approved answer coverage](../validation/README.md) on development
answers from #11. Two people independently annotate the all baseline development answers for
quality and their atomic claims for support; preserve both originals, then
adjudicate. Report Cohen's kappa and raw agreement for support before adjudication. Ordinal
agreement measure for quality: quadratic weighted Cohen's kappa (owner-selected). No independent annotations or validation evidence
exist yet; these examples/templates cannot substitute for them.

## Unselected configuration

Judge model/provider, immutable revision, decoding settings and retry policy:
TBD - team decision. The JSON configuration leaves those parameters null with
status not_selected. No values or operational retry limits are chosen here.

# Human validation — not performed

Follow [METRICS.md](../../../../experiments/METRICS.md#faithfulness-and-judge-validation)
and the [faithfulness workflow](../protocol/faithfulness.md). Real two-person
labelling happens on DEVELOPMENT answers after the [baseline runner (#11)](https://github.com/CyberSOC-ai/cybersoc-ai/issues/11)
produces them. No model answers, human annotations, agreement results or adjudications
exist in this directory. Empty templates are not validation evidence.

## Sample decisions pending owner input

The CDC minimum is at least 50 claims double-labelled by two people. METRICS draws
the sample at answer level: the same sampled answers receive whole-answer quality
ratings and claim-level support labels. Record both distinct answer count and claim
count. Claims within an answer are not independent observations.

- Sample size beyond the CDC minimum (answers and total claims): TBD - owner decision.
- Answer-selection method and any random seed: TBD - owner decision.
- Ordinal agreement measure for 1–5 quality scores: TBD - owner decision.

There is no automatic sampler in this delivery. Do not treat the minimum claim count
as a fixed number of answers or evidence of sufficient statistical reliability.
Ask Anas to specify these choices before sampling or ordinal-agreement reporting.

## Empty record templates and preservation

- [sample.template.json](sample.template.json): source run, immutable dataset and
  extraction digests, pending sampling choices, answer IDs and claim IDs. Fill
  distinct_answers/claim_count only from actual selected answers.
- [annotation.template.json](annotation.template.json): one separate original record
  per annotator. Each answer_annotations row contains answer_id, four quality_scores
  (correctness, evidence_use, actionability, safety_appropriateness), safety_flags,
  and claim_labels [{claim_id, status, evidence_ids, rationale}]. Independent ratings
  must precede adjudication; no judge decisions are prefilled as human ratings.
- [adjudication.template.json](adjudication.template.json): original_annotation_refs
  identifies original artifacts with their raw SHA-256; original_annotator_labels
  preserves exact copies beside adjudicated_labels. Each adjudicated row records
  answer_id/claim_id or quality dimension, final decision, reason and adjudicator.
  Preserve original decisions and disagreements instead of replacing them with only
  the final decision.

Compute pre-adjudication support agreement and class balance from originals; use
scoring.cohens_kappa for nominal support categories. Reconcile discrepancies with
documented reasons. Any later judge comparison is separate from human-human
agreement. Quality reference examples are illustrative and pending review; they
are not original annotator labels.

Templates are record layouts, not a completed study. Reviewers must verify actual
completion and preservation before reporting validation evidence. No real data or
simulated human labels have been added here.

# No RAG improvements and handoff

The current execution path is reproducible and its seven-case outputs are
recorded. Reasoning quality remains unresolved. The next work should address
measured weaknesses without overwriting the frozen baseline or changing several
experimental factors at once.

## Observed weaknesses

| Area | Evidence from the recorded run | Consequence |
|---|---|---|
| Use of approval context | Approved account creation is labelled malicious; approved PowerShell maintenance remains undetermined | Correct event detection is confused with adversarial activity, or supplied context is ignored |
| Authorization uncertainty | Administrator-group addition is labelled malicious despite an incomplete approval search | The answer overstates what missing authorization evidence establishes |
| Summary completeness | File, vulnerability and maintenance answers omit essential context | Correct label fields can conceal an incomplete investigation |
| Vulnerability reasoning | Generic client-vulnerability summary does not explain build/configuration or distinguish applicability from exploitation | Separate applicability and exploitation review remains necessary |
| Risk justification | Some values match an accepted set without a complete rationale | Numeric/category agreement must not replace explanation review |
| Latency | Median client inference was 125.16 seconds, with variable per-token processing rates | Performance needs repeated, controlled measurement; no single-factor speed claim is established |

The SSH and Windows-login answers preserve important observed facts and
uncertainty. All seven outputs are contract-valid with empty action and ATT&CK
lists. Those are useful execution observations, not proof of complete reasoning,
action recall or confirmed technique detection.

## Completed development review

[EVALUATION.md](EVALUATION.md) now contains the completed seven-case technical
assessment, evidence for every rating, 27 claim annotations and the recorded
phase decision. All 21 required facts were assessed: nine met, four partial,
eight missing. Verdict agreement is 4/7; risk-in-set field agreement is 5/7.
Whole-answer support is 23/27 (85.19%), including seven coded triage interpretations.
Quality means are correctness 2.86, evidence use 3.86, actionability 2.29 and
safety/appropriateness 3.71 out of five; every dimension has 7/7 coverage.

The decision is to preserve the baseline with its measured weaknesses and start
a small controlled Vector RAG comparison. It is an experimental reference, not
an overall model-quality approval. No expected label or observed output was
changed to create a pass. Retrieval must be tested rather than assumed to fix
approval/context errors about information already present in the incident.

Independent validation remains open: no second human annotation, paired agreement
or 50-claim double-labelled set exists. These seven cases contain only 27 substantive
claims under the recorded extraction convention and no confirmed malicious or
technique-positive labels. Do not pad claims, add labels to the model input or
claim attack recall. Future reviewed data belongs to a new source release.

## Optional later No RAG diagnostics

If further No-RAG diagnosis is selected later, change one intended factor at a
time. It is not a prerequisite to keep tuning the seven examples before starting
the requested small RAG comparison. Examples of bounded experiments:

| Question | One intended change | Keep fixed |
|---|---|---|
| Does instruction length obscure relevant context? | Shorter equivalent general instructions, with unchanged semantics | Model, policy, incidents, output schema and limits |
| Does structured decoding affect interpretation? | A separately recorded diagnostic decoding condition | Incident content, semantic task and model; do not deploy unvalidated output |
| Does model representation matter? | One approved model or quantization comparison | Source release, policy, general instructions, evaluation definitions and comparable budgets |
| Is latency limited by CPU scheduling? | One threading/resource condition with repeated measurements | Model, prompts, incidents, policy and output requirements |

These are proposals, not experiments already performed or permission for downloads,
new infrastructure or model execution. Preserve all failures. Create a new baseline
identity before running; never revise the prompt after seeing an output and present
that revision as part of the same frozen experiment. Do not insert case-specific
expected answers or overfit to make these seven examples pass.

Remaining errors belong to the tested model/prompt/decoder/runtime combination.
The checks rule out observed truncation or missing incident input in this run;
they do not prove every configuration choice is optimal or isolate model weights
as the sole cause.

## Priority 3 Make evaluation easier to reproduce

A future evaluator can read an identified run and separate labels from model input.
It should implement the three-class verdict semantics, accepted-risk sets, manual
ATT&CK hypothesis qualifications and vulnerability prose checks. The retained
binary helpers cannot be reused directly for these expected undetermined cases.

Report intended/attempted/valid/failed/not-attempted coverage, field agreement and
reasoning separately. Keep undefined precision/recall values null with reasons.
Do not treat all empty actions or techniques as perfect detection. Preserve exact
output, evaluator and source identities alongside manual review records.

The current lock is verified explicitly; the launcher does not automatically
refuse a drifted baseline. An optional future lock check could make accidental
configuration drift fail before model startup, with tests for changed prompt,
policy, settings and source identity. No such feature is claimed implemented.

## Priority 4 Independent reproduction

A second environment should restore the frozen source release and pinned artifacts,
verify identities, run preflight and reproduce a bounded case. Record platform,
image/runtime, resource settings, actual templates and results. Check one artifact
save/restore cycle without silently rebuilding or replacing source data.

Hosted CI, clean-image dependency reproduction, independent cloud/teammate replay
and a served real-model API request are not established by the latest local run.
The standalone CLI and the optional backend adapter have different composition
responsibilities; do not infer a deployed service from an importable adapter.

## Conditions for moving to Vector RAG

- The completed seven-case technical review and its unresolved judgments are
  preserved in EVALUATION.md.
- The baseline configuration, outputs and expected-behavior version are preserved.
- The requested phase transition is recorded: the baseline is adequate as an
  experimental reference, without claiming perfect reasoning, independent gold
  validation or unsupported detection metrics.
- The Vector implementation uses the same incident release and comparable recorded
  model/policy/budget settings, with reference context as an explicit extra input.
- Evaluator labels never enter retrieval, prompt context or source indexing.
- Empty retrieval, unavailable dependencies, invalid evidence and timeouts remain
  explicit failures; no silent fallback to No-RAG.
- Independent reproduction and the remaining B0 handoff requirements are checked
  against the [roadmap](../../docs/ROADMAP.md), not assumed complete from local tests.

The next implementation remains a small fresh Vector RAG. Graph/Hybrid, agent
workflows, analyst UI and approved sandbox execution remain later roadmap work.

# Development SOC corpus assignments — S2-T01

This proposed S2-T01 development assignment covers only the two real LAB-01
authentication-failure observations already preserved in the repository and
normalized by S1-T06. It is submitted for Soulaiman's review; no independent
review, frozen benchmark membership or model-quality result is claimed.

Inputs: `tests/normalizer/fixtures/lab01-run01-incident.json` and
`lab01-run02-incident.json`. Original observations and collection limitations are
recorded in [the lab results](../../infrastructure/soc-lab/S1-T05-RESULTS.md).
These are isolated authentication failures, not a demonstrated brute-force
attack. Preserve detector severity without assigning an analyst verdict.

Both observations belong to `G-SSH` for leakage exclusion, alongside the pilot's
SSH family. Their observed runs remain `LAB01-run01` and `LAB01-run02`.
The [policy](soc-policy.json) pins each canonical incident digest and the exact
[split file](../evaluation/soc-eval-v1/splits.json) bytes. It explicitly links all
related SSH pilot cases. The current split is unfrozen, so this corpus is
**development only**. Changing the evaluation split invalidates the policy hash;
review assignments again and regenerate before using a frozen evaluation.

Only the already published lab identifiers and private lab addresses in the
normalized fixtures are carried forward. No new raw log collection or extra
personal identifiers are introduced. The incident schema rejects evaluator-only
fields. Review descriptions manually for sensitive material and annotation
leakage when adding new records: schema validation cannot establish that prose
is sanitized. Assignment and sanitization references are declarations subject to
review, not an automatic privacy or near-duplicate classifier.

All other incident IDs are quarantined unless explicitly assigned. A test or
quarantined assignment is excluded; known held-out groups, runs and related case
IDs cannot be admitted as development records. Near-duplicate/template-family
grouping remains a required owner/reviewer responsibility.

The original observations remain project lab evidence; this assignment grants
no new external redistribution license. Retain this notice with local derived
corpora. Raw snapshots and generated corpora remain in ignored local artifact
storage until the team's artifact-storage decision is resolved.

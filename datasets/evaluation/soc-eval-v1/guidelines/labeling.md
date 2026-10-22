# Pilot labeling notes — pending peer review

Apply [METRICS.md](../../../../experiments/METRICS.md); do not redefine metrics.
Verdict concerns the simulated incident, not permission to conduct a lab exercise.
Compare observed accounts, sources, times and effects with the supplied access
records. A record's mere existence is not authorization for a different actor or
window. Benign triggers match permitted activity; detector errors need contradictory
raw observations. Unresolved incidents remain outside this pilot.

Every false positive has informational gold severity. Low is reserved for real
incidents of minor impact (none in this release). Medium covers repeated failed
access without a session, or a bounded inert-file edit outside the access record.
High covers an enabled privileged account or successful access followed by an
interactive session. These owner-approved anchors await peer review. Detector
severity is a separate, noisy rule output, never the gold label.

P01/P02/P11 use T1110.001 for repeated password attempts against one account.
P11 also uses T1078 because the same source authenticates as lab-admin and runs
commands in the resulting session. P08 uses T1136.001 for local account creation
outside the creator's role. Do not infer malware from a file edit or an adversarial
technique merely because PowerShell ran. Empty MITRE sets require a reason.
Anas approved the case mappings; peer review and source-snapshot verification remain pending.

Only P01/P02/P11 require block_ip. The shared [runner policy](../protocol/README.md)
supplies service scope, duration bounds and envelope configuration to every runner;
labels retain expected action projections solely for evaluation. Incident text
supplies observed source and endpoint facts, never the containment rule. P06/P08/
P11/P12 also carry non-scored analyst guidance. No action execution is authorized.

Every evidence item names the field it supports and quotes at most 120 characters
from the incident using a resolving JSON pointer. Verdict and severity always need
support; nonempty MITRE and required actions need support too. These quotations
are authored synthetic evidence, not collected logs; locator checks cannot prove
entailment. Anas has reviewed all 14 cases: label_author is "Anas". Assigned
reviewer Oussama has not reviewed them; keep pending_review and needs_review=true.

## Grouping rule

Rule: cases sharing a scenario template family or describing the same episode share a group_id.

Applied with owner approval in soc-eval-v1-pilot.3:
- P01-P05, P11, P13 and P14 share G-SSH.
- P06, P07 and P12 share G-FIM.
- P08/P09 remain G-ACCOUNT; P10 remains G-POWERSHELL.

There are four template families. P01/P02 also describe the same episode.
Shared families must not be treated as independent case constructions.

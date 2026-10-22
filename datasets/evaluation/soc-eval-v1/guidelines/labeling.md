# Pilot labeling notes — pending human review

Apply [METRICS.md](../../../../experiments/METRICS.md); do not redefine metrics.
The simulated incident, not permission to conduct a lab exercise, determines
verdict. A benign trigger is a real permitted activity that does not warrant an
adversarial incident; detector error requires explicit contradictory source
observations. CTRL-01 is a routed control event, not a collected false alert.
Unresolved incidents are excluded rather than assigned a negative verdict.

Provisional assessed-severity anchors for these authored cases: informational for
verified authorized activity/detector error without impact; low for the permitted
credential mistake causing a short access delay; medium for repeated unauthorized
failed access or a bounded unauthorized inert-file edit without service impact;
high for an enabled unauthorized privileged account providing continued access.
These anchors are proposed annotation policy, not objective measurements or
reviewed operational severity guidance. Detector severity remains separate.

Use only supported adversarial ATT&CK behavior. P01/P02 map to broad T1110 because
credential retry details are absent; P08 maps to T1136.001 for an unauthorized
local account intended to maintain access. Do not map benign PowerShell merely
because PowerShell ran, or map an unexplained inert-file edit to malware or data
impact. Empty sets need a reason and are valid scored sets, not missing annotations.
Public reference pages: [T1110](https://attack.mitre.org/techniques/T1110/) and
[T1136.001](https://attack.mitre.org/techniques/T1136/001/). Mapping and immutable
source-snapshot review are still pending.

Only P01/P02 have the owner-requested draft block projection; action policy pending
owner confirmation. Every needed target/source/port and draft duration scope is
visible in those incidents. A label projection is not an approved executable
action. P06/P08 instead use non-scored analyst guidance. Review evidence quotations,
severity and mapping before accepting any label. Locator resolution is not an
entailment proof. All authorship/reviewer fields are task assignments; retain
`pending_review` and `needs_review: true` until actual human review occurs.

# Proposal matching

[METRICS.md](../../../../experiments/METRICS.md#action-and-agent-metrics) owns the
matching rules and aggregation. The implementation is
[scoring.py](../../../../ai/evaluation/scoring.py); the existing common runner
configuration is [runner-policy.json](runner-policy.json).

The scorer validates the whole investigation-result envelope before evaluating
proposals. match_actions projects semantic action fields and uses maximum
bipartite matching, so overlapping allowed duration ranges do not cause a greedy
mismatch. It compares action_type, endpoint target, source_ip, port, protocol and
whether duration_seconds falls inside the required range. Generated IDs and
explanatory wording do not determine semantic matches. Extra or missing proposals
prevent exact case match; empty/empty matches with null proposal precision/recall.
Output/incident IDs still must agree; invalid full outputs cannot earn an empty-set
match. METRICS remains the authority for denominator and missing-output handling.

The fixed policy supplies envelope values and service scope to every runner.
It does not decide whether a case warrants a proposal. The existing never-act
local shortcut check matches 11/14 cases; disclose that limitation. The 0.80 line
in fake-player tests is a local data-quality check, not a project metric or an
acceptance threshold from METRICS.

Proposal correctness does not establish execution safety: current inventory,
approval verification, executor permissions, idempotency, rollback and actual
effects remain outside proposal scoring. The existing policy disables execution.

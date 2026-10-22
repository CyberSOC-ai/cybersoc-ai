# Fixed pilot runner policy

[runner-policy.json](runner-policy.json) is model-visible configuration, identical
for all cases. Its canonical and raw SHA-256 hashes are pinned in the dataset
manifest and checked before scoring. It contains no case IDs or gold decisions.

For a warranted SSH containment proposal, use the observed endpoint and source
with the configured service scope and inclusive duration range. The runner decides
whether containment is warranted from the incident; this policy is not a command
to block every source. Local-only events have no remote source to invent.

Fill target_inventory_revision, environment_id, policy_version and response defaults
from this config. Generate proposal IDs/idempotency keys in the runner, copy
incident_id from the incident, and keep status proposed and requires_approval true.
Never read labels or evaluator context to populate these fields. Logical targets
are fictional fixtures, not an operational allowlist. execution_enabled is false;
this policy permits scoring proposals only, not executing them.

## Evaluation protocol assets

[METRICS.md](../../../../experiments/METRICS.md) is the authority. Use the
[faithfulness workflow](faithfulness.md), [claim extraction prompt](claim_extraction_prompt.md),
[judge prompt](faithfulness_judge_prompt.md), [unselected judge config](judge_config.template.json),
[quality reference examples](quality_rubric.md), [action matching guide](action_matching.md),
[human validation templates](../validation/README.md).
These are pending-review tools and instructions, not completed evaluation evidence.

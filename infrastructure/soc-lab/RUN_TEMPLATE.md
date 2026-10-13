# SOC Lab scenario run record

Copy this template for each actual run; use `not run`, `failed` or `not applicable` explicitly. Never fill outcomes from expected behavior alone. Keep raw data and secrets out of Git.

## Identity and configuration

- Run / experiment ID (S0-T06 convention):
- Scenario ID and revision; live / replay / synthetic:
- Operator; authorization reference; reviewer:
- UTC start / end; clock synchronization evidence:
- Git commit; lab/environment ID; inventory revision:
- VM IDs, OS/image versions, baseline snapshot IDs:
- Wazuh server/agent/ruleset versions; custom rule/config reference:
- Dataset version and development / frozen test split:
- Model, prompt, workflow and policy versions (if investigation runs):

## Preconditions and isolation

- Endpoint/agent/service health and pre-state:
- Firewall, routes and enabled interfaces evidence:
- Required lab connectivity allowed:
- Internet/LAN and simulation-to-management connectivity denied:
- Automatic response disabled; executor dispatch state:
- Planned count, duration and stop conditions:

## Stimulus and observation

- Actual stimulus/count and timestamps:
- Ground truth and authorization context, decided independently of AI:
- Collection settings; observation deadline:
- Source event reference; agent / alert / rule IDs:
- Sanitized fixture path; restricted raw artifact reference and checksum:
- Alert observed / absent / observation failed; explanation:
- Duplicate, dropped or delayed events:

## Normalization and investigation (when implemented)

- Normalized incident ID, contract version and validation result:
- Ingestion failure/replay status:
- Investigation/trace ID, selected mode and output reference:
- Expected labels/actions and actual validated output:
- Failures, evidence gaps and discrepancies:

## Response (S4 onward; otherwise not run)

- Proposed revision, target identity, inventory/policy binding and arguments:
- Human decision, authenticated actor, timestamp, expiry and approval ID:
- Required audit persistence and executor recheck evidence:
- Dispatch/idempotency reference:
- Actual effect; succeeded / failed / unknown; audit outcome reference:
- Denial/no-effect evidence for negative cases:
- Reconciliation and any newly approved retry:

## Reset and reproducibility

- Cleanup/rollback or operator snapshot reset; authorization:
- Post-state and recovery access checked:
- Approval invalidation after identity/inventory changes:
- Repeated-run IDs and comparison, including failures:
- Outcome: pass / fail / blocked / not run:
- Follow-up issue references; coverage limitations:

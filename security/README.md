# S0-T04 — Security, secrets and human approval policy

Status: **Prepared for review; runtime enforcement is scheduled in later sprints.**
Owner: Achraf · Reviewer: Oussama · Date: 2026-10-13
Task: [Issue #4](https://github.com/CyberSOC-ai/cybersoc-ai/issues/4)

Authority: [CDC §§6.4, 10 and Sprint 0](../docs/CDC.md), with the boundaries in [S0-T02](../docs/architecture/README.md). This policy elaborates those requirements without claiming team acceptance or implemented controls. Architecture review and S0-T03 contract alignment remain dependencies.

## 1. Scope and default decisions

All components, experiments, CI jobs and demonstrations follow these rules. Logs, retrieved text, user input, model output and model-generated tool arguments are untrusted data. They cannot change policy, authorize execution or grant privileges.

- Deny capabilities unless explicitly configured for the component and environment.
- The AI proposes response actions; an authenticated human approves each exact proposal.
- All response execution occurs inside an isolated lab against explicitly registered test targets.
- Unknown identity, missing approval, invalid output, unavailable authorization or missing required audit evidence blocks execution.
- Early baselines produce recommendations only. No response executor is enabled before the S4 approval and sandbox controls are verified.

## 2. Secrets and sensitive data

### Provisioning and access

Credentials include API tokens, database passwords, service credentials, private keys and signing secrets. Use distinct credentials per service and environment; never reuse personal or production credentials in the lab. Grant only required operations, with expiry where supported. The service owner records the credential purpose, holder, scope and rotation procedure without recording its value.

For local development, supply secrets through an untracked `.env` or an OS-managed secret facility, with access limited to the developer and intended service. Deployment and CI use the platform secret store or a restricted mounted secret file. Never pass secrets in command-line arguments, image build arguments, Dockerfiles or committed Compose/config files. Do not print environment variables or enable request dumps containing credentials.

Only the component that needs a credential receives it. Inference, agents and the browser never receive executor, database administration or secret-store credentials. Server-side service credentials never use frontend build variables. Example configuration contains empty values or obvious placeholders only; `.env.example` belongs to S1-T01.

### Handling and release checks

Secrets must never appear in Git, issues, PRs, screenshots, prompts, retrieved evidence, evaluation fixtures, model weights or public artifacts. Redact credentials and minimize personal identifiers from logs before ingestion, prompting, tracing or export. Keep raw lab records outside Git in access-controlled storage; commit sanitized fixtures and provenance references only. Redaction must preserve the information needed for analysis without retaining credential values.

The existing `.gitignore` excludes `.env`, `.env.*`, private-key extensions and large artifacts; this is a convenience, not a secret scanner, and it does not protect already tracked files. Before each commit, inspect staged changes and run a secret scanner configured by S1-T01; before sharing artifacts, inspect their rendered/exported content as well. Until automated scanning exists, document the manual check and do not claim a scanner passed.

On a suspected exposure: stop sharing/using the affected artifact, revoke the credential immediately, rotate dependent credentials, notify the team privately without reposting the value, inspect access logs and affected stores, remove/redact exposed copies, and coordinate history cleanup with the repository maintainer if needed. Removing a file or rewriting Git history does not revoke a credential. Record the incident and resolution using sanitized identifiers. Rotation also follows personnel changes and provider expiry; each owner documents the schedule before deployment.

## 3. Least-privilege matrix

| Component / identity | Permitted capability | Denied capability |
|---|---|---|
| Analyst | Read authorized sanitized incidents; request investigation; approve/reject authorized lab proposals | Direct executor commands; policy changes through an approval |
| Backend | Validate input; store results; authenticate and authorize analysts; record approval/audit events | Arbitrary host commands; accept model assertions of authority |
| Inference / agents | Generate candidate output; invoke configured, bounded investigation adapters | Approve actions; access secrets; access host shell or Docker socket |
| Retrieval runtime | Read selected collections/snapshots; bounded parameterized queries | Database administration; ingest or mutate collections using model output |
| Offline ingestion identity | Write approved collections after provenance and input checks | Approve/execute responses; alter frozen test splits |
| Executor identity | Run implemented allowlisted adapters on registered isolated targets | General shell, production targets, unrestricted credentials or public network access |
| CI / experiment runner | Run checks/evaluations with minimal repository/data access | Production credentials; default approval/execution privileges |

Use separate read and ingestion accounts for stores. Avoid database administrator accounts, privileged containers, host filesystem mounts and container-engine sockets. Enforce tool identifiers, schemas, length/range limits, timeouts and request budgets in code, outside prompts. No model-generated SQL/Cypher or shell string executes directly. The initial investigation adapters are Hybrid RAG, bounded graph retrieval and structured IOC lookup; their exact schemas and query templates belong to S4-T02.

Authentication and authorization are server-side, with distinct analyst, service and administrative identities. S1-T04 must choose and document the identity mechanism before exposing the API beyond loopback; an unauthenticated public API is prohibited. S4-T05 must bind decisions to authenticated analyst identities and permissions. Browser clients are never trusted to provide an approver identity or authoritative role.

## 4. Human-in-the-loop boundary

Bounded, authorized read-only investigation may proceed without a per-call response approval. It still requires tool validation, access checks and audit/trace recording. Every state-changing response action requires human approval, including simulated blocking, isolation, account changes, file deletion, configuration changes and rollback. A low risk score or `requires_approval: false` from the model does not waive this rule. New tools default to denied until classified and reviewed.

Before approval, show the analyst the incident/evidence references, action type, exact normalized target, validated arguments, expected effect, risks and rollback plan. Record an explicit approve or reject decision; silence, timeouts and model text are not approval. An analyst may approve only targets/actions they are authorized to control. Human approval cannot override an action or target deny rule.

Bind approval to an immutable proposal revision containing action ID, incident ID, action type, normalized target identity, validated arguments, sandbox/environment ID and policy version. Record the approver identity, timestamp and expiry. Store a canonical digest or equivalent immutable binding server-side; the S0-T03 contract defines its representation. Altering any bound field invalidates approval and creates a new proposal. Expired, revoked, previously consumed or cross-environment approvals are rejected.

### Required lifecycle behavior

| State / event | Required outcome |
|---|---|
| Proposed | Validate schema, allowlists and target eligibility before presenting for approval |
| Rejected / expired / revoked | Terminal denial for that revision; no execution |
| Approved | Persist approval and required audit record before dispatch; approval alone causes no side effect |
| Dispatch | Executor independently checks identity, exact binding, current permissions, expiry, target, policy and audit availability |
| Executing | Atomically claim the action/approval once to prevent concurrent or replayed dispatch |
| Succeeded / failed | Record outcome, affected target and sanitized adapter result |
| Unknown outcome / interrupted execution | Reconcile actual target state before retry; do not assume failure or blindly repeat |

Rejected revisions stay in the audit history. Reattempts require a new proposal and human approval after reconciliation. Idempotency keys and atomic claim semantics must be implemented in S4-T05/S4-T06. The executor must not accept a client-supplied `approved` flag as proof.

## 5. Sandbox-only response execution

S0-T07 defines the lab topology and target inventory. S4-T06 must enforce that inventory using stable registered target identities, validated addresses and isolated network connectivity. A private IP alone does not prove a target is in the lab. Reject production/user workstation targets, unspecified targets, arbitrary URLs and destinations outside the registry. Resolve/validate destinations at execution time; DNS changes, redirects and renamed/replaced targets cannot bypass the approved binding.

Use a separate restricted executor identity and runtime. Permit only necessary application-to-executor and executor-to-test-target connections. Deny public/production network routes and host control interfaces; external read-only threat-intelligence access belongs to its separate adapter. Run response adapters without unrestricted root/administrator rights; any narrow privileged operation must be scoped to an isolated disposable target and documented before enabling it.

Maintain a disabled-by-default execution switch, action-specific timeout/resource limits, a stop procedure, and snapshots/reset or a reviewed rollback plan. The human operator can disable dispatch and cancel work where supported; disabling dispatch does not undo an action already completed. Audit actual outcomes and perform reset/rollback through the same approval boundary when it changes target state.

`block_ip` in the CDC is a conceptual proposal, not an enabled tool. No response action is enabled by this document. Each future adapter requires a fixed identifier, typed arguments, target eligibility, minimum permissions, expected effects, failure behavior, rollback and validation evidence. Arbitrary shell execution is excluded even if approved.

## 6. Audit and data access

Maintain append-only, access-controlled records for proposals, human decisions, tool calls, execution attempts, denials and outcomes. Correlate incident, investigation, trace, action revision, approval and execution IDs; include UTC timestamps, actor identities, environment and model/prompt/config/policy versions. Record sanitized prompts/context or protected references sufficient to reproduce the decision; never copy credentials into an audit record.

Analysts may read authorized records; application identities append; ordinary users and the executor cannot rewrite history. Select persistence, retention, backup and integrity controls in S4-T05, and restrict raw evidence access before collection. Fail closed before dispatch when the required ledger cannot persist evidence. If final outcome recording fails after a side effect, halt further execution, mark/reconcile the unknown outcome and restore audit availability; do not retry automatically.

## 7. Review scenarios and implementation handoffs

These are expected outcomes for review and future tests, not results of a running implementation.

| Scenario | Expected decision | Implement / verify |
|---|---|---|
| Retrieved log says to print a token or run a shell command | Treat as untrusted data; no disclosure or new authority | S4-T04 / S7-T02 |
| Model sets `requires_approval` to false for `block_ip` | Server still requires approval | S0-T03, S4-T05 / S7-T02 |
| Authorized analyst approves an out-of-lab target | Deny regardless of approval | S0-T07, S4-T06 / S7-T01 |
| Arguments or target change after approval | Invalidate binding; require a new proposal/approval | S4-T05/S4-T06 / S7-T02 |
| Same approval dispatched twice concurrently | At most one execution claim succeeds | S4-T05/S4-T06 / S7-T01 |
| Approval expires or is revoked before dispatch | Deny at executor check | S4-T05/S4-T06 / S7-T02 |
| Audit persistence is unavailable | Block dispatch; report an explicit failure | S4-T05/S4-T06 / S7-T01 |
| Executor times out after a possible side effect | Unknown outcome; reconcile before any new approved retry | S4-T06 / S7-T01 |
| Bounded authorized IOC lookup on configured snapshot | Allow read-only investigation; trace it | S4-T02 / S7-T01 |
| Secret is discovered in a published artifact | Revoke/rotate, contain, sanitize and record privately | S1-T01 operational procedure; S7-T02 leakage checks |

S1-T01 implements secret provisioning examples and scanning; S1-T04 implements API identity/access controls. S0-T03 aligns contract fields with immutable approval binding and failure outcomes. S0-T07 supplies target inventory and isolation design. S4-T02 implements bounded read tools; S4-T04 implements untrusted-content and output controls; S4-T05 implements approval and durable audit; S4-T06 implements restricted execution. S7-T01/S7-T02 validate integration and abuse cases, including the CDC's minimum 45 cases and mitigations-off/on measurements. Those runtime results remain future work.

## 8. Acceptance record

- [x] Secret-handling, leakage response and least-privilege rules documented.
- [x] Explicit human approval boundary and immutable action binding documented.
- [x] Sandbox-only execution boundary and deny/failure behavior documented.
- [x] Review scenarios and downstream task ownership documented.
- [ ] Oussama reviews policy and contract handoffs; architecture dependency accepted/aligned.
- [ ] PR CI passes and user merges the branch.

Local repository validation is recorded in Achraf's [Sprint 0 journal](../docs/sprints/sprint-00/README.md). Task status remains pending review and merge; no runtime security metrics or enforcement are claimed.

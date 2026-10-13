# S0-T07 — SOC Lab architecture and scenario plan

Status: **Planning deliverables prepared; review and deployment pending.**
Owner: Achraf · Reviewer: Soulaiman · Date: 2026-10-13
Task: [Issue #7](https://github.com/CyberSOC-ai/cybersoc-ai/issues/7)

References: [CDC §7 and Sprint 0](../../docs/CDC.md), [component architecture](../../docs/architecture/README.md), and [S0-T04 security policy](../../security/README.md). The lab owns detection and reproducible evidence; CyberSOC AI consumes alerts for triage, investigation and recommendations. No lab, scenario or response action has been deployed or executed by this task.

## 1. Minimum topology

Use three isolated VMs for the initial lab: a SOC VM, a Linux endpoint VM and a small simulation VM. VM boundaries make snapshots and endpoint isolation explicit. The SOC VM hosts Wazuh server, indexer and dashboard in an all-in-one deployment. The Linux endpoint runs a Wazuh agent and a dedicated SSH test service. The simulation VM generates bounded events using disposable lab accounts. A separate Windows endpoint is optional when resources permit; it must never be the developer's workstation.

Wazuh's [official architecture](https://documentation.wazuh.com/current/getting-started/architecture.html) describes the central components and agent data flow. S1-T01/S1-T05 will pin supported OS, Wazuh and hypervisor versions and document measured resource requirements before installation. No unverified hardware sizing or compatibility is assumed here. Record available RAM, CPU and storage; preserve host headroom, bound log retention and validate the complete three-VM topology before adding Windows or model workloads. Inference may run separately from the lab.

```text
ISOLATED TEST SEGMENT                 SOC / APPLICATION SEGMENT

simulation-01 -- bounded events --> linux-01 -- agent telemetry --> soc-01
       |                              windows-01 (optional) ---------^
       |                                                           |
       +--> sink-01 (optional local connection sink)                |
                                                        sanitized alert export
                                                                   v
                                                  normalizer --> CyberSOC AI
                                                                   |
                                                exact human-approved proposal
                                                                   v
                                           executor-01 (S4, disabled initially)
                                                                   |
                                               registered isolated target only
```

These are logical segments, not prescribed address ranges. Select non-overlapping subnets after inspecting host/VPN routes; record them in the deployment inventory. Use internal virtual networks with no default route to the Internet or physical LAN. The analyst accesses the SOC dashboard through a restricted management interface. Simulation machines have no management-segment access. Where a SOC VM is dual-homed, explicitly disable routing/forwarding and verify it cannot bridge the segments.

The application and normalizer run in the application segment. S1 begins with an operator-exported sanitized alert file, avoiding a live bidirectional connector. S1-T06 chooses and validates later read-only ingestion transport. The response executor is a separate restricted runtime introduced in S4; it does not share the model's privileges or the developer host.

## 2. Inventory and allowed traffic

| Stable logical ID | Role | Required stage | Response eligibility |
|---|---|---|---|
| `soc-01` | Wazuh server, indexer, dashboard | S1 MVP | Never a response target |
| `linux-01` | Disposable Linux endpoint with Wazuh agent and test SSH service | S1 MVP | Specific approved lab adapters in S4 only |
| `simulation-01` | Bounded scenario source | S1 MVP | Never a response target |
| `windows-01` | Disposable Windows endpoint with agent and configured audit channels | Optional extension | Only separately registered adapters |
| `sink-01` | Local inert connection sink; may be a restricted container on simulation VM | Connection scenario extension | Never a response target |
| `executor-01` | Restricted response service | S4-T06 | Cannot target itself |

Before launch, inventory each VM/runtime with lab ID, stable target ID, VM UUID, OS/image version, snapshot ID, approved addresses/interfaces, segment, owner and eligibility. Logical IDs here are planned names, not an executable allowlist. Recreated VMs get a new inventory revision and invalidate approvals tied to the old identity. Only `linux-01` and a separately registered `windows-01` can become response targets; a private IP is insufficient proof of eligibility.

| Source → destination | Purpose / rule |
|---|---|
| Registered endpoints → `soc-01` | Wazuh agent telemetry; allow only configured agent transport |
| Operator → `soc-01` management interface | Authenticated dashboard access; restrict to operator identity/address |
| `simulation-01` → `linux-01` | SSH test service during bounded login scenario only |
| Registered endpoint → `sink-01` | Selected inert local connection scenario only |
| Operator export → normalizer | Sanitized alert file; preserve provenance, no embedded credentials |
| Application → executor | Authenticated approved-action dispatch, only after S4 controls pass |
| Executor → registered endpoint | Fixed action-adapter transport and minimum privileges, selected in S4-T06 |
| Everything else | Deny by default, including simulation → management and lab → Internet/LAN |

S1-T05 records exact ports/protocols from the pinned Wazuh release and deployed services; this table does not authorize broad subnet access. Enrollment access is temporary and limited to expected agents; enrollment credentials remain outside Git. Central-component traffic stays local to the SOC VM or a private service network. Do not publish indexer or administrative APIs to the host LAN. Disable Wazuh automatic Active Response: detection rules must not bypass the project's approval gate. Verify this configuration after upgrades.

Install/update images during a separate operator-controlled maintenance phase, with execution disabled and no scenarios running. Remove temporary Internet/NAT adapters and routes, snapshot the prepared machines and repeat isolation checks before each exercise. Do not grant the executor network access for downloads.

## 3. Scenario catalog

All scenarios use disposable accounts, inert files/processes and registered lab destinations. No live malware, stolen credentials, public targets or unrestricted attack tools are required. Expected observations are hypotheses for validation; rule IDs, timing and final ground-truth labels must be established on the pinned deployment with S1-T02/S1-T05.

| ID / stage | Setup and bounded stimulus | Expected observable evidence | Expected recommendation / later response | Reset |
|---|---|---|---|---|
| LAB-01 / S1 MVP | Test SSH account on `linux-01`; from simulation VM perform at most 10 failed logins in a fixed 60-second window, then stop; no password lists | Authentication failures with source, user, times and rule reference; correlated alert if configured threshold matches | Investigate repeated failures; optionally propose a temporary block of the registered simulation source in S4 | Restore baseline service/account state; remove approved test rule if present |
| LAB-02 / S1 extension | Monitor a dedicated lab fixture directory with file integrity monitoring; change one inert text file once | File path, old/new integrity evidence, time and monitoring rule | Inspect change; avoid declaring malware from a file change alone | Restore fixture content and wait for monitoring baseline |
| LAB-03 / later Linux | Enable account-change audit collection; operator creates one clearly named disposable privileged test account | Account creation and privilege-change records linked to operator/scenario | Verify change authorization; propose disabling only the disposable account if scenario is labelled unauthorized | Remove disposable account through operator reset or approved adapter |
| LAB-04 / optional Windows | Configure process and PowerShell audit channels; launch one harmless local PowerShell command that prints a fixed lab marker | Process/PowerShell record with marker, parent and timestamp; custom lab rule if needed | Investigate context; benign script alone is not a malicious verdict | Close process, remove marker artifacts; keep audit setup |
| LAB-05 / extension | Endpoint makes one bounded connection to registered `sink-01`; sink records metadata without serving payloads; no public address | Endpoint network telemetry, destination and sink receipt; alert only with validated lab rule | Investigate configured suspicious destination; optionally propose a target-scoped firewall rule in S4 | Close connection and remove only the approved lab firewall rule |
| LAB-06 / extension | Place one inert fixture whose hash is explicitly listed in a local test IOC set | File/hash match, IOC-set version and detection rule; mark as synthetic | Verify match and propose quarantine of that exact lab fixture in S4 | Restore fixture and local IOC baseline |
| CTRL-01 / benign control | One successful test SSH login by authorized operator | Successful authentication and no repeated-failure correlation | No disruptive response; benign ground truth | End session |
| CTRL-02 / benign control | Authorized fixture update paired with change record | Same FIM evidence as LAB-02 plus authorization context | Explain authorized maintenance; no automatic quarantine | Restore fixture |

LAB-01 is the first alert-producing scenario, LAB-02 the fallback if SSH correlation cannot be configured in the time box. A fallback must generate a real Wazuh alert; replaying a fixture is labelled replay, not a live run. Synthetic IOC matches and custom lab rules are explicitly labelled and never reported as independent real-world detection performance. Low-level events may exist without a correlated alert; record both and do not fabricate missing detection.

Ground truth is decided from scenario setup and collected evidence, not copied from AI output. Mark malicious behavior versus authorized simulation context explicitly in evaluation labels. S1-T02 assigns verdict, severity, MITRE mapping and expected action where evidence supports them. Windows-only work can be deferred with a recorded coverage gap. Later process-stop demonstrations use a dedicated inert process with verified identity; arbitrary PID termination is prohibited.

## 4. Repeatable execution and evidence

Use the [run record template](RUN_TEMPLATE.md) for every exercise.

1. Select a development scenario and approved registered machines. Check versions, baseline snapshot, clock synchronization, monitoring health and collection settings. Keep frozen test cases out of development/retrieval/fine-tuning stores under S0-T06/S1-T02 rules.
2. Verify isolation with recorded firewall/routes and controlled connectivity checks: required lab service allowed; Internet/LAN and management access from simulation denied. No scanning of external networks. Verify auto-response is disabled and executor dispatch is disabled before S4 acceptance.
3. Capture the pre-state and operator authorization for the exercise. Run only the scenario's bounded stimulus and record UTC start/end times and the actual count. Stop at the limit or if unexpected traffic/load appears.
4. Collect source event, Wazuh alert/rule/agent identifiers and sanitized export. Record missing alerts, service failures and timing explicitly. Preserve raw evidence in restricted artifact storage; store only sanitized fixtures and references in Git.
5. Pass the sanitized alert to the S1-T06 normalizer and S1-T04 API when implemented. Check the S0-T03 incident contract, source reference and timestamps. Record investigation mode, configuration/version references, structured result and trace separately from detection evidence.
6. Keep response disabled for initial runs. In S4, record the exact approved proposal, analyst identity, immutable binding, executor rechecks, execution result and audit reference before claiming approved response success.
7. Reset the disposable state, inspect actual outcome, and repeat the same scenario after reset. Report run counts and failures. Comparable repeated evidence is required before calling the scenario reproducible; two runs is an initial operational check, not a performance benchmark.

An exercise failure is not a clean negative example: disconnected agents, missing collection, delayed ingestion and invalid normalization remain explicit failures. Record observation deadlines selected during deployment and investigate after a timeout rather than declaring no detection.

## 5. Response sandbox boundary

S0-T04 governs every response and rollback that changes endpoint state. Keep response disabled until S4-T05/S4-T06 demonstrate authenticated approval, immutable binding, single execution claim, current target validation and durable audit. No Wazuh auto-response or model tool can independently invoke these operations.

Initial candidate: a temporary firewall block of the registered simulation source on `linux-01`. Scope it to the test service/source and preserve agent telemetry and operator recovery access. Predefine expiry/rollback, capture the original rule state and verify only the intended traffic is affected. A dedicated scoped adapter is required; accepting arbitrary shell commands is excluded. Account disablement, inert-process stop and inert-file quarantine are later candidates with separate typed schemas and permission reviews, not enabled capabilities.

Executor authorization binds lab/environment ID, target identity and inventory revision, action type, validated arguments and policy version. Deny changed/replaced targets, expired/revoked/consumed approval, unsupported actions, missing audit, malformed output and routes outside the lab. Approval cannot authorize `soc-01`, the developer host or production. An interrupted action with unknown effects must be reconciled before a new approval and retry.

Before execution acceptance, verify: denied proposal causes no target change; changing the target after approval fails; a duplicate dispatch acts at most once; out-of-registry target is refused; missing audit blocks dispatch; an approved eligible action has observable target effect and a durable outcome record. Record actual results in S4/S7, not in this planning task.

Operator recovery uses VM console access and clean snapshots. Stop simulation, disable dispatch, preserve evidence and restore only disposable machines. Snapshot restoration is a manual lab-maintenance procedure, not an AI tool; record operator authorization and invalidate old target approvals after restoration. A snapshot does not undo network effects elsewhere, which is why isolation must precede the exercise.

## 6. Ownership, dependencies and acceptance

| Handoff | Owner / task | Required result |
|---|---|---|
| Reproducible runtime, secrets and pinned versions | Ahmed / S1-T01 | Setup procedure and example config without credentials |
| Wazuh and one endpoint; first repeatable alert | Achraf / S1-T05 | Real deployed topology, isolation proof and repeated LAB-01 or fallback evidence |
| Alert export and incident normalization | Ahmed / S1-T06; Oussama / S0-T03 | Sanitized fixtures, contract validation, explicit failure/replay behavior |
| Labels, dataset splits and run versions | Anas / S1-T02, S0-T06 | Frozen test separation and reviewed labels/metrics |
| Approval / executor implementation | Oussama / S4-T05; Ahmed / S4-T06 | Authorization, audit, isolation and action adapter evidence |
| Architecture review | Soulaiman / S0-T07 reviewer | Confirm topology, resource/deployment choices and security alignment |

Open choices before S1 deployment: host capacity, hypervisor and supported VM images; pinned Wazuh version; actual addresses and ports; log collection settings and correlation threshold; clock source, retention and artifact access; live ingestion transport. Record these with deployment evidence. Windows inclusion is conditional; its absence must remain visible. Contract and version details follow S0-T03/S0-T06 rather than being invented here.

- [x] Minimum topology and required/optional components specified.
- [x] Initial scenarios, benign controls and repeatability/reset procedure specified.
- [x] Response-sandbox boundary and inventory requirements specified.
- [x] Dependencies and implementation acceptance gates assigned.
- [ ] Soulaiman reviews this plan and architecture/security dependencies are aligned.
- [ ] PR CI passes and the user merges.

This completes the planning artifacts for the two CDC S0-T07 deliverable groups. It does not claim a running SOC lab, rendered diagram verification, benchmark results or reviewer acceptance. Implementation starts in S1-T05.

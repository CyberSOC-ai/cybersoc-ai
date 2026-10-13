# Sprint 0 — Governance, Architecture, Contracts & Planning

## Sprint Information
- Dates: 2026-10-08 → 2026-10-12
- Main objective: Remove ambiguity before implementation.
- Main dependencies: No prior-sprint task dependencies.
- Exit criteria:
  - CDC accepted by all five members
  - Architecture and contracts reviewed
  - Security and lab boundaries understood
  - Project board ready
  - Sprint 0–8 README templates are initialized, committed and contain the five fixed member sections
  - Experiment versioning begins before the first benchmark
  - Supervisor has confirmed, or the team has recorded in ADR-009, the interpretation points: detection boundary (§3.3), six-agent target with reduced fallback (S4-T07), required minimal fine-tuning (§9.3)

## Sprint Tasks

| Task | Owner | Reviewer | Domain | Status |
|---|---|---|---|---|
| S0-T01 — GitHub governance and workflow | Ahmed | Soulaiman | devops | Done |
| S0-T02 — Architecture and component boundaries | Soulaiman | Anas | backend | Backlog |
| S0-T03 — Incident, retrieval, response and trace contracts | Oussama | Ahmed | backend | Backlog |
| S0-T04 — Security, secrets and HITL policy | Achraf | Oussama | llm-security | Backlog |
| S0-T05 — Data, knowledge-source and benchmark inventory | Oussama | Anas | rag | Backlog |
| S0-T06 — Experiment and version-tracking convention | Anas | Ahmed | llmops | Backlog |
| S0-T07 — SOC Lab architecture and scenario plan | Achraf | Soulaiman | soc | Backlog |
| S0-T08 — Initialize sprint documentation structure | Ahmed | Oussama | documentation | Done |

# 1. Ahmed
## Assigned tasks

S0-T01, S0-T08

## Work completed

### S0-T01 — GitHub governance and workflow

Completed on 2026-10-11. The implementation was merged in [PR #65](https://github.com/CyberSOC-ai/cybersoc-ai/pull/65); this documentation update completes the task record. Close [issue #1](https://github.com/CyberSOC-ai/cybersoc-ai/issues/1) when the final documentation PR is merged.

- Initialized issue and PR templates, Definitions of Ready / Done, and the repository workflow.
- Documented branch naming: `feature/<issue-number>-short-name`, `fix/<issue-number>-short-name`, and `experiment/<issue-number>-short-name`.
- Configured the [GitHub project board](https://github.com/orgs/CyberSOC-ai/projects/1) with Backlog, Ready, In progress, In review and Done statuses; CDC priorities P0–P3; all 12 domains; owner, reviewer, sprint and dependency fields. Created matching priority, domain and task-type labels.
- Configured public-repository protection for `main`: PRs required, zero required approvals, passing `repository-checks` CI required, branch up to date, administrators included, force pushes and deletion blocked.
- Added CI for changed whitespace, unresolved merge conflicts and broken local Markdown file links. Application linting and tests remain part of S1-T01.

### S0-T08 — Initialize sprint documentation structure

Implementation completed in bootstrap commit [4ee82e2](https://github.com/CyberSOC-ai/cybersoc-ai/commit/4ee82e24a566067f9184e835a11ce404ddfd5cd0); all deliverables verified on 2026-10-11. This update records the completion evidence for [issue #8](https://github.com/CyberSOC-ai/cybersoc-ai/issues/8), to be closed when the final documentation PR merges.

- Created `docs/sprints/sprint-00` through `sprint-08`, each with a tracked `README.md`.
- Initialized fixed sections for Ahmed, Soulaiman, Anas, Achraf and Oussama, with all ten required member subsections.
- Added shared integration sections, exit criteria verification and sprint retrospectives to every sprint README.
- Documented individual / shared editing ownership and Issue / PR linking in every README; CDC §11.6 defines the documentation and merge rules.

## Technical approach

Use a required `repository-checks` job on each PR. Require the branch to be up to date with `main`, apply protection to administrators, and block force pushes and deletion. Request the assigned reviewer; record unavailability before the author merges without approval.

**S0-T08:** Use a consistent sprint template with five fixed member sections and a shared integration section. Keep future-sprint entries as placeholders until supported by validated work. Record individual work in the owner's section and integrate documentation on the related task branch.

## Files / components modified

`docs/CDC.md`, root `README.md`, `.github/ISSUE_TEMPLATE/cdc-task.md`, `.github/PULL_REQUEST_TEMPLATE.md`, `.github/workflows/ci.yml`, `infrastructure/ci/check_repository.py`, and this member section.

**S0-T08:** The bootstrap initialized all nine `docs/sprints/sprint-XX/README.md` files and the policy in `docs/CDC.md` §11.6. This completion PR updates only this Sprint 0 README.

## Tests / validation

Repository integrity passed locally for 47 tracked text files; changed whitespace checks passed. The `repository-checks` job passed on [PR #65](https://github.com/CyberSOC-ai/cybersoc-ai/pull/65). GitHub's protection API confirmed zero required approvals, a required GitHub Actions `repository-checks` check, an up-to-date branch requirement, administrator enforcement, and blocked force pushes / deletion on `main`.

**S0-T08:** Checked every sprint README against the required member headings and subsections, shared headings and editing rules; confirmed each file is tracked by Git. All nine passed. Confirmed CDC §11.6 documents ownership, same-branch documentation and Issue / PR references. Repository integrity and changed-whitespace checks also pass locally; the final PR must pass required CI before merge.

## Results / metrics

Main protection is configured with 0 required approvals and 1 mandatory CI job. The initial job checks repository integrity; application linting and tests remain part of S1-T01.

All three S0-T01 deliverable groups are implemented: project workflow / classification, branch / PR rules, and templates / Ready / Done definitions.

**S0-T08:** All four deliverable groups are implemented. Verified 9 tracked READMEs, 45 member sections, 450 required member subsections and 63 shared subsections. Future-sprint work remains unfilled until performed.

## Problems encountered

Branch protection and rulesets were unavailable while the repository was private on the current GitHub plan. Ahmed made the repository public, enabling the `main` protection settings. Mandatory reviewer approval could delay merges when the reviewer was unavailable; Ahmed selected advisory reviews with mandatory CI instead.

**S0-T08:** The structure already existed from the bootstrap, but its task entry remained Backlog without a completion record. Verified the existing artifacts and recorded evidence rather than recreating the templates.

## Decisions made

2026-10-11: Ahmed directed that reviewer approvals remain advisory so reviewer availability does not block work. CI remains a mandatory merge gate. This replaces the earlier peer-approval requirement in CDC §11.3 and §14.

**S0-T08:** Preserve the existing template structure and other members' entries. Finalize this task through a documentation PR referencing issue #8, with Oussama as the assigned reviewer under the advisory-review policy.

## Related Issues / Pull Requests

[S0-T01 / Issue #1](https://github.com/CyberSOC-ai/cybersoc-ai/issues/1); [merge policy and initial CI / PR #65](https://github.com/CyberSOC-ai/cybersoc-ai/pull/65).

**S0-T08:** [Issue #8](https://github.com/CyberSOC-ai/cybersoc-ai/issues/8); [bootstrap implementation commit](https://github.com/CyberSOC-ai/cybersoc-ai/commit/4ee82e24a566067f9184e835a11ce404ddfd5cd0); [completion evidence / PR #68](https://github.com/CyberSOC-ai/cybersoc-ai/pull/68).

## Learning outcome

The task established how an issue defines the work, a linked branch isolates its changes, and a PR proposes merging into `main`. Requesting a reviewer sends a notification; the board's reviewer field alone does not request review. Passing CI is an enforced merge gate, while approval is advisory. `Closes #1` in a PR description closes the issue when merged into the default branch. Board status automation is separate from CI and should be verified before relying on automatic transitions.

**S0-T08:** A consistent sprint journal makes each member's work and validation traceable while separating individual contributions from shared integration. Existing committed artifacts can satisfy a task once their requirements are verified and the completion evidence is linked to its issue and PR.


# 2. Soulaiman
## Assigned tasks

S0-T02 — Architecture and component boundaries (reviewer: Anas).

## Work completed

2026-10-12: Prepared the [architecture and component boundaries](../../architecture/README.md). It covers component responsibilities, deployment boundaries, interface handoffs, staged investigation flows, security boundaries and the S0/S1 dependency path. Soulaiman verified the local walkthrough. Assigned-reviewer review and the PR workflow remain pending; S0-T02 is not Done.

## Technical approach

Propose a modular FastAPI application with explicit Python interfaces for inference, retrieval and orchestration. Separate the SOC lab and restricted response executor from application responsibilities. Define the No-RAG baseline first and show how retrieval and agents extend it. Detailed schemas remain S0-T03 work; security policy and lab topology remain S0-T04/S0-T07 work.

## Files / components modified

Added `docs/architecture/README.md` and updated only Soulaiman's member section in this sprint journal. No application runtime changes.

## Tests / validation

Local validation on 2026-10-12: repository integrity passed for 47 tracked text files, and `git diff --check` passed. Because the architecture document is untracked, it was checked separately for local link targets, balanced code fences, conflict markers and whitespace. Mermaid diagrams have not been render-verified. The acceptance checklist distinguishes static checks from reviewer acceptance and future runtime validation. Local checks were rerun after staging the architecture document: 48 tracked text files passed. PR CI is tracked in PR #69; its latest result should be checked before merge.

## Results / metrics

The three S0-T02 deliverable groups have draft coverage: component/service boundaries, ownership-independent interfaces and critical path. No runtime performance or integration results are claimed.

## Problems encountered

The CDC provides conceptual contract examples but leaves duplicate handling, error outcomes, baseline trace representation and some triage evaluation fields unspecified. These are explicit handoffs to S0-T03. Incident/result persistence and executor transport require later implementation decisions.

## Decisions made

Soulaiman verified the local architecture on 2026-10-12. The responsibility split was clarified: retrieval prepares evidence, inference constructs model input and generates candidate output, and the investigation pipeline coordinates their calls. Team review remains pending. Soulaiman subsequently authorized branch creation, commit, push and issue closure before merging; merge into `main` remains with Soulaiman. Task branch: `2-s0-t02-architecture-and-component-boundaries`.

## Related Issues / Pull Requests

[S0-T02 / Issue #2](https://github.com/CyberSOC-ai/cybersoc-ai/issues/2). Branch: `2-s0-t02-architecture-and-component-boundaries`. [Architecture PR #69](https://github.com/CyberSOC-ai/cybersoc-ai/pull/69) is open with Anas requested as reviewer. Issue #2 was closed as completed at Soulaiman's explicit request before merge; review and merge evidence remain pending. Closure does not imply that review, CI or merge has completed.

## Learning outcome

Architecture specifies component responsibilities and their connections; contracts specify the exact exchanged data. A repository folder need not be a separate deployed service. Documented proposals and open decisions must remain distinguishable from implemented and accepted behavior.


# 3. Anas
## Assigned tasks

S0-T06

## Work completed

> To be completed from validated sprint evidence.

## Technical approach

> To be completed from validated sprint evidence.

## Files / components modified

> To be completed from validated sprint evidence.

## Tests / validation

> To be completed from validated sprint evidence.

## Results / metrics

> To be completed from validated sprint evidence.

## Problems encountered

> To be completed from validated sprint evidence.

## Decisions made

> To be completed from validated sprint evidence.

## Related Issues / Pull Requests

> To be completed from validated sprint evidence.

## Learning outcome

> To be completed from validated sprint evidence.


# 4. Achraf
## Assigned tasks

S0-T04, S0-T07

## Work completed

2026-10-13: Prepared [S0-T04 security, secrets and human approval policy](../../../security/README.md) for review. It defines credential handling and exposure response, least privilege, human approval bound to an immutable action, sandbox-only execution and audit failure behavior. S0-T07 planning work is recorded below. S0-T04 is not Done: reviewer acceptance, PR CI and merge remain pending.

**S0-T07:** 2026-10-13: Prepared [S0-T07 SOC Lab architecture and scenario plan](../../../infrastructure/soc-lab/README.md) and a [scenario run record](../../../infrastructure/soc-lab/RUN_TEMPLATE.md). Covers minimum topology, traffic boundaries, target inventory, six event scenarios, two benign controls, reset/repeatability and sandbox-only response. No lab deployment or scenario execution is claimed. The local main history confirms S0-T04 merged through [PR #70](https://github.com/CyberSOC-ai/cybersoc-ai/pull/70); its implementation controls remain future work.

## Technical approach

Derive explicit deny-by-default rules from CDC §§6.4 and 10 and the S0-T02 architecture. Keep model recommendations separate from human authorization and executor policy checks. Specify review scenarios and downstream implementation ownership without claiming runtime controls already exist.

**S0-T07:** S0-T07: Plan a three-VM baseline (Wazuh all-in-one SOC, Linux endpoint, bounded simulation source) with optional Windows. Keep initial ingestion file-based and response disabled. Explicitly assign version/port/resource selection and runtime validation to S1; approval and restricted response to S4.

## Files / components modified

Added `security/README.md` and updated Achraf's Sprint 0 section only.

**S0-T07:** S0-T07: Added `infrastructure/soc-lab/README.md` and `infrastructure/soc-lab/RUN_TEMPLATE.md`; updated this member section. Preserved other members and shared sections.

## Tests / validation

Local checks on 2026-10-13: staged repository integrity and changed whitespace checks passed. Manually checked the policy against both CDC S0-T04 deliverable groups and architecture handoffs, and inspected the staged changes for credential values. No automated secret scanner or runtime security tests were run; those controls are scheduled in later tasks.

**S0-T07:** S0-T07 local validation on 2026-10-13: staged whitespace and repository integrity checks passed (51 tracked text files). Compared both CDC deliverable groups and S0-T04 boundaries with the plan; checked scenario coverage, handoff ownership and local Markdown links. No VM/network tests, Mermaid rendering, automated secret scan or live detection/response measurements were performed.

## Results / metrics

Both policy deliverable groups are documented, with a component privilege matrix, action lifecycle rules and ten review scenarios. No runtime security effectiveness or attack-success metrics are claimed.

**S0-T07:** S0-T07: Documented three required VM roles, optional Windows, six scenario plans and two benign controls. Supplied a run template that separates expected from observed outcomes. Reproducibility and performance must be established on the deployed lab.

## Problems encountered

Windows denied Git metadata writes in the original GitHub Desktop checkout despite an access grant. Work was prepared in a separate workspace checkout on the task branch. GitHub issue details could not be fetched; scope was taken from the tracked CDC task table. Review and contract alignment remain pending dependencies.

**S0-T07:** S0-T07: Original Git metadata write restrictions required a separate workspace checkout. Actual host capacity, image versions, addresses, configured collection/rules and live ingestion transport remain implementation decisions; no running lab evidence was available.

## Decisions made

Every state-changing response needs explicit human approval and an isolated registered target. Models cannot waive approval. Changed proposals invalidate approval; unknown execution outcomes require reconciliation before a newly approved retry. The user retains merge responsibility.

**S0-T07:** S0-T07: Prefer disposable VMs, isolated internal networks and LAB-01 repeated SSH failures for the MVP; use FIM as a recorded fallback. Disable Wazuh automatic response so it cannot bypass approval. Recreated/restored targets invalidate old approvals. Retain the user as merge owner.

## Related Issues / Pull Requests

[S0-T04 / Issue #4](https://github.com/CyberSOC-ai/cybersoc-ai/issues/4). Branch: `feature/4-security-secrets-hitl-policy`. PR creation and assigned-reviewer review remain pending; issue closure must wait for merge. S0-T07 review and merge remain pending.

**S0-T07:** S0-T07: [Issue #7](https://github.com/CyberSOC-ai/cybersoc-ai/issues/7). Branch: `feature/7-soc-lab-architecture-scenarios`. Assigned reviewer: Soulaiman (`soulaimane-22`). PR review, CI and merge remain pending; do not mark Done until their evidence is recorded.

## Learning outcome

A policy defines requirements and failure behavior; later implementation and abuse-case evidence prove whether they hold. Human approval is authorization for one exact eligible lab action, and cannot grant unrestricted execution privileges.

**S0-T07:** S0-T07: A topology and scenario plan establishes what to deploy and measure. An expected event, observed Wazuh alert, normalized incident and AI judgment are separate evidence stages; simulated inputs and replayed fixtures must be labelled.



# 5. Oussama
## Assigned tasks

S0-T03, S0-T05

## Work completed

2026-10-13 — S0-T05: Prepared knowledge/threat-intelligence and SOC-log inventories, candidate evaluation datasets, licensing notes and a Qwen/Phi/SmolLM2 shortlist with conditional memory-fit estimates. No raw datasets, feeds or model weights were acquired; review and downstream execution remain pending.

## Technical approach

S0-T05: Verify publisher/official source pages, record format/access/license/provenance and intended consumers, map lab scenarios to eligible historical logs, and define evaluation-case/held-out exclusions. Separate parameter-derived weight estimates from measured total GPU memory and actual access.

## Files / components modified

S0-T05: Expanded `datasets/README.md`; added `datasets/SOURCES.md` and `datasets/MODELS.md`; updated only Oussama’s member section here.

## Tests / validation

S0-T05: Checked all five issue deliverables against the CDC and inventory tables; reviewed official source/model/license pages on 2026-10-13. Existing repository integrity and whitespace checks passed after staging. Manually inspected changes for credentials. No download/parser tests, live authenticated feed calls, GPU-fit tests, benchmarks or hosted CI were run; no application tests are needed for this documentation-only inventory.

## Results / metrics

S0-T05: Three required knowledge sources, one intended primary IOC feed plus fallback candidate, six lab-log groups, four dataset candidates and four model candidates documented. License/access and hardware gates are explicit; no model-quality or detection metrics are claimed.

## Problems encountered

S0-T05: Team hardware capacity is undocumented. ThreatFox/URLhaus access and derived/snapshot usage must be confirmed before ingestion. Artifact storage and exact acquisition revisions remain undecided. Some NVD pages yielded no readable browser content; acquisition details are supported by its official feed page, with exact API limits deferred to acquisition-time verification.

## Decisions made

S0-T05: Plan a bounded ThreatFox snapshot for S2-T08 subject to authenticated access and allowed use, with URLhaus as a separately gated fallback. Prefer lab-built evaluation cases; external flow labels are not complete assistant ground truth. Record Qwen 3B’s research license separately from smaller Qwen checkpoints. Leave final model/storage/tracking decisions to their scheduled ADRs.

## Related Issues / Pull Requests

S0-T05: [Issue #5](https://github.com/CyberSOC-ai/cybersoc-ai/issues/5); branch `feature/issue-5-data-knowledge-benchmark-inventory`. Reviewer: Anas (`Anas-Rabih`). [Inventory evidence](../../../datasets/README.md). No PR created or issue state changed; push, PR, CI, review, merge and closure remain pending.

## Learning outcome

S0-T05: Public availability does not establish unrestricted reuse. Incident-level split/provenance prevents answer leakage; theoretical weight memory is only a lower bound and cannot establish runtime or fine-tuning fit.

# Shared Sprint Integration

## Integrated components

> To be completed by the sprint coordinator or explicitly assigned person.

## Architecture changes

> To be completed by the sprint coordinator or explicitly assigned person.

## Shared experiments

> To be completed by the sprint coordinator or explicitly assigned person.

## Security considerations

> To be completed by the sprint coordinator or explicitly assigned person.

## Known limitations

> To be completed by the sprint coordinator or explicitly assigned person.

## Exit criteria verification

> To be completed by the sprint coordinator or explicitly assigned person.

## Sprint retrospective

> To be completed by the sprint coordinator or explicitly assigned person.

Individual work is edited only in the named member section. Shared sections are maintained by the sprint coordinator or explicitly assigned person. Each task entry links its Issue and PR before Done.

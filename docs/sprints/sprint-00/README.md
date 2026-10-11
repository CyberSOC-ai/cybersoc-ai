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
| S0-T08 — Initialize sprint documentation structure | Ahmed | Oussama | documentation | Backlog |

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

## Technical approach

Use a required `repository-checks` job on each PR. Require the branch to be up to date with `main`, apply protection to administrators, and block force pushes and deletion. Request the assigned reviewer; record unavailability before the author merges without approval.

## Files / components modified

`docs/CDC.md`, root `README.md`, `.github/ISSUE_TEMPLATE/cdc-task.md`, `.github/PULL_REQUEST_TEMPLATE.md`, `.github/workflows/ci.yml`, `infrastructure/ci/check_repository.py`, and this member section.

## Tests / validation

Repository integrity passed locally for 47 tracked text files; changed whitespace checks passed. The `repository-checks` job passed on [PR #65](https://github.com/CyberSOC-ai/cybersoc-ai/pull/65). GitHub's protection API confirmed zero required approvals, a required GitHub Actions `repository-checks` check, an up-to-date branch requirement, administrator enforcement, and blocked force pushes / deletion on `main`.

## Results / metrics

Main protection is configured with 0 required approvals and 1 mandatory CI job. The initial job checks repository integrity; application linting and tests remain part of S1-T01.

All three S0-T01 deliverable groups are implemented: project workflow / classification, branch / PR rules, and templates / Ready / Done definitions. The final documentation PR closes the task; this entry does not mark S0-T08 complete.

## Problems encountered

Branch protection and rulesets were unavailable while the repository was private on the current GitHub plan. Ahmed made the repository public, enabling the `main` protection settings. Mandatory reviewer approval could delay merges when the reviewer was unavailable; Ahmed selected advisory reviews with mandatory CI instead.

## Decisions made

2026-10-11: Ahmed directed that reviewer approvals remain advisory so reviewer availability does not block work. CI remains a mandatory merge gate. This replaces the earlier peer-approval requirement in CDC §11.3 and §14.

## Related Issues / Pull Requests

[S0-T01 / Issue #1](https://github.com/CyberSOC-ai/cybersoc-ai/issues/1); [merge policy and initial CI / PR #65](https://github.com/CyberSOC-ai/cybersoc-ai/pull/65).

## Learning outcome

The task established how an issue defines the work, a linked branch isolates its changes, and a PR proposes merging into `main`. Requesting a reviewer sends a notification; the board's reviewer field alone does not request review. Passing CI is an enforced merge gate, while approval is advisory. `Closes #1` in a PR description closes the issue when merged into the default branch. Board status automation is separate from CI and should be verified before relying on automatic transitions.


# 2. Soulaiman
## Assigned tasks

S0-T02

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


# 5. Oussama
## Assigned tasks

S0-T03, S0-T05

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

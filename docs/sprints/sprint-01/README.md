# Sprint 1 — Platform Baseline, SOC Lab MVP & No-RAG Baseline

## Sprint Information
- Dates: 2026-10-13 → 2026-10-25
- Main objective: Produce the first reproducible, end-to-end baseline without RAG.
- Main dependencies: S0-T01, S0-T03, S0-T04, S0-T05, S0-T06, S0-T07
- Exit criteria:
  - Project starts reproducibly
  - Lab generates at least one valid incident
  - Normalized incident reaches the backend
  - Baseline SLM produces a structured result
  - Baseline metrics are recorded
  - `soc-eval-v1` and its evaluation protocol (faithfulness, quality rubric, dev / test split) are versioned and reviewed

## Sprint Tasks

| Task | Owner | Reviewer | Domain | Status |
|---|---|---|---|---|
| S1-T01 — Reproducible local environment + Docker + basic CI | Ahmed | Achraf | devops | In progress |
| S1-T02 — Evaluation dataset v1 and evaluation protocol | Anas | Oussama | ai-slm | Backlog |
| S1-T03 — Baseline SLM runner | Soulaiman | Anas | ai-slm | Backlog |
| S1-T04 — FastAPI core + incident ingestion | Oussama | Soulaiman | backend | Backlog |
| S1-T05 — SOC Lab MVP | Achraf | Ahmed | soc | Backlog |
| S1-T06 — SOC alert normalizer | Ahmed | Oussama | soc | Backlog |
| S1-T07 — No-RAG end-to-end baseline | Anas | Ahmed | ai-slm | Backlog |

# 1. Ahmed
## Assigned tasks

S1-T01, S1-T06

## Work completed

2026-10-15 — S1-T01: Implemented and locally validated the development foundation on `feature/9-reproducible-local-environment`. PR, assigned-reviewer request, hosted CI and merge remain pending. S1-T01 is not yet Done.

- Recorded Python 3.12 and Node.js 24 conventions. Built a Python development image with pinned Python packages, a regular `dev` user and a read-only project bind mount through Compose.
- Centralized Python dependencies in root `requirements.txt`; added Ruff configuration, a comment-only `.env.example`, build-context exclusions and a [development setup guide](../../development.md) linked from the root README.
- Updated the existing required `repository-checks` CI job to use checkout v6, the Gitleaks v3 Action, Docker build, Ruff and contract tests. Removed the standalone whitespace gate at Ahmed's request. Existing repository integrity checks remain.

S1-T06 has not started. This task does not claim a deployed API, SOC lab, model runner or end-to-end baseline.

## Technical approach

Use Docker as the shared Python environment, without requiring a local virtual environment. Install dependencies during image build, then run checks as user ID 1000 with source files mounted read-only at `/workspace`. Code edits are visible on the next run; dependency or Dockerfile changes require rebuilding.

Keep CI commands explicit: build the image, run Ruff, then run the existing contract suite. Gitleaks runs through its official GitHub Action with the license supplied through GitHub Secrets; automatic PR comments are disabled. Local pre-commit scanning uses the separately installed CLI documented in the setup guide.

## Files / components modified

Added `.python-version`, `.nvmrc`, `requirements.txt`, `pyproject.toml`, `.env.example`, `.dockerignore`, `compose.yaml`, `infrastructure/docker/Dockerfile.dev` and `docs/development.md`.

Updated `.github/workflows/ci.yml`, root `README.md`, `backend/contracts/README.md` and this task row/member section. Removed `tests/contracts/requirements.txt` after moving its dependency into the root requirements file.

## Tests / validation

Local Linux x86_64 validation during 2026-10-14/15:

- Compose configuration parsed and the development image built successfully. Default execution reported Python 3.12.15; `id` confirmed `uid=1000(dev)` and `gid=1000(dev)`.
- `docker compose run --rm -T dev python -m pip --no-cache-dir check` reported no broken requirements after pinning all 19 installed Python packages.
- `docker compose run --rm -T dev ruff check --no-cache .` passed, and `docker compose run --rm -T dev python -B -m unittest discover -s tests/contracts -v` passed all 17 test methods through the read-only mount.
- Workflow YAML parsed after the CI changes. GitHub metadata confirmed the `GITLEAKS_LICENSE` secret name exists; its value was not read or displayed. This is not evidence that the hosted Gitleaks Action has passed.
- The setup guide/root README check verified balanced code fences and 21 existing local Markdown link targets before this journal update.
- Final pre-commit checks passed for all 77 staged/tracked text files. Gitleaks 8.30.1 found no suspected secrets in the staged changes. The Compose build, Ruff and all 17 contract tests were rerun successfully before committing.

Fresh-checkout reproduction, hosted CI and other-platform validation remain pending. No model-quality, lab-detection or performance benchmark was run.

## Results / metrics

One Python development service builds and runs locally; 19 package versions are recorded in one requirements file; Ruff and all 17 contract test methods pass. The CI configuration includes secret scanning, repository integrity, Docker build, lint and tests under the existing required job name.

## Problems encountered

The host Python environment initially lacked the project's pinned format-checking dependencies and local virtual-environment support. Running the checks in the Python 3.12 Docker environment resolved the contract-test dependency mismatch.

The initial draft introduced more setup layers than Ahmed wanted. It was discarded and rebuilt through small explained changes. Gitleaks' organization Action required a license key; Ahmed obtained it and stored it in GitHub Secrets, allowing removal of the temporary manual installer.

## Decisions made

Use a Docker-first workflow, one central Python requirements file, a non-root runtime user and a restricted build context. Keep Python and future Node tooling separate. Do not invent environment variables before a component needs them.

Prefer readable direct CI steps over a custom check-runner wrapper. Keep functional/security checks and remove the cosmetic whitespace gate. Use the official Gitleaks Action once its organization license is available.

The Python base image tag can receive updates and is not digest-pinned. Node.js is a version convention only and is not installed in the Python image. The full project bind mount includes local files even when `.dockerignore` excludes them from builds; read-only mounting prevents writes, not reads.

## Related Issues / Pull Requests

[S1-T01 / Issue #9](https://github.com/CyberSOC-ai/cybersoc-ai/issues/9). Branch: `feature/9-reproducible-local-environment`. Assigned reviewer: Achraf (`Eachr4f`). Ahmed authorized commit and branch publication on 2026-10-15. PR creation remains pending; add the actual PR link and hosted validation evidence before completion. S1-T06 remains tracked separately in [issue #14](https://github.com/CyberSOC-ai/cybersoc-ai/issues/14).

## Learning outcome

A Dockerfile builds an image; Compose records how to build and run it; a bind mount makes local code visible without rebuilding for each edit. Requirements record installed packages, while Ruff configuration selects code checks. GitHub Actions reruns the shared checks on PRs; local success does not prove hosted CI passed. Secrets belong in protected configuration, not source files. A documented local implementation becomes Done only after the remaining project workflow requirements are satisfied.


# 2. Soulaiman
## Assigned tasks

S1-T03

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

S1-T02, S1-T07

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

S1-T05

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

S1-T04

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

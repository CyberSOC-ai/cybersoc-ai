# S0-T06 validation evidence

Date: 2026-10-15. Local checks use Python 3.12.14, jsonschema 4.26.0 and Ruff 0.14.14 in a temporary environment. Dependencies were installed outside the repository. No Docker executable was available locally; hosted CI separately builds the project development image.

## Reproduce

From a configured project development environment, run the existing CI commands:

```sh
python -B -m unittest discover -s tests/contracts -v
ruff check --no-cache .
python -B infrastructure/ci/check_repository.py
git diff --check
```

Stage the intended new files before the repository integrity check, which inspects tracked files. The existing CI automatically discovers the two new example-integration tests; workflow or dependency changes are unnecessary.

## Observed evidence

- 19 unittest methods pass: 17 existing contract tests plus 2 S0-T06 integration checks.
- New checks parse the three JSON templates and resolve the synthetic manifest/trace pair, validate the existing v1 trace schema offline, compare required versions and trace identity, check step sequence and chronology, and verify the example claims no measured metrics.
- Ruff, tracked-file integrity/link checks and changed-whitespace checks pass locally.
- An additional one-off check confirmed three incompatible trace mutations are rejected: an extra run_id field, an unsupported schema version and an agent field on a baseline backend step. These are schema compatibility checks, not runtime enforcement tests.
- Reviewed the 12 worked metric examples by arithmetic/policy inspection; no executable metric evaluator is delivered in S0-T06.
- Checked the diff for accidental modifications to contracts, CDC, other member sections and runtime configuration. Manual sensitive-data review found only constructed fixtures, public URLs and provenance references. No local Gitleaks executable was available; the hosted secret scan remains separate evidence.

## Verified merge and CI status

The merge CI run passed repository integrity, secret scanning, the development-image build, Ruff and all 19 contract tests. This is hosted evidence, separate from the local checks dated above.

## Limits and remaining gates

2026-10-17: [PR #76](https://github.com/CyberSOC-ai/cybersoc-ai/pull/76) merged at `18ee4dcd2e853603e86f1538d4a8f9b4d86afb69`; [merge CI](https://github.com/CyberSOC-ai/cybersoc-ai/actions/runs/39063140796) passed and [issue #6](https://github.com/CyberSOC-ai/cybersoc-ai/issues/6) is closed. Ahmed was requested as reviewer; no submitted GitHub review is recorded as of this check. ADR-010 remains Proposed; team acceptance and the teammate usability exercise remain pending. MLflow deployment, real dataset/group leakage checks, teammate usability exercise, judge calibration, model runs, GPU memory/performance, audit behavior and benchmark reproducibility have not been executed. Documentation and synthetic schema checks do not establish those outcomes.

Protocol clarifications requiring review: No-RAG evidence eligibility, zero-claim/incomplete-judge handling, training within development, answer-level versus claim-level annotation units, and action argument matching. They are visible in the proposed protocol, with CDC and interchange schemas unchanged.

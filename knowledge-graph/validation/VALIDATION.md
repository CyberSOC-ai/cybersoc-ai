# S3-T01 — Verification to run

Status: user-executed local checks partially complete. Evidence is preserved in
[user-verification.txt](user-verification.txt). The assistant did not rerun checks.
86 tests passed, Ruff passed and both example validations passed. Repository integrity
remains pending after a container tooling error; CI and Neo4j checks remain pending.

## Local commands

From the repository root in PowerShell, with Docker Desktop running:

```powershell
docker compose build dev
docker compose run --rm -T dev ruff check --no-cache .
docker compose run --rm -T dev python -B -m unittest discover -s tests/knowledge_graph -v
docker compose run --rm -T dev python -B -m rag.graph.validate knowledge-graph/examples/minimal-graph.json
docker compose run --rm -T dev python -B -m rag.graph.validate knowledge-graph/examples/lab-mentions.json
docker compose run --rm -T dev python -B -m unittest discover -s tests/contracts -v
docker compose run --rm -T dev python -B -m unittest discover -s tests/ingestion -v
python -B infrastructure/ci/check_repository.py
git diff --check
```

Stop at failures and retain the error output. Expected CLI counts, if validation
passes: minimal 9 nodes / 9 relations; lab mentions 7 nodes / 5 relations.
These counts were confirmed in the supplied user transcript. No model download or Neo4j
service is needed for these checks. CI includes the graph suite and existing suites.
The repository integrity script reads tracked files; run it again after explicitly
staging intended new files so new Markdown links are included.

## Record real evidence

| Check | Status | Command/output reference |
|---|---|---|
| Build | Passed (user-run) | Docker dev image built successfully |
| Ruff | Passed (user-run) | All checks passed! |
| Graph unit tests | Passed (user-run) | 22 tests, 0.394s, OK |
| Example CLI validation | Passed (user-run) | Minimal: 9/9; lab: 7/5 nodes/relations |
| Contract regression | Passed (user-run) | 20 tests, 0.471s, OK |
| Ingestion regression | Passed (user-run) | 44 tests, 3.517s, OK |
| Repository integrity | Pending host rerun | Container failed before checking: Git missing |
| Whitespace | Passed for checked diff (user-run) | git diff --check returned without output; repeat after staging new files |
| CI | Not run | Pending PR run URL |
| Neo4j constraints | Not run | Version/edition and execution pending |

The transcript shows Windows PowerShell with checks inside the Python 3.12 dev
container. Exact local Python/Git versions and an immutable tested commit were not
provided. These results apply to the user-tested working tree, not to a published CI run.

The initial integrity command was incorrect: the dev image has no Git executable.
Run `python -B infrastructure/ci/check_repository.py` on the Windows host, where Git
is available; the script uses only the Python standard library. If `python` is not
recognized, use `py -3 -B infrastructure/ci/check_repository.py`. CI already runs
this check on its host runner. No Dockerfile change or image rebuild is needed.
Stage intended new files and repeat integrity/whitespace checks to include them.
Only documentation and this evidence log changed after the submitted test results.
Link CI and request Ahmed's review. Do not mark issue #24 Done yet.

## Optional Neo4j smoke verification, coordinated with S3-T03

Choose and document an exact Neo4j version/edition. On an isolated development
database, run schema/constraints.cypher twice, inspect SHOW CONSTRAINTS, and verify
duplicate same-label UIDs are rejected. Node uniqueness does not enforce required
properties or endpoint labels. Database population and full Cypher validation are
S3-T03 work. No database connection/configuration was added here.

## Coverage

Graph tests cover closed structures, registry agreement, all eight business types,
required fields, invalid formats, duplicates, unresolved references, label pairs,
deterministic scoped identities, source versions, parallel assertions, matching IP
indicators, valid intervals, ATT&CK hierarchy and mentions-only lab relationships.
ETL source authenticity, test-split exclusion and production merge behavior must be
implemented and tested in S3-T02; this contract does not replace those controls.

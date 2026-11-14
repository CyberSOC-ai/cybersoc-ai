# Incremental data and RAG reset

Authorized by Ahmed on 13 November 2026. Rebuild RAG from scratch around the
agreed `shared-dev-v1` release. This changes implementation, not the full product
requirements or the baseline-first order in [the roadmap](../ROADMAP.md).

## Preserve

- Frozen `datasets/releases/shared-dev-v1` and its existing distribution package.
  Expected manifest SHA-256:
  `8376256e0d5bfa6733fc6d045ffa42f23be779fe51a1d23a8fae0a79315ef88e`.
- Shared-v1 No-RAG CLI, terminal, core runner, policy, runtime, model and run evidence.
- Backend contracts, incident ingestion, normalizer and SQLite persistence.
- Independent contract checks, relevant tests, development tools and CI.
- Requirements, roadmap, decisions, historical reports and unrelated local work.

No commits, pushes, service startup, model execution, downloads or remote deletion
are part of this cleanup. No broad Docker prune or removal of API storage.

## Increment 1: obsolete preparation bundles

Completed locally on 13 November 2026: nine directories, 101 files (4,093,800
bytes) removed. Frozen manifest and all 80 payload checksums passed before and
after removal. Repository integrity and whitespace checks passed. No model,
service or dependency environment was started or changed.

Remove these exact directories, including their files:

```text
datasets/development/b0-six-case-review-v1
datasets/development/b0-reference-library-v1
datasets/development/b0-reference-library-v2
datasets/development/b0-retrieval-review-v1
datasets/development/b0-retrieval-review-v2
datasets/development/b0-vulnerability-case-v1
.codex-local/data/b0-reference-library-v1
.codex-local/data/b0-reference-library-v2
.codex-local/data/b0-vulnerability-case-v1
```

These are superseded preparation copies. Shared-v1 contains its own source bytes,
notices and evaluator files. None of these directories is Git-tracked. No active
Python, shell or configuration references were found outside the bundles. Local
historical handoff notes retain their dated descriptions, superseded by the reset
entry. A local metadata-only removal inventory records file hashes and sizes.

Gate: verify all 80 shared-v1 payload checksums and its pinned manifest before and
after removal; run repository integrity and whitespace checks. Do not treat those
checks as inference, SOC-quality evaluation or hosted CI.

## Increment 2: coupled legacy implementation retirement (completed locally)

Completed on 13 November 2026. Local inventory records 157 retired files, with
30 documentation/evidence files relocated into `docs/history/reset-2026-11-13`.
The old baseline guide was also preserved there before replacing active instructions.

Retirement scope:

- Retire previous `rag/ingestion`, `rag/vector` and `rag/generation` implementations
  and their implementation-specific configurations/tests. Preserve generation
  evidence as historical reports outside the active package.
- Remove `backend/vector_adapter.py` and pipeline-specific citation coupling.
  Preserve API contracts and make unavailable RAG requests fail explicitly.
- Retire `datasets/evaluation/soc-eval-v1`, `retrieval-dev-v1` and old prepared
  knowledge configuration. Replace retained baseline/backend test dependencies
  with explicit sanitized test fixtures; fixtures are not a second active dataset.
- Retire legacy dataset entry points and dataset-specific evaluation tooling/tests;
  retain independently useful scoring/contract behavior where applicable.
- Update Compose, requirements, CI, repository checks and active documentation to
  reflect the remaining capabilities. Record reduced test coverage honestly.
- Locate generated corpus/index files and inspect the narrowly named historical
  Qdrant resource `cybersoc-s2t02-qdrant` before any removal. Do not assume that a
  Compose declaration proves a volume exists or is safe to delete while in use.

Gate: retained tests pass; no active imports/defaults point to removed data/code;
shared-v1 remains unchanged; RAG is explicitly unavailable. Inventory references
inside historical reports separately from executable dependencies.

## Increment 3: release workflow (documented); fresh RAG remains future work

The retained shared CLI explicitly pins v1 and its manifest, with no legacy
fallback. [The active workflow](workflow.md) documents future release activation.
Use an explicitly selected release ID and manifest hash, with no legacy fallback.
Future changes are staged separately, reviewed and validated, then frozen as v2,
v3 and later releases without overwriting previous bytes. Preserve stable item
IDs, predecessor manifest identity, per-file checksums and a change record.

Keep evaluator criteria outside model inputs/retrieval and development groups
separate from future held-out tests. Store derived artifacts separately, binding
them to source content, preparation configuration/code and model identities.
Reuse unchanged embeddings only after verifying those identities.

The frozen release's `VERSIONING.md` already defines these boundaries, summarized
in the [tracked release guide](shared-dev-v1.md). Enforce them in the fresh workflow
without editing the frozen release. Finish No-RAG assessment, then implement a
small Vector RAG and independent save/restore/reproduction before B0 acceptance.

## Final local verification — 13 November 2026

- 127 retained offline tests passed in the existing Python 3.12 image: backend 21,
  baseline 49, contracts 20, normalizer 16 and independent evaluation metrics 21.
  This count excludes the deliberately retired legacy dataset/ingestion/vector
  tests; it is not a coverage or quality comparison with historical totals.
- Ruff, repository links/conflict checks, Bash syntax and whitespace checks passed.
- Pinned v1 manifest and all 80 bundled payload checksums passed again. Shared
  No-RAG release/model/runtime preflight passed without inference.
- Removed old `.local/ingestion` contents after preserving both BGE model packages
  under `artifacts/retained-models/legacy-bge` and historical results/reviews under
  `artifacts/historical-rag/reset-2026-11-13`. The empty parent directory remains.
  Metadata inventory covered 987 files / 10,853,627,310 bytes before separation.
- Inspected the stopped `cybersocai-qdrant-1` container, its mounts and project
  labels; removed that container and `cybersoc-s2t02-qdrant` volume. No other
  service, image, API storage, local inference artifact or model was removed.
- New model/history directories use local `.git/info/exclude` entries, not a
  tracked ignore-rule change. Exclusion is not a confidentiality guarantee.
- No dependency install/build/download, real model run, remote update, commit,
  branch or push. Hosted CI and fresh-image reproduction were not run. Existing
  Python image contains previously installed extras; removing obsolete pins does
  not claim a newly built minimal environment. Fresh RAG and B0 acceptance remain
  pending.

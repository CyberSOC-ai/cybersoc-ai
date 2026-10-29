# S2-T01 — Reproducible knowledge and SOC-history ingestion

Owner Ahmed; reviewer Soulaiman; [issue #16](https://github.com/CyberSOC-ai/cybersoc-ai/issues/16).
Work branch: `feature/16-knowledge-ingestion`. The expanded implementation is local
pending review/publication. This prepares source records; chunking, embeddings,
retrieval scoring and vector-store selection belong to S2-T02.

## Source selection

Read [the selection and coverage rationale](../../datasets/knowledge/SOURCE_SELECTION.md)
and its [exact revisions/files](../../datasets/knowledge/sources.json) first.
The corpus combines ATT&CK, a full annual NVD feed, selected official CVE records,
KEV enrichment, CWE, selected Sigma rules/playbooks, our existing normalized lab
observations and selected OTRF/Splunk excerpts. Current selection covers the NVD 2024, 2025 and 2026 identifier-year feeds,
with 2026 limited to records available at acquisition. It is not an all-years
vulnerability mirror. Add explicit years to `nvd_years` to expand coverage;
older vulnerabilities may still matter for your asset inventory.

CVE providers are joined by exact CVE ID into one searchable document. KEV catalog
entries enrich matching CVEs and remain available for structured lookup. Active
ATT&CK relationships are exported separately rather than inflated into the vector
text corpus. External events are explicitly assigned development examples, with
no invented backend severity, timestamps or analyst verdicts.

## 1. Environment

From the repository root:

```sh
docker compose build dev
mkdir -p .local/ingestion
```

The image uses Python 3.12 with pinned `ijson` for streaming large feeds and
`PyYAML` for safe Sigma parsing. Source stays mounted read-only; the commands below
add a writable artifact mount. `.local/` is ignored by Git. Neither acquisition
nor normalization executes rules, playbooks, event commands or source-provided
links. All retrieved/source prose remains untrusted data.

## 2. Acquire and build a fresh selection

```sh
docker compose run --rm -T -v "$PWD/.local/ingestion:/artifacts" dev python -B -m rag.ingestion.build --artifacts /artifacts --output /artifacts/s2-t01-2024-2026-release --acquire --lab-acquired-at "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

`--acquire` explicitly enables bounded provider downloads. Existing snapshots are
reused only if their recorded revision/selection matches the plan; every source
and notice digest is verified before normalization. Existing output directories
are never intentionally overwritten. To refresh mutable NVD feeds/notices, use a
new artifact root and retain the prior version. Partial snapshots/releases are
staged and only published after success. Do not use concurrent writers for the
same destination.

Without `--acquire`, the same build is fully offline and fails if a required
snapshot is missing:

```sh
docker compose run --rm -T -v "$PWD/.local/ingestion:/artifacts" dev python -B -m rag.ingestion.build --artifacts /artifacts --output /artifacts/s2-t01-2024-2026-replay
```

Replaying identical snapshots, policies, selection, code and dependency versions
must reproduce normalized JSONL and manifests. The build rejects implementation
edits made while it is running. Original acquisition timestamps are input metadata;
normalization does not add a fresh wall-clock timestamp to every record.

## 3. Outputs and downstream use

| Release artifact | Purpose |
|---|---|
| `release.json` | Complete build provenance, versions, per-source reports and composed-corpus report |
| `selection.json` | Exact source-selection plan |
| `normalized/<source>/` | Per-source JSONL, manifest, preserved notice and applicable policy/splits |
| `corpus/records.jsonl` | Deterministically sorted searchable reference documents and eligible SOC excerpts |
| `corpus/relationships.jsonl` | ATT&CK relationship records for later graph processing |
| `corpus/facts.sqlite` | Exact CVE/KEV lookup plus stored documents/relationships; downstream internal handoff |
| `corpus/manifest.json` | Input manifests, final hashes/counts, CVE joins, KEV coverage and corpus-use restriction |
| `corpus/notice-*.txt` | Source notices corresponding to ordered input manifests |

All source and release files live on the host PC under `.local/ingestion/`.
The `/artifacts` container path is a bind mount of that same local directory,
not remote storage. `nvd-2024/`, `nvd-2025/` and `nvd-2026/` retain the raw annual
feeds. The derived `facts.sqlite` is a reference store, not the future vector
index. S2-T02 will create embeddings and load the selected index from these
prepared records; the model will receive retrieved passages rather than the whole
database. Neither model training nor per-question annual-feed downloads occur.

The public upstream snapshots/ZIPs, selected source bytes and acquisition receipts
remain in the artifact root. Releases preserve their hashes/references. Shared
artifact storage is not selected by this task; local artifact paths do not provide
team-wide availability. Retain original snapshots, especially mutable NVD data and
notice pages, for exact replay. All raw/generated datasets remain outside Git.

Exact lookup example (replace the release directory if needed):

```sh
docker compose run --rm -T -v "$PWD/.local/ingestion:/artifacts" dev python -B -m rag.ingestion.corpus lookup --corpus /artifacts/s2-t01-2024-2026-release/corpus --cve CVE-2024-6387
```

This returns structured reference facts, not a judgment that the lab is vulnerable.
It uses exact parameterized CVE-ID lookup. The SQLite file is an internal derived
artifact, not a new backend API or the selected vector database.

## 4. Record contract and citations

The [record schema](schemas/record.schema.json),
[snapshot schema](schemas/snapshot.schema.json),
[lab policy](schemas/soc-policy.schema.json) and
[external policy](schemas/external-policy.schema.json) define the handoff.

- `record_id`: stable source/source-record identity; `content_sha256` tracks text changes.
- `collection`: `knowledge`, `soc_history` or separate `relationships`.
- `title`/`content`: source text for chunking; never assume it is an instruction.
- `source`/`source_record_id`/`snapshot_ref`: citation identity preserved into evidence.
- `provenance`: owner, original URL/version/time, input digest and notice references.
- Typed `metadata`: source-specific fields, CVE provider data/provenance chains,
  rule status/false positives, or event lineage and split eligibility.

Documents may exceed the backend evidence limit of 16,000 characters and require
bounded chunking. Derive chunk IDs while retaining document/source/snapshot identity.
Do not embed or send dataset paths, technique-bearing event paths, group/split
membership or evaluator metadata as incident features. Reference technique IDs in
ATT&CK/Sigma are knowledge; dataset labels about an evaluated incident are not.

Supplemental KEV/CNA claims need evidence cited to their corresponding provenance
snapshot, not silently attributed to the primary NVD description. Consumers must
render relevant structured fields into separately cited evidence as needed. The
existing backend evidence schema now permits `detection_rule` and `playbook`;
update any copied source enums. Ingestion does not fabricate retrieval scores or
claim measured retrieval quality. Some graph endpoints remain outside this subset.

## 5. SOC-history safeguards

Read [lab assignments](../../datasets/knowledge/SOC_ASSIGNMENTS.md) and
[external assignments](../../datasets/knowledge/EXTERNAL_ASSIGNMENTS.md).
Policies pin source digests and exact evaluation split bytes. Unknown inputs are
quarantined; held-out groups/runs/related cases and test/quarantine assignments
are excluded. Present exact held-out duplicates are excluded for normalized lab
incidents. Manual sensitivity and near-duplicate grouping review is still required.
External examples are excerpts, not independently labeled incidents.

The current pilot has no frozen test split. All SOC outputs explicitly declare
`development_only`, and the combined release inherits that restriction. A changed
split invalidates the policy hash and requires reassignment/rebuild. Evaluation
labels are never loaded into the corpus; explicit label fields are rejected.
Playbook hypotheses and Sigma detection patterns are reference knowledge, not
proof of the current incident's verdict. No new real lab run is claimed.

## 6. Component commands and bounds

For individual acquisitions use `python -m rag.ingestion.acquire` (ATT&CK, one CVE
or CWE), `python -m rag.ingestion.nvd_bulk acquire --year 2024 --output ...`, or
`python -m rag.ingestion.curated --selection datasets/knowledge/sources.json
--provider sigma --output ...`. Each module has `--help`.

For a bounded snapshot use `python -m rag.ingestion --input ... --snapshot ...
--notice ... --output ...` with `--soc-policy`/`--splits` for SOC. Annual NVD feeds
use `python -m rag.ingestion.nvd_bulk normalize --snapshot-dir ... --output ...`.
The in-memory path is limited to 128 MiB. The annual path streams JSON and uses
SQLite for identity checks/sorting; compressed acquisition is capped at 128 MiB,
decompressed input at 2 GiB, nesting at 64 and per-record parse/output budgets at
8 MiB. It rejects malformed/truncated JSON, duplicate keys/IDs, count mismatches,
META integrity mismatches and feed changes during acquisition.

Curated sources permit only the selected official repositories, pinned commits
and at most 50 named files per provider. HTTP redirects are disabled. Git LFS size
and SHA-256 are checked. ZIP contents are bounded and read without extracting
upstream paths. YAML aliases, duplicate keys and executable tags are rejected;
only a safe loader is used. Source-specific notices and usage restrictions apply.

## 7. Checks and acceptance

```sh
docker compose run --rm -T dev ruff check --no-cache .
docker compose run --rm -T dev python -B -m unittest discover -s tests/ingestion -v
```

The offline suite runs in CI alongside existing contract/evaluation/backend/
normalizer/baseline suites. No upstream downloads or model runs are required in
CI. See [validation](../../datasets/knowledge/VALIDATION.md) for actual results
and exact hashes. S2-T01 remains under review until required publication, hosted
CI, reviewer handling, merge and linked issue closure are completed.

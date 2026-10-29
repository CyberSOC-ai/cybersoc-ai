# S2-T01 2024–2026 local validation — 2026-10-29

Branch: `feature/16-knowledge-ingestion`; prior published head:
`5aae31a793a4e2a2a54223f65b8c79b71d704b59`.
[Draft PR #86](https://github.com/CyberSOC-ai/cybersoc-ai/pull/86) is the publication
and review target for the expanded implementation. Ahmed authorized pushing it
on 2026-10-29 and retains review/merge control. This record documents local
validation; final-head hosted CI is tracked in PR checks. No independent peer
approval, merge or issue closure is claimed.

The 2024–2026 coverage update extends local commit `0eff293`. It changes the
source plan and documentation only; ingestion code and schemas are unchanged.
All 44 ingestion tests were rerun successfully for this update, alongside the
real-source build/replay checks below. The 169-test full-suite result records the
preceding implementation validation.

The user approved all proposed source additions. Exact immutable revisions/files
are in [the source plan](sources.json), with roles/coverage in
[SOURCE_SELECTION.md](SOURCE_SELECTION.md). Complete input/output/code/schema
hashes, acquisition versions/times, notices and reports are preserved in the
[machine-readable validation summary](validation-summary.json).

## Local checks

The development image rebuilt with Python 3.12.15, ijson 3.6.0 and PyYAML 6.0.3.
All **169 tests** passed: 19 contracts, 43 evaluation, 20 backend, 16 normalizer,
27 baseline and 44 ingestion/acquisition. Ruff and dependency consistency
(`pip check`) passed. Existing FastAPI/Starlette dependencies emit an HTTP-client
deprecation warning; their tests pass. No model, embeddings or benchmark inference
was run. Repository integrity passed for 230 tracked text files; staged whitespace
checks and Gitleaks 8.30.1 passed with no suspected secrets. The scanner ran with
networking disabled. CI uses mocked source responses and synthetic parser fixtures, not live
upstream downloads.

Expanded regression coverage includes annual-feed streaming, byte/depth/record
bounds, duplicate keys/IDs, malformed/truncated JSON, NVD counts and META integrity,
exact CVE provider/KEV joins, corpus tampering, source revision checks, safe YAML,
Git LFS identity, real event-format handling, grouped split exclusion, and the
new backend evidence source values. Existing backend/contract/evaluation/normalizer/
baseline suites were retained. Parser tests do not certify retrieval relevance.

## Real-source result

| Searchable source | Records/excerpts |
|---|---:|
| cve | 162,499 |
| cwe | 956 |
| detection_rule | 3 |
| mitre_attack | 706 |
| playbook | 2 |
| soc_log | 35 |

Total: **164,201** searchable documents/excerpts. An additional
**21,660 ATT&CK relationships** are exported separately in
`relationships.jsonl`; they are not counted as vector documents.

- NVD: official **2024, 2025 and 2026** JSON 2.0 feeds, each verified against
  its own META size and SHA-256. Retained **162,499** non-rejected CVEs:
  2024 retained 38,494 of 39,360 (866 rejected); 2025 retained 43,642 of 45,432
  (1,790 rejected); 2026 retained 80,363 of 81,464 (1,101 rejected).
  The 2026 feed covers records available at acquisition on 2026-10-29, not future
  records for the remainder of the year. This is not an all-years database mirror.
  Exact CVE-year counts were independently checked in the derived SQLite store.
- Official CVE Program: five pinned records joined to existing NVD documents;
  CNA/ADP fields, alternate descriptions and provenance remain available without
  duplicate vector records. These records do not establish lab exposure.
- KEV: all 1,762 catalog records retained for structured
  lookup. Exactly 544 indexed CVEs were enriched by CVE-ID
  match; 1,218 unmatched entries remain lookup records.
  Membership is exploitation context, not proof of exploitation in an incident.
- ATT&CK: 706 active techniques; 21,660 active relationships. Excluded 4,004
  unsupported objects, 161 revoked/deprecated objects and 159 relationships to
  inactive endpoints. Some relationship endpoints remain outside this selection.
- CWE: official release 5.0, namespace 8, 956 weaknesses; excluded 493 catalog
  groupings/views/categories and 28 deprecated weaknesses. Consumed-field
  validation is not full upstream XSD validation.
- Sigma: three selected Linux rules, all with upstream status `test`; preserve
  descriptions, detection patterns, references and false-positive guidance.
- Playbooks: two Windows reference guides, retained as text, never executed.
  They do not establish Windows lab deployment or coverage.
- SOC: two existing real Wazuh observations plus 12 OTRF and 21 Splunk excerpts.
  These 35 observations/excerpts are not 35 independent incidents. Splunk's source
  documentation is retained but not indexed as event content; five further
  excerpts are counted as excluded by the explicit selection limit.

The first external-format attempt assumed JSONL and failed without publishing a
corpus. Inspection identified auditd text and Sysmon XML, so the adapter preserves
those formats as typed observations without invented severity/time/verdict fields.
Manual review of the selected small public files and a credential-pattern check
found no new project credentials; this is not a privacy certification for entire
upstream datasets. Source/dataset metadata remains separate from event content.

## Full replay verification

Two independent builds from fixed code and the same retained snapshots produced
**28 byte-identical files**: `release.json`, composed manifest/JSONL/relationship
export, and all twelve per-source manifests/JSONL files. The SQLite binary was not
compared; the JSON evidence and manifests define the reproducibility check.
The implementation fingerprint also covers backend validation code, shared JSON
schemas and root dependency pins; runtime dependency versions are recorded.

Searchable JSONL SHA-256: `d2226bce888a6ca57f21616b61a16e4569b8525ce04582f93d3c847cd46dda83`.

The final local releases are `.local/ingestion/s2-t01-2024-2026-release` and
`.local/ingestion/s2-t01-2024-2026-replay`. Their `normalized/` directories retain
source notices, snapshot manifests and applicable policy/split inputs. Raw source
snapshots, ZIPs and acquisition receipts remain in their original ignored artifact
folders. Reproduce with the [runnable guide](../../rag/ingestion/README.md).
No raw/public-event dataset or generated corpus is committed or newly redistributed.

All files are stored on the project PC. Docker's `/artifacts` path maps to the
same `.local/ingestion` directory. Raw annual feeds live in `nvd-2024/`,
`nvd-2025/` and `nvd-2026/`; the release contains prepared JSONL and a derived
`facts.sqlite` reference store. S2-T02 will build an embedding/vector index from
the prepared text. There is no per-question annual-feed download or model
training here, and no vector index has been created by this task.

## Acceptance boundaries

The current synthetic pilot split is unfrozen. Local/external event assignments
are proposed development groupings for review; the complete release declares
`development_only`. Changed source/split hashes invalidate eligibility. Unknown
files are quarantined; manual sensitive-prose and near-duplicate-family review
remains necessary. No evaluator labels are loaded into retrieval. Public source
availability is not independent validation of every example or a universal
redistribution license. Retain notices and resolve OTRF's differing README/root
license labels before external redistribution.

S2-T01 is locally implemented and verified, **not formally Done**. Ahmed authorized
publication and retains merge control. The expanded head still needs hosted CI, Soulaiman's
handoff/source/policy review, review handling, merge and issue closure. Shared
artifact storage remains unresolved under ADR-006. S2-T02/S2-T03 still own indexing
and measured retrieval quality; S2-T08 IOC feed ingestion is not completed here.

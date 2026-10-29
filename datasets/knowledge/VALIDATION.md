# S2-T01 expanded local validation — 2026-10-29

Branch: `feature/16-knowledge-ingestion`; prior published head:
`5aae31a793a4e2a2a54223f65b8c79b71d704b59`.
[Draft PR #86](https://github.com/CyberSOC-ai/cybersoc-ai/pull/86) contains the earlier
implementation. This record covers the expanded **local, unpushed follow-up**.
No hosted CI, independent peer review, merge or issue closure is claimed for it.

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
| cve | 38,494 |
| cwe | 956 |
| detection_rule | 3 |
| mitre_attack | 706 |
| playbook | 2 |
| soc_log | 35 |

Total: **40,196** searchable documents/excerpts. An additional
**21,660 ATT&CK relationships** are exported separately in
`relationships.jsonl`; they are not counted as vector documents.

- NVD: complete official **2024** JSON 2.0 feed, verified against NVD META size
  and SHA-256. Parsed 39,360 CVEs; excluded 866 rejected entries; retained 38,494.
  This is one identifier year, not an all-years database mirror.
- Official CVE Program: five pinned records joined to existing NVD documents;
  CNA/ADP fields, alternate descriptions and provenance remain available without
  duplicate vector records. These records do not establish lab exposure.
- KEV: all 1,762 catalog records retained for structured
  lookup. Exactly 164 indexed CVEs were enriched by CVE-ID
  match; 1,598 unmatched entries remain lookup records.
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
**24 byte-identical files**: `release.json`, composed manifest/JSONL/relationship
export, and all ten per-source manifests/JSONL files. The SQLite binary was not
compared; the JSON evidence and manifests define the reproducibility check.
The implementation fingerprint also covers backend validation code, shared JSON
schemas and root dependency pins; runtime dependency versions are recorded.

Searchable JSONL SHA-256: `081bf66fe0df5f887baefba2e02263203ac267da2b371f1fb6114c693486b885`.

The final local releases are `.local/ingestion/s2-t01-release-final` and
`.local/ingestion/s2-t01-release-replay`. Their `normalized/` directories retain
source notices, snapshot manifests and applicable policy/split inputs. Raw source
snapshots, ZIPs and acquisition receipts remain in their original ignored artifact
folders. Reproduce with the [runnable guide](../../rag/ingestion/README.md).
No raw/public-event dataset or generated corpus is committed or newly redistributed.

## Acceptance boundaries

The current synthetic pilot split is unfrozen. Local/external event assignments
are proposed development groupings for review; the complete release declares
`development_only`. Changed source/split hashes invalidate eligibility. Unknown
files are quarantined; manual sensitive-prose and near-duplicate-family review
remains necessary. No evaluator labels are loaded into retrieval. Public source
availability is not independent validation of every example or a universal
redistribution license. Retain notices and resolve OTRF's differing README/root
license labels before external redistribution.

S2-T01 is locally implemented and verified, **not formally Done**. User approval
precedes any further push. The expanded head still needs hosted CI, Soulaiman's
handoff/source/policy review, review handling, merge and issue closure. Shared
artifact storage remains unresolved under ADR-006. S2-T02/S2-T03 still own indexing
and measured retrieval quality; S2-T08 IOC feed ingestion is not completed here.

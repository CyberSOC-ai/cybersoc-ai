# S2-T01 local validation — 2026-10-28

This is author-side validation on `codex/16-knowledge-ingestion`, based on main
`48c224ff6f358b0d9ffd878d4af3013b503d230b`. It is not peer approval or hosted CI.
The [machine-readable summary](validation-summary.json) records exact snapshot,
notice, code, schema and output hashes, versions, acquisition times and exclusions.

## Local checks

The shared Docker development image built and reported Python 3.12.15; dependency
consistency (`pip check`) passed. Ruff passed. All **150
tests** passed: 19 contracts, 43 evaluation, 20 backend, 16 normalizer, 27 baseline,
and 25 ingestion/acquisition. Repository integrity passed for 219 tracked text
files; staged whitespace checks and Gitleaks 8.30.1 passed with no suspected
secrets. The scanner ran with networking disabled. No models were loaded. The existing dependency
stack emits a FastAPI/Starlette HTTP client deprecation warning; its tests passed.

Offline ingestion tests cover required provenance, strict JSON, byte limits,
duplicate IDs, typed source metadata, source/notice tampering, deterministic
identity, missing CVE enrichment, CWE namespaces 7/8, XML declaration rejection,
revoked techniques/inactive relationships, no partial publication, source notice
retention, pinned lab preparation and explicit SOC split/duplicate exclusions.
Acquisition tests use mocked HTTP, including redirects, response bounds, streaming
deadlines and failed notice requests. CI performs no upstream downloads.

## Real-source smoke and replay

| Source | Accepted records | SHA-256 of normalized JSONL |
|---|---:|---|
| cve | 1 | `0021f9bca0ec4aa83e66debdd1ad7665709c4170371bb0b8c3abeb02f73e1e8e` |
| cwe | 956 | `91f096f7c9bbb9c9db1d9044341d9abcded83ea1a4cb178b337e0cf24dba07ca` |
| mitre_attack | 22366 | `bd1880ba1b24f84d297bc8a125268c62bb28c601e4914c23a2807bc894c50cb4` |
| soc_log | 2 | `ccade0b5444e1ba4865341dbce0a0bd8dcecb2038ccd22967573d17e9ba355d7` |

Each final corpus was normalized twice from identical retained input bytes with
fixed implementation files. **Both `records.jsonl` and `manifest.json` were
byte-identical for all four pairs.** SHA-256 alone is an integrity identifier,
not proof of source trust or content safety.

- ATT&CK: Enterprise STIX from official commit
  `c2494b29dd268c46a5d0ea0990553e4327cd2253`; 706 techniques and 21,660 relationships.
  Excluded 4,004 unsupported STIX objects, 161 revoked/deprecated objects and 159
  relationships to inactive endpoints. Some active relationship endpoints remain
  upstream objects outside the selected technique/relationship corpus.
- CWE: official release 5.0, namespace `http://cwe.mitre.org/cwe-8`, schema-version
  identifier 8.0; 956 weaknesses. Excluded 493 groupings/views/categories and 28
  deprecated weaknesses. Adapter validation covers the consumed fields, not full
  upstream XSD validation.
- NVD: one actual API response for CVE-2021-44228. Original modification times,
  references and supplied CVSS/CWE/CPE enrichment are preserved. This is a bounded
  parser/integration sample, not a comprehensive vulnerability corpus. The exact
  response is retained because subsequent API requests can change its bytes.
- SOC: two existing real LAB-01 authentication-failure observations normalized
  by S1-T06. Both are explicitly assigned to the pilot's `G-SSH` family for
  development under the proposed [policy](soc-policy.json). The current test split
  is unfrozen; both record metadata and corpus manifest mark that limitation.
  No analyst ground truth, model output or newly generated lab evidence is used.

The early artifact mount was not writable by the container's regular user;
corrected ownership of the newly created directory and repeated acquisitions.
Initial CWE parsing exposed namespace 8 and initial NVD notice acquisition exposed
an official 301 redirect. Both were corrected and covered by tests. An intermediate
replay overlapped implementation edits and correctly produced different code
fingerprints; only the final run with fixed source files is recorded as passing.

## Reproduction and storage

Follow [the runnable guide](../../rag/ingestion/README.md). The final local smoke
corpora are `.local/ingestion/mitre_attack-verified-final`, `cve-verified-final`,
`cwe-verified-final` and `soc_log-verified-final`; corresponding `*-replay-final`
directories hold the comparison outputs. Source snapshots remain in `attack`,
`cve`, `cwe` and `soc-final`. Corpus manifests copy the exact input manifest,
source notice and any SOC policy/split inputs. Raw snapshots, notices, generated
corpora and temporary replay scripts are ignored local files, not Git contents.

Local SHA-addressed artifacts provide this machine's reproducibility. Team-wide
artifact sharing is still unresolved under ADR-006. Retain the exact snapshots
before cleanup; reacquiring a mutable NVD response or notice page is not an exact
reproduction guarantee. The public receipts and hashes contain no credentials or
raw SOC descriptions. No new redistribution permission is inferred.

## Acceptance boundaries

S2-T01 is implemented for review; it is **not Done**. Soulaiman must review the
record contract and proposed SOC assignments; feedback/reviewer handling,
hosted CI, PR merge and issue closure remain part of the project workflow.
Before a frozen benchmark, review all incident/template families against its
split and regenerate policy/corpora. Schema checks cannot establish prose
sanitization or detect every near-duplicate family. No retrieval-quality,
model-quality, serving-performance or full RAG integration result is claimed.

# Sprint 2 — Vector RAG & Threat-Intelligence Ingestion

## Sprint Information
- Dates: 2026-10-26 → 2026-11-08
- Main objective: Add evidence-grounded semantic retrieval, ingest real threat-intelligence data, and prove that retrieval quality is measurable.
- Main dependencies: S0-T05, S1-T02, S1-T03, S1-T04, S1-T05, S1-T06
- Exit criteria:
  - Ingestion is reproducible (knowledge and threat intelligence)
  - Retriever quality is measured separately
  - Vector RAG works through the backend
  - No-RAG vs Vector-RAG results are recorded

## Sprint Tasks

| Task | Owner | Reviewer | Domain | Status |
|---|---|---|---|---|
| S2-T01 — Cybersecurity knowledge normalization / ingestion | Ahmed | Soulaiman | rag | In progress (implemented; review/CI pending) |
| S2-T02 — Chunking, embeddings and vector index | Soulaiman | Ahmed | rag | Backlog |
| S2-T03 — Retriever evaluation | Achraf | Anas | rag | Backlog |
| S2-T04 — Vector-RAG generation pipeline | Anas | Oussama | rag | Backlog |
| S2-T05 — RAG API integration | Oussama | Anas | backend | Backlog |
| S2-T06 — No-RAG vs Vector-RAG experiment | Achraf | Soulaiman | rag | Backlog |
| S2-T07 — SOC Lab scenario set v1 | Oussama | Ahmed | soc | Backlog |
| S2-T08 — Threat-intelligence ingestion | Ahmed | Oussama | soc | Backlog |

# 1. Ahmed
## Assigned tasks

S2-T01, S2-T08. This update covers S2-T01 only; S2-T08 remains Backlog.

## Work completed

2026-10-28 — Implemented [offline knowledge ingestion](../../../rag/ingestion/README.md)
on `codex/16-knowledge-ingestion`, based on main `48c224f`. Added separate bounded
public acquisition and offline adapters for Enterprise ATT&CK STIX, NVD CVE JSON
2.0, CWE XML namespaces 7/8, and eligible normalized SOC history. Every record
preserves source identity, provenance, notice references and snapshot hashes.
This is implemented for review; no peer approval, hosted CI or merge is claimed.

## Technical approach

Use the existing Python 3.12/Docker environment and JSON Schema dependency. Emit
canonical JSONL plus manifests with source/output/code/schema hashes, counts and
exclusion reasons. Validate the entire corpus before atomic directory publication.
Keep knowledge and SOC history logically separate for Soulaiman's S2-T02 handoff.
No embeddings, vector store, model run or S2-T08 feed is introduced.

## Files / components modified

Added `rag/ingestion/`, versioned input/record/policy schemas, offline tests and
`datasets/knowledge/` assignment/validation records. Added the ingestion suite to
CI and linked the guide from the dataset inventory. Existing backend contracts,
other members' sections and shared sprint sections are unchanged.

## Tests / validation

Python 3.12 development image built. All 150 tests passed: 19 contracts, 43
evaluation, 20 backend, 16 normalizer, 27 baseline and 25 ingestion/acquisition.
Ruff, dependency consistency, repository integrity, staged whitespace and
Gitleaks 8.30.1 passed. The ingestion tests use mocked HTTP and synthetic parser examples;
actual source smoke/replay evidence is separate in the
[validation record](../../../datasets/knowledge/VALIDATION.md).

## Results / metrics

Real-source normalization produced 706 active ATT&CK techniques and 21,660
relationships (22,366 records), 956 CWE weaknesses, one bounded CVE sample and two
real LAB-01 development observations. These are corpus counts, not retrieval or
model-quality metrics. Exact snapshot/output hashes and replay outcomes are in
the validation record. The single CVE does not establish broad CVE coverage.

## Problems encountered

The current CWE 5.0 release uses namespace 8 and Groupings; added support while
retaining namespace 7 compatibility. NIST's former license URL redirects, so
acquisition now uses the current official destination without enabling arbitrary
redirects. The new Docker artifact mount initially had the wrong ownership;
repaired the newly created directory and repeated failed acquisitions. The
existing FastAPI/Starlette dependency emits a deprecation warning; its tests pass.

## Decisions made

Exclude revoked/deprecated ATT&CK objects and relationships to inactive endpoints.
Preserve missing CVE enrichment as missing. Admit only hash-pinned, explicitly
assigned development SOC records; exclude held-out groups/runs, related test cases
and exact present duplicates. Near-duplicate grouping and sensitive prose still
require manual owner/reviewer checking. Both real SSH observations are grouped
with `G-SSH`. Current evaluation splits are unfrozen, so SOC corpus use is
explicitly development-only. Raw/downloaded and generated corpora remain ignored
local artifacts; shared artifact storage is unresolved. The vector database
remains ADR-001's team decision.

## Related Issues / Pull Requests

[S2-T01 / issue #16](https://github.com/CyberSOC-ai/cybersoc-ai/issues/16).
Reviewer: Soulaiman (`soulaimane-22`). Branch: `codex/16-knowledge-ingestion`.
PR publication, assigned review handling, hosted CI, merge and issue closure are
pending. This task is not Done. Review the record contract, SOC assignment policy
and documented coverage/storage limitations before S2-T02 integration.

## Learning outcome

Stable source identity and immutable snapshot provenance serve different purposes.
Deterministic offline preparation makes ingestion reproducible, while grouped
split exclusions prevent SOC history from contaminating evaluation. A clean
corpus and passing parsers alone do not demonstrate retrieval quality.


# 2. Soulaiman
## Assigned tasks

S2-T02

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

S2-T04

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

S2-T03, S2-T06

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

S2-T05, S2-T07

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

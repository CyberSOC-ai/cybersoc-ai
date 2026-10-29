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

S2-T01, S2-T08. This update covers S2-T01 and the user-approved source expansion;
S2-T08 IOC-feed ingestion remains Backlog.

## Work completed

2026-10-29 — Completed the expanded local [knowledge-ingestion implementation](../../../rag/ingestion/README.md)
on `feature/16-knowledge-ingestion`. The user approved including bulk CVE/NVD,
CISA KEV, Sigma, playbooks and selected OTRF/Splunk examples alongside ATT&CK,
CWE and existing lab history. The user subsequently authorized adding the 2025
and 2026 annual NVD feeds alongside 2024; the selection now covers all three
identifier years through their acquisition snapshots. The earlier draft is [PR #86](https://github.com/CyberSOC-ai/cybersoc-ai/pull/86);
these follow-up changes are local and have not been pushed. User review precedes
any further push. No merge, issue closure or independent peer approval is claimed.

## Technical approach

Stream annual NVD JSON into a disk-backed identity/sort stage; verify compressed
feed acquisition against NVD META size/SHA-256 and detect concurrent feed changes.
Acquire only named public files at pinned official-repository commits, retaining
licenses/notices, Git LFS identity, ZIP checks and receipts. Normalize with typed
schemas; reject unsafe YAML and XML, duplicate identities and changed source bytes.
Join NVD/CVE Program records and KEV by exact CVE ID. Keep ATT&CK relationships
separate from searchable prose. Compose a reproducible offline release with
structured CVE/KEV lookup. No models, embeddings, rule deployment or notebook
execution occur.

## Files / components modified

Extended `rag/ingestion/`, versioned ingestion schemas, offline tests and source/
assignment/validation records in `datasets/knowledge/`. Added pinned ijson/PyYAML
dependencies. Extended the draft backend evidence source enum with `detection_rule`
and `playbook`, retaining existing examples/fields; consumers with frozen enums
must refresh them. Other members' journals and shared sprint sections are unchanged.

## Tests / validation

Python 3.12.15 development image rebuilt. All 169 tests passed: 19 contracts,
43 evaluation, 20 backend, 16 normalizer, 27 baseline and 44 ingestion/acquisition.
Ruff passed. Expanded tests cover streaming bounds/counts/duplicate keys, NVD META
integrity, exact vulnerability joins, input-corpus tampering, source revision pins,
Git LFS identity, safe YAML and real external event formats/split exclusion.
The 44 ingestion tests passed again for the three-year selection update; its
code/schemas are unchanged. Full-source replay and final check details are in the
[validation record](../../../datasets/knowledge/VALIDATION.md). CI for the previously
published draft does not validate these unpushed changes.

## Results / metrics

The updated local collection contains 164,201 prepared documents/excerpts:
162,499 CVEs across 2024 (38,494), 2025 (43,642) and 2026 (80,363),
706 ATT&CK techniques, 956 CWE weaknesses, three Linux Sigma rules, two Windows
playbooks and 35 SOC excerpts/observations. Exported 21,660 ATT&CK relationships
separately. Five official CVE records join existing documents; 544 CVEs gain KEV
context from a 1,762-record catalog, with 1,218 unmatched entries retained for
structured lookup. Two independent full builds reproduced 28 JSONL/report files
byte-for-byte, and exact CVE-year counts were checked in SQLite.

These are collection counts, not retrieval/model-quality results. The three-year
selection is not an all-years mirror; 2026 covers records available at acquisition.
The official CVE supplement is five records, and the external event selection is
33 excerpts rather than independent incidents. Data lives on this PC under
`.local/ingestion/`; the container mount is the same host directory. Git excludes
these datasets. S2-T02 will build the vector index from the prepared records.

## Problems encountered

The initially selected external logs were auditd text and Sysmon XML, so added
format-aware observation parsing instead of treating them as JSONL or inventing
backend incident fields. Some selected Sigma rules have upstream `test` status;
retain it rather than claiming production readiness. The selected playbooks are
Windows reference content, not deployed Windows-lab evidence. Existing dependency
stack emits an HTTP-client deprecation warning; tests pass.

## Decisions made

Use [the explicit source plan](../../../datasets/knowledge/sources.json) and
[coverage rationale](../../../datasets/knowledge/SOURCE_SELECTION.md). Preserve
NVD/CNA/ADP/KEV provenance separately and cite claims to the correct snapshot.
Keep source text as untrusted data. Both local SSH observations and the selected
external SSH run share `G-SSH`; network-discovery examples share their own family.
Unknown/unassigned files are quarantined. Changed split/source hashes invalidate
eligibility. The current pilot is unfrozen; all SOC material and the combined
release remain development-only. Manual prose-sensitivity and near-duplicate
review are still required. Retain source-specific notices; resolve OTRF's differing
README/root-license labels before external redistribution. Raw/generated artifacts
stay ignored locally; shared storage remains unresolved under ADR-006. Vector
store/embedding choices remain S2-T02/ADR-001 work.

## Related Issues / Pull Requests

[S2-T01 / #16](https://github.com/CyberSOC-ai/cybersoc-ai/issues/16).
Reviewer: Soulaiman (`soulaimane-22`). Branch: `feature/16-knowledge-ingestion`.
[Draft PR #86](https://github.com/CyberSOC-ai/cybersoc-ai/pull/86) contains the earlier
implementation. User approval to push this expanded follow-up, hosted CI for its
head, assigned review handling, merge and issue closure remain pending. This task
is not formally Done. No merge or new reviewer notification was performed.

## Learning outcome

A large vulnerability reference needs bounded acquisition, incremental parsing
and exact identity joins. Reference knowledge, event examples and evaluator labels
have different roles. Preserving provenance and separating relationship exports
helps downstream retrieval; corpus size alone does not demonstrate answer quality.


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

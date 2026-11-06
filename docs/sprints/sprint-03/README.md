# Sprint 3 — Knowledge Graph, Graph RAG & Hybrid RAG

## Sprint Information
- Dates: 2026-11-09 → 2026-11-22
- Main objective: Add structured cyber relationships and combine graph + vector evidence.
- Main dependencies: S0-T03, S0-T05, S1-T03, S2-T04, S2-T08
- Exit criteria:
  - Graph schema documented
  - Graph populated reproducibly
  - Graph queries validated
  - Graph RAG and Hybrid RAG work
  - Comparison metrics are stored

## Sprint Tasks

| Task | Owner | Reviewer | Domain | Status |
|---|---|---|---|---|
| S3-T01 — Knowledge Graph ontology / schema | Achraf | Ahmed | knowledge-graph | Backlog |
| S3-T02 — Graph ingestion / ETL | Soulaiman | Ahmed | knowledge-graph | Backlog |
| S3-T03 — Neo4j population + Cypher validation | Oussama | Soulaiman | knowledge-graph | Backlog |
| S3-T04 — Graph retrieval service | Anas | Oussama | knowledge-graph | Backlog |
| S3-T05 — Graph-RAG pipeline | Achraf | Anas | rag | Backlog |
| S3-T06 — Hybrid RAG orchestration | Anas | Ahmed | rag | Backlog |
| S3-T07 — Retrieval comparison experiment | Oussama | Achraf | rag | Backlog |

# 1. Ahmed
## Assigned tasks

Reviewer for S3-T01. Ownership transferred to Achraf on 2026-11-04 in exchange
for S2-T03; Ahmed remains the graph-schema reviewer.

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


# 2. Soulaiman
## Assigned tasks

S3-T02

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

S3-T04, S3-T06

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

S3-T01, S3-T05. S3-T01 transferred from Ahmed on 2026-11-04; Ahmed reviews.

## Work completed

S3-T01 implementation prepared on 2026-11-06: eight business node types,
allowlisted relations, SourceRecord provenance, batch schema, offline validator,
synthetic and lab mentions examples. User local tests passed; host integrity
rerun, CI and review remain pending.
S3-T05 has not been implemented by this change.

## Technical approach

Typed Neo4j property graph with scoped deterministic identities and versioned
source assertions. Closed JSON Schema validates structure; Python validates
references, labels, identifiers, dates and selected semantic rules. No inferred
ownership, vulnerability or ATT&CK mapping from mere co-occurrence.

## Files / components modified

- [Graph ontology and handoff](../../../knowledge-graph/README.md)
- [Offline validator](../../../rag/graph/validate.py)
- [Schema tests](../../../tests/knowledge_graph/test_schema.py)
- [Semantic tests](../../../tests/knowledge_graph/test_semantics.py)
- [ADR-003](../../adr/ADR-003.md)
- CI includes the offline graph suite.

## Tests / validation

User-supplied transcript: Docker build and Ruff passed; 22 graph tests, 20
contract tests and 44 ingestion tests passed. Both example CLI validations passed.
Integrity failed before file checks because Git is absent from the dev image; use
the corrected host command in the [verification guide](../../../knowledge-graph/validation/VALIDATION.md).
The checked diff had no whitespace errors. No assistant test rerun, CI pass or
Neo4j execution is claimed.

## Results / metrics

86 user-executed tests passed: graph 22 (0.394s), contracts 20 (0.471s),
ingestion 44 (3.517s). Minimal example: 9 nodes / 9 relations; lab example:
7 nodes / 5 relations. Evidence is the user transcript linked in the guide;
results refer to the tested working tree, with no immutable commit provided.

## Problems encountered

Current ATT&CK ingestion omits malware objects; some relation endpoints cannot
resolve. Incident entity roles are absent. Source-local scopes avoid unsupported
merges. Production ETL must apply existing split policies before graph creation.

## Decisions made

Proposed ontology v1, documented canonical identity keys, per-record assertions,
self-contained batches, atomic indicators and deferred extra entity types.
Approval is pending; ADR-003 remains Proposed.

## Related Issues / Pull Requests

[S3-T01 #24](https://github.com/CyberSOC-ai/cybersoc-ai/issues/24).
Downstream: [S3-T02 #25](https://github.com/CyberSOC-ai/cybersoc-ai/issues/25).
PR not created. Issue remains open pending verification and delivery requirements.

## Learning outcome

Prepared material covers node/relationship semantics, stable identities, provenance
and ETL handoff. Achraf/Ahmed walkthrough and demonstrated verification are pending.


# 5. Oussama
## Assigned tasks

S3-T03, S3-T07

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

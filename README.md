# CyberSOC AI

Current local implementation (13 November 2026): shared-v1 No-RAG, backend
foundations and a fresh standalone Vector RAG pipeline are available. Prior
pilot implementations remain retired.
See [cleanup progress](docs/data/cleanup-reset.md) and [data workflow](docs/data/workflow.md).


Intelligent Cybersecurity SOC Assistant — Master Project 2026. This is the living consolidated final report required by [CDC v2.2](docs/CDC.md).

**Deadline:** 01 January 2027. **Status:** Baseline-first roadmap reset; B0 delivery pending.

Current execution: [baseline-first roadmap](docs/ROADMAP.md) · [GitHub roadmap](https://github.com/CyberSOC-ai/cybersoc-ai/issues/94). Ahmed delivers shared foundation, No-RAG and small complete Vector RAG before the downstream handoff. All later assignments are left for Ahmed. Original sprint journals preserve contribution history.

## Local pipeline handoff

| Area | Start here | Owns |
|---|---|---|
| No-RAG | [ai/no_rag](ai/no_rag/README.md) | Incident-only execution, prompt and evaluation |
| Vector RAG | [rag/vector](rag/vector/README.md) | Preparation, retrieval, reference context and evaluation |
| Data | [datasets](datasets/README.md) | Downloads, source additions, licenses, immutable releases and reuse |
| Shared runtime | [ai/runtime](ai/runtime/README.md) | Model/server setup, transport, contracts and proposal policy |

On a new machine, obtain the reviewed source revision, follow runtime setup and
restore the pinned source release, then run No-RAG before preparing/restoring RAG.
The guides provide explicit setup/run/check/restore steps. Large payloads remain
outside Git. Current layout identity: `local-layout-v2`; historical seven-case
scores retain their original source identities. Kaggle support, fresh-environment
reproduction and full B0 handoff remain pending.

## Project overview

> To be completed from validated sprint evidence.

## Objectives

> To be completed from validated sprint evidence.

## Architecture

> To be completed from validated sprint evidence.

## SOC Lab

> To be completed from validated sprint evidence.

## Models

> To be completed from validated sprint evidence.

## RAG

[Vector RAG](rag/vector/README.md) provides verified source preparation, pinned
BGE-small embeddings, persistent Qdrant retrieval, snapshot recovery and bounded
local generation. Its [evaluation](rag/vector/EVALUATION.md) separates retrieval
integrity from answer quality. Backend integration and complete B0 acceptance
remain pending.

## Knowledge Graph

> To be completed from validated sprint evidence.

## Agentic AI

> To be completed from validated sprint evidence.

## LLM Security

> To be completed from validated sprint evidence.

## Inference Optimization

> To be completed from validated sprint evidence.

## LLMOps

> To be completed from validated sprint evidence.

## Web Application

> To be completed from validated sprint evidence.

## Experiments

> To be completed from validated sprint evidence.

## Results

> To be completed from validated sprint evidence.

## DevSecOps workflow

Issue → Ready → branch → implementation → tests → Pull Request → CI passes → merge → sprint documentation → Done. Request the assigned reviewer; approvals are advisory. If the reviewer is unavailable, record that in the PR and the author may merge after checking the changes and confirming CI passes. The full merge policy is in [CDC §11.3](docs/CDC.md#113-pull-request-flow), and the Definition of Done is in [CDC §14](docs/CDC.md#14-definition-of-done).

## No RAG baseline

[The No-RAG folder](ai/no_rag/README.md) contains the implementation, setup/run
guide, [seven-case evaluation record](ai/no_rag/EVALUATION.md) and
[improvement plan](ai/no_rag/IMPROVEMENTS.md). The evaluation record includes
actual prompts and outputs with blank reviewer worksheets; it does not declare
an overall quality pass.

## Reproducibility

[Development setup and checks](docs/development.md): Docker prerequisites, build and test commands, configuration, secret scanning and troubleshooting.

[Shared development data — shared-dev-v1](docs/data/shared-dev-v1.md): Google Drive download, release hashes, incident/reference/evaluation boundaries and versioning. [ADR-006](docs/adr/ADR-006.md) records the storage decision. This is initial development data; B0 acceptance remains pending.

> To be completed from validated sprint evidence.

## Team

Ahmed · Soulaiman · Anas · Achraf · Oussama

## Final demo

> To be completed from validated sprint evidence.

## Conclusions

> To be completed from validated sprint evidence.

## Sprint documentation

[Current revised-stage journals](docs/sprints/README.md). The Sprint 0–8 links below are historical execution records; their old owners/status tables do not assign current work.

- [Sprint 0](docs/sprints/sprint-00/README.md)
- [Sprint 1](docs/sprints/sprint-01/README.md)
- [Sprint 2](docs/sprints/sprint-02/README.md)
- [Sprint 3](docs/sprints/sprint-03/README.md)
- [Sprint 4](docs/sprints/sprint-04/README.md)
- [Sprint 5](docs/sprints/sprint-05/README.md)
- [Sprint 6](docs/sprints/sprint-06/README.md)
- [Sprint 7](docs/sprints/sprint-07/README.md)
- [Sprint 8](docs/sprints/sprint-08/README.md)

The [Sprint 1 backend API](backend/README.md) documents loopback startup, strict incident ingestion, SQLite storage and the pending baseline-runner interface.

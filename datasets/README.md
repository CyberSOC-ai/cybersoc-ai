# S0-T05 — Data, knowledge-source and benchmark inventory

Owner: Oussama · Reviewer: Anas · Date: 2026-10-13 · [Issue #5](https://github.com/CyberSOC-ai/cybersoc-ai/issues/5)

Status: inventory prepared for review; no datasets, feeds, model weights or benchmarks downloaded or executed.
Authority: [CDC §§8–9 and Sprint 0](../docs/CDC.md), [architecture](../docs/architecture/README.md) and [SOC Lab plan](../infrastructure/soc-lab/README.md).

- [Source inventory, licensing and evaluation-case requirements](SOURCES.md)
- [SLM shortlist, memory estimates and hardware gates](MODELS.md)

This inventory supplies S0-T06, S1-T02, S2-T01, S2-T08 and S3-T01. Exact schemas come from S0-T03; metric/version conventions from S0-T06; collection and evaluation execution from S1 onward. This branch is independent of the S0-T03 branch and does not assume its files have merged.

## Storage and provenance rules

Git stores documentation, small sanitized fixtures and references. Shared artifact storage (ADR-006, still proposed) stores raw logs, PCAPs, feed snapshots, larger datasets, weights and benchmark outputs under access controls. No storage provider is selected here.

Every acquired snapshot must record source ID, official URL, upstream release or immutable revision, acquisition UTC time, SHA-256, format/schema version, original license/notice reference, usage restrictions, owner and artifact reference. Preserve original notices alongside derived datasets and normalized records. Model manifests additionally pin model/tokenizer revision, quantization source, runtime and configuration. An inventory entry is not proof of authenticated access, redistribution permission or download integrity.

Sanitize before ingestion, prompting, tracing and sharing. Never commit sensitive raw logs, credentials or giant collections. Treat retrieved content as untrusted data; provenance permits investigation of poisoning but does not prove trustworthiness. Keep frozen test incidents, labels, near-duplicate runs and their derived records out of retrieval/fine-tuning corpora. Test labels remain evaluator-only.

## Acceptance evidence and handoff

| Issue deliverable | Evidence | Downstream owner / task |
|---|---|---|
| MITRE/CVE/CWE and actual planned threat-intel feed | SOURCES.md knowledge/feed tables, intended ThreatFox ingestion and fallback conditions | Ahmed / S2-T01, S2-T08 |
| SOC-log sources | SOURCES.md lab-source map and leakage exclusions | Ahmed / S1-T06, S2-T01 |
| Candidate SOC datasets and evaluation cases | SOURCES.md candidate table and label requirements | Anas / S1-T02 |
| Licensing and usage notes | Official source/terms links and per-source acquisition gates | Each consuming task owner |
| Qwen/Phi/other compact model shortlist | MODELS.md license, size, estimated memory and hardware gates | Soulaiman / S1-T03, ADR-002 |
| Versioning and ontology inputs | Provenance/split requirements and entity coverage | Anas / S0-T06; Ahmed / S3-T01 |

Validation: checked coverage against all five issue deliverables and CDC S0-T05; inspected official source/model pages on 2026-10-13; local Markdown links and whitespace checked with the existing repository checks after staging. No live feed-access, GPU-fit, parser, performance or model-quality test is claimed. This documentation task does not add application tests that would merely assert its text.

Remaining gates: actual GPU capacity, authenticated feed access and allowed derived/snapshot use, artifact storage, chosen source/model revisions, lab collection, reviewed labels and split protocol. Peer review, authorized PR, CI, merge and issue closure remain pending; the issue must not be called Done from this inventory alone.

## Partial requirements reviewed — 2026-10-14

The source inventory names ThreatFox, but authenticated access and allowed
snapshot/derived/publication use are still unverified. SOURCES.md now lists each
outstanding check, owner and required evidence. The model shortlist records
licenses and weight estimates; available team GPU capacity and actual runtime
fit are still unverified for every candidate. MODELS.md now separates calculated
weight storage, additional memory components and future compatibility evidence.
Neither partial requirement is upgraded to complete by documenting its gap.
No models/datasets were downloaded and no benchmarks were run.

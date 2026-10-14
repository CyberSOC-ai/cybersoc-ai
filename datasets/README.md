# S0-T05 — Data, knowledge-source and benchmark inventory

Owner: Oussama · Reviewer: Anas · Date: 2026-10-13 · [Issue #5](https://github.com/CyberSOC-ai/cybersoc-ai/issues/5)

Status: inventory prepared for review; no datasets, feeds, model weights or benchmarks downloaded or executed.
Authority: [CDC §§8–9 and Sprint 0](../docs/CDC.md), [architecture](../docs/architecture/README.md) and [SOC Lab plan](../infrastructure/soc-lab/README.md).

- [Source inventory, licensing and evaluation-case requirements](SOURCES.md)
- [SLM shortlist, memory estimates and hardware gates](MODELS.md)

This inventory supplies S0-T06, S1-T02, S2-T01, S2-T08 and S3-T01. Exact schemas come from S0-T03; metric/version conventions from S0-T06; collection and evaluation execution from S1 onward. S0-T03 contracts are now merged; this follow-up changes only S0-T05 documentation.

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

## Sprint 0 evidence update — 2026-10-14

The original inventory merged in [PR #73](https://github.com/CyberSOC-ai/cybersoc-ai/pull/73) at 2026-10-14 00:42:50 UTC, merge commit `aed2ee844a19d59bb92c665223fe554d0b029e7e`. Its [repository-checks CI job](https://github.com/CyberSOC-ai/cybersoc-ai/actions/runs/38491624307/job/115617906822) passed at 00:42:00 UTC. Anas was requested as reviewer; no submitted review was recorded when checked for this follow-up. Approval is advisory under CDC §11.3; feedback or reviewer unavailability must be handled under the DoD. These results apply to PR #73, not this follow-up.

[MODELS.md](MODELS.md) now records the user-supplied October 14 RTX 3050 Laptop measurements and assesses all four candidates at FP16, 8-bit and 4-bit, with explicit cache/runtime/headroom assumptions. This satisfies the documented Sprint 0 hardware-assessment scope; experimental fit remains unverified. No models, datasets or feeds were downloaded and no benchmarks were run. Final model selection remains ADR-002.

ThreatFox is the intended real feed for S2-T08. Its documented access/use requirements and source choice supply the Sprint 0 inventory; authenticated access verification, permitted snapshot/derived/sharing use, bounded acquisition and ingestion are **future Sprint 2 work**, owned by Ahmed. The six checks in [SOURCES.md](SOURCES.md) remain mandatory before ingestion, not mandatory live API tests for S0-T05. URLhaus has independent gates.

Other downstream gates remain artifact storage, immutable acquisition revisions, lab collection, reviewed labels and split protocol. Issue #5 stays open pending [follow-up PR #74](https://github.com/CyberSOC-ai/cybersoc-ai/pull/74), its [CI checks](https://github.com/CyberSOC-ai/cybersoc-ai/pull/74/checks), reviewer handling, approved merge and explicit closure. No experiment metadata or measured-fit claim is created by a documentation assessment.

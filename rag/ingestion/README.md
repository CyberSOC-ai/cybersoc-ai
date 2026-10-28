# S2-T01 — Reproducible knowledge ingestion

Owner Ahmed; reviewer Soulaiman; [issue #16](https://github.com/CyberSOC-ai/cybersoc-ai/issues/16).
Python 3.12 in the existing development image. No new dependencies are required.

The pipeline turns pinned ATT&CK, NVD, CWE and normalized SOC snapshots into
validated JSONL records and a reproducibility manifest. Acquisition is a separate,
explicit command. Normalization and all CI tests work offline. Embeddings,
chunking, vector-store choice and indexing belong to S2-T02.

## 1. Prepare the environment and artifact mount

From the repository root:

```sh
docker compose build dev
mkdir -p .local/ingestion
```

The source mount stays read-only. Each command below adds a writable artifact
mount for generated files. `.local/` is ignored by Git. Preserve these snapshots
and receipts; team artifact storage is still undecided in ADR-006. Do not treat
this machine's local artifact path as shared storage.

## 2. Acquire versioned public snapshots

```sh
docker compose run --rm -T -v "$PWD/.local/ingestion:/artifacts" dev python -B -m rag.ingestion.acquire --source mitre_attack --version c2494b29dd268c46a5d0ea0990553e4327cd2253 --output /artifacts/attack
docker compose run --rm -T -v "$PWD/.local/ingestion:/artifacts" dev python -B -m rag.ingestion.acquire --source cve --version CVE-2021-44228 --output /artifacts/cve
docker compose run --rm -T -v "$PWD/.local/ingestion:/artifacts" dev python -B -m rag.ingestion.acquire --source cwe --version 5.0 --output /artifacts/cwe
```

These commands deliberately cover the Enterprise ATT&CK snapshot, one CVE for
smoke validation, and one CWE release. One CVE demonstrates the adapter, not broad
vulnerability coverage. The offline NVD adapter also accepts larger bounded JSON
2.0 snapshots. Define the relevant CVE subset before expanding the corpus.

ATT&CK pins an upstream Git commit. CWE pins a numeric release, catalog version
and supported XML namespace/schema version (CWE 7 or 8). CWE parsing validates
the consumed fields, not the full upstream XSD. NVD responses are mutable: the
manifest pins the acquired response SHA-256 as part of its version. Reacquisition
can change bytes; exact replay requires the retained original snapshot.

Acquisition writes the original snapshot, preserved notice, manifest and receipt;
CWE also retains the original ZIP and its hash. It uses fixed official providers,
TLS verification, no redirects, a 128 MiB body limit, per-operation timeouts and a
180-second streaming deadline checked between reads. The network read timeout
bounds a stalled read. A notice request failure publishes no snapshot. There is
no crawling, API key requirement for this single-CVE request, or advisory/payload
download. Respect upstream usage limits when acquiring additional records.

The sources and usage requirements come from [the inventory](../../datasets/SOURCES.md).
Official format references: [ATT&CK STIX](https://github.com/mitre-attack/attack-stix-data),
[NVD JSON API](https://nvd.nist.gov/developers/vulnerabilities) and
[CWE downloads](https://cwe.mitre.org/data/downloads.html). Preserve the acquired
notices and source attribution with all derived corpora. Retrieved prose remains
untrusted input regardless of source or hash.

## 3. Normalize offline

```sh
docker compose run --rm -T -v "$PWD/.local/ingestion:/artifacts" dev python -B -m rag.ingestion --input /artifacts/attack/snapshot.json --snapshot /artifacts/attack/snapshot-manifest.json --notice /artifacts/attack/notice.txt --output /artifacts/attack-corpus
docker compose run --rm -T -v "$PWD/.local/ingestion:/artifacts" dev python -B -m rag.ingestion --input /artifacts/cve/snapshot.json --snapshot /artifacts/cve/snapshot-manifest.json --notice /artifacts/cve/notice.txt --output /artifacts/cve-corpus
docker compose run --rm -T -v "$PWD/.local/ingestion:/artifacts" dev python -B -m rag.ingestion --input /artifacts/cwe/snapshot.xml --snapshot /artifacts/cwe/snapshot-manifest.json --notice /artifacts/cwe/notice.txt --output /artifacts/cwe-corpus
```

Every input and source notice must match its manifest hash. Output directories
must be new. The pipeline validates all records before renaming a staged corpus
directory into place; malformed input never publishes a partial corpus. It never
overwrites an earlier corpus during ordinary sequential use. Do not run concurrent
writers against the same output path.

For each corpus:

| File | Meaning |
|---|---|
| `records.jsonl` | Canonical UTF-8 records, sorted by stable record ID |
| `manifest.json` | Input/output hashes, implementation/schema hashes, counts and exclusions |
| `snapshot.json` | Exact input snapshot manifest |
| `source-notice.txt` | Byte-preserved acquired notice |
| `soc-policy.json`, `splits.json` | Exact SOC policy/split inputs when applicable |

The acquisition snapshot itself stays in its original local artifact directory.
Replaying the same snapshot, provenance, policy and implementation produces
identical JSONL and manifest bytes. Acquisition timestamps are input provenance;
the normalizer does not add a fresh wall-clock timestamp to each replay.

## 4. Prepare the eligible SOC history

Read [the development assignments](../../datasets/knowledge/SOC_ASSIGNMENTS.md)
before expanding the corpus. The supplied policy covers the two existing real
LAB-01 observations, linked to the pilot's `G-SSH` family. It is a proposed
development assignment for review, not a claim of a frozen test set.

```sh
docker compose run --rm -T -v "$PWD/.local/ingestion:/artifacts" dev python -B -m rag.ingestion.prepare_lab --output /artifacts/soc --acquired-at 2026-10-28T23:34:26Z
docker compose run --rm -T -v "$PWD/.local/ingestion:/artifacts" dev python -B -m rag.ingestion --input /artifacts/soc/snapshot.json --snapshot /artifacts/soc/snapshot-manifest.json --notice /artifacts/soc/notice.txt --soc-policy datasets/knowledge/soc-policy.json --splits datasets/evaluation/soc-eval-v1/splits.json --output /artifacts/soc-corpus
```

The timestamp above reproduces the validation snapshot's preparation metadata.
When preparing a new snapshot, supply its actual UTC preparation time. This is
distinct from original event timestamps and does not invent missing lab metadata.

The policy pins the exact split file and canonical sanitized incident digests.
Unknown records are quarantined. Test/quarantined assignments, held-out groups,
related test case IDs and policy-held-out runs are excluded. New or changed splits
invalidate the hash and require reviewing assignments again. The current pilot
has `test_frozen=false`, so SOC outputs explicitly declare `development_only`.
No evaluation labels or expected actions are loaded. Input must satisfy the
strict incident v1 schema; extra evaluator fields fail validation. Manual review
is still required for sensitive prose and correct near-duplicate grouping.

## 5. Handoff to S2-T02

The [record schema](schemas/record.schema.json) is the proposed ingestion contract.
The [snapshot schema](schemas/snapshot.schema.json) and
[SOC policy schema](schemas/soc-policy.schema.json) are independently versioned
under ingestion v1; existing backend interchange schemas are unchanged.

| Field | Downstream use |
|---|---|
| `record_id` | Stable hash of source and source record ID; document upsert identity |
| `content_sha256` | Detect changed normalized text; snapshot hash tracks all input changes |
| `collection` | Keep `knowledge` and `soc_history` separate |
| `title`, `content` | Input for Soulaiman's chunking/embedding strategy |
| `source`, `source_record_id`, `snapshot_ref` | Preserve into retrieval evidence and citations |
| `provenance` | Source URL/revision/time, raw snapshot hash, notice and usage references |
| `metadata` | Technique IDs, CVE enrichment, CWE relationships, or SOC lineage/split |

Do not concatenate lineage, split membership or evaluator metadata into model
context. ATT&CK includes active techniques and relationships; other STIX object
types are counted as excluded. Some relationship endpoints refer to upstream
objects outside this corpus; this is not a complete graph export. Revoked/
deprecated techniques and relationships to inactive endpoints are excluded.
CVE CVSS/CWE/CPE enrichment is preserved only when supplied; missing fields stay
missing. CWE categories, views and groupings are excluded from weakness records.

Soulaiman must derive bounded chunks and chunk IDs, choose an embedding model
and store through ADR-001, and supply real retrieval scores/methods at query time.
The v1 evidence contract limits each content item to 16,000 characters; documents
here may be larger and must be chunked. Preserve `source_record_id` and
`snapshot_ref` for every chunk. Ingestion does not fabricate retrieval scores or
claim retriever quality.

## 6. Validation and review

```sh
docker compose run --rm -T dev ruff check --no-cache .
docker compose run --rm -T dev python -B -m unittest discover -s tests/ingestion -v
```

CI includes this offline suite alongside all existing project suites. Tests
cover deterministic replay, malformed input, duplicate IDs, required provenance,
notice/snapshot tampering, optional enrichment, both CWE namespaces, XML entity
rejection, redirects, acquisition bounds, atomic publication and SOC exclusions.
They use synthetic parser fixtures and mocked HTTP; real-source smoke evidence
is recorded separately in [the validation record](../../datasets/knowledge/VALIDATION.md).

Before Done: review the proposed record/policy interface with Soulaiman, resolve
feedback, pass hosted CI, merge the reviewed PR and close issue #16 through the
project workflow. Local checks are not hosted CI or independent peer approval.

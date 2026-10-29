# S2-T02 local validation record

Date: 2026-10-29. Owner: Soulaiman. Assigned reviewer: Ahmed.
[Issue #17](https://github.com/CyberSOC-ai/cybersoc-ai/issues/17).
Local implementation is verified and submitted for review on the task branch.
Hosted CI and reviewer approval are recorded on the linked PR; local validation
does not imply approval, merge or issue closure.

## Delivered behavior

- Offline hash-verified BGE model acquisition and pinned CPU environment.
- Source-preserving token-aware chunks, stable IDs, explicit quality decisions.
- Real normalized float32 384-dimensional CLS embeddings in bounded batches.
- Persistent Qdrant knowledge/SOC collections with provenance and typed filters.
- Receipt/config/model/policy validation, full point readback and overwrite refusal.
- Query encoding, filters before top-K, global cosine merge, closed cited evidence.
- Explicit no-match/error behavior, stale-state rejection and reader reload checks.

## Validation corpus

| Source | Input records | Stored points |
|---|---:|---:|
| CVE | 100 | 106 |
| CWE | 100 | 101 |
| ATT&CK | 100 | 138 |
| Sigma | 3 | 3 |
| Playbook | 2 | 21 |
| SOC history | 35 | 37 |
| Total | 340 | 406 |

The knowledge collection has 369 points; SOC history has 37. All prepared SOC
records, Sigma rules and playbooks are represented. Knowledge coverage is a
bounded subset of the acquired corpus. Manifests preserve `limit_per_source=100`
and `development_only`; no frozen-test independence or gold-label quality result
is implied. Reviewer acceptance must consider the downstream corpus needs.

## Evidence identities

- BGE model/tokenizer revision: `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`.
- Weight SHA-256: `3c9f31665447c8911517620762200d2245a2518d6e7208acc78cd9db317e21ad`.
- Chunk manifest SHA-256: `505cac307f237c321b44a539f821cb0fddf04e0a881cea7efc11fdd5bdb67417`.
- Embedding manifest SHA-256: `891932d107769f43b9618f90892bd69eadfa4533d80314d4a64a0b33163c6200`.
- Index receipt SHA-256: `e438308b135bddfd3d6c87187ad3fccf84436c367dfec6663cb9191b5f5dc35c`.
- Index build: `966d3cf2c8339ea02ba4487ff525f8bd33d0e6381ca205fb2e0fd7f5fb1fe9ed`.

Local artifact directories are `.local/s2t02/step9-chunks-pilot`,
`.local/s2t02/step9-embeddings-pilot`, and
`.local/s2t02/final-index-validation`. Receipt-linked point spools and output
hashes permit readback validation. Data, weights and outputs stay outside Git.
The source was an uncommitted task branch based on
`5c56f928dc5c4e20958733f6b4c147fc75909632`; implementation digests accompany builds.

## Final checks

All **220 tests** passed: 50 vector, 20 contract, 43 evaluation, 20 backend,
16 normalizer, 44 ingestion and 27 baseline tests. Ruff passed. CPU embeddings
were reproduced byte-for-byte.

The evaluator preparation command was exercised against the verified local
corpus/model and saved chunks/vectors. It created new collections, verified all
406 points and wrote a ready receipt. Two offline tests additionally cover input
linking and refusal of partial reuse/existing outputs. See the
[evaluator setup guide](EVALUATOR_SETUP.md) for a rebuild independent of these
private local paths.

For the final 406-point index, every payload/vector matched its verified spool.
All 380 positive filter-value checks passed, along with negative source/snapshot/
split/freeze checks and filtered stored-vector queries. Recreating only Qdrant's
container retained the named-volume data and settings. Both downloaded snapshots
were checksum-verified and recovered into fresh collections; all 406 recovered
points, payloads and settings matched. Original collections remained intact.

Real query checks covered SOC-only, playbook-only, Sigma-only and combined search,
an unmatched snapshot, token overflow, repeated exact queries and reconstruction
from persisted artifacts. Responses passed the closed retrieval-response schema
and preserved request/trace IDs. Returned metadata was limited to evidence fields;
administrative lineage was not appended. Results are saved locally as
`final-retrieval-validation.json`, `final-before-recreate.json`,
`final-after-recreate.json`, `final-snapshot-validation/manifest.json` and
`final-tests-<suite>.txt` under `.local/s2t02/`.

## Limits and scope

Issue #17 does not explicitly require a GPU, cloud execution or all-record
encoding. Full corpus chunking was completed as additional
evidence (164,793 records -> 174,883 passages); full-corpus vectorization was not
run and is not presented as a requirement already agreed with the reviewer.

This index is below Qdrant's HNSW threshold and uses full scans. ANN-scale
performance, gold-label Recall@K/Precision@K/MRR and answer quality are not measured
here. S2-T03 owns relevance evaluation, S2-T04 generation and S2-T05 API routes.
Formal Done still requires applicable CI, review and issue/PR workflow.

# Incremental preparation with preserved index versions

The pipeline can reuse verified chunks and embeddings from a previous prepared
release. It publishes a **new** pair of knowledge/SOC Qdrant collections and a new
`READY.json`. Previous collections, receipts, chunks and vectors remain untouched.
This is explicit batch preparation, not a background watcher or in-place update.

## Input and reuse rules

Supply a **complete desired S2-T01 corpus release** containing the old records you
still want plus additions/updates. A file containing only new records is not an
append instruction: records absent from the supplied selection will be absent
from the new version. Normalize/deduplicate/compose inputs using ingestion first.

- Unchanged body and reference header: reuse passage boundaries and token counts.
  Regenerate record-bound IDs, provenance, quality flags and filters from the new
  record. Snapshot or metadata changes therefore cannot leave stale citations.
- Changed body/header or new record: chunk that record normally.
- Exact embedding text seen previously under the same model/runtime: reuse its
  vector, even when its citation/record-bound ID changed. New or changed embedding
  text is encoded in bounded batches. Identical new texts are encoded once per
  preparation. A completely cached update does not load the inference model.
- Removed or newly excluded records: omit their passages from the new version.
- Chunking configuration or embedding model/runtime changes: refuse incremental
  reuse; start a fresh build without the previous-release flags.

All input records, including those outside a preview limit, are still validated
against the corpus hash, source notices and current SOC policies/splits. Historical
policy bytes may differ for cache input; they never authorize the new output.
Ineligible records in the new corpus are rejected, not silently accepted from the
cache. Recompose ingestion after policy changes before preparing an update.

The previous READY hash pins its index receipt, which pins chunk/vector manifests;
the chunk and vector streams are checked in full before their cached work is used.
Reuse requires matching model file identities and pinned dependency-file digests.
Temporary SQLite caches bound Python memory and are removed on success/failure.
Allow disk space for those caches, the new artifacts and both database versions.

## Prepare an updated version

Use the same model, CPU image, Qdrant service and `/artifacts` mount described in
[the evaluator setup guide](EVALUATOR_SETUP.md). Keep all paths referenced by the
old READY and manifests accessible under the same container layout.

Example PowerShell, after creating the new approved corpus under
`.local/rag-eval/corpus-release-v2/corpus/`:

```powershell
$previousSha = (Get-FileHash .local/rag-eval/achraf-01/READY.json -Algorithm SHA256).Hash.ToLowerInvariant()
$qdrantId = docker compose --profile vector ps -q qdrant
docker run --rm --network "container:$qdrantId" `
  --mount "type=bind,source=${PWD},target=/workspace,readonly" `
  --mount "type=bind,source=${PWD}/.local/rag-eval,target=/artifacts" `
  cybersoc-rag-eval python -B -m rag.vector.prepare `
  --corpus /artifacts/corpus-release-v2/corpus --model /artifacts/model `
  --output /artifacts/achraf-02 `
  --previous-ready /artifacts/achraf-01/READY.json --previous-ready-sha256 $previousSha
```

With previous-release flags, the selection limit is inherited from the previous
manifest. Without them, the default remains 100 records per source. Explicitly
use `--limit-per-source N` to change bounded coverage, or `--all-records` to select
the complete corpus. Expanding beyond the previous coverage requires computing
the additional chunks/embeddings; incremental reuse is not a substitute for the
first full embedding run. `--reuse-chunks/--reuse-vectors` remain exact-release
reuse and cannot be combined with incremental flags.

Inspect the new READY's `incremental` section for reused-span records/chunks,
rechunked records, previously chunked records removed from the selection, unique
texts encoded, vectors reused (including duplicates within this run), parent
hashes and publication mode. These counters describe work, not retrieval quality.

Each version still writes complete chunk/vector artifact streams and uploads all
selected points to its new Qdrant collections. Database loading and verification
therefore remain proportional to corpus size. This design saves token splitting
and model inference; it does not implement storage-level delta updates or snapshots.

## Use, failure handling and rollback

Switch a consumer by opening `Retriever` with paths/hashes from the new READY,
using the example in the evaluator guide. There is no automatic global active
pointer or shared-server deployment. A previous reader remains bound to its old
collections and can continue to read them if its eligibility policy remains valid.
Rollback means reopening the previous READY; an outdated SOC policy is still
rejected rather than overridden for rollback.

Existing output directories and collection names cannot be overwritten. A failed
update does not publish a READY. Completed intermediate files and unready new
collections may remain for inspection; the old version is not changed or deleted.
An entirely empty selection is refused, as in the original pipeline; this command
does not erase the old index when all records are removed.
Use a new output directory for a retry. No automatic retention/garbage collection
is implemented. Keep evaluation corpus/index identities fixed while measuring
Recall@K, Precision@K or MRR; an update starts a new experiment version.

See [the local validation record](INCREMENTAL_VALIDATION.md) for automated checks
and the controlled real-model update/reload results.

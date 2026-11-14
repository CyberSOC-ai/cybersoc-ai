# Data releases and source additions

This folder owns how source data is acquired, reviewed, normalized, versioned and
handed to the investigation pipelines. It is the authoritative workflow for adding
references, incidents and evaluator labels. Model/runtime setup belongs to
[ai/runtime](../ai/runtime/README.md); index preparation and retrieval belong to
[Vector RAG](../rag/vector/README.md).

## Start with the current release

Only `shared-dev-v1` is active: seven synthetic normalized incidents, 21 reference
documents and 21 retrieval questions with draft judgments. These are development
examples, not production/customer logs or untouched final tests. Download and
verify the source ZIP using [SHARED_DEV_V1.md](SHARED_DEV_V1.md). That guide contains
the approved file links, exact ZIP/manifest hashes and extraction commands.

```text
datasets/
  README.md              Source-addition and release workflow
  SHARED_DEV_V1.md        Current source download and verification
  SOURCES.md, MODELS.md   Historical research inventories, not active selections
  staging/               Proposed additions; local and ignored
  releases/
    shared-dev-v1/       Verified frozen source; local and ignored
    shared-dev-v2/       Example future release; not currently created or active
```

Git contains source/configuration, instructions and release identities. Large
source payloads, model weights, prepared indexes and run bundles belong in the
approved artifact store. Google Drive is selected for B0 in
[ADR-006](../docs/adr/ADR-006.md). Downloads must match recorded hashes; filenames
or Drive links alone do not establish immutable content. The last recorded folder
sharing check was 11 November 2026 and showed Editor access. It has not been
rechecked or changed in this task. Source-specific sharing rights remain separate.

## Three boundaries

| Release area | Contents | Consumer |
|---|---|---|
| `knowledge/` | Reference text, source snapshots, provenance and notices | RAG preparation only |
| `incidents/inputs/` | Observable normalized incident facts and supplied business context | Both investigation modes |
| `evaluation/` | Expected labels, required facts, retrieval judgments and solutions | Evaluator only |

References explain event meaning and possible behavior; they cannot authenticate
a private approval or prove a host was compromised. Expected answers and held-out
incident material must never be indexed. Previous case solutions are not a
reference library for evaluating those same cases. Historical SOC examples need
explicit eligibility, group separation and rights review before retrieval use.

No-RAG currently reads only the seven inputs pinned to v1. RAG preparation reads
only declared knowledge files. Generation reads incidents, fixed policy and sealed
retrieval packets. Only the explicit retrieval-evaluation command reads judgments.
Never point a generic recursive loader at the entire release directory.

## Add a new source, step by step

### 1. Propose a useful source

Identify a concrete knowledge gap: an unsupported event type, relevant advisory,
platform configuration or response procedure. Prefer the original publisher,
vendor documentation and reviewed operational guidance. Record the purpose and
which question the reference can answer. Avoid collecting unrelated volume.

Create a new local staging directory; do not write into a frozen release:

```sh
mkdir -p datasets/staging
mkdir datasets/staging/source-proposal-01
```

For each source, record its publisher, original/resolved URL, retrieval time,
upstream version/revision, source format, stable document ID, extraction method,
license/terms, preserved notices and intended usage/access. Review privacy and
sharing eligibility before acquisition or upload. A publicly readable page is not
a blanket redistribution license. Preserve a source snapshot and hashes; a URL
alone cannot reproduce changing content.

### 2. Normalize through a reviewed adapter

Convert HTML/PDF/JSON/CSV into readable factual text with a stated extraction
method. Preserve qualifiers, table meaning, affected-version conditions and
paragraph boundaries. Do not silently summarize, translate or discard context.
If automatic extraction changes, give that method a new version and review samples.

The current RAG consumer accepts this release format:

```json
{"document_id":"DOC-EXAMPLE-GUIDE","title":"Example vendor guide","source_url":"https://example.invalid/guide","content":"Verified extracted reference text."}
```

Store one record per line in `knowledge/records.jsonl`. Its paired entry in
`knowledge/sources.json` records at least the following existing fields:

```json
{
  "document_id": "DOC-EXAMPLE-GUIDE",
  "source_url": "https://example.invalid/guide",
  "snapshot": "knowledge/snapshots/DOC-EXAMPLE-GUIDE.source",
  "snapshot_sha256": "<SHA-256 of original bytes>",
  "text": "knowledge/text/DOC-EXAMPLE-GUIDE.txt",
  "text_sha256": "<SHA-256 of extracted UTF-8 bytes>",
  "usage": {"status": "<review status>", "label": "<terms>", "notices": []}
}
```

These are illustrative records, not valid hash fixtures. Preserve the full
provenance fields used by v1, including extraction description, upstream metadata,
retrieval time, resolved URL and release/access status. The extracted text file
must equal the record's `content` exactly. Declare every consumed text/snapshot
file in the release manifest with matching SHA-256.

New upstream formats need an explicit acquisition/extraction adapter; there is no
implemented general crawler or automatic release publisher. Review source-category
mapping too: the current consumer recognizes ATT&CK/CVE/CWE identity conventions
and maps other operational documents to `playbook`. That category is reference
metadata, not permission to execute a response. A new source type may need a
reviewed mapping/schema change rather than inventing a label or forcing its format.

### 3. Deduplicate and separate evaluation

Keep a stable ID for the same logical document across revisions, but record new
content hashes when its bytes/text change. Never reuse an ID for a different item.
Deduplicate exact content and review near-duplicates, mirrors and multiple versions;
otherwise retrieval can be dominated by copies of the same explanation. Record
which version supersedes another and why it is included or excluded.

Normalize new incidents against `backend/contracts/v1/incident.schema.json`.
Document whether each is synthetic, lab-recorded or real, its provenance, supplied
context and privacy handling. Keep original observations separately when permitted;
do not invent missing actor, approval or exploitation facts. Build evaluator labels
and rationales in `evaluation/`, with evidence and review status. Preserve the
source dataset's original label meaning before any agreed mapping.

Split by related scenario/incident groups, not individual log rows. Reserve held-out
groups before prompt/retrieval tuning. A case already used for development cannot
be relabeled as an untouched final test. Future attack examples need benign and
uncertain controls; ATT&CK resemblance is not proof of malicious intent.

### 4. Create a new complete source release

After review, assemble `shared-dev-v2` in a new destination. Keep v1 unchanged.
Include unchanged eligible material plus accepted additions/corrections. Record:

- New release ID and format/contract version.
- Predecessor release ID and manifest hash.
- Added, changed and removed item IDs, with reasons.
- File paths, byte lengths and SHA-256 values in `manifest.json`.
- Counts, source/label review status, splits and access restrictions.
- Agreement/versioning notes and `SHA256SUMS` for the release payload.

Validate the complete asset inventory, safe paths, uniqueness, checksums, schemas,
record/text/snapshot equality, source notices and evaluator separation. Review
representative extracted text manually. The existing consumers enforce their own
boundaries; they are not a substitute for a complete source/rights review.

Package the release with a separate archive checksum and publish only to an
approved destination after sharing eligibility is resolved. Do not overwrite an
old archive or extract v2 over v1. Announce the exact archive/manifest identity and
provide fresh-destination download/verification instructions like the v1 guide.
No new source release or external publication is performed by this refactor.

### 5. Explicitly activate the new release

For Vector RAG, copy `rag/vector/config.json` to a new trusted configuration and
change its `configuration_id`, `release_id` and `release_manifest_sha256`. Select
that configuration and restored release explicitly. Merely placing v2 beside v1
must not activate it. Retain the old configuration and all runs.

Review the proposal policy separately. Unchanged incidents can retain verified
annotations. A changed annotated incident requires a new hash-bound, reviewed
policy/configuration; do not auto-update permissions. New incidents without
annotations receive no eligible response targets. Fixed policy never comes from
retrieved/model text.

The No-RAG CLI deliberately still pins the v1 manifest and seven-case inventory.
Using new incidents there requires an explicit loader/version update and tests;
`--release` currently changes only where the same v1 bytes are located. This
limitation must be resolved before claiming a paired No-RAG/RAG evaluation on v2.
New source formats, contracts or runtime/model variants may require code changes;
not every future addition is a configuration-only operation.

## Prepare new artifacts without overwriting old ones

With a reviewed new RAG config/release, choose new output paths. In these launcher
examples `/artifacts` maps to `artifacts/local-inference/vector-v1` on the host;
the storage directory name does not select the source-release identity.

```sh
bash infrastructure/run-vector.sh build \
  --config rag/vector/configs/shared-dev-v2.json \
  --release datasets/releases/shared-dev-v2 \
  --reuse /artifacts/previous-build --output /artifacts/shared-v2-build
```

`configs/shared-dev-v2.json` and `previous-build` are future/example paths, not
artifacts shipped by this checkout. Use the actual compatible predecessor.
Reuse requires identical embedding inputs under the same model/tokenizer,
encoder implementation and library identities. Compatible unchanged inputs reuse
vectors; new/changed passages are embedded. Incompatible encoders fail rather than
mix vector spaces. Changed text can shift passage boundaries, so more than the
edited words may need re-embedding. Removal excludes the document from the new
snapshot without mutating the predecessor.

Publish to a new collection, evaluate retrieval with separately reviewed queries,
create new incident packets, preflight context and run generation using the
[Vector RAG commands](../rag/vector/README.md). Inspect retrieval failures, unknown
judgments, reference answerability, input preservation and citation usefulness.
Keep failed/abstained/unattempted cases in metric accounting. Never make new labels
fit a model's output or treat a valid source ID as proof that a claim is supported.

For a source-only change with no new incidents, compare modes on the same existing
inputs and disclose which knowledge changed. For new cases, complete compatible
loaders and evaluator labels for both modes first. Expand judgments before claiming
full precision; unjudged documents are not negative examples.

## Artifact handoff and future cloud execution

Keep derived passages/vectors, index snapshots, packets, models and run bundles
outside frozen sources. Each needs its own checksums and source/config/code/model
identities. To restore an index without document re-embedding, provide the complete
build directory, native Qdrant snapshot and sidecar, plus compatible runtime/model
configuration. Query embedding and new investigation generation still require
computation. Native snapshot compatibility must be checked on the receiving host.

Kaggle/Colab adaptation has not been implemented or tested. The intended next step
is a thin notebook calling repository modules, exporting versioned preparation
artifacts and results, then a verified local restore. Do not copy pipeline logic
into notebook cells or assume SDK-local Qdrant files are native server snapshots.
Start with v1; larger corpora need measured memory/disk/runtime bounds. The current
consumer caps documents/chunks and validates a small corpus; it is not a measured
large-scale ingestion service.

[SOURCES.md](SOURCES.md) and [MODELS.md](MODELS.md) preserve historical research,
not current acquisition authorization. Old datasets and reports remain historical
under `docs/history/reset-2026-11-13` and local artifact archives. Synthetic software
fixtures under `tests/` are not additional benchmark releases.

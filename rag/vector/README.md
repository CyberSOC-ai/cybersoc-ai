# S2-T02 vector retrieval preparation

Status: **local implementation verified for review**. The current development
validation build covers 340 source records and 406 passages. [ADR-001](../../docs/adr/ADR-001.md)
records the rationale and alternatives;
[selection-v1.json](configs/selection-v1.json) records exact proposed settings.
It is a design record, not a command input or a complete index-build manifest.
Its null score threshold means disabled. Inference dependencies are pinned in a
separate optional Linux/amd64 Python 3.12 environment.

See [VALIDATION.md](VALIDATION.md) for final coverage, artifact identities, checks
and the remaining review/publication steps.
Achraf can start from [EVALUATOR_SETUP.md](EVALUATOR_SETUP.md), which provides
fresh-corpus setup and the evaluator API without laptop-specific artifact paths.
For updated corpora, [incremental preparation](INCREMENTAL.md) reuses unchanged
passage spans and embeddings while preserving the previous index version.

The selected flow is:

1. Ahmed's verified corpus supplies source text and provenance.
2. The chunker splits eligible text using the pinned BGE tokenizer.
3. BGE-small converts each chunk into 384 numbers on the CPU. It does not generate
   answers and does not replace the existing Qwen/Phi baseline model.
4. A local Qdrant server persists those vectors in separate knowledge and SOC
   collections with filterable provenance. Queries use the same pinned encoder.
5. Later tasks evaluate retrieval and supply selected evidence to the answer model.

Example: a query about repeated SSH authentication failures can search reference
passages about password guessing and eligible historical observations. Whether
it actually retrieves the correct passages must be measured; similarity alone
does not prove an attack, identify a CVE or establish that a machine is vulnerable.

## Run offline chunking

Build the development image with `docker compose build dev`. The pinned
`tokenizers==0.22.1` dependency reads a local tokenizer JSON; it does not need
PyTorch, Sentence Transformers, GPU access or model weights. The inference
environment uses the additional lock described below.

Acquire [tokenizer.json at the pinned revision](https://huggingface.co/BAAI/bge-small-en-v1.5/resolve/5c38ec7c405ec4b44b94cc5a9bb96e735b38267a/tokenizer.json)
once into `.local/s2t02/tokenizer/tokenizer.json`. The model repository is MIT
licensed; retain its notice with any redistributed tokenizer package. The
chunker verifies SHA-256
`d241a60d5e8f04cc1b2b3e9ef7a4921b27bf526d9f6050ab90f9267a1f9e5c66`
before loading, disables tokenizer truncation/padding, and never fetches files.

From repository root, this PowerShell command uses the verified local step-2
release. Other acquisitions must supply their own verified manifest digest; do
not copy this digest onto a different release:

```powershell
docker run --rm --network none `
  --mount "type=bind,source=${PWD},target=/workspace,readonly" `
  --mount "type=bind,source=${PWD}/.local/s2t02,target=/artifacts" `
  cybersoc-ai-dev python -B -m rag.vector.chunk `
  --corpus /workspace/.local/ingestion/s2-t01-local-20261029-release/corpus `
  --manifest-sha256 bee53b00297cabcd61dbd174278798e5e48a6314cfbdff794e9d99daeff45dc2 `
  --tokenizer /artifacts/tokenizer/tokenizer.json `
  --output /artifacts/chunks-preview-new `
  --limit-per-source 3
```

`--limit-per-source` marks a preview; it still scans/verifies the complete input.
Omit it for a full chunk release. Always choose a new output directory. Optional
`--config`, `--splits` and repeatable `--policy` arguments select explicit inputs;
the defaults use current repository split/assignment files. No label file is read.
Changed eligibility policy/splits require a matching ingestion rebuild, not
silently trusting old SOC metadata. Processing is single-writer, streaming by
document; a failed build does not publish a partial output directory.

## Chunking policy v1

[chunking-v1.json](configs/chunking-v1.json) is the runnable chunker configuration.
It is separate from the broader proposed model/store selection record.

- **384 tokens total**, counting reference headers and CLS/SEP special tokens;
  **up to 48 tokens overlap** under the current window's tokenization. These are
  initial engineering settings, not relevance-tuned parameters.
- Bound the complete embedding text to **16,000 characters** as well. Token counts
  alone do not bound characters (a very long unknown word can be one token).
- Preserve original substrings with start/end character offsets. Do not decode
  token IDs into lowercased/normalized replacement evidence. Re-encode each final
  passage to check its true size, including subword/Unicode boundary effects.
  Splits can occur inside sentences or structured log text; this is a textual
  retrieval passage, not independently executable JSON, XML or a detection rule.
- Embed the primary source text. Knowledge can receive an ATT&CK/CVE/CWE reference
  identifier and a title if it is not already at the start of the body. SOC uses
  only its existing observed content, excluding its generated title and metadata.
- Retain short meaningful text with `short_primary_text`; exclude nonlexical/empty
  text and exact heading-only `Summary`/`Description` placeholders with a recorded
  reason. Other poor descriptions are not silently repaired or guessed.
- Keep distinct source identities, even with identical descriptions. Stable chunk
  IDs bind the complete parent record, configuration, ordinal, offsets and text;
  a derived UUID supplies a Qdrant-compatible point ID. Metadata/provenance changes
  therefore invalidate affected IDs too.
- Preserve source metadata internally, including supplementary provenance, without
  adding it to embedding text. This is not automatic sensitivity review of the
  source prose; source content remains untrusted data.

## Outputs and verification

| File | Contents |
|---|---|
| `chunks.jsonl` | Ordered chunk text/embedding text, exact token count, parent IDs/hashes, offsets, provenance, internal metadata and explicit filter projection |
| `decisions.jsonl` | One entry per selected record: chunk count, exclusion reason and quality flags |
| `manifest.json` | Input/config/split/policy and implementation digests, Git state, Python/OS, preview scope, counts and output hashes |
| `chunking-config.json` | Exact configuration used for the build |

The builder checks the composed manifest digest, record stream hash/counts,
schema, sorted unique IDs, source notices and primary/supplemental provenance.
SOC assignments are rechecked for held-out identities/groups/runs and current
development eligibility. The corpus remains development-only. Internal metadata
and `filters` are not a public evidence response and must not be passed wholesale
to the answer model. The build manifest records dirty code as exploratory evidence;
this does not certify an official evaluation run.

Offline CI tests use an explicitly synthetic small WordPiece vocabulary with the
real tokenizer engine. They need no network/model downloads and check token/character
bounds, source coverage, Unicode/subwords, identity stability, source separation,
quality decisions, eligibility, tampering, atomic failure and replay. The local
preview additionally uses the actual hash-pinned BGE tokenizer and real corpus.

```sh
docker compose run --rm -T dev python -B -m unittest discover -s tests/vector -v
```

## Remaining implementation handoff

- Step 6 encodes the saved `embedding_text` and checks that the inference
  tokenizer agrees with these counts. Never silently truncate or independently
  reformat that text. Source text has flattened whitespace, so paragraph breaks
  cannot be assumed.
- Download only the pinned model files, prefer Safetensors and disable remote
  code. Verify the publisher-reported weight hash against actual downloaded bytes
  and record hashes for tokenizer/config files. Inference after acquisition should
  use local files without contacting a hosted model. Tokenizer-only dependencies
  are pinned in `requirements.txt`; the optional inference dependencies are
  pinned in `requirements-embeddings.txt`.
- Start with a small real build before the full corpus. Validate finite normalized
  384-dimensional vectors, no silent truncation, filter behavior, citation mapping,
  persistence after restart and incompatible-config rejection. A fixed dummy
  embedding can test plumbing but cannot verify the real encoder or relevance.
- Create payload indexes before vector ingestion. The planned field names in the
  selection record describe the future index payload, not assumed paths in source
  metadata. Map source types explicitly; absent optional fields remain absent.
  Retain group/run/split lineage internally and revalidate eligibility against the
  current split policy. The local SOC corpus is development-only and unfrozen.
- Keep primary text separate from KEV/CVE supplements and evaluation metadata.
  Return only allowed evidence-contract fields. Align the retrieval request's
  missing `detection_rule`/`playbook` source filters with the evidence contract in
  implementation, with contract tests; other public filter fields need separate
  agreement with the API owner.
- Use a named Docker volume for live database data. Bind the host REST port only
  to loopback; another container will need the Compose service address rather
  than its own localhost. Keep large artifacts, acquired data and snapshots out of
  Git. Record the resolved volume/collection names and test snapshot recovery.
- S2-T03 owns relevance metrics, S2-T04 generation and S2-T05 backend routes.
  This step makes no measured quality, throughput or memory-fit claim.

## CPU embedding environment and acquisition

The optional [Dockerfile](../../infrastructure/docker/Dockerfile.embeddings)
installs both requirement files. It uses the official hash-pinned PyTorch 2.9.0
CPU wheel, Sentence Transformers 5.1.2, Transformers 4.57.1 and Tokenizers 0.22.1.
Regular CI stays lightweight and tests the artifact/failure logic without weights.

```powershell
docker build -f infrastructure/docker/Dockerfile.embeddings -t cybersoc-s2t02-embeddings .
.\.venv\Scripts\python.exe -B -m rag.vector.model --output .local/s2t02/models/bge-small-en-v1.5
```

Acquisition requires network access and the regular project dependencies. It
downloads only the 11 named files in [model-files-v1.json](configs/model-files-v1.json)
at the immutable revision. Verify the publisher's weight SHA-256 and byte count;
for small files verify the Git blob identity, then record every file's SHA-256.
Preserve the publisher README/license with the model. No pickle weights, ONNX
variants or source-code files are acquired. Existing output is refused; successful
acquisition publishes `acquisition.json` atomically with the verified files.

The encoder rechecks these files before loading locally with Safetensors and
remote code disabled. It requires the pinned CPU runtime. It encodes in float32,
uses CLS pooling and L2 normalization, and accepts 1–16 passages per call.
It compares the full input token-ID sequences against the step-5 tokenizer,
checks saved token counts, and rejects overflow before calling inference.

## Encode a verified chunk release

Take the expected SHA-256 from your verified chunk manifest; the example below
uses this machine's step-5 replay. Give each attempt a fresh output directory.

```powershell
docker run --rm --network none `
  --mount "type=bind,source=${PWD},target=/workspace,readonly" `
  --mount "type=bind,source=${PWD}/.local/s2t02,target=/artifacts" `
  cybersoc-s2t02-embeddings python -B -m rag.vector.embed `
  --chunks /artifacts/step5-preview-replay `
  --manifest-sha256 d95b7ce2116c032e770f136d708c5f2e06d70cabf84967494a0bd7dde2deedef `
  --model /artifacts/models/bge-small-en-v1.5 `
  --output /artifacts/embeddings-preview-new --batch-size 16
```

`vectors.jsonl` contains each original chunk/point ID, a hash of its exact
embedding text and 384 vector values. Numeric values originate as float32; JSON
serializes them as numbers. Payload and source text remain in the linked chunk
release. The embedding `manifest.json` binds model files, chunk/config/policy
identity, runtime package versions, code/lock digests, batch size, count, output
hash and elapsed inference/write time. Startup/model verification is outside that
timing boundary. Changing timings changes manifest identity; compare vector
values with a tolerance rather than requiring manifest bytes to match.

Before publication, the runner verifies stream hashes/counts, current eligibility
policies and model integrity. Invalid vectors, altered inputs or partial failures
leave no published output. The saved preview limit and development-only restriction
propagate to the embedding manifest. Docker Git state may be unavailable; retain
host revision/dirty state and the actual image identity alongside local run evidence.

`BGEEncoder.query(text)` prepends the exact instruction saved in the selection
record, checks the 4,000-character public limit and rejects a complete encoded
query over 512 tokens. It returns a vector from the same local model for step 8.
The character limit alone does not guarantee token fit. This is an internal
adapter; API route/error integration remains later work.

The real local smoke run encoded 36 passages from the 17-document preview.
This establishes small-build encoding behavior. It does not constitute a full
corpus run, retriever-quality result, training or vector-database deployment.

## Persistent local Qdrant storage

The opt-in `vector` Compose profile runs the pinned Linux/amd64 Qdrant 1.20.0
image, with telemetry disabled, a named volume `cybersoc-s2t02-qdrant` mounted at
`/qdrant/storage`, and REST published only on `127.0.0.1:6333`. The profile keeps
normal dev/API commands independent of database startup. Start only this service:

```powershell
docker compose --profile vector up -d qdrant
```

Load the verified local step-6 preview with the regular project virtual
environment (no Torch dependency needed for storage). Other releases need their
own verified manifest hashes. Always choose a fresh receipt directory:

```powershell
.\.venv\Scripts\python.exe -B -m rag.vector.index `
  --chunks .local/s2t02/step5-preview-replay `
  --chunk-manifest-sha256 d95b7ce2116c032e770f136d708c5f2e06d70cabf84967494a0bd7dde2deedef `
  --vectors .local/s2t02/step6-embeddings-replay `
  --embedding-manifest-sha256 4358c27d564da08d9ef88df945702af98fcba9e67250394a1897510cbc325545 `
  --output .local/s2t02/index-preview-new
```

`index.py` first verifies chunk/vector manifests, current split/policy identity,
model/tokenizer identity, entire input-stream hashes/counts, ID alignment,
normalized vectors, citation provenance and collection/filter mapping. It spools
verified points to temporary disk before any database mutation. No inference,
source acquisition, training, source command execution or external model service
is involved. The REST adapter disables environment proxies and accepts loopback
HTTP endpoints only.

The build identity covers input manifests, selection settings, point-file hashes
and implementation digests. Collections are named `knowledge_<build_id>` and
`soc_history_<build_id>`. Both existing names are checked before creating anything;
the loader refuses overwrite/resume, including an existing partial build. No alias
or existing collection is changed.

Each collection uses 384-dimensional float32 cosine vectors, cold vector/payload
storage and cached HNSW with `m=16`, `ef_construct=100`. The loader creates the
planned typed payload indexes **before** inserting points. It verifies resolved
server settings, every stored payload/vector and exact counts, marks the
collections ready, and publishes the receipt directory after both succeed.
The receipt is required to identify a complete pair; collection metadata alone
is insufficient if a failure occurs between the two ready updates.

If loading fails, no receipt is published and newly created collections remain
available for inspection. The error lists their names. There is no automatic
deletion or silent retry into those names. Do not use a partial collection as a
completed build. Inspect failure causes and explicitly handle its new collections
before retrying. Previously successful builds remain separate.

| Receipt file | Purpose |
|---|---|
| `manifest.json` | Build/collection names, input/settings/code identities, resolved configuration and payload schemas, counts, preview restriction and host Git state |
| `knowledge.jsonl` | Verified point/vector/internal-payload spool used for knowledge upload/readback |
| `soc_history.jsonl` | Corresponding SOC point spool |

Internal payload retains citation IDs/text/hashes, original offsets, provenance,
full source metadata and quality flags. Filter fields are explicitly projected
at the payload root: `source`, `snapshot_ref`, `source_record_id`, optional
`platforms`/`source_status`, and SOC `split`, `incident_group_id`, `test_frozen`.
For example, source matching uses
`{"must":[{"key":"source","match":{"value":"cve"}}]}`; multiple `must`
conditions combine source and snapshot restrictions. Platforms are lowercase
arrays; a keyword match finds an element. Boolean eligibility uses JSON booleans.
Administrative metadata remains internal and is never embedded as extra text.
The stored object is not the public evidence contract. The step-8 adapter projects
only allowed evidence fields and aligns the draft public source filters.

The actual step-7 preview contains **33 knowledge points and 3 SOC points**.
All points matched their verified local vectors/payloads. All 44 positive
filter-value checks, negative/boundary checks and two filtered stored-vector
queries passed before and after container recreation. Recreating only this
service keeps the named volume:

```powershell
docker compose --profile vector up -d --force-recreate qdrant
```

The preview is below the default indexing threshold: `indexed_vectors_count=0`
is expected and searches use full scans. HNSW settings are verified, but its
large-corpus behavior/performance still needs a full build. Container recreation
tests persistence; it does not test snapshot backup/recovery. Keep the volume and
the source/embedding/receipt artifacts for later work. Avoid `down -v` or volume
deletion when retaining this database.

The step-8 adapter below connects a query vector to filtered search and explicit
evidence projection. Retrieval relevance measurements remain S2-T03 work.

## Query to cited evidence

`retrieve.py` implements the internal retriever adapter and a file-based CLI.
It uses the existing request/response contracts. FastAPI routes, answer generation
and relevance evaluation remain the corresponding teammates' tasks.

Example request (save locally as `.local/s2t02/request.json`):

```json
{
  "schema_version": "1.0.0",
  "request_id": "REQ-example",
  "trace_id": "TR-example",
  "mode": "vector",
  "query": "Investigate suspicious LSASS process memory access",
  "top_k": 3,
  "filters": {"sources": ["playbook"]}
}
```

Use the verified index receipt's SHA-256. This command uses the current local
preview. The inference container shares Qdrant's network namespace so its
loopback address reaches the local database. Model loading remains offline.
Run it after Qdrant is started and use a new output file for each attempt:

```powershell
docker run --rm --network container:cybersoc-ai-qdrant-1 `
  --mount "type=bind,source=${PWD},target=/workspace,readonly" `
  --mount "type=bind,source=${PWD}/.local/s2t02,target=/artifacts" `
  cybersoc-s2t02-embeddings python -B -m rag.vector.retrieve `
  --index /artifacts/step7-index-preview `
  --index-manifest-sha256 2386619245c9642b6b937352811ccdcac2aaf77d83706cffe109ffb5a7630c33 `
  --chunks /artifacts/step5-preview-replay `
  --vectors /artifacts/step6-embeddings-replay `
  --model /artifacts/models/bge-small-en-v1.5 `
  --request /artifacts/request.json --output /artifacts/response-new.json --exact
```

The reader checks the receipt hash/build identity, selection settings, current
split/policy identity, embedding/model identity, ready collection pair and exact
counts. It verifies the local point-spool hashes and reads all stored points back
once on startup, checking payloads and vectors before loading query inference.
It retains per-point fingerprints rather than all source text/vectors in memory.
Reusing one `Retriever` instance avoids repeating this startup verification/model
load for every request. This full readback has a startup cost to measure at scale.

For each request it rechecks live collection state and eligibility, encodes the
query with the pinned instruction, and passes filters to Qdrant **before** top-K.
Source values within `sources` and snapshot values within `snapshot_refs` use OR;
the fields combine with AND. Missing/empty arrays mean no restriction on that
field. SOC queries additionally require the current development split/freeze
state. Group/run/test policy changes invalidate this saved build rather than
silently using stale eligibility. Per-case exclusions and the evaluation split
protocol still belong to S2-T03; this development preview is not a held-out test.

Each collection contributes at most K candidates. Since both use the same
encoder/cosine metric, the adapter merges their raw scores and returns at most K
overall, sorting equal candidate scores by evidence ID. Approximate search and
ties at a candidate cutoff need not produce identical candidate sets on different
machines. Default search uses the recorded HNSW parameters; `--exact` requests
full-scan search for correctness checks. No relevance threshold or reranker is used.

Returned hits must match the startup payload/vector fingerprints and requested
filters; their reported score is checked against the vector cosine. Evidence is
explicitly limited to `evidence_id`, `source`, `source_record_id`, `snapshot_ref`,
`content`, `score`, `score_kind` and `retrieval_method`. It contains source slices,
not internal metadata or generated query instructions. Chunk IDs provide stable
evidence IDs. Separate chunks of one document can occupy several result slots.
Supplemental KEV/CNA facts remain outside the primary-text evidence projection.

The response preserves request/trace IDs. No candidates returns `status=ok` with
empty evidence. Unsupported graph/hybrid modes, query overflow, changed index
state, invalid points and unavailable/timed-out dependencies produce explicit
contract error responses with no partial evidence. Invalid request envelopes are
rejected before retrieving. The CLI prints a short status/count; inspect the saved
response's `status`/`error` for operation outcome. It refuses output replacement.

The draft request source filter now matches all eight existing evidence sources,
including `detection_rule` and `playbook`; copied validators must refresh. A schema
test guards this agreement. Source filters with no matching indexed records return
empty evidence; they do not fall back to another source.

The real preview checks covered SOC-only, playbook-only, Sigma-only and combined
queries, an unmatched snapshot and token overflow. For example, the LSASS query
returned three passages citing the selected LSASS Memory Read Access playbook.
Exact queries repeated consistently, and reopening the reader from the persisted
artifacts produced the same response. These verify the adapter on 36 preview
points; Recall@K, Precision@K, MRR and answer quality have not been measured.

## Final local validation and task scope

The validated development build contains **369 knowledge points and 37 SOC
points** from 340 source records: 100 CVEs, 100 CWE entries, 100 ATT&CK entries,
all three selected Sigma rules, both selected playbooks and all 35 prepared SOC
records. Input selection is explicit (`limit_per_source=100`); it is a bounded
development validation corpus, not the whole acquired knowledge corpus.

Its local receipt is `.local/s2t02/final-index-validation/manifest.json`, SHA-256
`e438308b135bddfd3d6c87187ad3fccf84436c367dfec6663cb9191b5f5dc35c`.
Use `.local/s2t02/step9-chunks-pilot` and
`.local/s2t02/step9-embeddings-pilot` as the linked chunk/vector directories.
These names identify saved artifacts; no new encoding is needed to query them.
For the query CLI above, substitute these paths and the final receipt hash.

Issue #17 requires configured chunking/embeddings, separate vector collections,
provenance/filters and validation evidence. It does not explicitly require GPU
execution or vectorizing every acquired record. No external-compute handoff is a
completion prerequisite. The reviewer must assess whether this documented corpus
coverage is sufficient for downstream evaluation/generation needs.

Additional local evidence: complete chunking checked 164,793 records and produced
174,883 passages in about 14.5 minutes. One placeholder was explicitly excluded;
ten short descriptions retained quality flags. Full chunks remain ignored under
`.local/`; a full-corpus embedding/index run and ANN-scale benchmarks were not run.
The CPU pilot produced 406 embeddings in about 136 seconds including startup/build,
114 seconds inference/write, about 735 MiB peak process RSS. These exploratory
measurements overlapped chunking and do not constitute an official benchmark.

The working pipeline and validation artifacts are ready for peer review. Formal
Done still requires the applicable PR, hosted CI, reviewer handling and issue
closure. No push, publication or external transfer is included in local completion.

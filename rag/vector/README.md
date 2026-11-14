# Vector RAG

This folder implements a local two-stage retrieval-augmented investigation path:
verified source documents become a persistent vector index; incident-derived
queries retrieve passages that are then supplied to the existing local model.
It is a fresh implementation, separate from the retired pipeline and from the
frozen [No-RAG reference](../../ai/no_rag/README.md).

## Read this folder

- `README.md`: architecture, execution, restoration and data growth.
- [EVALUATION.md](EVALUATION.md): preparation/retrieval checks, corrections and
  the recorded seven-case generation evaluation. Publisher passage text is omitted
  from distributable prompt views; exact prompts remain in local artifacts.
- [IMPROVEMENTS.md](IMPROVEMENTS.md): measured limits and future work.

The Python modules have one responsibility each: `data.py` verifies source and
artifact identities and creates exact-span passages; `index.py` handles pinned
embeddings and Qdrant persistence; `retrieval.py` verifies search results and
creates incident-bound packets; `generation.py` assembles bounded context and
validates investigations through the shared `ai/runtime` contracts/policy; `run.py` exposes the commands. `config.json` and
`prompt.txt` identify the active preparation/retrieval settings and instructions.
The dependency lock and Dockerfile describe the embedding environment. Tests are
in `tests/vector/`; the launcher is `infrastructure/run-vector.sh`.

Raw models, indexes, snapshots and run records are outside this folder under
`artifacts/local-inference/vector-v1/`, excluded from Git. Source releases stay
separate. No evaluator label or expected answer is indexed or passed to the model.
The backend's RAG endpoint remains unavailable: this delivery is a standalone
CLI pipeline, not a served API integration or an analyst dashboard.

## Recorded local result

The first frozen seven-case batch completed with six validated results and one
policy-rejected answer. Verdict agreement is 4/7; delivered risk-field agreement
is 5/7. Retrieval found known references for all 18 answerable development
questions, but the generated answers often attach citations without explaining
the references. This is a usable local experiment pipeline, with no demonstrated
answer-quality improvement over the frozen No-RAG reference. The complete
[review](EVALUATION.md) retains every intended case and the failed raw output.

## Architecture

```text
Frozen knowledge → verified text → tokenizer passages → local BGE → Qdrant
Incident → event-topic query → verified passages → bounded prompt → local Qwen
                                                          → result and trace
```

Embedding and generation run sequentially in separate existing images, avoiding
two loaded models in the same process. Qdrant has its own persistent storage and
an isolated network namespace with no external network or published ports.
Embedding/retrieval clients join that namespace and use loopback. The generator
runs separately with no external network and its own loopback model server.

The current source is `shared-dev-v1`: 21 references and seven synthetic incidents.
Only declared knowledge assets enter the corpus. Source text/snapshot hashes,
usage records, document identities and exact character offsets are retained.
Platform/operational documentation uses the existing v1 `playbook` source category;
this does not make it an executable response plan. Current coverage has no
threat-feed or historical-SOC collection, and those sources are not claimed implemented.

BGE-small-en-v1.5 produces normalized 384-dimensional CLS embeddings using the
pinned local model/tokenizer. Passages use 192 tokenizer tokens with 32-token
overlap, preferring paragraph boundaries near the limit. Text is never silently
truncated. Queries use the publisher's retrieval prefix; passages do not.
Model files, embedding implementation and library versions define reuse compatibility.

Qdrant stores point/vector and provenance identities. Retrieval checks the entire
point inventory against saved float32 vectors, then checks hit IDs, payloads,
filters and cosine scores. One passage per document is retained in the ranked
results. Up to two passages are considered for generation; complete passages are
selected only when the actual model tokenizer says the whole prompt fits.

The model returns core decisions plus `citation_ids` such as `R1`. That array is
the single model-authored citation representation; trusted code renders stable
source IDs into the stored summary. Raw output is preserved. ID membership is
validated, but it does not establish that a cited passage supports the claim.
Empty citations are allowed when no reference-supported claim is made. Such an
answer may be structurally valid while failing the source-use review.

## Fresh-machine setup

1. Obtain the reviewed repository revision and follow
   [runtime setup](../../ai/runtime/README.md) to restore shared-v1, verify the
   Qwen/server bytes and prepare the inference environment. Set `VECTOR_LLM_IMAGE`
   to its verified full content identity when it differs from the recorded default.
2. Obtain the BGE model at the revision/hash inventory in `config.json`. Retain the
   publisher notices and acquisition provenance. Use an approved offline bundle,
   or explicitly download the declared files from the pinned publisher revision
   using the block below. The retained directory name includes `legacy-bge` for
   path compatibility; its verified model bytes are actively used by this pipeline.
3. Prepare the embedding image and pinned Qdrant image as described below. Image
   preparation may require network access; normal pipeline workers do not download.
4. Run the offline tests, then follow the numbered execution sequence. Review every
   intended case, including failure records. New directories are required for reruns.

The following is an explicit first-time model acquisition step. It never executes
remote code. Do not run it over an existing model directory. Check publisher terms
and only use trusted repository configuration.

```sh
python3 - <<'PYMODEL'
from hashlib import file_digest
from pathlib import Path
import json
import shutil
from urllib.request import urlopen
config = json.loads(Path('rag/vector/config.json').read_text())
target = Path(config['embedding_path'])
target.mkdir(parents=True, exist_ok=False)
for name, expected in config['embedding_files_sha256'].items():
    path = target / name
    path.parent.mkdir(parents=True, exist_ok=True)
    url = ('https://huggingface.co/' + config['embedding_model'] + '/resolve/'
           + config['embedding_revision'] + '/' + name)
    with urlopen(url, timeout=300) as response, path.open('xb') as stream:
        shutil.copyfileobj(response, stream)
    with path.open('rb') as stream:
        if file_digest(stream, 'sha256').hexdigest() != expected:
            raise SystemExit('Checksum mismatch: ' + name)
print('All declared embedding-model files verified')
PYMODEL
```

If interrupted or a hash differs, retain the failed attempt for diagnosis and
resolve it before activating any directory; do not skip checks or substitute HEAD.
The model is [BGE-small-en-v1.5 at the pinned revision](https://huggingface.co/BAAI/bge-small-en-v1.5/tree/5c38ec7c405ec4b44b94cc5a9bb96e735b38267a).

## Runtime images

The default launcher uses already-present, content-addressed Qdrant, embedding and
Qwen runtime images. It never pulls/builds images or downloads models/packages.
It uses read-only source mounts, restricted capabilities and explicit CPU/RAM
limits. Models stay at the paths pinned by configuration. Missing bytes/hashes
cause failure. The source release can be restored using
[the release guide](../../datasets/SHARED_DEV_V1.md).

For a fresh approved environment, the embedding Dockerfile is a build recipe:

```sh
docker build -f rag/vector/Dockerfile -t cybersoc-vector-embedding:local .
```

Building requires obtaining the pinned base/dependencies and is not performed by
the launcher. The recipe has not been independently built/reproduced in this phase;
local execution uses the verified existing image. After building and verifying a
new image, pass its full content identity through `VECTOR_EMBED_IMAGE`. A different
generation environment can similarly use `VECTOR_LLM_IMAGE`. Mutable tags are
rejected by the launcher; record the new identity and rerun compatibility checks.
The lock describes the tested environment, including installed extras, not a
claim that all packages are minimal runtime dependencies.

Before pipeline execution, explicitly acquire the pinned store image when absent:

```sh
docker pull qdrant/qdrant:v1.20.0@sha256:2d1b0bfd0a961275481ea09400fc98008216ae54e1b52ed7d24520d63050c644
export VECTOR_EMBED_IMAGE="$(docker image inspect --format '{{.Id}}' cybersoc-vector-embedding:local)"
```

The override above assumes the fresh embedding recipe was built. Alternatively,
load a verified export of the tested image and use that identity. The recorded
local embedding image is
`cybersoc-rag-eval@sha256:4e3e26e112a65a2566ea2930eae2ef2fe02055d04327b6d739531aa2f5231c5c`.
Export archives need their own checksums and usage review; no shared image-bundle
link has yet been published. A local image name does not make it fetchable elsewhere.

## Commands from the repository root

`/artifacts` inside a worker maps to local `artifacts/local-inference/vector-v1`.
Choose new output paths; existing artifacts and collections are not overwritten.
Run each step separately and stop on an unexpected nonzero exit. The sequence is:
start store → build → publish → evaluate retrieval → create incident packets →
preflight → investigate → stop store. A recorded generation failure is exit 1 and
must remain in the review; inspect it before proceeding to further experiments.

```sh
bash infrastructure/run-vector.sh start
bash infrastructure/run-vector.sh build --output /artifacts/my-build
bash infrastructure/run-vector.sh publish --build /artifacts/my-build --output /artifacts/my-receipt.json
bash infrastructure/run-vector.sh evaluate --build /artifacts/my-build --receipt /artifacts/my-receipt.json --output /artifacts/my-retrieval-review.json
bash infrastructure/run-vector.sh retrieve --build /artifacts/my-build --receipt /artifacts/my-receipt.json --output /artifacts/my-packets
bash infrastructure/run-vector.sh preflight --build /artifacts/my-build --packets /artifacts/my-packets --output /artifacts/my-preflight
bash infrastructure/run-vector.sh investigate --build /artifacts/my-build --packets /artifacts/my-packets --output /artifacts/my-run
bash infrastructure/run-vector.sh stop
```

`investigate` runs every incident in the selected release. Add `--case CASE_ID`
to select one. `preflight` starts its owned model server for template/token checks
but generates no answer. Stop the store when it is no longer needed; generation
uses sealed retrieval packets and does not require the store to stay loaded.
The store container is deliberately retained stopped so `start` can reuse its
persistent files. Do not delete storage or an existing collection to make a rerun
appear fresh; choose a new artifact identity instead.

Exit 0 means the requested operation completed; it is not semantic acceptance.
Exit 1 means a recorded investigation/preflight had failures; exit 2 means command,
configuration or unexpected failure. There is no automatic retry, output repair,
action filtering or fallback to No-RAG. Interrupted/unexpected generation retains
available artifacts with failed status. Inspect every intended-case count.

## Snapshot export and restoration

```sh
bash infrastructure/run-vector.sh snapshot --build /artifacts/my-build --receipt /artifacts/my-receipt.json --output /artifacts/my-index.snapshot
bash infrastructure/run-vector.sh restore --build /artifacts/my-build --snapshot /artifacts/my-index.snapshot --output /artifacts/my-restored-receipt.json
bash infrastructure/run-vector.sh evaluate --build /artifacts/my-build --receipt /artifacts/my-restored-receipt.json --output /artifacts/my-restored-review.json
```

Snapshot creation writes the binary and its identity/receipt sidecar. Restoration
uses the native Qdrant snapshot API into a distinct `_restore` collection and
verifies counts. The complete build directory, snapshot and sidecar form the
portable artifact set. Query embeddings still require the verified embedding
model, but document embeddings are not recomputed during restore.

## New or larger source releases

Never edit frozen v1. Stage/review additions under the
[shared data workflow](../../datasets/README.md), then select the new release
ID and manifest hash in a new trusted configuration. Pass it with `--config` and
`--release`. The loader accepts the same declared knowledge and incident contract
layout without hard-coding seven cases. Changed source formats require an explicit
adapter rather than recursive directory indexing.

Use `build --reuse /artifacts/previous-build --output /artifacts/new-build` when
embedding/model/tokenizer implementation identities match. Unchanged exact
embedding inputs reuse their vectors; changed/new inputs are embedded. The new
build records its predecessor and reuse/new counts. Incompatible embeddings fail
rather than being silently mixed. New source/corpus identities create distinct
collections; old runs remain bound to their original source and index.

Changes to retrieval/context selection can reuse the same compatible index but
must create new packets/configuration/run identities. A new or changed incident
with no reviewed proposal scope receives no eligible block targets. Changed scope
requires a new policy file/hash; it does not modify the frozen No-RAG policy.
The current implementation bounds source/chunk sizes and is tested only on the
small corpus; large-scale throughput and approximate-index tuning remain future work.

## Layout version and historical experiments

`shared-vector-layout-v2` is the current configuration, using shared runtime paths.
The seven-case scores in [EVALUATION.md](EVALUATION.md) describe the earlier frozen
`shared-vector-v3` experiment. Its original snapshots/configuration and raw outputs
remain unchanged. Current commands create a new experiment; they do not enforce
or reproduce that old source freeze merely because the model settings match.

Changed paths do not require recomputing compatible document embeddings. Build a
new artifact with `--reuse`, publish its new identity, and create new packets under
the new configuration. Existing packets bound to the old configuration are rejected.
Do not rewrite their hashes or modify a historical build to force compatibility.

## Evaluation and reproducibility boundaries

The 21 retrieval questions are evaluated independently from generation. Their
judgments are draft and incomplete: unlisted documents are unjudged, not negative.
Known-reference coverage is not full precision or proof of answerability. Similar
reference passages cannot authenticate approvals or prove a host was exploited.

Generation keeps the No-RAG model, quantization, core label semantics, policy and
initial 3,072/512/4,096-token limits. It adds reference context and citation fields,
so the prompts are not identical. The 180-second inference deadline includes
context selection/generation; retrieval/embedding are a separately recorded stage.
Do not compare partial latency boundaries or infer causal speedups across runs.

Each generation output freezes source/configuration, runtime/image, build and
packet identities before inference. It retains actual messages/rendered prompts,
selected references, raw output, citation mapping, result/failure, measurements,
trace and hashes. Integrity and schema checks are separate from semantic review.
The process validates only locally selected trusted artifact paths; it is not an
authenticated public service or protection against an attacker controlling the host.

Hosted CI, fresh-image builds, cloud storage/replay and independent teammate
reproduction are not established merely by local tests or snapshot recovery.
Sources retain their original usage limits; this task does not publish source
snapshots or claim new sharing rights.

## Troubleshooting and handoff

- Missing image/model: complete explicit setup and compare full identities. Workers
  use `--pull=never` and offline model loading; absence is a failure, not a download.
- Store unavailable: start the task-owned container, inspect its local state and
  storage permissions. Do not publish Qdrant ports or alter unrelated containers.
- Build/config/packet mismatch: select matching artifacts or create new ones; do
  not edit manifests to make changed contents appear verified.
- Context overflow/empty retrieval/invalid proposals: inspect the recorded failure,
  selected references, raw output and scope. No output repair or hidden fallback.
- Disk/RAM pressure: stop the owned store after packet creation, run models
  sequentially and use smaller reviewed development input. Larger bounds require
  explicit measurement and configuration; they are not a silent runtime adjustment.

For teammate restoration, hand over the reviewed source revision, source-release
hash, model/image identities, complete build directory and native snapshot/sidecar.
Follow the snapshot restoration commands, rerun retrieval evaluation and record
the restored collection/results. Document artifact access separately; this checkout
does not include model/index bytes or establish independent reproduction.

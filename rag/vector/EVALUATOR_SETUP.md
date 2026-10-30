# S2-T03 start guide for Achraf

This branch supplies the retriever needed by [issue #18](https://github.com/CyberSOC-ai/cybersoc-ai/issues/18).
Use it for integration/development while #17 is reviewed; formal dependency closure
still follows review/CI/merge. Ahmed reviews #17; Anas reviews the evaluation task.

## Inputs and coverage

The public PR contains code, configuration, tests and sanitized validation records.
Large data/model/index files are not in Git. Start with an approved S2-T01 composed
corpus from Ahmed, or reproduce acquisition using the commands below. No files from
Soulaiman's `.local` directory are required. Exact replay of his corpus requires
the same source snapshots; fresh NVD acquisition can change record contents and
hashes. Record your own corpus identity and keep it fixed for evaluation.

The validated selection used 100 records per source, yielding 340 records and
406 points (369 knowledge, 37 SOC); it covers all prepared SOC, Sigma and playbook
records. A fresh acquisition may produce different selected IDs/counts. Selection
is deterministic by corpus order and recorded in manifests. Choose any expanded
coverage explicitly with the reviewer; do not silently treat this subset as the
entire acquired corpus. A GPU or full-corpus performance run is not a setup gate.

## Rebuild your local index (PowerShell, repository root)

Check out this PR's branch, then build the environments and start Qdrant:

```powershell
git fetch origin
git switch codex/17-chunking-embeddings-vector-index
docker compose build dev
docker build -f infrastructure/docker/Dockerfile.embeddings -t cybersoc-rag-eval .
docker compose --profile vector up -d qdrant
New-Item -ItemType Directory -Force .local/rag-eval | Out-Null
```

If Ahmed has supplied an approved corpus, put the release at
`.local/rag-eval/corpus-release/` with `corpus/manifest.json`, `records.jsonl` and
the source notices, preserving its directory structure. Otherwise acquire it:

```powershell
$acquiredAt = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
docker compose run --rm -T -v "${PWD}/.local/rag-eval:/artifacts" dev `
  python -B -m rag.ingestion.build --artifacts /artifacts/acquisition `
  --output /artifacts/corpus-release --acquire --lab-acquired-at $acquiredAt
```

This is Ahmed's explicit acquisition pipeline: it downloads selected public
sources, preserves notices and uses the repository's current SOC policies. It
does not execute source commands/rules. Review its [guide](../ingestion/README.md)
for acquisition/storage requirements. Use new output directories for new releases.

Acquire the pinned model once, then prepare chunks, real CPU embeddings and the
separate persistent collections. Acquisition needs internet; inference uses local
files. Namespace sharing makes the container's loopback reach Qdrant:

```powershell
docker run --rm `
  --mount "type=bind,source=${PWD},target=/workspace,readonly" `
  --mount "type=bind,source=${PWD}/.local/rag-eval,target=/artifacts" `
  cybersoc-rag-eval python -B -m rag.vector.model --output /artifacts/model

$qdrantId = docker compose --profile vector ps -q qdrant
docker run --rm --network "container:$qdrantId" `
  --mount "type=bind,source=${PWD},target=/workspace,readonly" `
  --mount "type=bind,source=${PWD}/.local/rag-eval,target=/artifacts" `
  cybersoc-rag-eval python -B -m rag.vector.prepare `
  --corpus /artifacts/corpus-release/corpus --model /artifacts/model `
  --output /artifacts/achraf-01 --limit-per-source 100
```

Success creates `achraf-01/READY.json`: paths, hashes, actual counts and development
scope. Existing outputs/collections are refused. A failed preparation can retain
completed intermediate artifacts and unready collections for inspection; use a
new output directory after addressing it. If reusing independently verified
chunk/vector releases, pass both `--reuse-chunks` and `--reuse-vectors`; their
corpus/model identity must agree. This avoids re-encoding, without bypassing index
input/readback validation. `READY.json` paths belong to the host/container layout
used for preparation; retain the same `/artifacts` mount for the example below.

## Call the retriever from the evaluator

For later corpus updates, use [incremental preparation](INCREMENTAL.md) to reuse
unchanged chunks/embeddings and publish a separate index version. Keep the index
fixed during an evaluation run.

Inside the CPU inference environment with the same mount and Qdrant namespace:

```python
import json
from pathlib import Path
from rag.vector.retrieve import Retriever

ready = json.loads(Path("/artifacts/achraf-01/READY.json").read_bytes())
reader = Retriever(ready["index"], ready["index_manifest_sha256"],
                   ready["chunks"], ready["vectors"], ready["model"], exact=True)
try:
    result = reader.retrieve({
        "schema_version": "1.0.0", "request_id": "REQ-eval-001",
        "trace_id": "TR-eval-001", "mode": "vector",
        "query": "Repeated SSH authentication failures", "top_k": 5,
        "filters": {"sources": ["mitre_attack", "soc_log"]}
    })
    if result["status"] != "ok":
        raise RuntimeError(result["error"]["code"])
    evidence = result["evidence"]
finally:
    reader.close()
```

Reuse one reader across evaluation cases: startup verifies all saved points and
loads the model. `exact=True` provides an exact-search control; omit it to use the
configured approximate-search settings. Filters are applied before top-K and
results merge globally. Responses preserve request/trace IDs and expose only
closed evidence fields. Source/snapshot identity plus stable chunk evidence IDs
allow relevance judgments at an explicitly chosen granularity. Treat errors
separately from successful empty results.

Achraf owns query/relevance judgments, K choices, Recall@K/Precision@K/MRR and
their report. Freeze the corpus/chunk/model/config identities before labeling or
comparing runs. The current SOC set is development-only and unfrozen; exclude
evaluated incident families from retrieval as required by the protocol (or use
knowledge-only retrieval for that comparison). This adapter does not create an
independent test set or gold labels. Corpus coverage must suit the chosen queries.

Save `READY.json`, its linked manifests, per-case results/errors and environment
records outside Git. See [VALIDATION.md](VALIDATION.md) for the already measured
local behavior and [the experiment conventions](../../experiments/README.md).

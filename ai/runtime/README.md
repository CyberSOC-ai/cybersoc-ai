# Shared runtime

Both investigation modes use this package for model process lifecycle, loopback
transport, strict JSON/contracts, proposal policy and provenance. Importing it
never downloads artifacts or starts a server. No-RAG owns its incident-only prompt;
RAG owns retrieval and its reference-aware prompt. Neither pipeline imports the
other. The API and its versioned schemas remain in `backend/`.

## Contents and configuration

| Path | Responsibility |
|---|---|
| `lifecycle.py` | Start/stop only the owned local llama.cpp process |
| `llama_server.py` | Bounded loopback template, tokenization and completion requests |
| `contracts.py` | Shared decision schema, strict JSON and inference errors |
| `policy.py` | Proposal-only permissions and incident-bound source-role checks |
| `configuration.py`, `provenance.py` | Verify binaries; identify code/configuration and run artifacts |
| `smoke.py` | Small structured-output compatibility check, without incident evaluation |
| `configs/qwen-cpu-linux.json` | Pinned Linux CPU model/runtime and generation bounds |
| `configs/shared-dev-v1-policy.json` | Shared disabled-execution proposal policy |
| `Dockerfile` | Fresh inference environment recipe; weights/binaries mounted separately |

`local-layout-v2` identifies the reorganized implementation. The source moves and
shared-policy extraction do not change prompts, label definitions, response
permissions or model settings. Frozen experiments predate this layout; they are
historical evidence, not source locks for these paths.

## 1. Prepare a supported machine

Use Linux x86_64 (or a Linux x86_64 Docker environment), Git and Docker with Compose.
The pinned llama.cpp binary is not a native Windows/macOS/ARM executable. Those
hosts need a suitable Linux environment or a separately verified runtime/config.
Allow several GB of free RAM and disk space for the images, models and artifacts.
The current launchers limit each worker to 3 GiB and two CPUs; models run sequentially.

Obtain the reviewed source revision, then work from its repository root:

```sh
git clone https://github.com/CyberSOC-ai/cybersoc-ai.git
cd cybersoc-ai
```

Use the exact reviewed branch/commit containing this layout; it is not assumed to
be merged into the default branch. Check `git rev-parse HEAD`. Restore the source
release using [the data guide](../../datasets/SHARED_DEV_V1.md). Keep credentials
outside code, data bundles and recorded execution snapshots.

## 2. Obtain and verify the model and server

For an offline teammate handoff, obtain the approved model/runtime bundle from the
maintainer, retain notices and receipts, restore the paths below and verify hashes.
A verified shared download link for model/runtime/image bundles has not yet been
published. Source data already has its own download guide. Do not mistake a local
Docker image ID for an image another machine can fetch.

Alternatively, after reviewing the publishers' usage terms, obtain the pinned bytes
from the official sources below. These are explicit download instructions; normal
pipeline commands never download anything.

| Artifact | Immutable source / expected identity |
|---|---|
| Qwen Q4_K_M GGUF | [Publisher revision](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/tree/91cad51170dc346986eccefdc2dd33a9da36ead9); model SHA-256 `6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e` |
| llama.cpp Linux CPU archive | [b11827 release](https://github.com/ggml-org/llama.cpp/releases/tag/b11827); archive SHA-256 `7c1de2b2a139aa90e28b88d44a75f5966485604f68aa0ccdc2339959bca9b5f6` |
| Extracted llama-server | SHA-256 `92ff7abb8a59c94a98acdbca4f50aaf54d2cb08a05fad57b254587a101366aac` |

Run these shell blocks separately and stop if a download or checksum fails. Use a
fresh destination; do not overwrite existing artifacts. The archive contains
companion libraries: retain its complete extracted directory, not just the server.

```sh
mkdir -p artifacts/local-inference/models
mkdir artifacts/local-inference/models/qwen2.5-1.5b-instruct-q4_k_m
curl --fail --location --output artifacts/local-inference/models/qwen2.5-1.5b-instruct-q4_k_m/qwen2.5-1.5b-instruct-q4_k_m.gguf \
  https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/91cad51170dc346986eccefdc2dd33a9da36ead9/qwen2.5-1.5b-instruct-q4_k_m.gguf
```

From that same pinned publisher revision, retain `LICENSE` and `README.md` beside
the model. Record the source URL, revision, date and checksums with the acquisition.

```sh
mkdir -p artifacts/local-inference/runtime
mkdir artifacts/local-inference/runtime/llama.cpp-b11827-linux-x64
curl --fail --location --output artifacts/local-inference/runtime/llama-b11827-bin-ubuntu-x64.tar.gz \
  https://github.com/ggml-org/llama.cpp/releases/download/b11827/llama-b11827-bin-ubuntu-x64.tar.gz
```

Verify model/archive bytes before extracting:

```sh
python3 - <<'PY'
from hashlib import file_digest
from pathlib import Path
items = {
 'artifacts/local-inference/models/qwen2.5-1.5b-instruct-q4_k_m/qwen2.5-1.5b-instruct-q4_k_m.gguf': '6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e',
 'artifacts/local-inference/runtime/llama-b11827-bin-ubuntu-x64.tar.gz': '7c1de2b2a139aa90e28b88d44a75f5966485604f68aa0ccdc2339959bca9b5f6',
}
for name, expected in items.items():
    with Path(name).open('rb') as stream:
        if file_digest(stream, 'sha256').hexdigest() != expected:
            raise SystemExit('Checksum mismatch: ' + name)
print('Model and archive checksums verified')
PY
tar -xzf artifacts/local-inference/runtime/llama-b11827-bin-ubuntu-x64.tar.gz \
  -C artifacts/local-inference/runtime/llama.cpp-b11827-linux-x64
```

The resulting server path must match `configs/qwen-cpu-linux.json`. Model/server
hashes are checked again before execution. Retain the runtime's bundled notices.

## 3. Prepare Python environments

The fastest offline path is a verified export of the tested inference image.
Record the exported image archive hash, load it with `docker load --input PATH`,
and inspect its content identity. The recorded local image is
`sha256:3f1fc28da92c04f52ba621ac8837e010297c82982c04f13be86afd97301232b4`.
A fresh build is a new environment, not that historical image.

To build from the repository instead, explicitly run:

```sh
docker compose build dev
docker build -f ai/runtime/Dockerfile -t cybersoc-inference:layout-v2 .
docker image inspect --format '{{.Id}}' cybersoc-inference:layout-v2
```

These steps require network/package access. The runtime recipe pins its Python
base and Python packages; OS packages are resolved at build time, so record the
resulting image identity rather than claiming byte-identical rebuilds. Fresh
network builds have not yet been executed for this layout.

Set both launchers to the resulting full `sha256:...` identity. For example:

```sh
export NO_RAG_IMAGE="$(docker image inspect --format '{{.Id}}' cybersoc-inference:layout-v2)"
export VECTOR_LLM_IMAGE="$NO_RAG_IMAGE"
```

For an existing tested image, use its verified full identity instead. The launchers
reject mutable image tags. RAG's separate embedding environment is described in
[its guide](../../rag/vector/README.md). Both launchers mount source read-only,
disable external networking during inference and record the actual image identity.

## 4. Verify before incident inference

```sh
bash infrastructure/run-no-rag.sh --check
docker compose run --rm -T dev python -B -m unittest discover -s tests/runtime -v
```

`--check` validates source/model/server bytes and configuration without loading the
model. Then follow [No-RAG](../no_rag/README.md) or [Vector RAG](../../rag/vector/README.md)
for actual execution. A small structured-output smoke is also available in a
properly prepared Python environment:

```sh
python3 -B -m ai.runtime.smoke --config ai/runtime/configs/qwen-cpu-linux.json \
  --output artifacts/local-inference/runtime-checks/my-smoke-01
```

The output directory must be new. This command loads the model but no incident or
evaluator data. It needs Python 3.12 and `requirements.txt`, plus the runtime's OS
libraries; a successful smoke is compatibility evidence, not answer-quality evidence.

## Changes, failures and handoff

Keep model/runtime/budget changes explicit: create a new config and experiment
identity, run preflight and record actual output/failure. Do not edit a historical
lock to make a changed environment appear identical. Other model families,
quantizations or GPU offload need new measured compatibility checks. Kaggle/Colab
adaptation and GPU execution are still pending; notebooks must call these modules.

If startup fails, inspect the owned run's `runtime.log`, binary hash, companion
libraries, platform, loopback port 8087 and available memory. Do not kill another
user's process or silently substitute a model. Token-budget errors mean the input
needs a reviewed configuration change, not silent truncation. Invalid output and
policy failures must remain failures; response execution stays disabled.

A handoff must provide the exact source revision, source-release hash, model/runtime
identities, dependency/image identity, run/configuration identities and restore
commands. A fresh teammate run, hosted CI and cloud persistence are acceptance
checks beyond a successful local unit suite.

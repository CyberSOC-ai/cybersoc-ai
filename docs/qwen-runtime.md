# Linux CPU model runtime

The initial development model is Qwen2.5-1.5B-Instruct Q4_K_M. This is a provisional implementation choice; the final Qwen/Phi comparison remains separate. Use the existing Docker Python environment instead of installing packages into system Python.

## Pinned local artifacts

[The Linux configuration](../ai/baseline/configs/qwen-cpu-linux.json) records executable/model hashes, revisions and generation limits. Download these artifacts separately; weights, executables and run logs stay outside Git under `artifacts/local-inference/`.

- Model: [publisher GGUF repository at the pinned revision](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/tree/91cad51170dc346986eccefdc2dd33a9da36ead9), file `qwen2.5-1.5b-instruct-q4_k_m.gguf` (1,117,320,736 bytes). Retain its model card and license. Place the file under `artifacts/local-inference/models/qwen2.5-1.5b-instruct-q4_k_m/`.
- Runtime: [official llama.cpp b11827 Ubuntu x64 archive](https://github.com/ggml-org/llama.cpp/releases/download/b11827/llama-b11827-bin-ubuntu-x64.tar.gz). Archive SHA-256: `7c1de2b2a139aa90e28b88d44a75f5966485604f68aa0ccdc2339959bca9b5f6`. Extract under `artifacts/local-inference/runtime/llama.cpp-b11827-linux-x64/`, retaining the archive's `llama-b11827/` directory and adjacent libraries.

The artifact revision identifies executed weights. The separately recorded upstream revision is an inspected upstream snapshot, not verified conversion lineage. Download only the selected GGUF file, rather than every quantization in the repository.

## Container preparation

Run from the repository root, after reviewing [development setup](development.md):

```sh
docker build -f infrastructure/docker/Dockerfile.dev -t cybersocai-dev:latest .
docker build -f infrastructure/docker/Dockerfile.inference -t cybersoc-qwen-cpu:b11827 .
```

The derivative adds `libgomp1` and `libzstd1`, required by the Linux executable. Builds require network access. The base image and OS package repository can change; record image IDs and installed versions when reproducing a run. This is a tested local setup, not an immutable container distribution or a verified teammate reproduction.

## Bounded compatibility check

Choose a new run name for each attempt. The output parent must exist and be writable by container user 1000. These commands start and stop one temporary model process; they do not evaluate incidents.

```sh
mkdir -p artifacts/local-inference/runs
RUN_NAME=runtime-smoke-01
docker run --rm --network none --read-only \
  --memory=3g --memory-swap=3g --cpus=2 --pids-limit=128 \
  --cap-drop ALL --security-opt no-new-privileges \
  --tmpfs /tmp:rw,nosuid,nodev,size=134217728 \
  --mount "type=bind,src=$PWD,dst=/workspace,readonly" \
  --mount "type=bind,src=$PWD/artifacts/local-inference/runs,dst=/output" \
  --workdir /workspace --env PYTHONPATH=/workspace \
  cybersoc-qwen-cpu:b11827 \
  python -B -m ai.baseline.smoke \
  --config ai/baseline/configs/qwen-cpu-linux.json --output "/output/$RUN_NAME"
```

No ports are published. The smoke verifies model/executable hashes before startup, checks structured output against a tiny schema and saves configuration, environment, runtime version, timings and process shutdown in `report.json`. Existing output directories are rejected. Failure remains a failure; there is no repair or retry. Runtime logs and reports remain local; inspect them before sharing.

The smoke uses two inference threads, 32 output tokens and a 60-second generation deadline. Startup has the runtime's separate bounded health deadline. The checked-in incident configuration retains its own 512-token output budget. Successful `{"status":"ready"}` output establishes basic compatibility only; it does not validate SOC reasoning, the shared development release, or model quality. The historical pilot entry point still targets its historical dataset; use a dedicated shared-release entry point for new development runs.

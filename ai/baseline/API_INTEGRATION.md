# S1-T03 — Local backend integration evidence

Date: 2026-10-22 · Owner: Soulaiman · Local branch: `feature/11-baseline-slm-runner`.
Branch publication and PR review are authorized; no merge, reviewer agreement or task completion is claimed.

## Scope and source identity

Tested our runner against Oussama's actual backend snapshot from PR #79 at commit
`d1957f7a804fabb274dc6a771b4e6cbec4f45bac`, extracted from the fetched Git branch
into ignored `.local/api-integration/backend-snapshot`. No backend implementation
was copied into tracked source or merged into this branch. This is a pinned
snapshot test, not a claim about any subsequent PR changes.

Our implementation was uncommitted at measurement time. Project commit
`e8014108784a9ed8c99b623115a3f8f5fe496382` in the smoke trace identifies the base
checkout, not a commit containing these local changes. Review the local diff
alongside the evidence; no official experiment is claimed.

## What changed

- `compose_api` explicitly supplies the runner, fixed policy, trace version
  references, private runtime directory, one-call concurrency and bounded deadline
  to the backend's existing factory. The caller owns model loading/lifecycle.
- Conditional integration tests exercise the actual ASGI handlers and SQLite
  repository when S1-T04 is present in a POSIX environment. They skip with an
  explicit reason on this branch without the backend, or on native Windows.
- CLI tests now inject checkout identity through `git_state`, avoiding a test-only
  dependency on Git in the slim container. Actual CLI runs still read real Git state.
- `integration_smoke.py` runs a real model through the API, verifies stored
  result/trace identity and retains local evidence. It publishes no API port and
  enables no response execution.

## Environment and portability findings

The first native Windows attempt failed because the backend repository enforces
POSIX ownership through `os.getuid()`. Those controls were not patched or bypassed.
Docker Desktop was started, and validation moved to a non-root Linux container
using Python 3.12 and the backend snapshot's pinned requirements.

Temporary integration image:
`sha256:ca2a731d2f0e27f50f9dde5900103bd7777b114d3204bae192d00fdf7a43bded`.
It uses the project's Python 3.12 slim-bookworm family with `libgomp1` added for the
Linux CPU model runtime. The shared project Dockerfile/Compose and requirements
were not changed by this integration exercise.

Linux llama.cpp b11827 archive SHA-256:
`7c1de2b2a139aa90e28b88d44a75f5966485604f68aa0ccdc2339959bca9b5f6`.
The official archive and extracted executable were checked before inference.
The GGUF model is the same pinned Qwen Q4_K_M artifact as the development pilot.
This is not a comparison between Windows and Linux performance.

The composition uses an explicit 180-second inference deadline rather than the
backend's 30-second default. Phi's previous CPU observations can exceed 30 seconds;
this is a bounded local configuration, not removal of timeout enforcement.

## Verification

| Check | Observed outcome |
|---|---|
| Baseline suite, with actual backend available | 21 tests passed |
| Oussama's backend suite | 20 tests passed |
| Existing contracts and evaluation suites | 19 + 43 tests passed |
| Combined Python 3.12 Linux run | **103 tests passed** |
| New synthetic incident through API | HTTP 201 |
| Identical duplicate | HTTP 200, existing incident retained |
| Actual Qwen investigation through API | HTTP 200, contract-valid No-RAG result |
| SQLite persistence | Exactly one investigation result and matching baseline trace |
| Timeout / unavailable model / invalid output | Controlled integration tests returned 504 / 503 / 502 and persisted failure records |

The real smoke uses an in-process ASGI HTTP client. Model requests use container
loopback; no Uvicorn TCP listener or external client was tested. The container ran
with networking disabled except its loopback and source mounted read-only. SQLite
ran in a private temporary directory owned by the non-root service user, outside
the snapshot source tree. Its evidence copy remains in ignored local storage.

The real smoke tested one successful Qwen incident. Error mappings were exercised
with controlled generators, not induced real-model outages. No Phi-through-API,
live Wazuh ingestion, multi-client deployment, authentication, human approval or
action execution is established. A dependency warning about the backend's
httpx-based TestClient was emitted; it did not fail the tests and dependency pins
were not changed to suppress it.

## Local reproduction and evidence

Ignored assets under `.local/api-integration/` contain the pinned backend snapshot,
temporary image Dockerfile, test launcher, Linux model configuration and evidence.
Completed smoke evidence is under `evidence/qwen-smoke/`: HTTP statuses, output,
trace, raw model answer, measurements, SQLite copy, runtime log and artifact hashes.
Inspect before sharing. These files have not been published.

With the recorded local image/assets available, run the checked-in smoke module
inside the container with trusted arguments:

```sh
python -B -m ai.baseline.integration_smoke \
  --backend-root /workspace/.local/api-integration/backend-snapshot \
  --backend-commit d1957f7a804fabb274dc6a771b4e6cbec4f45bac \
  --project-commit e8014108784a9ed8c99b623115a3f8f5fe496382 \
  --config /workspace/.local/api-integration/linux-config.json \
  --output /evidence/a-new-run
```

The command assumes the read-only project mount at `/workspace` and an explicitly
writable local evidence mount at `/evidence`. Choose a new output directory; old
run evidence is not overwritten. Configuration and source paths are trusted CLI
inputs, never HTTP/model-controlled imports. The caller must identify the actual
backend/project state when repeating this on changed source.

## Remaining handoff

Agree the interface and local deployment settings with Oussama, recheck against
the backend's approved merged revision, and obtain reviewer/CI evidence before
closing S1-T03. Prompt quality review remains deferred at Soulaiman's request.
The successful connection does not change the weak development-pilot accuracy
reported in [LOCAL_RESULTS.md](LOCAL_RESULTS.md).

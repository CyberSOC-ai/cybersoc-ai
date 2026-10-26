# Sprint 1 API — Issue #12

For saved Wazuh exports, first use the [SOC alert normalizer](normalizer/README.md)
to produce incident v1 JSON suitable for `POST /incidents`.

The FastAPI boundary validates normalized incidents, stores them in SQLite and dispatches No-RAG investigations through an injectable runner. [Existing v1 contracts](contracts/README.md) remain unchanged. [Runner interface](RUNNER_INTERFACE.md) was documented before dispatch implementation, then approved by Soulaiman and successfully exercised with Qwen in a Linux in-process ASGI smoke. See the [scoped integration evidence](../ai/baseline/API_INTEGRATION.md). A missing real runner is an explicit 503, not a successful synthetic answer.

## Run locally

The backend currently supports **Linux, Docker/Linux containers or an appropriate Linux environment such as WSL2**. Native Windows Python is unsupported because runtime-path and SQLite ownership checks use POSIX APIs including `os.getuid()`. Windows users should run the backend inside a Linux environment (for example, Docker Desktop Linux containers or WSL2), retaining ownership checks. An explicit runtime directory alone does not provide native Windows support. Only the documented Linux container integration is evidenced here; validate the chosen host/VM setup separately.

From the repository root, using the [Docker development environment](../docs/development.md):

```sh
docker compose build dev api
docker compose up -d api
curl --fail http://127.0.0.1:8000/health
curl --fail -X POST http://127.0.0.1:8000/incidents \
  -H 'Content-Type: application/json' \
  --data-binary @backend/contracts/v1/examples/incident.json
curl -i -X POST http://127.0.0.1:8000/incidents/INC-001/investigate
```

The last request returns **503 dependency_unavailable** with the default application. `/docs` and `/openapi.json` describe the HTTP API, including embedded local copies of the unchanged JSON Schemas and a synthetic incident example. API health returns storage state and runner configuration separately; `configured_not_probed` is not proof that a model is ready. Health performs no inference or external requests.

Compose publishes only `127.0.0.1:8000`. Uvicorn listens on the container interface so that port forwarding works; this is not permission to publish the host port publicly. The development API has no authentication and is for a trusted single-user loopback environment. Add reviewed authentication/authorization and transport protection before exposing it beyond loopback; private lab networking alone is not identity. No CORS access is enabled.

For a configured **Linux host Python environment**, run:

```sh
uvicorn backend.app:create_app --factory --host 127.0.0.1 --port 8000 --workers 1
```

There is no environment variable or HTTP parameter that dynamically imports a runner. S1-T03 supplies the [composition helper](../ai/baseline/api_adapter.py) calling `create_app(runner=real_adapter)`; never attach a test runner to the deployed service. After trusted model loading and policy/version setup, a Python composition entry point can explicitly use:

```python
from ai.baseline.api_adapter import compose_api

app = compose_api(core, policy, versions, runtime_dir, timeout_seconds=180)
```

Here `core`, `policy`, `versions` and the private `runtime_dir` are configured by trusted deployment code, not HTTP input. The backend default remains **30 seconds**; `compose_api` currently defaults to **180 seconds** for CPU use and passes an explicit setting to the backend. Keep the core/model runtime deadline consistent; the earlier effective deadline wins. This is bounded configuration, not disabled timeout enforcement. Phi CPU runs may require the longer budget, but Phi-through-API remains unverified. The existing default Compose application deliberately has no runner and still returns 503. A real llama.cpp runtime also needs its own verified binaries/libraries; the reported integration image included `libgomp1`.

## Persistence and event identity

`SQLiteRepository` implements the `Repository` protocol; routes do not issue SQL. SQLite uses per-operation connections, parameterized queries, foreign keys and transactions. `BEGIN IMMEDIATE` serializes event ingestion; unique constraints cover both incident ID and `(source, source_event_id)`.

- A new event returns 201 and a receipt with `schema_version`, original `incident_id` and `created: true`.
- An identical event returns 200 and that original ID with `created: false`, even when the incoming delivery supplies a different incident ID.
- Event comparison uses decoded JSON content, ignoring object-key order, the delivery's incident ID, `ingestion_kind` and `raw_event_ref`. Entity-array order remains significant. Original event/provenance is immutable; successful delivery metadata is stored separately.
- Different event content under the same source/event key, or reuse of an incident ID for a different event, returns 409. No evidence is overwritten.
- Each investigation result and its correlated baseline trace are saved together in one transaction before a response is reported successful. Repeated investigation requests create distinct attempts; they are not deduplicated model calls.

Compose stores the database in the persistent `api-runtime` named volume at `/runtime`, owned by the non-root service user. Source remains mounted read-only at `/workspace`. The host default is `/tmp/cybersoc-ai-<uid>`; override with `CYBERSOC_RUNTIME_DIR` pointing to a private service-owned directory outside the source tree. Runtime-directory permissions must be 0700 and the SQLite file is 0600. Source-tree directories, runtime-directory symlinks and database symlinks are rejected. `/tmp` is development storage and may be cleared by the OS; select a durable private host path when retaining evidence.

Database contents include incident text and sanitized results/traces and remain local/private, outside Git. Input producers must remove secrets before submission; this API does not claim to detect every secret or anonymize arbitrary free text. Raw-event references are stored as inert strings and never dereferenced. This minimal incident/result repository is not the future S4 append-only approval ledger.

Stop the service with `docker compose stop api`. Restart with `docker compose start api`; the named volume persists. Do not delete the volume as a routine cleanup step. No approval/response/executor routes exist.

## HTTP behavior and validation

| Operation | Success | Failure behavior |
|---|---|---|
| GET `/health` | 200 API/storage health, separate runner-configuration fields | 503 if persistent storage is unavailable |
| POST `/incidents` | 201 new event; 200 identical duplicate | 409 conflicting identity; 422 invalid contract/version |
| POST `/incidents/{incident_id}/investigate` | 200 validated/persisted No-RAG result | 404 unknown incident; 503 missing/busy/unavailable runner; 504 deadline; 502 invalid output/runner failure |

POST `/incidents` requires `application/json`. Investigation accepts an empty body or `{}` only: clients cannot override mode, timeout, model/configuration, identity or policy. Versioned incident validation uses `jsonschema` Draft 2020-12, format checking and a closed offline schema registry, not Pydantic coercion. Unsupported versions use `unsupported_version`; malformed JSON uses 400 `validation_error`; wrong media type uses 415. Duplicate JSON keys, NaN/Infinity/overflowed numbers, invalid UTF-8 and nesting above 32 levels are rejected. API IDs, dates, typed entities and unknown fields retain their strict contract rules.

All requests are bounded to 65536 body bytes, including chunked bodies and absent/lying Content-Length; excess is 413. Body receipt has a five-second deadline (408). Model output is bounded to 131072 serialized UTF-8 bytes before schema validation. Default inference deadline is 30 seconds and concurrency is one per process, with no waiting queue. These limits are deployment settings supplied to `create_app`, not request parameters. Only one Uvicorn worker is supported for the laptop; using more processes would multiply concurrency.

Most errors use `{"error":{"code":"validation_error","message":"...","retryable":false}}`, reusing the common v1 error definition. Attempted inference failures return a complete v1 `status: error` investigation (with backend-created IDs and empty evidence/actions) and are persisted with a failed trace. Missing-runner, saturation and pre-dispatch errors use the small envelope. Storage errors are 503 `audit_unavailable`; no success is returned when result/trace storage fails. Messages never contain exception strings, request bodies, model text or database paths. `retryable` does not trigger automatic retries.

A timeout cannot kill a Python thread. Its concurrency slot remains occupied until it actually exits, and a late answer cannot overwrite the recorded timeout. The same capacity bound holds after caller cancellation. The real runner must respect the supplied monotonic deadline; hard cancellation requires a supervised process/service. An abrupt process crash or cancelled HTTP handler may leave no completed result/trace; this implementation is not a durable work queue or crash-recovery scheduler. Runner code is trusted application code, while its candidate output is untrusted and must pass schema and relational checks. Recommendations stay `proposed` and confer no execution authority.

## Verification and completion boundary

```sh
docker compose run --rm -T dev python -B -m unittest discover -s tests/backend -v
docker compose run --rm -T dev python -B -m unittest discover -s tests/contracts -v
docker compose run --rm -T dev python -B -m unittest discover -s tests/evaluation -v
docker compose run --rm -T dev ruff check --no-cache .
python3 -B infrastructure/ci/check_repository.py
```

Backend tests use controlled runners exclusively; they cover successful and failed dispatch, strict input/output validation, local OpenAPI references, persistence, concurrent deduplication, sanitation, timeout/late-result/cancellation behavior and body limits. CI explicitly discovers backend tests alongside the existing suites. Passing API tests does not establish model quality, actual GPU fit or the full lab-to-model pipeline. Soulaiman's [integration report](../ai/baseline/API_INTEGRATION.md) and [PR comment](https://github.com/CyberSOC-ai/cybersoc-ai/pull/79#issuecomment-6353520974) additionally report one successful real Qwen **in-process ASGI** request with SQLite result/trace persistence and a 103-test combined Linux run against backend snapshot `d1957f7`. This is historical owner-reported evidence; the runner checkout was dirty and detailed artifacts remain local, so it is not an independently reproduced official benchmark. Backend files were unchanged between that snapshot and the approved final PR head. The [formal approval](https://github.com/CyberSOC-ai/cybersoc-ai/pull/79#pullrequestreview-5633412190) agrees the tested interface.

The original backend smoke tested a Uvicorn loopback listener with **no real runner**. The separate Qwen integration used an ASGI client **without a Uvicorn TCP listener**. These two checks do not jointly prove an externally served real-model deployment. Phi-through-API, real-model external clients, live Wazuh integration, authentication and multi-client deployment remain unverified. Live normalized alerts and the full end-to-end baseline remain #14/#15 work; model quality and remaining S1-T03 acceptance remain #11 work. They are not additional Issue #12 acceptance criteria. This documentation follow-up downloads no models and runs no new model inference, benchmarks, training, RAG or response execution.

## Issue #12 acceptance and closure assessment — 2026-10-23

Re-read the [exact issue criteria](https://github.com/CyberSOC-ai/cybersoc-ai/issues/12) and [CDC §14](../docs/CDC.md#14-definition-of-done). The required scope is health/incident validation and the baseline investigation endpoint/OpenAPI, with validation evidence and applicable DoD conditions.

| Acceptance / DoD requirement | Evidence / remaining action |
|---|---|
| Health endpoint; incident validation | Implemented, backend tests and loopback smoke documented in PR #79 and Oussama's journal |
| Baseline investigation endpoint; OpenAPI | Implemented, controlled success/error tests plus Soulaiman's scoped real Qwen integration |
| Validation and affected documentation linked in PR | [PR #79](https://github.com/CyberSOC-ai/cybersoc-ai/pull/79) links implementation, security controls, test results and runner handoff; this documentation correction is local pending publication |
| Dedicated branch, relevant tests, passing checks, no secrets | Original feature branch, 82 local tests, staged secret scan and successful hosted CI; see linked runs below |
| Requested reviewer and feedback handled | Soulaiman formally approved the final head; Windows/timeout documentation feedback is addressed in this follow-up, not yet merged |
| Owner sprint documentation and linked closure | [Oussama's Sprint 1 journal](../docs/sprints/sprint-01/README.md#5-oussama) records implementation and merge evidence; this follow-up needs its approved publication/CI/review/merge workflow, and Issue #12 remains open |
| Experiment metadata when applicable | Issue #12 is backend implementation, not a model benchmark; referenced S1-T03 smoke metadata and limitations remain in its evidence record, without claiming full experiment reproducibility |

PR #79 merged at `7e4bdb2533541a1cc52feff43b3c72d48280d14f` on 2026-10-23 19:25:40 UTC. Its [final-head CI](https://github.com/CyberSOC-ai/cybersoc-ai/actions/runs/40011091986) and [post-merge main CI](https://github.com/CyberSOC-ai/cybersoc-ai/actions/runs/40011328644) passed, including backend, baseline, contract and evaluation suites, lint and secret scanning. These are evidence for PR #79, not hosted CI for this local documentation branch.

No additional blocking code requirement was identified for Issue #12. Its technical acceptance scope is satisfied; formal Done/closure remains pending the documentation follow-up workflow and Oussama's explicit closure approval. Do not require a model-quality benchmark, native Windows support, authentication/public deployment or live Wazuh integration to close this scoped issue.

# Baseline runner coordination proposal — Issue #12

Proposed for Soulaiman (S1-T03 / issue #11), documented before backend runner integration on 2026-10-22. No agreement, real model integration or model run is claimed. Issue #11 does not formally block independent S1-T04 development.

## Interface and ownership

The application factory accepts a trusted, process-local `BaselineRunner` object. The default is **no runner**: investigation of an existing incident returns HTTP 503 with `dependency_unavailable`, never a synthetic successful answer. Test runners live only in automated tests. No request can select/import code, choose a model path or configure a runner.

The proposed synchronous Python protocol is `run(request: RunnerRequest) -> dict`. `RunnerRequest` contains a detached validated incident, backend-issued `investigation_id` and `trace_id`, and an absolute `deadline_monotonic` in seconds from `time.monotonic()`. Input mode is always `no_rag`, one incident per call. No labels, evaluator context or retrieval packet is supplied. The incident already contains `schema_version: 1.0.0`; its original identity, source severity and ingestion provenance must be retained. Raw-event references are inert data, not fetch instructions.

The runner also exposes `versions`: the five strings required by the existing trace contract (`model`, `prompt`, `dataset`, `configuration`, full lowercase 40-character `commit`). Use immutable/versioned references resolvable through the S0-T06 experiment manifest; `dataset: not_applicable` is permitted for an individual API request, with the applicability reason in its external manifest. Model/configuration selection, tokenizer/chat template, prompt construction and actual inference remain S1-T03 responsibilities. Validate this configuration at application construction; do not load models in health or request handlers.

Return a complete candidate [investigation result](contracts/v1/investigation-result.schema.json) with the supplied IDs, `mode: no_rag`, no retrieved evidence and only `proposed` recommendations. The backend checks the unchanged JSON Schema plus cross-record identities, action IDs and proposal status before storing or reporting success. Inference cannot approve or execute actions. Source alert severity is distinct from assessed `risk_level`. The backend persists the incident, result and baseline trace; the runner does not write the API database. Configuration is trusted deployment input; model output is always untrusted.

## Deadlines, errors and concurrency

Default API inference timeout: 30 seconds; default concurrent calls: 1, per application process. There is no waiting queue: a saturated runner returns HTTP 503. The API runs blocking inference off the event loop. A timeout returns HTTP 504 and records a failed investigation. Python cannot safely kill an inference thread: its slot remains occupied until the call exits, and a late answer is discarded. Client cancellation similarly does not permit unbounded replacement calls. The real runner **must** honor the deadline, including bounded loading/network/generation, or use a separately supervised process/service for hard cancellation. One Uvicorn worker is the supported SQLite/laptop configuration; multiple processes would multiply concurrency limits.

Raise `RunnerUnavailable` for missing/unavailable model resources (503) or `RunnerTimeout` for an internal deadline (504). Unexpected exceptions and invalid candidate output become sanitized `invalid_output` (502); exception text and model output are never included in HTTP errors. A schema-valid candidate `status: error` is not success: allowed inference errors map to 503/504/502. Backend storage failures return sanitized 503 `audit_unavailable`; success requires durable result/trace storage. Every actual inference attempt has a backend-created investigation/trace identity. No automatic inference retries.

## Items for agreement with Soulaiman

- Confirm the synchronous adapter signature and ownership of candidate construction versus raw model decoding.
- Confirm cooperative deadline behavior and whether a process/service boundary is needed for hard cancellation.
- Supply accurate version references and an external manifest; do not substitute API code SHA for the upstream model revision.
- Confirm structured-output failure semantics and the bounded proposal fields required by v1.
- Real runner and API integration remain pending S1-T03. Controlled tests demonstrate API behavior only; they are not model-quality or real-model compatibility evidence.

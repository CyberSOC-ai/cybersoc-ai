# S0-T03 — Versioned interchange contracts

Owner: Oussama · Reviewer: Ahmed · Date: 2026-10-13 · [Issue #3](https://github.com/CyberSOC-ai/cybersoc-ai/issues/3)

Status: local contract implementation; peer review, PR CI and integration pending.
Authority: [CDC §6](../../docs/CDC.md#6-core-contracts), [architecture handoffs](../../docs/architecture/README.md#5-interface-map) and [security policy](../../security/README.md). These schemas elaborate the CDC examples; consumers must adopt the explicit `schema_version: "1.0.0"` envelope. No runtime API, storage, approval service or executor is implemented here.

## Contract map

Schemas use JSON Schema Draft 2020-12. All objects reject unknown properties. IDs are opaque, case-sensitive bounded identifiers; text is bounded. UTC timestamps must be valid RFC 3339 date-times ending in `Z`. IP entities accept IPv4/IPv6; domain entities use hostname validation; hash entities accept hexadecimal MD5/SHA-1/SHA-256 identifiers (for IOC matching, not security-sensitive hashing). Enable format checking: some JSON Schema implementations treat `format` as annotation only.

| Schema | Producer → consumer | Required information / behavior |
|---|---|---|
| [Incident](v1/incident.schema.json) | Normalizer → backend | Identity, event identity, UTC event time, source severity, description, typed entities, live/replay/synthetic origin; optional protected raw-event reference |
| [Retrieval request](v1/retrieval-request.schema.json) | Pipeline/agent → retriever | Request/trace identity, Vector/Graph/Hybrid mode, query, bounded `top_k` (1–100), typed source/snapshot filters |
| [Retrieval response](v1/retrieval-response.schema.json) | Retriever → pipeline/agent | Same request/trace identity, success or error, evidence with source record and snapshot references, method and score semantics |
| [Investigation result](v1/investigation-result.schema.json) | Pipeline → backend validator | Investigation/incident/trace identity, mode, outcome; successful output includes summary, triage verdict, assessed risk, evidence, MITRE IDs and proposed actions |
| [Response action](v1/response-action.schema.json) | Model proposal → backend → later executor | Exact versioned lab proposal, fixed typed arguments, approval-required invariant, lifecycle record and server-recorded authorization references |
| [Trace](v1/trace.schema.json) | Baseline/workflow → trace sink | Correlated run, model/prompt/dataset/configuration/commit references, UTC run times, outcome and bounded ordered steps |
| [Common definitions](v1/common.schema.json) | All contracts | IDs, UTC times, severity, modes, evidence, errors and version references |

The `.invalid` schema IDs are stable identifiers, not network endpoints. Register every local schema by its `$id`; resolve references from that registry and refuse remote resolution. The tests do this offline. Repository placement under `backend/contracts/` denotes API ownership, not a requirement to import a backend runtime into AI/RAG components.

## Incident ingestion and result semantics

`source_event_id` identifies an event within `source`; the producer must ensure uniqueness for that source. The backend deduplicates on `(source, source_event_id)`: an identical normalized incident returns the existing incident reference; different event content for the same key returns `conflict` and never overwrites evidence. Compare event content excluding delivery metadata (`ingestion_kind` and raw-reference location); keep replay delivery metadata separately without rewriting the original event. Persist assigned incident IDs rather than generating a new one on each delivery. Transport-level idempotency and atomic storage belong to S1-T04. Deliberate scenario repetitions use distinct event IDs; replay of the same event keeps its identity and is labeled `replay`. Raw references are data, never an instruction to fetch arbitrary URLs.

Incident `severity` is the detector's normalized severity. Investigation `risk_level` is the AI assessment and must remain separate. `triage_verdict` allows `undetermined` so absent context does not force fabricated ground truth; dataset expected labels and judging are owned by S1-T02. `mitre_techniques` can be empty when unsupported.

No-RAG results carry no retrieved evidence. Recommendations must remain `proposed`, with no approval/execution metadata. Candidate model output is validated before storage/reporting as successful. API route names, synchronous/asynchronous completion and persistence technology remain S1-T04 decisions.

## Retrieval, evidence and errors

`ok` with an empty evidence list means search completed and found no evidence. `error` requires a structured error and an empty evidence list; failed retrieval must not silently become No-RAG. Partial-success retrieval is excluded in v1: fail explicitly when a required store fails, or use a separately configured and recorded mode before the request.

Evidence is cited by `evidence_id`, resolved to `source_record_id` in `snapshot_ref`. Producers assign unique evidence IDs within a result. References must point to sanitized records available to authorized consumers, not raw secret-bearing logs. Filters are limited to sources and snapshot references; graph query templates and tool allowlists are future adapter work. `top_k=5` is the CDC default chosen by callers; schemas do not insert defaults. Responses must contain at most the requested `top_k` entries, enforced by the caller because JSON Schema cannot compare separate messages.

Scores carry `score_kind`: cosine (higher is better), distance (lower is better), rank (lower is better), reciprocal-rank fusion / `rrf` (higher is better), or `none` with null score. Native store scores must not be directly compared across methods. Hybrid fusion proposes RRF over ranked lists; exact weighting and tuning remain S3-T06 responsibilities and must be recorded in configuration. Validate ranges according to the selected adapter. Missing evidence differs from unknown relevance.

Common error codes: `validation_error`, `unsupported_version`, `conflict`, `dependency_unavailable`, `timeout`, `invalid_output`, `permission_denied`, `audit_unavailable`. Messages are sanitized and contain no stack traces, tokens or raw private logs. `retryable` is advice for bounded reads/inference, never permission to repeat a state-changing action. `unknown` execution outcomes require reconciliation even if an underlying error is transient. Errors at other boundaries reuse the common definition; HTTP status mapping belongs to S1-T04.

## Response proposals and authorization

V1 specifies the planned initial `block_ip` adapter only; it enables no tool. `target` is the stable registered endpoint ID where the rule would be applied, not the source address being blocked. `arguments.source_ip` is that source address, with fixed port/protocol and duration (1–3600 seconds). These schema caps are proposal-validation ceilings, not granted capabilities. Deployment policy can impose stricter limits. New action types require a reviewed contract version and typed adapter, never a free-form shell field.

The immutable binding covers these proposal fields, in this exact conceptual set: schema version, action ID, incident ID, revision, action type, target, target inventory revision, environment ID, policy version, arguments, reason, expected effect, risks, rollback plan, requires-approval flag and idempotency key. In S4, canonicalize that object using [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785), hash its UTF-8 representation with SHA-256 and store the lowercase hexadecimal digest server-side. Approval metadata, lifecycle status, execution reference and errors are excluded from the digest. Client/model-supplied digests and actor IDs are never trusted. A change to any bound field requires a new revision and explicit new approval. `idempotency_key` is unique per action revision and environment, issued by the backend.

| Lifecycle record | Schema requirement | Future runtime requirement |
|---|---|---|
| proposed | No approval, execution reference or error | Validate current policy, target and arguments before presentation |
| approved | Approval with `approve`, actor/time/expiry/digest/audit reference | Authenticate actor; recompute binding; persist decision and audit |
| rejected | Decision `reject` | Terminal denial for revision |
| expired / revoked | State recorded | Terminal denial; preserve prior decision in append-only history |
| executing | Approve decision and execution reference | Atomically claim once after all executor rechecks |
| succeeded | Approve decision and execution reference | Record actual target effect and durable outcome |
| failed / unknown | Approve decision, execution reference and explicit error | Record outcome; reconcile unknown effects before new approval/retry |

The schema validates record shape, not permitted transitions or authority. S4-T05/S4-T06 must verify authentication, authorization, registry membership, environment isolation, inventory revision, digest equality, timestamp ordering, expiry/revocation/consumption, concurrency and audit persistence. A private IP, valid digest-shaped string or client `approved` state proves none of those. Test fixtures include only proposed actions and documentation-only addresses. Approval test records use dummy digests, not signed authorization.

## Trace and compatibility

`workflow` distinguishes `baseline`, `single_agent`, and `multi_agent`; baseline steps cannot claim to be agents. Agent steps name one of the six CDC roles. Success steps require output references; failure steps require errors. All runs reference exact configuration and version identifiers; absent versions must be explicitly represented by an agreed sentinel such as `not_applicable`, not omitted. S0-T06 owns the final naming convention, so examples use visibly synthetic version names.

Consumers must check unique contiguous step numbers starting at 1, chronological start/finish times, consistent run/step outcomes, incident/action/citation references and unique evidence IDs. These relational checks require application logic and are future integration requirements. A failed workflow may preserve successful earlier steps; sanitize or protect referenced input/output content. Do not store credentials or unrestricted prompts in Git.

The six [example files](v1/examples/incident.json) are synthetic fixtures, not collected incidents or model runs. The cross-reference test verifies the fixture bundle remains consistent. Consumers explicitly reject unsupported versions before integration. Any contract change needs reviewed downstream impact; changes to required fields, semantics, enums, bounds or unknown-field policy require a new version. Keep this v1 schema immutable once adopted. Store/transport and tool framework choices stay behind these boundaries.

## Validation and acceptance evidence

Run from the feature worktree root:

```sh
python3 -m venv /tmp/cybersoc-contracts-venv
/tmp/cybersoc-contracts-venv/bin/python -m pip install -r requirements.txt
/tmp/cybersoc-contracts-venv/bin/python -B -m unittest discover -s tests/contracts -v
python3 -B infrastructure/ci/check_repository.py
git diff --check
```

The contract suite checks all schema definitions, valid examples, required fields/versioning, incident identity/time, bounded typed retrieval, provenance, score semantics, empty versus failed retrieval, investigation failure output, approval-required actions, lifecycle record shape, baseline/agent traces and fixture references. Runtime security, digest recomputation and integration behavior are explicitly outside these schema-only tests.

| Issue acceptance group | Delivered evidence |
|---|---|
| Incident and retrieval contracts | Three schemas, examples, semantics and negative tests |
| Investigation and response contracts | Two schemas, examples, immutable-binding specification and negative tests |
| Agent trajectory contract | Trace schema/example and baseline/single-/multi-agent tests |
| Validation and affected documentation | This README, test suite and Oussama's sprint journal |
| Definition of Done | Local artifacts delivered; assigned review, authorized PR/CI/merge and issue closure remain pending |

## Regex audit and CI correction — 2026-10-14

Audited all seven `pattern` occurrences: shared IDs, evidence IDs, UTC suffix,
MD5/SHA-1/SHA-256 entity hashes, Git commit SHA, MITRE technique IDs and proposal
digests. Replaced each final `$` with `(?![\s\S])`, a negative lookahead that
requires the actual end of the string. It is compatible with JSON Schema's
ECMAScript regex dialect and Python's validator; no Python-only end anchor is
used. Existing start anchors and character/length restrictions remain intact.
All seven patterns were also checked with Node's ECMAScript regex engine using
valid controls and trailing newline, CRLF, Unicode separator and whitespace cases.
UTC still requires format checking for date validity; its regex enforces the
terminal `Z` independently. This is a correction to the unmerged v1 draft.

Five regression methods cover newline/CRLF/Unicode line separators, whitespace,
invalid characters and lengths, with valid boundary controls for IDs, MITRE
techniques, all supported hash lengths, commit/digest forms and UTC timestamps.
The new tests reproduced the defect before correction. The full suite now has
17 test methods.

The existing `repository-checks` GitHub Actions job installs the pinned contract
test dependency on Python 3.12 and runs the full suite after repository checks.
Existing PR/main triggers, read-only workflow permissions and the required job
name remain unchanged. Hosted CI execution remains pending an authorized push
and PR; local test results are not a hosted CI result.

## S2-T01 source extension — 2026-10-29

The draft v1 evidence source enum additionally accepts `detection_rule` and
`playbook` for the user-approved corpus expansion. Existing sources and valid
examples remain accepted; no API operation or result shape changes. Consumers
that copied/froze the enum must refresh it before ingesting these sources.
The expanded offline tests validate both values against the retrieval-response
schema. This pre-merge schema extension requires Soulaiman's handoff review.

KEV/CNA enrichment remains attached to CVE records with source provenance chains;
consumers must cite supplemental claims to their own snapshots. Dataset split
metadata is not model evidence. See the [source-selection rationale](../../datasets/knowledge/SOURCE_SELECTION.md).

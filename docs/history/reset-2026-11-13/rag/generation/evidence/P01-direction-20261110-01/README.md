# P01 direction-definition comparison — 2026-11-10

**Source-IP direction failed again.** One action used destination `10.77.0.20`
as source; no abstention occurred. The complete raw decision was byte-identical
to the boundary run. Quotation relevance passed, but unsupported T1078 and action
reasoning remained unchanged. This is a negative single-case result, not proof
that definitions can never help. Reviewer acceptance and #19 remain pending.

The [complete synthetic packet](evidence.json) preserves the actual inputs,
retrieved passages/IDs, catalogue/exclusions, messages/schema, formatted prompt,
raw answer, complete structured result, recorder, configurations/source hashes,
comparison receipts and previous boundary result. Full source, transport events,
health/resources, checks and checksums remain at
`.local/P01-direction-20261110-01/`. Artifact access owner: Anas. Packet text is
verbatim synthetic/reference data; nothing was repaired, hidden or substituted.
All earlier failures remain preserved.

## Comparison confirmed before inference

- Incident, policy and retrieval-request bytes were identical to the boundary run.
- Actual live response, evidence order/scores, six candidates and five exclusions
  matched. Full P01 query, MITRE-only K=2 and exact search were unchanged.
- System prompt, runtime launch and decoding settings matched. Removing only
  target/source_ip descriptions reproduced the prior decision schema and user
  message. Replacing that user message in the formatted prompt reproduced the
  prior formatted prompt exactly. The descriptions reached prompt text and the
  separate grammar schema; no other model-input change was made.
- Actual input: **2,462 tokens**, versus 2,378 before (+84), under cap 3,072.
  Output cap 512, context 4,096 and shared diagnostic deadline 300s were unchanged.
  No candidate was selected manually. Labels/manual example were not model input.

The saved pre-inference inspection binds request/catalogue/exclusion hashes.
Post-run comparison also confirms identical runtime-file hashes and all pinned
configuration fields. Only the internal descriptions define observed containment
endpoint, event-relative originating peer and abstention if direction is missing.
No parser, role validator, mapping rule, extra stage or action-field rule changed.

## Source direction first

The output proposed target `linux-01`, source_ip `10.77.0.20`. The supplied report
explicitly states `src=192.0.2.10 dst=10.77.0.20`. The selected argument therefore
contradicts the supplied directional role. Entity membership and schema validity
do not make it correct. The argument and all associated text are retained exactly.

**No abstention occurred and correct source selection was not demonstrated.**
An empty list, had it occurred, would require assessing its justification and
would not demonstrate selecting the right IP. Here the wrong selection is explicit.
The descriptions were delivered, but the output did not follow that relationship;
the artifacts do not reveal the model's internal cause.

## Quotation, mappings and every action field

Selected Q-000-00201-00289 is exact SSH passage [201:289], 88 characters:

> SSH is a protocol that allows authorized users to open remote shells on other computers.

Integrity/boundaries and relevance to general SSH context pass. This statement
does not establish successful P01 access, credential validity, maliciousness,
account changes, IP roles or a block's effect. Both full actual passages remain
in the evidence array; reference knowledge is not incident observation.

This is manual technical assessment, not a formal CDC judge metric or independent
double annotation. Incident support is conditional on the supplied unverified
synthetic report, not independent verification of events.

| Field / claim | Assessment and source |
|---|---|
| Copied report: time, linux-01, sshd event, lab-admin | Exact incident.description with unverified-input attribution; no generated paraphrase |
| Copied report: source/destination, eight failures, 57s, password method, one account | Exact supplied observations; source roles are explicit in prose, not verified by references |
| Copied report: registry entry/source absence | Exact supplied observation; absence alone does not prove maliciousness |
| Copied report: no accepted session, service up, audit/heartbeat coverage | Negative evidence preserved; successful access not established |
| Quotation/citation | Exact complete unit and correct evidence pairing; relevant general fact, not proof of incident findings |
| true_positive | Defensible judgment that the suspicious attempt warrants investigation, not proof of compromise; no separate verdict rationale generated |
| medium risk | Defensible given repeated failures without reported session/impact; matching detector severity is not proof of independent reasoning |
| T1078 | Unsupported: no successful valid-credential use established. The full reference's general possibility does not establish occurrence |
| Omitted T1110.001 | Still differs from pending-review pilot mapping; retrieval lacks a dedicated supporting taxonomy passage. No replacement was forced |
| action_type=block_ip | Permitted proposal category only; does not establish warrant or correct arguments |
| target=linux-01 | Observed incident endpoint and policy-permitted fixture host |
| source_ip=10.77.0.20 | Wrong directional role; destination selected instead of reported source 192.0.2.10 |
| port=22, protocol=tcp, duration=300 | Runner-owned policy defaults within configured bounds; not independent network observations or proof the block is correct |
| reason: failed passwords, lab-admin, 57s, password method, one account | Supported by incident.description, but does not justify blocking destination; count/source/registry rationale is not developed |
| expected_effect: block source to prevent brute-force attempts | Unsupported for the actual destination argument; no directionally correct rule/effect was tested. Failures do not prove successful compromise |
| risks: may disrupt legitimate administrative tasks | Plausible conditional collateral warning, generic and incomplete; misses reversed role and actual impact assessment |
| rollback_plan | Inadequate: unspecified period, no exact-rule removal/restoration verification, wrong IP unrecognized; text preserved |
| Result schema/version, IDs, trace, mode/status | Trusted envelope/recorder identity; status=ok establishes structural completion, not semantic correctness |
| Evidence content/IDs/source/snapshot/method/scores | Actual live response retained; readback/cosine/eligibility checks applied |
| Action schema/revision/proposed/approval-required | Policy-derived metadata, not granted approval; no action executed |
| Action ID/idempotency key/incident identity | Runner-generated/copied identities, not model findings |
| Environment/inventory/policy identity | Recorded synthetic fixture configuration, not operational authorization |

## Outcome and before/after

One retrieval and one completion returned a complete validated vector result:
EOS, 175 output tokens, no truncation. Pipeline 141.803826s includes retrieval
2.762240s and client generation 138.842370s. Client time includes roughly 71s of
pre-inference inspection. Backend prompt 45.030927s/decode 21.705185s; TTFT was
not measured. Total recorder lifecycle 220.022909s includes prerequisite/setup
outside the pipeline deadline. Different inspection pauses prevent a speed claim.

| Dimension | Boundary run | Definition run |
|---|---|---|
| Input tokens | 2,378 | 2,462 |
| Source/action count | Wrong destination; one action | Same wrong destination; one action |
| Quotation | Relevant SSH definition | Same quotation |
| Mappings | Unsupported T1078 | Same unsupported T1078 |
| Raw judgments/action text | Previous answer | Byte-identical answer |

Both raw-answer SHA-256 values are
`c5ac3badf6951b40a76ff91a6f9382d26c618376b6cd391e627e9740733ed85e`.
Public generated IDs differ as expected; that is not changed reasoning.
The definitions produced **no observed decision correction in this attempt**.
This does not establish a general causal effect or lack of effect. No additional
attempt or implementation change follows automatically.

## Provenance, reproduction and checks

Pinned model: Phi Q4_K_M, SHA-256
01999f17c39cc3074afae5e9c539bc82d45f2dd7faa3917c66cbef76fce8c0c2.
Linux b11827/970b51ce7 executable:
92ff7abb8a59c94a98acdbca4f50aaf54d2cb08a05fad57b254587a101366aac.
CPU six threads/one slot, temperature0, seed42, cache_prompt=false, n_keep0,
no context shift. Existing 340-record/406-vector index receipt:
a612015b4246d0a4cb15c4c8c717422e161836afdd932486ba3fc278c907d59d.
BGE revision 5c38ec7c405ec4b44b94cc5a9bb96e735b38267a; Qdrant1.20.0.
Production default remains180s; diagnostic shared deadline300s included inspection.
Phi SWA-disabled warning and unverified GGUF conversion lineage remain limitations.

The snapshot matches the checked definitions export: 107 vector, 27 baseline and
20 contract tests passed, plus Ruff/integrity/whitespace. These 154 scoped tests
include instruction-delivery checks, not semantic correctness. Other suites were
not rerun for the annotation-only change; previous full-check/scanner records are
preserved. Final documentation/evidence checks are recorded separately. No hosted
CI result is claimed.

Reproduction requires separate authorization and a fresh directory, never marker
reuse. Supply the exact saved snapshot/check receipts, preview/runtime/model
artifacts, and recorder_source from the packet. Mount snapshot at
`/delivery/snapshot`, repository/preview at `/workspace`, runtime/models read-only
at `/runtime` and `/models`, sharing the existing Qdrant network namespace. Use
image9072b252d340280ba72ff364846ff39c5e372496bb1bcfa04c11b34f2900590e,
offline HF/Transformers flags, and `python -B /delivery/recorder.py`. It verifies
comparison and stops at the pre-inference hash/token inspection gate; no preferred
candidate, download, rebuild, fallback or retry is provided.

Incorrect source-role generation, unsupported mapping and inadequate action
reasoning remain unresolved. No perfect-accuracy requirement is invented, and
this wrong blocking IP is not accepted as correct. Assigned review and applicable
CDC requirements remain pending. No commit, push, merge or reviewer message was
performed. Work stops after this assessment and documentation.

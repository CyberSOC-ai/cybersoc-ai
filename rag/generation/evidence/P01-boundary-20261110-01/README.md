# P01 boundary correction — one approved live investigation

**Outcome: boundary correctness and quotation relevance passed for this case;
decision/action quality failed. Reviewer acceptance and #19 completion remain
pending.** A better quotation is not a fix for unsupported mappings or the wrong
blocking IP. No retries, repairs, hidden actions, model changes or extra experiments.

The [complete synthetic evidence packet](evidence.json) retains the incident,
fixed policy, unchanged request, both actual retrieved passages/IDs, every
candidate/exclusion, actual messages/schema/prompt, raw answer, complete v1 result,
configuration, source hashes, recorder source, checks and before-result. Full
snapshot, transport events, resources, process/health observations and checksum
manifest remain in `.local/P01-boundary-20261110-01/`. Anas owns artifact access.
Packet text is a verbatim selection of synthetic/reference data; no incident or
model output was repaired or redacted. Historical failures remain unchanged.

## Frozen acceptance and implementation

Issue #19 requires evidence-grounded structured generation with cited evidence.
Review 5819222237 requests a complete real-model example, reproducibility,
incident/reference distinction, a claim assessment, appropriate generation
handling, regressions and documentation with unresolved failures. It does not
require perfect accuracy or a particular P01 verdict. CDC §14 additionally
requires checks, experiment metadata, documentation, CI and peer review.
The pre-run frozen checklist is included in the packet and local ACCEPTANCE.md.

Only deterministic quotation candidates changed. The single-call prompt, model,
shared schemas/validators, query, filters, K, action handling and incident-report
attribution were preserved. The full retrieved passages still reach the model.
`sentence-boundaries-v1` uses observed top-level .!? endings outside protected
Markdown brackets, parentheses, double quotes and matching backtick runs;
attached balanced `(Citation: ...)` blocks stay with the sentence. It omits the
uncertain leading unit, unfinished tails, known abbreviations/initials/ellipses,
malformed protected syntax, single-word headings, forbidden markers and whole
units over160 characters. Original offsets/text are retained without rewriting.
It does not claim universal English sentence detection, grammatical independence,
semantic relevance or correct judgments. Unknown abbreviations and unsupported
markup remain limitations. Exclusion reasons are deterministic, not relevance
judgments. Full evidence is never removed. Empty/size/token failures remain
explicit; nothing is truncated or pruned to fit.

## Pre-inference inspection — no preferred candidate

Actual unchanged live retrieval: full saved P01 description as query, MITRE-only,
K=2, exact=True. Full readback verified the existing 340-record/406-vector preview
(369 knowledge, 37 SOC), BGE model identity, eligibility and source exclusions.
Retrieved passages/order and cosine scores matched the prior run: SSH passage
CHK-3dc9cf3df0995a5a6efcfc40f30655803116fe894520e0ff8eb21257ce280741,
score0.6944915; spraying/LDAP/Kerberos fragment
CHK-482e7dca780e17fcdedc6ebca929499203b74fe0b63fadee84134e4b7c07acef,
score0.6904734. Both complete passages remain in evidence.json.

The actual generated catalogue contained six candidates and five exclusions:

| Source offsets | Eligible unit / exclusion |
|---|---|
| SSH [0:4] | Leading `SSH.` omitted: uncertain leading boundary |
| SSH [5:138] | Complete general statement about possible Valid Accounts SSH use |
| SSH [139:200] | Complete sentence about actions as the logged-on user; requires context |
| SSH [201:289] | Complete SSH protocol/remote-shell definition |
| SSH [290:410] | Complete Linux/macOS installation/default-enablement statement |
| SSH [411:636] | Entire225-character ESXi sentence/citations omitted, not sliced |
| SSH [637:728] | Complete Windows SSH statement/citation; not necessarily relevant to P01 |
| SSH [729:869] | Complete password/keypair authentication statement |
| SSH [870:1123] | Entire253-character key-authorization sentence omitted |
| Other passage [0:157] | Leading fragment omitted: uncertain leading boundary |
| Other passage [158:435] | Entire277-character unit omitted |

The old Q-000-00480-00640 fragment was absent by ID and text. All six candidates
and five exclusions were inspected before inference. No preferred ID was selected,
no candidate was removed manually, and no query/filter/K change occurred.
The exact real adapter template/tokenizer reported **2378 input tokens** against
cap3072; output cap512 and context4096 were unchanged. Saved catalogue, exclusions
and completion request hashes were bound to the inspection receipt. Inspection
finished before COMPLETION_STARTED; completion transport was blocked until then.
The manual design example/expected labels were not supplied to the generator.

## Actual result and separate assessments

Pipeline: one live retrieval, one completion, status=ok; EOS, not truncated.
Pipeline89.280938s, retrieval2.958592s, client generation86.107256s; total recorder
lifecycle172.661006s includes prerequisite verification/startup. Client generation
includes approximately20 seconds waiting for the manual pre-inference inspection;
it is not pure inference time. Backend prompt43.937046s, decode21.751429s;
175 output tokens. TTFT was not measured. The shared diagnostic deadline300s
included inspection; production default180 remains unchanged.

Selected Q-000-00201-00289, exact SSH [201:289], 88 characters:

> SSH is a protocol that allows authorized users to open remote shells on other computers.

This is a complete supported general explanation of the protocol in the incident.
It does not establish that this source authenticated, opened a shell, changed an
account or was malicious. It supports neither the returned T1078 incident mapping
nor the wrong block argument. The selected sentence being present in the earlier
manual example is not an inserted answer: it was generated alongside all other
candidates by the same source-only algorithm and the model freely selected its ID.

## Field-by-field assessment

Manual technical review only; not a formal CDC judge score or independent human
double annotation. Support for incident observations is conditional on the
supplied synthetic report, not independent event verification.

| Substantive field / claim | Assessment and source |
|---|---|
| Copied report: timestamp, linux-01, SSH/auth-fail event, lab-admin | Exact incident.description copy with unverified-input label; no model paraphrase |
| Copied report: src192.0.2.10, dst10.77.0.20 | Exact input roles preserved; references do not establish them |
| Copied report: eight password failures, 57 seconds, one account | Exact supplied observations; not independently checked logs |
| Copied report: registry192.0.2.22, source absent | Exact supplied observation; registry absence alone does not prove maliciousness |
| Copied report: no accepted session, service up, audit/heartbeat coverage | Negative evidence retained exactly; successful access not established |
| Reference quotation/citation | PASS integrity/boundary/relevance for general SSH context; exact source/evidence pairing; no incident-fact attribution to it |
| triage_verdict=true_positive | Defensible judgment about investigating the suspicious attempt, not proof of successful compromise; model gives no separate verdict rationale |
| risk_level=medium | Defensible given repeated failures and no reported session/impact; independent risk reasoning is not established merely by matching detector severity |
| mitre_techniques=[T1078] | FAIL: no accepted session or successful credential use reported; general SSH/Valid Accounts reference does not prove occurrence |
| Omitted T1098 versus before | Unsupported account-modification prediction no longer present in this output; no claim of general mapping competence or causal proof |
| Omitted T1110.001 | Does not match the pending-review pilot mapping; repeated single-account password attempts support considering guessing, but actual retrieval lacks dedicated taxonomy support. No expected answer was forced |
| action_type=block_ip | Permitted proposal category; source containment may be considered, but this does not validate its arguments |
| target=linux-01 | Observed incident host and policy-permitted fixture target; no policy-only Windows host was invented as an observation |
| arguments.source_ip=10.77.0.20 | FAIL: incident.description identifies this as destination. Actual reported source is192.0.2.10. Membership-only validation accepts the wrong role; unchanged raw and public arguments preserved |
| arguments.port22/protocoltcp/duration300 | Code-owned fixed-policy defaults, within configured bounds; not independent evidence of observed network-port details or correct containment |
| reason: failed passwords, lab-admin, 57s, password method, one account | Each claim supported by incident.description; reason does not justify blocking destination. Source registry discrepancy is omitted from this justification |
| expected_effect: prevent further brute-force attempts by blocking source | FAIL for actual argument: source containment effect is not established for destination10.77.0.20. “Brute-force attempts” is a plausible interpretation of failures, not proof of success; no actual rule/effect tested |
| risks: may disrupt legitimate administrative tasks | Plausible conditional collateral warning, generic and incomplete; does not identify reversed role or establish actual impact |
| rollback_plan | Inadequate: “after a certain period” is vague; does not identify exact rule, restoration verification or detect that the proposed IP is destination. Kept unchanged |
| schema_version, incident/investigation/trace IDs, mode, status | Code/recorder-owned envelope verified by existing contracts; statusok establishes completion, not semantic correctness |
| evidence IDs/content/source record/snapshot/method/score_kind/scores | Actual closed retrieval response preserved; live payload/vector/readback/cosine checks applied; source knowledge is not incident observation |
| action schema_version/revision/status/requires_approval | Policy-derived1.0.0/revision1/proposed/true; no execution occurred |
| action_id/idempotency_key/incident_id | Runner-owned generated/copy identities, not factual findings |
| environment_id/target_inventory_revision/policy_version | Recorded synthetic-pilot/fixture-inventory-pilot-v1/synthetic-pilot-policy-v2; fictional fixture configuration, not operational authorization |

## Before/after and conclusion

| Dimension | Previous fixed-slice live run | Boundary run |
|---|---|---|
| Candidates | Eleven arbitrary fragments | Six bounded units; five exclusions |
| Selected quotation | Incomplete ESXi/citation fragment | Complete relevant SSH definition |
| Input tokens | 3042 | 2378 |
| Verdict/risk | undetermined/medium | true_positive/medium |
| Mappings | T1078,T1098 | T1078; still unsupported |
| Blocking argument | Destination10.77.0.20 | Same destination; still wrong |
| Result | Structurally complete, quality failed | Structurally complete, quality failed |

The demonstrated fragment defect is corrected under the documented boundary
grammar. Quotation selection was relevant in this single development attempt.
It is not proof of generally relevant selection, faithful decisions, action safety
or model accuracy. Decision/action quality failed. No further model attempt or
architecture change follows automatically. Oussama's review and applicable CDC
requirements remain pending; the wrong blocking IP is not accepted as correct.

## Reproduction and checks

Pinned Phi Q4_K_M SHA-25601999f17c39cc3074afae5e9c539bc82d45f2dd7faa3917c66cbef76fce8c0c2;
Linux b11827/970b51ce7 executable92ff7abb8a59c94a98acdbca4f50aaf54d2cb08a05fad57b254587a101366aac;
CPU6 threads/1 slot, temperature0, seed42, cache_prompt=false, n_keep0, no context
shift. Runtime warns Phi SWA is disabled; GGUF conversion lineage remains
unverified. Index receipt a612015b4246d0a4cb15c4c8c717422e161836afdd932486ba3fc278c907d59d;
BGE revision5c38ec7c405ec4b44b94cc5a9bb96e735b38267a; Qdrant1.20.0. Full identities,
runtime files and Python packages are in the packet, not inferred from HEAD alone.

Use the saved exact snapshot, preview and read-only runtime/model mounts in a
fresh directory, never reuse the attempt/transport markers. Extract recorder_source
from the packet as recorder.py, snapshot at /delivery/snapshot, repository/preview
at /workspace, runtime at /runtime, model at /models and the existing Qdrant network
namespace. Use image9072b252d340280ba72ff364846ff39c5e372496bb1bcfa04c11b34f2900590e;
run `python -B /delivery/recorder.py` with offline HuggingFace/Transformers flags.
The recorder requires the saved passing test results and scanner adjudication,
verifies prerequisites, and stops at a hash-bound pre-inference inspection gate.
A reproduction requires independent inspection of all actual units/exclusions
and token count; never authorize a preferred ID. No download/index rebuild/retry
is a fallback. Another reproduction is not authorized by this report.

Pre-run frozen-export checks: **292 tests passed** (contracts20, evaluation59,
backend20, normalizer16, ingestion44, vector106 including generation29, baseline27).
Actual integrity, Ruff and correctly baselined whitespace passed. Source hashes
matched before/after. Gitleaks returned exit1 for the same eight tree findings and
one history finding previously inspected as seven file digests, a synthetic
proposal key and historical prose. No suppressions were added; this is not an
all-checks/hosted-CI pass. Prior raw-checkout policy-digest errors remain preserved;
clean Git-object dataset bytes pass unchanged validators. Logs and commands are
in the packet/local checks directory. Documentation/evidence packaging is checked
separately after the run; it does not trigger another model attempt.

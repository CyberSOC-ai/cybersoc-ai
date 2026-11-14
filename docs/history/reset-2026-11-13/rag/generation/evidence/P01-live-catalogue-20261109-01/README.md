# P01 live catalogue investigation — 2026-11-09

This is one synthetic development investigation, not a benchmark or a grounding
quality pass. Reviewer acceptance remains pending. No retries, answer repairs,
model substitution, query changes, validator changes or response execution occurred.

The [evidence packet](evidence.json) contains the exact incident, fixed policy,
request, actual retrieved passages and evidence IDs, catalogue, messages/schema,
raw model output, complete structured result, measurements, provenance and the
executed recorder source. Local full artifacts and the frozen source snapshot are
under `.local/P01-live-catalogue-20261109-01/`; previous run directories and the
Phi feasibility archive remain unchanged. The packet is a verbatim selection of
synthetic/reference artifacts: no incident, evidence or output text was redacted
or repaired. Local process/resource logs and source snapshot remain outside Git.
Artifact access/retention owner: Anas; no external publication or reviewer message
was performed. MITRE source snapshot/provenance is retained in each passage.

## Four separate outcomes

| Dimension | Observed outcome |
|---|---|
| Pipeline completion | PASS: status=ok, complete v1 vector result; one live retrieval and one completion. 109.531 seconds pipeline; 3.523 retrieval; 105.826 generation client; 236 output tokens, EOS, not truncated. Startup/verification are outside the pipeline deadline; total recorder lifecycle 182.505 seconds. |
| Quotation integrity | PASS: Q-000-00480-00640 resolves to the first passage's exact Python character slice [480:640], length 160; evidence pairing and final rendering match. |
| Quotation relevance | FAIL: the selected fragment starts inside an ESXi command, contains citation titles and ends inside “Modern”. It does not supply a useful general explanation of this Linux password-failure incident. |
| Judgment/action quality | FAIL: unsupported T1078/T1098 incident mappings; destination IP proposed as source; unjustified effect and flawed rollback condition. Medium risk is defensible; undetermined is an abstention rather than a correct detection of the reported attack attempt. |
| Reviewer acceptance | PENDING: evidence and limitations are available for Oussama's assessment; #19 is not declared complete. |

## Pre-inference suitability and actual retrieval

Suitability was defined and saved before inference: **a passage must support a
relevant general reference statement; it need not independently verify incident
facts**. The inspected SSH passage supports general password/key authentication,
possible valid-account SSH access and actions as the logged-on user. This is
relevant SSH context for P01 even though P01 reports no accepted session. The
recorder required those actual passage bytes, without changing search inputs.
This conservative recorder gate is not a production semantic validator, and it
does not force the model to select a relevant span.

The unchanged request uses the full saved P01 description as query, MITRE-only,
K=2, exact=True. Actual live hits, in order:

| Evidence ID | Score | Support and boundary |
|---|---|---|
| CHK-3dc9cf3df0995a5a6efcfc40f30655803116fe894520e0ff8eb21257ce280741 | 0.6944915 | Full SSH passage supports the general reference statements above. It does not establish successful login, credential compromise, account modification, P01 endpoint roles or triage. |
| CHK-482e7dca780e17fcdedc6ebca929499203b74fe0b63fadee84134e4b7c07acef | 0.6904734 | Fragment describes throttled password spraying and LDAP/Kerberos versus SMB alert visibility generally. P01 reports one account and SSH password failures; it does not establish spraying, throttling, LDAP, Kerberos or SMB activity. |

Suitability was recorded at 23:53:19.826927 UTC, before the completion marker.
All general-reference support must be distinguished from support conditional on
the supplied, unverified synthetic incident. The passage identified in the prior
handoff as d626c0659413 is actually T1590.006 Network Security Appliances, not
this SSH passage. P11 was dropped; it was not run or tuned here.

## Field-by-field assessment

This is a manual technical assessment, not a validated independent LLM-judge score
or a human double-annotation result. “Supported” below is conditional on the named
input/policy; it does not independently verify a real event. JSON paths refer to
objects in evidence.json. The pending-review P01 label was consulted for analysis
after generation, never supplied to the generator.

| Field / claim | Assessment | Source and reasoning |
|---|---|---|
| summary: report timestamp, linux-01, SSH/auth-fail event | Supported as supplied input | incident.description; exact literal copy labelled “Supplied incident report (unverified input)”. |
| summary: src=192.0.2.10, dst=10.77.0.20, user=lab-admin | Supported as supplied input | incident.description explicitly states these roles; references do not establish them. |
| summary: eight password failures in 57s against one account | Supported as supplied input | incident.description; no independent log verification. |
| summary: owner registry lists 192.0.2.22, not 192.0.2.10 | Supported as supplied input | incident.description; absence from this registry does not independently identify an attacker. |
| summary: no accepted session; service stayed up; collector/audit coverage | Supported as supplied input | incident.description; preserve negative evidence, no successful compromise established. |
| summary: quotation and citation | Integrity supported, relevance failed | raw_answer.summary.quotation_id -> catalogue Q-000-00480-00640 -> retrieval_response.evidence[0].content[480:640]. Exact ESXi fragment, not a relevant complete statement. Code's “Reference quotation” label does not make it relevant. |
| triage_verdict=undetermined | Uncertain / missed attempt classification | The report supports a suspicious repeated single-account password attempt from an unlisted source. Uncertainty about successful compromise is warranted; no accepted session is reported. Abstention does not equal the pending-review true_positive label or a quality pass. |
| risk_level=medium | Defensible judgment, rationale absent | Eight failures from an unlisted source, no accepted session, service up support bounded risk. Matching incident.severity or the label alone is not independent risk reasoning. |
| mitre_techniques[0]=T1078 | Unsupported for this incident | SSH passage describes possible valid-account access generally; P01 explicitly reports no accepted session or successful credential use. |
| mitre_techniques[1]=T1098 | Unsupported for this incident | No account modification or SSH-key change is reported. A reference link to SSH Authorized Keys is not evidence that modification occurred. |
| omitted T1110.001 | Missed defensible mapping | Repeated password attempts against one account support password guessing under the pilot rubric. The retrieved preview lacks a dedicated T1110.001 passage; do not pretend a retrieved citation verifies that mapping. |
| recommended_actions[0].action_type=block_ip | Plausible proposal category only | Fixed policy permits proposals; repeated attempts can justify considering source containment. This does not validate the supplied arguments. |
| target=linux-01 | Supported target identity | incident.entities host and description; also permitted by policy.targets. windows-01 appears only in policy and is not invented as an incident host in the copied report. |
| arguments.source_ip=10.77.0.20 | Contradicted role / wrong argument | incident.description identifies this as dst; source is 192.0.2.10. Shared validator accepts IP entity membership and does not prove direction. Result preserved unchanged. |
| arguments.port=22, protocol=tcp, duration_seconds=300 | Policy-derived, not observed network proof | policy.ssh_containment supplies these code-owned values; duration is within [300,3600]. Correct policy values do not make the destination-IP block correct. |
| reason: failures, user, 57s, password, one account | Supported facts, insufficient justification for this block | Each claim occurs in incident.description. They support considering the reported source, not blocking destination 10.77.0.20. |
| reason: owner record and missing source entry | Supported as supplied input | incident.description; does not link destination IP to an attacking origin. |
| reason: no accepted session and service stayed up | Supported as supplied input | incident.description; negative evidence retained. |
| expected_effect | Unsupported / causally incorrect | Blocking 10.77.0.20 is not established to stop attempts from 192.0.2.10. No firewall direction/semantics or target binding validates this prediction. |
| risks | Plausible conditional warning, incomplete | A wrong destination block may affect legitimate traffic. The text does not diagnose the reversed role or establish actual collateral impact. |
| rollback_plan | Inadequate / unsupported condition | Names removal of the wrong-IP block but conditions it on confirmation of malicious activity. Does not specify removing the exact rule, recovery verification or a sound restoration criterion. |
| result schema_version, incident_id, investigation_id, trace_id, mode, status | Provenance/structural fields, verified | Existing v1 validator; recorder-supplied investigation ID; incident and request identities; VectorPipeline sets vector. status=ok means structural completion, not semantic correctness. |
| evidence content, IDs, snapshot, source record, score_kind, method, scores | Provenance verified | Live Qdrant readback matches pinned point payload/vector spools; cosine checks and closed projection applied. Content is reference material, not incident observation. |
| action schema_version, revision, status, requires_approval | Policy-derived, verified | response_defaults: 1.0.0, revision 1, proposed, approval required. No response action was executed. |
| action_id, idempotency_key, incident_id | Code-derived identity, verified | Existing runner generates IDs, copies incident identity. Nondeterministic IDs are not quality claims. |
| environment_id, target_inventory_revision, policy_version | Policy-derived, verified | synthetic-pilot / fixture-inventory-pilot-v1 / synthetic-pilot-policy-v2. Fictional fixture policy is not operational authorization. |

## Before / after and limitations

| Behavior | Preserved previous Phi feasibility trial | Current live investigation |
|---|---|---|
| Completion | 223.069-second model completion; rejected at quotation_integrity; no final investigation | Complete validated vector result, 109.531 seconds pipeline |
| Incident attribution | Invented windows-01 observation and incorrect host/IP associations | Code copies supplied report with explicit unverified-input attribution; no generated incident paraphrase |
| Quotation | Model-written excerpt altered with newline; rejected | Exact catalogue span rendered; relevance still fails |
| Verdict / mappings | undetermined; T1078/T1098 | Same judgments; unresolved quality failures |
| Action | source_ip=10.77.0.20 (destination) | Same directional error accepted by unchanged shared validation |

Previous artifact: `.local/phi-feasibility-160-300-20261109/kaggel outpu/phi-p01-feasibility-03.zip`.
Earlier full P01, timeout and source-selection runs remain under the preview runs
directory. No failure is replaced by this attempt. The previous Phi trial used
fixed saved retrieval on Kaggle; the current attempt uses live retrieval locally
and catalogue handling. Source shape, prompt, token counts and environment differ:
these are behavior observations, not a controlled speed/model comparison.

## Configuration and reproduction

- Phi Q4_K_M bytes: SHA-256 `01999f17c39cc3074afae5e9c539bc82d45f2dd7faa3917c66cbef76fce8c0c2`.
- Linux llama.cpp b11827 / commit 970b51ce7 executable: `92ff7abb8a59c94a98acdbca4f50aaf54d2cb08a05fad57b254587a101366aac`.
- CPU, six threads, one slot, context 4096, no context shift; input cap 3072,
  output cap 512, temperature 0, seed 42, cache_prompt=false, n_keep=0.
- Input was 3042 tokens. Server reported EOS, 236 output tokens and no truncation.
- Shared diagnostic deadline 300 seconds; production default remains 180.
- BGE-small-en-v1.5 revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, pinned CPU packages.
- Qdrant 1.20.0; index receipt `a612015b4246d0a4cb15c4c8c717422e161836afdd932486ba3fc278c907d59d`;
  build `c080708ee3505239b72951e82c6ef843a507dc619711c7ee212aa246df72765b`.
- Existing preview: 340 records / 406 vectors, 369 knowledge + 37 SOC;
  development-only, test split empty. MITRE-only filtering excludes SOC results.
- Current dirty source bytes are frozen and hashed; the published HEAD alone does
  not reproduce catalogue behavior. GGUF checkpoint/conversion lineage remains
  unverified. Runtime warns Phi SWA is disabled. No general accuracy claim follows.

Do not execute the recorded attempt directory again. For independent reproduction,
Anas supplies the frozen snapshot and preview/runtime/model artifacts with hashes.
Create a fresh empty run directory, place that snapshot at `snapshot/`, and extract
`recorder_source` from evidence.json as `recorder.py`. Retain the previous input
directory at the recorder's documented preview-relative path. Mount the repository
read-only as `/workspace`, new directory as `/delivery`, existing runtime/models
read-only at `/runtime` and `/models`; use the existing Qdrant network namespace.
Use image `sha256:9072b252d340280ba72ff364846ff39c5e372496bb1bcfa04c11b34f2900590e`.
Run `python -B /delivery/recorder.py` with `PYTHONDONTWRITEBYTECODE=1`,
`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `TOKENIZERS_PARALLELISM=false`.
The recorder stops if hashes, eligibility, full readback, memory or suitable live
evidence fail. It submits at most one completion and retains failures. No index
rebuild or download is a fallback. Exact output repeatability is not promised.

## Applicable offline checks

Fresh runs: 98/98 vector tests (including 21 generation tests), 20/20 contract
tests and repository-wide Ruff passed. Baseline: 24 passed, three CLI errors from
the unchanged runner-policy raw-byte digest mismatch; 27 attempted. This is not
an all-suite pass. The development image lacks Git: the original repository
integrity command failed and the check harness stopped before its whitespace
command. That failure is retained. Host Git's CRLF-aware `diff --check` passed.
The supplementary text/link check uses the actual host Git file listing and the
same conflict-marker/local-link rules, including new evidence files; results and
original logs are in `checks.json` and the local artifact directory. Hosted CI
has not been run for this dirty checkout.

The remaining
review decision is whether the focused attribution changes and this candid
complete investigation adequately address #19; relevance, mapping and directional
action failures are explicitly unresolved. No further model run is authorized.

# soc-eval-v1 — SYNTHETIC PILOT

Release: `soc-eval-v1-pilot.1`. Part of #10; owner Anas, assigned reviewer
Oussama. All ten cases are development-only, `test` is empty and
`test_frozen` is false. This does not complete S1-T02.

These small fixtures were assistant-authored for Anas from the
[lab scenario catalog](../../../infrastructure/soc-lab/README.md), not collected
from a deployed SOC. They are not evidence of real SOC performance. No model,
judge, human double-labelling or response execution is claimed. The
[inventory](../../SOURCES.md) requirement for collected cases remains outstanding.
All labels are pending review; naming Oussama assigns review, it does not record
review completion. `label_author: Anas` identifies the task owner, not an assertion
that Anas independently annotated assistant-authored material.

## Layout and boundaries

- `inputs/P01.json` through `inputs/P10.json`: incident v1 objects, the only
  case material returned by `load_model_inputs`.
- `labels/`: evaluator-only decisions, evidence locators and non-scored guidance;
  validated by [labels.schema.json](labels.schema.json).
- `context/`: evaluator-only synthetic provenance, template family and fixture
  inventory. Logical IDs are not an operational allowlist.
- [splits.json](splits.json): membership, groups, complete case digests and freeze flag.
- [manifest.json](manifest.json): component and case hashes, split-file hash,
  declared severity and MITRE scoring universes.
- [guidelines/labeling.md](guidelines/labeling.md): provisional label policy.

The evaluator preflights with `validate_dataset`, then hands only the input-only
loader interface to model code. This is API separation, not a filesystem security
boundary. Labels and context never enter prompts or retrieval records. All facts
used for proposed incident decisions are in descriptions/entities; source IPs,
hosts and detector severity are legitimate observations, not annotation leakage.
Do not use fixture filenames or grouping metadata as model features.

## Label and scoring policy

Verdict refers to the simulated incident's intent, not authorization to run a lab
exercise. There are four proposed true positives and six false positives/controls.
P01-P05 share `G-SSH`, P06-P07 `G-FIM`, P08-P09 `G-ACCOUNT`, and P10
`G-POWERSHELL`; P01/P02 are two views of the same episode. Thus ten cases are only
four conservative template-family groups, not ten independent observations.

Input `severity` is detector severity; evaluator `gold_severity` maps to result
`risk_level`. Manifest universes are fixed for this pilot release, not a frozen
test split. Severity covers informational, low, medium and high, not critical.
MITRE covers T1110 and T1136.001; empty sets require `mitre_reason`. Public MITRE
technique pages were checked (versions 2.8 and 1.5 respectively), but a pinned STIX
snapshot and human mapping review remain outstanding. No retrieved corpus exists:
all relevance judgements are `not_labelled`, with reasons.

Only P01/P02 require the draft `block_ip` projection: fixture target `linux-01`,
source `192.0.2.10`, TCP port 22, inclusive duration 300–3600 seconds. The action
policy is pending owner confirmation. Other cases require no supported action;
P06/P08 carry non-scored analyst guidance. No account-disable/quarantine adapter
is invented. Full proposed outputs still require the existing action contract
and approval flag; a correct projection does not grant execution permission.

[METRICS.md](../../../experiments/METRICS.md) is authoritative. Failed/invalid or
undetermined verdicts remain incorrect; true-incident abstentions add FN, benign
abstentions add no TP/FP/FN. Binary zero denominators yield null with reasons.
Per-label macro-F1 zero denominators yield **0**, the explicit METRICS exception;
precision/recall remain null. Macro-F1 uses declared universes and discloses
out-of-universe predictions. Action matching is one-to-one with no extras or
omissions; empty/empty matches with null precision/recall. Failed full outputs
never obtain an empty-action match. Missing prediction keys mean not attempted;
explicit null means attempted failure. Per-case reasons and counts are retained.

## Hashing: soc-eval-json-v1

The short implementation is [hashing.py](../../../ai/evaluation/hashing.py).
Parse strict UTF-8, rejecting BOMs, duplicate keys, floats (including exponent
notation), non-finite numbers and invalid Unicode. Serialize string-keyed objects
with sorted keys, compact separators and UTF-8 (`ensure_ascii=False`); preserve
array order and string contents without normalization. No trailing newline enters
canonical bytes. Hash with SHA-256, lowercase hexadecimal. This is a named project
format, not RFC 8785 or the future action-approval digest format.

Each component has canonical and raw-byte hashes. A case digest hashes an object
with `hash_scheme`, `case_id`, `input`, `labels`, `context` and their full values.
Both manifests reference each complete case digest; manifest also hashes exact
`splits.json` bytes. Neither file includes its own hash. Experiment records must
pin the exact raw manifest digest externally; `verify(...,
expected_manifest_sha256=...)` checks it. Without that argument verification checks
internal consistency only, not authorization to replace all data and checksums.

Raw hashes detect whitespace-only changes too. Verification is read-only and
rejects missing/unlisted case files; it never updates checksums. Changed labels,
context, inputs or split membership require a new manifest/release per the
[version convention](../../../experiments/README.md). These checks are integrity
checks, not evidence that unreviewed labels are correct.

## Checks and known limits

From the repository root, install `pip install -r requirements.txt`, then run:

```sh
python -B -m unittest discover -s tests/evaluation -v
ruff check .
python -B infrastructure/ci/check_repository.py
```

Tests use temporary directories for mutations and never write into the dataset.
Oracle simulations test software plumbing, not model performance. Pending-review
labels are permitted for pilot self-tests and must not be presented as reviewed
benchmark ground truth. There is no frozen test set, collected lab evidence,
critical-severity coverage, judge, annotation study, retrieval evaluation or
operational response validation. Ten authored cases are too few for broad claims;
shared families further limit independence. Stage C owns the deferred evaluation
protocol/validation artifacts and test-release decisions. Dataset publication
licensing remains a team decision; no third-party records were copied.

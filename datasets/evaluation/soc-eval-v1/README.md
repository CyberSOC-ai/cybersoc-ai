# soc-eval-v1 — SYNTHETIC PILOT

Release: `soc-eval-v1-pilot.2`. Part of #10; owner Anas, assigned reviewer
Oussama. All 14 cases are development-only, `test` is empty and
`test_frozen` is false. This does not complete S1-T02.

These small fixtures were assistant-authored for Anas from the
[lab scenario catalog](../../../infrastructure/soc-lab/README.md), not collected
from a deployed SOC. They are not evidence of real SOC performance. No model,
judge, human double-labelling or response execution is claimed. The
[inventory](../../SOURCES.md) requirement for collected cases remains outstanding.
All labels are pending review; naming Oussama assigns review, it does not record
review completion. Each label records `label_author: Codex-drafted; Anas review pending`. It becomes
`Anas` only after the owner reviews that specific case; no such review is claimed.
All current labels remain pending_review / needs_review=true.

## Layout and boundaries

- `inputs/P01.json` through `inputs/P14.json`: incident v1 objects, the only
  case material returned by `load_model_inputs`.
- `labels/`: evaluator-only decisions, evidence locators and non-scored guidance;
  validated by [labels.schema.json](labels.schema.json).
- `context/`: evaluator-only synthetic provenance, template family and fixture
  inventory. Logical IDs are not an operational allowlist.
- [splits.json](splits.json): membership, groups, complete case digests and freeze flag.
- [manifest.json](manifest.json): component and case hashes, split-file hash,
  declared severity and MITRE scoring universes.
- [guidelines/labeling.md](guidelines/labeling.md): provisional policy and proposed grouping merges.
- [protocol/](protocol/README.md): faithfulness, prompt templates, rubric and action matching.
- [validation/](validation/README.md): empty sampling/annotation/adjudication templates.

The evaluator preflights with `validate_dataset`, then hands only the input-only
loader interface to model code. This is API separation, not a filesystem security
boundary. Labels and context never enter prompts or retrieval records. All facts
used for proposed incident decisions are in descriptions/entities; source IPs,
hosts and detector severity are legitimate observations, not annotation leakage.
Do not use fixture filenames or grouping metadata as model features.

## Label and scoring policy

Verdict refers to the simulated incident, not authorization to run a lab exercise.
There are 6 proposed true positives and 8 false positives, all informational.
Gold severity counts: informational 8, medium 4, high 2. Low is reserved for real
incidents of minor impact; this release has no low or critical cases.

P01-P05 share `G-SSH`, P06-P07 `G-FIM`, P08-P09 `G-ACCOUNT`, and P10
`G-POWERSHELL`; P01/P02 are two views of the same episode. New synthetic variants
P11-P14 use `G-SSH-SESSION`, `G-FIM-WINDOW`, `G-SSH-SCANNER`, `G-SSH-REPLAY`.
There are 8 authored groups; shared scenario types still limit independence.
The [grouping proposal](guidelines/labeling.md#grouping-proposal--not-applied) would
merge these into four template families. Approval: TBD - owner decision.
No group IDs or memberships have changed in this delivery.
P11/P13 extend LAB-01 beyond its live exercise limits: these are authored variations,
not collected runs or instructions to execute those counts.

Input `severity` is detector severity; evaluator `gold_severity` maps to result
`risk_level`. The manifest severity universe is informational, medium, high;
MITRE universe is T1078, T1110.001, T1136.001. Empty MITRE sets have reasons.
No source snapshot or human mapping review is claimed for the updated mappings.
All retrieval relevance remains `not_labelled`, with reasons.

Only P01/P02/P11 require block_ip; the common
[runner policy](protocol/runner-policy.json) defines its service scope and duration.
It is identical for every case and is included in manifest hashes. P06/P08/P11/P12
carry non-scored analyst guidance. Full action envelopes come from runner config,
not labels. The owner selected this pilot policy; execution remains disabled and
operational authorization is pending. No account-disable adapter is invented.

[METRICS.md](../../../experiments/METRICS.md) is authoritative. Implementations in
[scoring.py](../../../ai/evaluation/scoring.py) now include faithfulness accounting
and Cohen's kappa with raw agreement and disagreement counts. Protocol documentation
references the authority rather than replacing its metric definitions. Ordinal
agreement for the 1–5 quality ratings: TBD - owner decision.

## Runner integration

The injected `runner(incident, policy)` returns a full investigation-result object.
The runner must fill action target_inventory_revision, environment_id,
policy_version, generated IDs/idempotency keys and status `proposed` from the fixed
policy/config, never from labels; incident_id comes from the input. Pass the same
policy to every case. Evaluator bundles below stay outside the runner.

```python
from pathlib import Path
from ai.evaluation.hashing import read_json
from ai.evaluation.loader import load_model_inputs, load_evaluator_cases
from ai.evaluation.validation import validate_dataset, validators
from ai.evaluation.scoring import score_cases
root = Path.cwd()  # repository root
path = root / "datasets/evaluation/soc-eval-v1"
validate_dataset(root, path)  # evaluator preflight
policy = read_json(path / "protocol/runner-policy.json")
inputs = load_model_inputs(path, "development")
predictions = {i["incident_id"]: runner(i, policy) for i in inputs}
cases = load_evaluator_cases(path, "development")  # evaluator only
manifest = read_json(path / "manifest.json")
scores = score_cases(cases, predictions, manifest["severity_universe"],
                     manifest["mitre_universe"], validators(root, path)["investigation-result"])
```

Case-ID keys remain supported. Unknown IDs, duplicate incident IDs in the case
collection, and duplicate predictions (including case/incident aliases) raise a
clear error. Use a sequence of `(key, result)` pairs to retain duplicate keys for
validation: a Python dict has already discarded repeated identical keys.

Shortcut tests use input-only players. The always-block player blocks each observed
remote source and emits no block for local-only events with no source IP; it never
invents a source or reads labels. These development checks are not model results.

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
`splits.json` bytes and canonical/raw runner-policy hashes. All protocol/validation
assets have raw SHA-256 entries in manifest.assets. Verification rejects missing,
modified, duplicate or unlisted assets; prompt digests cover exact UTF-8 bytes. Neither file includes its own hash. Experiment records must
pin the exact raw manifest digest externally; `verify(...,
expected_manifest_sha256=...)` checks it. Without that argument verification checks
internal consistency only, not authorization to replace all data and checksums.
`build_manifests` returns split bytes and manifest without writing; it refuses
frozen/nonempty test splits. Explicitly save its outputs only for an updated pilot
release, then validate and verify. This release is pilot.2 / S1T02-pilot-v2.

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
operational response validation. Fourteen authored cases are too few for broad claims;
shared families further limit independence. Protocol drafts and empty validation
templates now exist; test-release decisions, real double-labelling and human review
remain pending. Dataset publication
licensing remains a team decision; no third-party records were copied.

## Datasheet: motivation, composition and use

**Motivation:** provide repeatable interfaces for the baseline runner and evaluation
software while lab collection is incomplete. No real SOC performance is established.

**Composition:** 14 cases, 8 existing groups; 6 proposed true positives and 8 false
positives. All are development-only, with no low/critical assessed severity or test
split. The eight groups must not be assumed independent construction families.

**Provenance and labelling:** assistant-drafted from catalog scenarios, unreviewed;
inputs are synthetic observations, not collected logs. Anas is the task owner and
Oussama the assigned reviewer; these roles do not establish completed annotation.
Author integrity is explicit in each label. No case facts or verdicts changed here.

**Exclusions:** unresolved incidents, real collected logs, reviewed retrieval
relevance, judge validation, independent human double-labelling, and execution-safety
validation are absent. The rubric examples are pending-review illustrations, not
human ratings or model outputs.

**Permitted use:** development checks and clearly identified synthetic demonstrations,
subject to the repository's pending publication/licensing decision. These artifacts
provide no operational execution permission or basis for held-out performance claims.
Test labels are evaluator-only by convention, not enforced by Git; currently there
are no test cases. API separation does not prevent repository readers seeing labels.

**Limits:** tickets are not a reliable signal, and authorization forms vary. The
never-act shortcut scores 11/14 exact action matches. The shortcut-baseline 0.80
line is a local data-quality check, not a metric or project acceptance threshold.
Small size and synthetic prose limit generalization even when shortcuts stay below
that line. No new threshold, confidence method, random seed or sample size is chosen.

**Pending owner choices:** sample size beyond the CDC minimum of 50 claims,
answer-selection method/seed, ordinal agreement measure, grouping approval and judge
configuration: TBD - owner decision. See the [validation guide](validation/README.md)
and [faithfulness guide](protocol/faithfulness.md) before real evaluation.

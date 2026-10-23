# S1-T03 — Local exploratory baseline observations

Date: 2026-10-22 · Owner: Soulaiman · Branch: `feature/11-baseline-slm-runner`.
Measurements were collected locally before commit. Publication on the task branch is authorized; reviewer approval and task completion are not claimed. Hosted CI is tracked on the associated PR.

## Observed runs

Both models used the same unchanged v1 prompt, 14 synthetic development incidents,
fixed proposal policy, schema-constrained generation, temperature 0, seed 42,
4096 context, 3072 input budget, 512 output budget, one slot, six CPU threads and
llama.cpp b11827 on the same Windows Ryzen 5 5625U / approximately 14 GiB RAM host.
The GGUF tokenizers/chat templates are model-specific. Models loaded sequentially;
no two model servers ran together.

| Model | Contract-valid | Rejected outputs | Correct triage verdicts / all attempted | Median client latency (s) | Server peak working set (GiB) |
|---|---|---|---|---|---|
| Qwen2.5 1.5B Q4_K_M | 8/14 | 6 | 3/14 | 14.12 | 2.20 |
| Phi-4-mini Q4_K_M | 13/14 | 1 | 1/14 | 34.77 | 5.32 |

Validity is not correctness. The raw triage scores are weak, with many
`undetermined` verdicts and no correct MITRE predictions in these passes. No
final model winner is selected. Phi's rejected proposal used `unknown` as an IPv4
source; Qwen's six rejections occurred at proposal-policy validation. Outputs were
not silently stripped or repaired into successful answers. The scorer includes
failures and abstentions using Anas's existing metric implementation. Full
precision/recall/F1, severity, MITRE and action scores remain in the local score files.

## Measurement limits

- The pilot is development-only, 14 authored cases in four shared template families;
  labels await independent review and there is no frozen test set or collected-lab
  performance claim. No prompt tuning or case/label changes were performed here.
- One pass per recorded model is not a controlled speed ranking. Interactive
  development and software tests were also active during parts of the work.
  Qwen's initial smoke/pilot runs are retained separately, not pooled as extra cases.
- Client latency includes template application and tokenization, excludes cold
  model loading, uses no warmup and disables per-request prompt caching. Server
  prompt/decode timings are separately recorded. First content chunk is measured;
  token-level TTFT is null. Peak memory is server lifetime peak working set including
  loading, not per-request memory, GPU memory or total system memory.
- These are quantized CPU development baselines, not the FP16/INT8/INT4 optimization
  study or the official frozen benchmark environment. Python was 3.14.3; the shared
  Python 3.12 Docker environment and hosted CI were not run for these changes.
- Faithfulness, hallucination rate and human quality ratings were not measured.
  Phi uses a community GGUF conversion; exact conversion source-checkpoint lineage
  remains unverified. Executed GGUF checksums/revisions and embedded templates are pinned.

## Local evidence

Run directories contain raw model answers, rendered prompts, validated predictions,
failures, timings, memory/environment, configuration, input/manifest identities and
runner-source snapshots. All referenced artifact hashes were checked after completion.
These directories are ignored and have not been published:

- `.local/runs/qwen-pilot-recorded`: artifact-manifest SHA-256 `ecd77e3c2be1a3a944207aa86637643a1bc915e6d3de584cdea7ca815af15613`.
- `.local/runs/phi-pilot`: artifact-manifest SHA-256 `25fd163234608b3187ceedaba4bedf0e50c1832d75f03494d082da30dc3666f8`.

The earlier `.local/runs/qwen-first` and `.local/runs/qwen-pilot` runs used the
initial recorder. Their upstream revision field refers to inspected repository
HEAD, not proven conversion lineage; the recorded artifact SHA-256 identifies the
actual executed weights. The later record distinguishes those identities explicitly.

These experiments were **not run from clean implementation commits**. The recorded
Git SHA identifies the base checkout and `dirty=true` records local changes. Their
historical source snapshots cover only `ai/baseline`, not the complete evaluator
implementation. Dataset manifests identify the recorded data, but cannot establish
the exact evaluator code used. The historical artifacts are retained unchanged;
the broader snapshot recorder added for [PR review](REVIEW_FIXES.md) does not
retroactively remove this reproducibility limitation. The owner has chosen to keep
the detailed artifacts local, so reviewer access and independent verification of
these reported real-model results remain outstanding.

## Remaining work

Review the runner and initial outputs with Soulaiman/Anas; agree the API adapter
with Oussama and test it against PR #79 after integration; address evaluation
readiness and formal workflow requirements before closing #11. Keep ADR-002
Proposed. Soulaiman authorized the review fixes and merge on 2026-10-23; that
authorization does not constitute reviewer approval or independent result verification.

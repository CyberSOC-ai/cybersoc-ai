# SLM shortlist and hardware-fit requirements

Checked: 2026-10-13 · S0-T05 inventory input to S1-T03 / ADR-002.
No model is selected, downloaded or benchmarked. Available team GPU/VRAM is not documented. This is a reproducible candidate shortlist with conditional fit estimates, not measured compatibility or quality. Recheck official cards/licenses and pin immutable model/tokenizer revisions before use.

## Candidate matrix

| Exact candidate / official card | Parameters | License / notice obligations | Weight-only GiB: FP16 / INT8 / INT4 | Intended consideration |
|---|---:|---|---:|---|
| [Qwen/Qwen2.5-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct) | 1.54B | Apache-2.0; retain license/notices and mark modifications when distributing | 2.87 / 1.43 / 0.72 | Small Qwen baseline candidate; an unquantized short-context run is a candidate for an 8 GiB GPU |
| [Qwen/Qwen2.5-3B-Instruct](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct) | 3.09B | [Qwen Research License](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct/blob/main/LICENSE), **not Apache-2.0**; research/evaluation only, commercial license separately; retain agreement/attribution and modification notices | 5.76 / 2.88 / 1.44 | Larger Qwen comparison, research restrictions must be accepted; prefer 16 GiB for initial unquantized trial |
| [microsoft/Phi-4-mini-instruct](https://huggingface.co/microsoft/Phi-4-mini-instruct) | 3.8B | MIT; retain copyright/license notices | 7.08 / 3.54 / 1.77 | Required Phi-family comparison candidate; 16 GiB short-context trial or separately validated quantized run on lower VRAM |
| [HuggingFaceTB/SmolLM2-1.7B-Instruct](https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B-Instruct) | 1.7B | Apache-2.0; retain license/notices and mark modifications when distributing | 3.17 / 1.58 / 0.79 | Additional compact family; low-resource/CPU feasibility candidate; an 8 GiB short-context GPU trial is plausible |

License labels, sizes and model roles come from the linked publisher cards; memory/fit figures are our estimates. Qwen's official 1.5B and 3B cards report 32,768-token context for these exact checkpoints; this is not a requirement to use the maximum. Phi's card reports 128K context and hardware-specific attention guidance. SmolLM2's card documents English-focused limitations. None of the publisher general benchmarks proves SOC task quality or safe response behavior.

The Qwen 3B license additionally imposes conditions on redistributed derivatives and models improved using its materials/output; inspect the complete license before publishing fine-tuned artifacts. The smaller Qwen license cannot be assumed to apply to the 3B checkpoint. Keep quantized derivative license/provenance together with the original model license.

## Memory estimates and conditional fit

Weight storage lower bound:

```text
GiB = parameter_count × bits_per_parameter / 8 / 2^30
```

These estimates assume every parameter has the named precision. Actual quantized checkpoints add scales/metadata and can retain embeddings or other layers at higher precision. Loading may create transient copies. The totals exclude KV cache, activations, framework/driver allocations and workspace, and therefore are not minimum total VRAM guarantees.

| Available resource, if confirmed | Candidate experiments / gate |
|---|---|
| CPU only | Trial small Qwen/SmolLM2 behind a compatible CPU runtime; verify RAM and latency; report CPU results separately from GPU results |
| 4 GiB VRAM | Quantized small-model feasibility only after backend support and measured peak memory checks; no FP16 or Phi fit guarantee |
| 8 GiB VRAM | Trial short-context batch-1 FP16 Qwen 1.5B / SmolLM2; trial larger candidates only with separately validated quantization/offload; do not mix offloaded timing with GPU-only comparisons |
| 16 GiB VRAM | Candidate for batch-1 short-context unquantized runs of all shortlisted models; verify actual peaks and available headroom before admitting any model |
| Larger / cloud GPU | Extend context/batch experiments only under recorded budgets and a consistent environment; account access, GPU type, quotas and availability remain unverified |

Start feasibility checks with batch 1, at most 2048 input tokens and 256 output tokens. These are proposed setup budgets, not benchmark protocol definitions. KV-cache memory grows with sequence length, batch size, layers, KV heads, head dimension and cache dtype; theoretical maximum context can exhaust otherwise adequate VRAM. Measure peak allocated/reserved memory and generation failures; reduce context/batch before changing model precision. Do not treat an out-of-memory run as a missing sample.

Inference fit does not imply QLoRA/training fit: gradients, optimizer states, adapters and training activations need separate S5-T06 measurements. The S0 shortlist does not promise training feasibility.

## Runtime and benchmark handoff

S1-T03 must verify tokenizer/chat template, checkpoint revision, supported runtime/attention backend and structured-output behavior. Qwen cards identify support in Transformers from 4.37; Phi's card describes integration in 4.49 and an eager-attention alternative for older GPUs. These are publisher compatibility notes, not the project's future dependency pins. Choose maintained compatible versions and test on the actual environment. Avoid remote-code execution by default; if a checkpoint/runtime requires it, inspect the pinned code and obtain review before enabling it. Do not copy provider examples granting arbitrary tool privileges.

Record CPU/GPU model, VRAM/RAM, OS, Python/PyTorch/runtime, attention implementation, quantization backend, checkpoint/tokenizer revision, input/output budgets, prompt/data versions and Git commit. Benchmark every candidate on the same reviewed development cases and protocol, then select the baseline in [ADR-002](../docs/adr/ADR-002.md). Final official environment freeze remains S5-T01 / ADR-007.

The CDC Qwen-versus-Phi comparison remains required; SmolLM2 is an additional candidate. Compare SOC triage, evidence grounding, structured output, action correctness, latency and memory using S0-T06/S1-T02 definitions. Keep development tuning separate from frozen-test reporting and do not rank models here using general publisher benchmark numbers.

S5-T06's Base-versus-Fine-tuned comparison refers to the selected unmodified checkpoint versus its adapted version under the frozen protocol; it must not be confused with comparing pretraining and instruct checkpoints. Track adapter provenance/license and training split separately. Exact model choice, inference serving, storage and benchmark environment remain their scheduled ADR decisions.

# SLM shortlist and hardware-fit requirements

Checked: 2026-10-14 · S0-T05 inventory input to S1-T03 / ADR-002.
No model is selected, downloaded or benchmarked. Verified laptop capacity and a documented inference-memory assessment are recorded below; successful runtime compatibility and quality remain experimentally unverified. Recheck official cards/licenses and pin immutable model/tokenizer revisions before use.

## Candidate matrix

| Exact candidate / official card | Parameters | License / notice obligations | Weight-only GiB: FP16 / INT8 / INT4 | Intended consideration |
|---|---:|---|---:|---|
| [Qwen/Qwen2.5-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct) | 1.54B | Apache-2.0; retain license/notices and mark modifications when distributing | 2.87 / 1.43 / 0.72 | Small Qwen comparison candidate; local 8-bit / 4-bit inference is estimated feasible under the budgets below |
| [Qwen/Qwen2.5-3B-Instruct](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct) | 3.09B | [Qwen Research License](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct/blob/main/LICENSE), **not Apache-2.0**; research/evaluation only, commercial license separately; retain agreement/attribution and modification notices | 5.76 / 2.88 / 1.44 | Larger Qwen comparison; local 4-bit fit is conditional; research restrictions must be accepted |
| [microsoft/Phi-4-mini-instruct](https://huggingface.co/microsoft/Phi-4-mini-instruct) | 3.8B | MIT; retain copyright/license notices | 7.08 / 3.54 / 1.77 | Required Phi-family comparison candidate; local 4-bit fit requires a more memory-efficient configuration than the conservative estimate below |
| [HuggingFaceTB/SmolLM2-1.7B-Instruct](https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B-Instruct) | 1.7B | Apache-2.0; retain license/notices and mark modifications when distributing | 3.17 / 1.58 / 0.79 | Additional compact family; local 4-bit inference is estimated feasible; 8-bit fit is conditional |

License labels, sizes and model roles come from the linked publisher cards; memory/fit figures are our estimates. Qwen's official 1.5B and 3B cards report 32,768-token context for these exact checkpoints; this is not a requirement to use the maximum. Phi's card reports 128K context and hardware-specific attention guidance. SmolLM2's card documents English-focused limitations. None of the publisher general benchmarks proves SOC task quality or safe response behavior.

The Qwen 3B license additionally imposes conditions on redistributed derivatives and models improved using its materials/output; inspect the complete license before publishing fine-tuned artifacts. The smaller Qwen license cannot be assumed to apply to the 3B checkpoint. Keep quantized derivative license/provenance together with the original model license.

## Verified development hardware — 2026-10-14

Evidence: hardware measurements supplied by Oussama on October 14, 2026. This laptop is available for local project development and model evaluation; these measurements were not repeated by this documentation change.

| Resource | Measured capacity / state |
|---|---|
| GPU | NVIDIA GeForce RTX 3050 Laptop GPU |
| VRAM | 4096 MiB total; 523 MiB used; 3573 MiB available (3.489 GiB) |
| NVIDIA driver | 610.57.04 |
| CUDA | Driver-reported version 13.3; this does not establish an installed CUDA toolkit or compatible framework build |
| System RAM | 15 GiB total; 5.1 GiB used; approximately 10 GiB available |
| Swap | 15 GiB; not included in usable RAM or VRAM budgets |

Free memory is a dated observation and must be checked before runs. CPU model, OS, installed toolkit/framework, quantization and attention backend remain to be recorded in S1-T03. Driver information alone does not prove runtime compatibility.

## Assessment assumptions and reproducible accounting

- One model and one request at a time; batch size 1; inference only, without gradients or training allocations.
- Maximum 2048 input tokens **including the chat template and all prompt content**, plus 256 generated tokens: 2304 total cached tokens. No maximum-context or concurrent serving claim.
- Full per-layer FP16 KV cache, including both keys and values; no cache quantization or offload assumed. KV size follows each publisher configuration, not the weight precision.
- Ideal weights use parameter counts from the candidate matrix. Conservative quantized-weight estimates leave the tied vocabulary embedding/output matrix in FP16 and add 10% to the remaining quantized weights for scales, metadata and mixed-precision effects. This is an explicit planning allowance, not a measured checkpoint size or universal upper bound; other retained FP16 layers can increase it.
- Add **0.5–1.0 GiB** for activations, CUDA/framework allocations, attention workspace and allocator behavior. This assumes memory-efficient attention and bounded loading without a second full GPU copy. Eager attention, full-prompt logits, loading peaks or a different runtime can exceed it; the range is not a guarantee.
- Reserve **512 MiB** of the measured free VRAM for headroom, in addition to the existing 523 MiB usage. Model-process budget: `(3573 - 512) / 1024 = 2.989 GiB`. Estimated totals below exclude existing usage and reserved headroom and are compared with this budget.
- No CPU offload in the table. Approximately 10 GiB available RAM makes CPU/offload trials possible to investigate, but does not prove load-time RAM fit, acceptable latency or runtime support. Swap is not a performance or capacity guarantee.

```text
ideal_weights_GiB = parameters * (weight_bits / 8) / 2^30
embedding_parameters = vocabulary_size * hidden_size  # tied matrix counted once
quantized_weights_GiB = ((parameters - embedding_parameters) * (weight_bits / 8)
                         * 1.10 + embedding_parameters * 2) / 2^30
KV_GiB = 2 * layers * KV_heads * head_dimension * batch * cached_tokens
         * cache_bytes_per_element / 2^30
estimated_process_GiB = estimated_weights_GiB + KV_GiB + runtime_allowance_GiB
```

Architecture inputs were checked against the publisher configuration files on 2026-10-14. These mutable references must be pinned to immutable revisions before execution; only public metadata was read, no weights downloaded.

| Model / official configuration | Layers | KV heads | Head dimension | Vocabulary × hidden size | FP16 KV at 2304 tokens |
|---|---:|---:|---:|---|---:|
| [Qwen 1.5B](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct/raw/main/config.json) | 28 | 2 | 128 | 151936 × 1536 | 0.062 GiB |
| [Qwen 3B](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct/raw/main/config.json) | 36 | 2 | 128 | 151936 × 2048 | 0.079 GiB |
| [Phi-4-mini](https://huggingface.co/microsoft/Phi-4-mini-instruct/raw/main/config.json) | 32 | 8 | 128 | 200064 × 3072 | 0.281 GiB |
| [SmolLM2 1.7B](https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B-Instruct/raw/main/config.json) | 24 | 32 | 64 | 49152 × 2048 | 0.422 GiB |

## Per-model inference compatibility assessment

**Theoretical weight fit** compares ideal weight storage with measured free VRAM (3.489 GiB), without runtime costs or headroom. **Estimated inference fit** compares the conservative process range with the 2.989 GiB budget. **Experimentally verified fit: none**, for every configuration below. No model has been downloaded, loaded, executed or benchmarked; no peak-memory, throughput, latency or SOC-quality measurements exist.

| Model | Weight precision | Ideal weights (GiB) | Theoretical weight fit | Estimated process (GiB) | Estimated inference fit on this laptop |
|---|---|---:|---|---|---|
| Qwen 1.5B | FP16 | 2.87 | Yes | 3.43–3.93 | Does not fit budget; weight fit alone is misleading |
| Qwen 1.5B | 8-bit | 1.43 | Yes | 2.34–2.84 | Estimated feasible within assumed range |
| Qwen 1.5B | 4-bit | 0.72 | Yes | 1.67–2.17 | Estimated feasible within assumed range |
| Qwen 3B | FP16 | 5.76 | No | 6.33–6.83 | Does not fit |
| Qwen 3B | 8-bit | 2.88 | Yes | 4.01–4.51 | Does not fit despite ideal weight fit |
| Qwen 3B | 4-bit | 1.44 | Yes | 2.58–3.08 | Conditional; upper estimate exceeds budget |
| Phi-4-mini | FP16 | 7.08 | No | 7.86–8.36 | Does not fit |
| Phi-4-mini | 8-bit | 3.54 | No | 5.19–5.69 | Does not fit |
| Phi-4-mini | 4-bit | 1.77 | Yes | 3.56–4.06 | Does not fit conservative assumptions; alternative configuration needed |
| SmolLM2 1.7B | FP16 | 3.17 | Yes | 4.09–4.59 | Does not fit despite ideal weight fit |
| SmolLM2 1.7B | 8-bit | 1.58 | Yes | 2.75–3.25 | Conditional; upper estimate exceeds budget |
| SmolLM2 1.7B | 4-bit | 0.79 | Yes | 1.93–2.43 | Estimated feasible within assumed range |

Rounded display values are not admission thresholds. Conditional rows require lower measured overhead, reduced context, a suitable quantization layout or CPU offload before claiming fit. No quantized artifact/backend is selected or verified here.

Phi's large embedding table makes quantization layout particularly significant. If a compatible 4-bit artifact quantizes **all** parameters with a 10% storage allowance, its alternative estimate is `1.770 * 1.10 + 0.281 + (0.5–1.0) = 2.73–3.23 GiB`: still conditional at 2304 tokens. Reducing total cached tokens to 1280 (1024 input + 256 output) makes that alternative approximately 2.60–3.10 GiB. This is a sensitivity calculation, not evidence that such an artifact or runtime works. CPU offload or a larger GPU remains a possible S1 comparison path; Phi is retained in the shortlist.

## Sprint 0 completion and future validation boundary

This documented hardware compatibility assessment supplies the S0-T05 licence/memory-fit evidence against an available machine. It does not certify experimental compatibility, choose a final model or claim training fit. **Final selection remains ADR-002**, after S1 evaluation. QLoRA/training memory requires separate S5-T06 assessment.

S1-T03 must record the full environment, pinned model/tokenizer and quantized-artifact revisions, precision/backend, actual input/output lengths, batch, offload settings, peak allocated/reserved GPU memory, device-level usage, successful generation or explicit failure, and remaining headroom. Loading peaks and host RAM must also be checked. Record out-of-memory failures explicitly. Baseline metrics and reproducibility follow S0-T06/S1-T02 conventions; the official environment freeze remains S5-T01.

## Runtime and benchmark handoff

S1-T03 must verify tokenizer/chat template, checkpoint revision, supported runtime/attention backend and structured-output behavior. Qwen cards identify support in Transformers from 4.37; Phi's card describes integration in 4.49 and an eager-attention alternative for older GPUs. These are publisher compatibility notes, not the project's future dependency pins. Choose maintained compatible versions and test on the actual environment. Avoid remote-code execution by default; if a checkpoint/runtime requires it, inspect the pinned code and obtain review before enabling it. Do not copy provider examples granting arbitrary tool privileges.

Record CPU/GPU model, VRAM/RAM, OS, Python/PyTorch/runtime, attention implementation, quantization backend, checkpoint/tokenizer revision, input/output budgets, prompt/data versions and Git commit. Benchmark every candidate on the same reviewed development cases and protocol, then select the baseline in [ADR-002](../docs/adr/ADR-002.md). Final official environment freeze remains S5-T01 / ADR-007.

The CDC Qwen-versus-Phi comparison remains required; SmolLM2 is an additional candidate. Compare SOC triage, evidence grounding, structured output, action correctness, latency and memory using S0-T06/S1-T02 definitions. Keep development tuning separate from frozen-test reporting and do not rank models here using general publisher benchmark numbers.

S5-T06's Base-versus-Fine-tuned comparison refers to the selected unmodified checkpoint versus its adapted version under the frozen protocol; it must not be confused with comparing pretraining and instruct checkpoints. Track adapter provenance/license and training split separately. Exact model choice, inference serving, storage and benchmark environment remain their scheduled ADR decisions.

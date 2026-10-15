# Evidence and design rationale

Reviewed 2026-10-15. Primary research and publisher/maintainer documentation only. These sources justify design choices; they are not evidence that CyberSOC AI has been evaluated successfully. The task's authority remains the CDC.

| Source | Relevant finding | Application and limitation |
|---|---|---|
| [REFORMS, Kapoor et al., author preprint](https://arxiv.org/abs/2308.07832) | Reporting standards address validity, reproducibility and generalizability. | Preserve study question, provenance, method, results and limitations. We adopt a compact project record, not a claim of complete checklist compliance. |
| [Leakage and the Reproducibility Crisis, Kapoor & Narayanan, author preprint](https://arxiv.org/abs/2207.07048) | Leakage can undermine scientific claims. | Incident-group splits and provenance are project-specific applications. No actual contamination study was performed here. |
| [RAGAs, Es et al., EACL 2024](https://aclanthology.org/2024.eacl-demo.16/) | Faithfulness checks extracted statements against context; generation and retrieval have distinct quality dimensions. | Retain atomic claims and support decisions. The paper's WikiEval results do not validate a SOC judge; do not assume its agreement figures transfer. |
| [Judging LLM-as-a-Judge, Zheng et al., NeurIPS 2023](https://papers.neurips.cc/paper_files/paper/2023/hash/91f18a1287b398d378ef22505bf41832-Abstract-Datasets_and_Benchmarks.html) | Judges exhibit position, verbosity and self-enhancement biases. | Version prompts/models and validate locally against humans. Its chat-preference experiments do not establish SOC correctness. |
| [PyTorch reproducibility guidance](https://github.com/pytorch/pytorch/blob/main/docs/source/notes/randomness.md) | Seeds alone do not guarantee results across versions/platforms; deterministic operations can change performance. | Capture environment and determinism settings; report repeated outcomes and avoid guarantees of bit-identical replication. |
| [MLflow self-hosting](https://mlflow.org/docs/latest/self-hosting/), [tracing FAQ](https://mlflow.org/docs/latest/genai/tracing/faq/) | Local/small-team hosting; run metadata and traces are distinct. | Proposed single tracking tool, with explicit run/trace correlation. No deployment or overhead measurement here. |
| [Langfuse self-hosting](https://langfuse.com/self-hosting) | Documents web/worker plus PostgreSQL, ClickHouse, Redis/Valkey and blob storage. | More services to operate than the documented minimal MLflow start; actual resource/cost measurements remain unverified. |
| [W&B academic offering](https://site.wandb.ai/research/) | Advertises academic access and team experiment collaboration. | Managed alternative; account eligibility, quotas, data handling and export must be checked before adoption. |

The proposal uses MLflow because this project combines classical model/inference experiments and future agent tracing. That is an engineering assessment based on documented capabilities, not a scientific ranking of tools. Pin an evaluated software release during deployment rather than installing an unbounded `latest`; these online documents can change.

## Explicit review decisions

- Preserve CDC faithfulness as context support, not general factual accuracy. A faithful answer may repeat poisoned evidence; score SOC correctness and security separately.
- Keep CDC's human-validation target of at least 50 double-labelled claims. This is a project minimum, not a scientifically established sufficient sample size.
- Freeze answer-level rubric anchors and claim-level support rules separately. Do not fabricate agreement thresholds, success targets or dataset size.
- Treat No-RAG evidence eligibility, zero-denominator handling, action-argument matching and train-within-development as reviewable protocol clarifications in this task's PR.

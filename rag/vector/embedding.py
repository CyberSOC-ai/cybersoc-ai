"""CPU BGE encoding with explicit token checks and no automatic truncation."""

import math
from importlib.metadata import version
from pathlib import Path

from rag.ingestion.core import IngestionError
from .chunking import Chunker
from .model import verify_model

QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


def validate_vectors(vectors, count):
    if len(vectors) != count:
        raise IngestionError("Embedding result count mismatch")
    result = []
    for vector in vectors:
        values = list(vector)
        if (len(values) != 384 or any(type(v) not in (int, float) or not math.isfinite(v) for v in values)):
            raise IngestionError("Expected finite 384-dimensional embeddings")
        norm = math.sqrt(sum(v * v for v in values))
        if abs(norm - 1.0) > 1e-5:
            raise IngestionError("Embedding is not L2 normalized")
        result.append(values)
    return result


class BGEEncoder:
    def __init__(self, directory, threads=4):
        if type(threads) is not int or not 1 <= threads <= 4:
            raise IngestionError("CPU threads must be between 1 and 4")
        self.identity = verify_model(directory)
        self.chunker = Chunker(Path(directory) / "tokenizer.json")
        # Optional heavy imports: regular CI can test artifact/validation logic
        # without importing a GPU runtime or downloading any model.
        import torch
        from sentence_transformers import SentenceTransformer
        for package, expected in {"torch": "2.9.0+cpu", "sentence-transformers": "5.1.2",
                                  "transformers": "4.57.1", "tokenizers": "0.22.1",
                                  "numpy": "2.3.4", "safetensors": "0.6.2"}.items():
            if version(package) != expected:
                raise IngestionError("Embedding runtime version mismatch; use requirements-embeddings.txt")
        if torch.version.cuda is not None:
            raise IngestionError("Use the pinned CPU-only PyTorch environment")
        torch.set_num_threads(threads)
        self.model = SentenceTransformer(
            str(Path(directory).resolve()), device="cpu", local_files_only=True,
            trust_remote_code=False, model_kwargs={"use_safetensors": True, "torch_dtype": torch.float32},
            prompts={"query": "", "document": ""})
        self.model.eval()
        self.model.max_seq_length = 512
        if self.model.get_sentence_embedding_dimension() != 384:
            raise IngestionError("Wrong model embedding dimension")
        self.threads = threads

    def encode(self, texts, expected_counts=None):
        if not texts or len(texts) > 16:
            raise IngestionError("Embedding batch must contain 1–16 texts")
        if any(not isinstance(t, str) or not t.strip() or len(t) > 16000 for t in texts):
            raise IngestionError("Invalid or oversized embedding text")
        reference = [self.chunker.tokenizer.encode(t).ids for t in texts]
        actual = self.model.tokenizer(texts, truncation=False, padding=False, add_special_tokens=True)["input_ids"]
        if actual != reference:
            raise IngestionError("Inference tokenizer differs from chunking tokenizer")
        counts = [len(ids) for ids in actual]
        if any(n > 512 for n in counts):
            raise IngestionError("Embedding input exceeds 512 tokens; no truncation permitted")
        if expected_counts is not None and list(expected_counts) != counts:
            raise IngestionError("Saved passage token count mismatch")
        values = self.model.encode(texts, batch_size=len(texts), show_progress_bar=False,
                                   convert_to_numpy=True, normalize_embeddings=True,
                                   precision="float32", prompt="")
        return validate_vectors(values.tolist(), len(texts))

    def query(self, text):
        if not isinstance(text, str) or not text.strip() or len(text) > 4000:
            raise IngestionError("Query must contain 1–4000 characters")
        return self.encode([QUERY_PREFIX + text])[0]

"""Offline streaming chunk build with atomic publication and exclusion accounting."""

import argparse
from collections import Counter
import hashlib
import os
from pathlib import Path
import platform
import subprocess
import tempfile

from rag.ingestion.core import IngestionError, canonical, digest
from .chunking import Chunker, DEFAULT_CONFIG
from .inputs import CorpusInput

ROOT = Path(__file__).resolve().parents[2]


def implementation_identity():
    paths = [*sorted((ROOT / "rag/vector").glob("*.py")),
             *sorted((ROOT / "rag/vector/configs").glob("*.json")),
             ROOT / "requirements.txt", ROOT / "rag/ingestion/core.py",
             ROOT / "rag/ingestion/adapters.py",
             *sorted((ROOT / "rag/ingestion/schemas").glob("*.json"))]
    return {p.relative_to(ROOT).as_posix(): digest(p.read_bytes()) for p in paths}


def git_state():
    def git(*args):
        result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                                check=True, timeout=10)
        return result.stdout.strip()
    try:
        return {"commit": git("rev-parse", "HEAD"), "dirty": bool(git("status", "--porcelain"))}
    except (OSError, subprocess.SubprocessError):
        return {"commit": None, "dirty": None, "reason": "git_unavailable"}


def build(corpus, manifest_sha256, tokenizer, output, *, config=DEFAULT_CONFIG,
          splits=ROOT / "datasets/evaluation/soc-eval-v1/splits.json",
          policies=None, limit_per_source=None):
    if limit_per_source is not None and (type(limit_per_source) is not int or limit_per_source < 1):
        raise IngestionError("Preview limit must be a positive integer")
    output = Path(output)
    if output.exists():
        raise IngestionError("Use a new chunk output directory")
    policies = policies if policies is not None else [ROOT / "datasets/knowledge/soc-policy.json",
                                                     ROOT / "datasets/knowledge/external-policy.json"]
    inputs = CorpusInput(corpus, manifest_sha256, splits, policies)
    chunker = Chunker(tokenizer, config)
    implementation = implementation_identity()
    state = git_state()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".chunks-", dir=output.parent) as tmp:
        stage = Path(tmp) / "release"
        stage.mkdir()
        counts, selected, excluded, flags, chunks_by_source = (Counter() for _ in range(5))
        checksums = {name: hashlib.sha256() for name in ("chunks.jsonl", "decisions.jsonl")}
        total_chunks, max_tokens, max_characters = 0, 0, 0
        with (stage / "chunks.jsonl").open("xb") as chunks_file, (stage / "decisions.jsonl").open("xb") as decisions:
            for record in inputs.records():
                source = record["source"]
                counts[source] += 1
                if limit_per_source is not None and selected[source] >= limit_per_source:
                    continue
                selected[source] += 1
                chunks, decision = chunker.chunks(record)
                if decision["excluded"]:
                    excluded[decision["excluded"]] += 1
                flags.update(decision["flags"])
                decision.update(record_id=record["record_id"], source=source,
                                source_record_id=record["source_record_id"],
                                snapshot_ref=record["snapshot_ref"], chunks=len(chunks))
                raw = canonical(decision) + b"\n"
                decisions.write(raw)
                checksums["decisions.jsonl"].update(raw)
                for chunk in chunks:
                    raw = canonical(chunk) + b"\n"
                    chunks_file.write(raw)
                    checksums["chunks.jsonl"].update(raw)
                    total_chunks += 1
                    chunks_by_source[source] += 1
                    max_tokens = max(max_tokens, chunk["token_count"])
                    max_characters = max(max_characters, len(chunk["embedding_text"]))
        # Recheck bytes that affect eligibility/configuration before publication.
        current = CorpusInput(corpus, manifest_sha256, splits, policies)
        if (current.policy_sha256s != inputs.policy_sha256s or
                current.splits_sha256 != inputs.splits_sha256 or
                implementation_identity() != implementation or
                Chunker(tokenizer, config).config_sha256 != chunker.config_sha256):
            raise IngestionError("Build inputs or implementation changed during chunking")
        manifest = {
            "schema_version": "1.0.0", "artifact_kind": "chunks_no_embeddings",
            "corpus_manifest_sha256": inputs.manifest_sha256,
            "corpus_records_sha256": inputs.manifest["records_sha256"],
            "corpus_use": inputs.manifest["corpus_use"],
            "splits_sha256": inputs.splits_sha256, "policy_sha256s": inputs.policy_sha256s,
            "config": chunker.config, "config_sha256": chunker.config_sha256,
            "implementation_files": implementation, "git": state,
            "environment": {"python": platform.python_version(), "system": platform.system()},
            "preview_limit_per_source": limit_per_source,
            "input_records": sum(counts.values()), "input_by_source": dict(counts),
            "selected_records": sum(selected.values()), "selected_by_source": dict(selected),
            "excluded": dict(excluded), "quality_flags": dict(flags),
            "chunks": total_chunks, "chunks_by_source": dict(chunks_by_source),
            "maximum_tokens": max_tokens, "maximum_characters": max_characters,
            "output_sha256": {name: h.hexdigest() for name, h in checksums.items()},
        }
        manifest["build_id"] = digest(canonical(manifest))
        (stage / "manifest.json").write_bytes(canonical(manifest) + b"\n")
        (stage / "chunking-config.json").write_bytes(chunker.config_bytes)
        if output.exists():
            raise IngestionError("Output appeared during build")
        os.rename(stage, output)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", required=True, type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--tokenizer", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--config", default=DEFAULT_CONFIG, type=Path)
    parser.add_argument("--splits", default=ROOT / "datasets/evaluation/soc-eval-v1/splits.json", type=Path)
    parser.add_argument("--policy", action="append", type=Path)
    parser.add_argument("--limit-per-source", type=int, help="Preview only; still verifies the complete input corpus")
    args = parser.parse_args()
    try:
        report = build(args.corpus, args.manifest_sha256, args.tokenizer, args.output,
                       config=args.config, splits=args.splits, policies=args.policy,
                       limit_per_source=args.limit_per_source)
    except (IngestionError, OSError) as exc:
        parser.exit(1, f"Chunk build failed: {exc}\n")
    print(canonical(report).decode())


if __name__ == "__main__":
    main()

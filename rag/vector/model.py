"""Acquire only pinned BGE files and verify their bytes before offline loading."""

import argparse
import hashlib
import os
from pathlib import Path
import tempfile

import httpx

from rag.ingestion.core import IngestionError, canonical, parse_json, read_bytes
from .chunking import TOKENIZER_REVISION, TOKENIZER_SHA256

PINS = Path(__file__).parent / "configs/model-files-v1.json"
WEIGHTS_SHA256 = "3c9f31665447c8911517620762200d2245a2518d6e7208acc78cd9db317e21ad"
FILES = {"1_Pooling/config.json", "README.md", "config.json", "config_sentence_transformers.json",
         "model.safetensors", "modules.json", "sentence_bert_config.json", "special_tokens_map.json",
         "tokenizer.json", "tokenizer_config.json", "vocab.txt"}


def pins():
    value = parse_json(read_bytes(PINS, 65536))
    if (value["model_id"] != "BAAI/bge-small-en-v1.5" or value["revision"] != TOKENIZER_REVISION or
            set(value["files"]) != FILES or value["files"]["model.safetensors"]["sha256"] != WEIGHTS_SHA256):
        raise IngestionError("Unsupported model pin manifest")
    return value


def verify_file(path, expected):
    if path.is_symlink() or not path.is_file() or path.stat().st_size != expected["bytes"]:
        raise IngestionError("Missing model file or byte-size mismatch")
    sha256 = hashlib.sha256()
    git_blob = hashlib.sha1(b"blob " + str(expected["bytes"]).encode() + b"\0")
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            sha256.update(block)
            git_blob.update(block)
    actual = sha256.hexdigest()
    if (("sha256" in expected and actual != expected["sha256"]) or
            ("sha256" not in expected and git_blob.hexdigest() != expected["git_blob_sha1"])):
        raise IngestionError("Model file integrity mismatch")
    return actual


def verify_model(directory):
    directory = Path(directory)
    if directory.is_symlink():
        raise IngestionError("Model directory must not be a symlink")
    identity = pins()
    found = {p.relative_to(directory).as_posix() for p in directory.rglob("*") if p.is_file()}
    if found != FILES | {"acquisition.json"}:
        raise IngestionError("Unexpected or missing model files")
    hashes = {}
    for name, expected in identity["files"].items():
        path = directory / name
        if not path.resolve().is_relative_to(directory.resolve()):
            raise IngestionError("Model file escapes directory")
        hashes[name] = verify_file(path, expected)
    if hashes["tokenizer.json"] != TOKENIZER_SHA256:
        raise IngestionError("Embedding/chunking tokenizer mismatch")
    receipt = parse_json(read_bytes(directory / "acquisition.json", 65536))
    if receipt != {"model_id": identity["model_id"], "revision": identity["revision"], "sha256": hashes}:
        raise IngestionError("Model receipt mismatch")
    return receipt


def acquire(output):
    output = Path(output)
    if output.exists():
        raise IngestionError("Use a new model directory")
    identity = pins()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".model-", dir=output.parent) as tmp:
        stage = Path(tmp) / "model"
        stage.mkdir()
        hashes = {}
        with httpx.Client(follow_redirects=True, timeout=httpx.Timeout(60, connect=20)) as client:
            for name, expected in sorted(identity["files"].items()):
                path = stage / name
                path.parent.mkdir(parents=True, exist_ok=True)
                url = f"https://huggingface.co/{identity['model_id']}/resolve/{identity['revision']}/{name}"
                with client.stream("GET", url) as response, path.open("xb") as target:
                    response.raise_for_status()
                    size = 0
                    for block in response.iter_bytes(1024 * 1024):
                        size += len(block)
                        if size > expected["bytes"]:
                            raise IngestionError("Model download exceeds pinned size")
                        target.write(block)
                hashes[name] = verify_file(path, expected)
        receipt = {"model_id": identity["model_id"], "revision": identity["revision"], "sha256": hashes}
        (stage / "acquisition.json").write_bytes(canonical(receipt) + b"\n")
        verify_model(stage)
        if output.exists():
            raise IngestionError("Model output appeared during acquisition")
        os.rename(stage, output)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        print(canonical(acquire(args.output)).decode())
    except (IngestionError, OSError, httpx.HTTPError) as exc:
        parser.exit(1, f"Model acquisition failed: {type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    main()

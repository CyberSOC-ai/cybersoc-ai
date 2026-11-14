"""Verify local model/runtime bytes before explicit process startup."""

from pathlib import Path

from .contracts import strict_json
from .provenance import ROOT, digest


def configuration(path):
    config = strict_json(Path(path).read_text(encoding="utf-8"))
    for key, hash_key in (("model_file", "model_sha256"), ("runtime_executable", "runtime_sha256")):
        artifact = Path(config[key])
        if not artifact.is_absolute():
            artifact = ROOT / artifact
        if digest(artifact) != config[hash_key]:
            raise ValueError(f"{key} checksum mismatch")
        config[key] = str(artifact.resolve())
    return config

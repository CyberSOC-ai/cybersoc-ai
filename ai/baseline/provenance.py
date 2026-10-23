"""Snapshot the explicit execution inputs, including locally edited evaluation code."""

import hashlib
from pathlib import Path


SOURCE_SCOPE = (
    "ai/baseline", "ai/evaluation", "backend/contracts/v1",
    "datasets/evaluation/soc-eval-v1", "experiments/templates",
    "experiments/METRICS.md", "requirements.txt", "pyproject.toml", ".gitattributes",
)
TEXT_SUFFIXES = {".py", ".txt", ".json", ".md", ".toml"}


def snapshot_sources(root, output):
    """Copy exact dependency bytes under source/<repository-relative path>.

    Includes dirty and untracked execution inputs inside the declared scope, not
    ignored artifacts, credentials, or arbitrary worktree files. New runtime
    dependencies must be added to SOURCE_SCOPE when introduced.
    """
    root, output = Path(root).resolve(), Path(output)
    target_root = output / "source"
    target_root.mkdir()
    manifest = {}
    for scope in SOURCE_SCOPE:
        source = root / scope
        if source.is_symlink():
            raise ValueError("Source snapshots cannot follow symlinks")
        if not source.exists():
            continue
        candidates = sorted(source.rglob("*")) if source.is_dir() else [source]
        for path in candidates:
            if path.is_symlink():
                raise ValueError("Source snapshots cannot follow symlinks")
            if not path.is_file() or (path.suffix not in TEXT_SUFFIXES and path.name != ".gitattributes"):
                continue
            relative = path.relative_to(root)
            data = path.read_bytes()
            target = target_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            manifest[relative.as_posix()] = hashlib.sha256(data).hexdigest()
    return manifest

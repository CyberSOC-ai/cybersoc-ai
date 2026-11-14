"""Source identity and portable run metadata shared by investigation modes."""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
IMPLEMENTATION_ID = "local-layout-v2"
# Execution sources only: no model inputs, evaluator labels or documentation.
SOURCES = tuple(str(p.relative_to(ROOT)) for p in sorted(Path(__file__).parent.glob('*.py')))
SOURCES += ("ai/runtime/configs/qwen-cpu-linux.json", "ai/runtime/configs/shared-dev-v1-policy.json",
            "ai/runtime/Dockerfile", "requirements.txt", "pyproject.toml")


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def utc():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def git_state():
    # The minimal inference image has no Git. Its launcher records host identity;
    # the execution snapshot independently identifies the actual source bytes.
    commit, dirty = os.environ.get("CYBERSOC_RUN_COMMIT"), os.environ.get("CYBERSOC_RUN_DIRTY")
    if commit is not None or dirty is not None:
        if not re.fullmatch(r"[0-9a-f]{40}", commit or "") or dirty not in ("true", "false"):
            raise ValueError("Invalid launcher Git identity")
        return commit, dirty == "true"
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
    return commit, dirty

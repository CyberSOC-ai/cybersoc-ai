"""Prepare the two existing lab fixtures as a reproducible offline SOC snapshot."""

import argparse
import os
from pathlib import Path
import tempfile

from .core import canonical, digest, parse_json, validate

ROOT = Path(__file__).resolve().parents[2]
PINNED_DIGESTS = (
    "b527e78b837606a52131b670a54ce12dab1c629c9db2fc8696cf89c7f6c0e435",
    "b9c5144378b4350087e7efe43809d02b99f7306b33556be580219f21a891420b",
)


def prepare(output, acquired_at):
    output = Path(output)
    if output.exists():
        raise ValueError("Use a new snapshot directory")
    paths = [ROOT / f"tests/normalizer/fixtures/lab01-run{run}-incident.json" for run in ("01", "02")]
    incidents = [parse_json(path.read_bytes()) for path in paths]
    if tuple(digest(canonical(item)) for item in incidents) != PINNED_DIGESTS:
        raise ValueError("Lab fixtures differ from the pinned S1-T06 revision")
    data = canonical(incidents) + b"\n"
    notice = (ROOT / "datasets/knowledge/SOC_ASSIGNMENTS.md").read_bytes()
    manifest = {
        "schema_version": "1.0.0", "source": "soc_log", "owner": "Ahmed",
        "source_url": "https://github.com/CyberSOC-ai/cybersoc-ai/tree/"
        "48c224ff6f358b0d9ffd878d4af3013b503d230b/tests/normalizer/fixtures",
        "upstream_version": "S1-T06:48c224ff6f358b0d9ffd878d4af3013b503d230b",
        "acquired_at": acquired_at, "sha256": digest(data),
        "artifact_ref": "sha256:" + digest(data),
        "license_ref": "project-internal:lab-evidence-no-new-redistribution-grant",
        "notice_ref": "datasets/knowledge/SOC_ASSIGNMENTS.md",
        "notice_sha256": digest(notice), "usage_scope": "project-retrieval",
    }
    validate("snapshot", manifest)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".lab-", dir=output.parent) as temp:
        staging = Path(temp) / "snapshot"
        staging.mkdir()
        (staging / "snapshot.json").write_bytes(data)
        (staging / "snapshot-manifest.json").write_bytes(canonical(manifest) + b"\n")
        (staging / "notice.txt").write_bytes(notice)
        os.rename(staging, output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--acquired-at", required=True, help="UTC snapshot preparation time, ending Z")
    args = parser.parse_args()
    prepare(args.output, args.acquired_at)


if __name__ == "__main__":
    main()

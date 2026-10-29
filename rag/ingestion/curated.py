"""Acquire an explicitly selected set of files from pinned official repositories."""

import argparse
from datetime import datetime, timezone
import io
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
import zipfile

import httpx

from .acquire import get
from .core import IngestionError, canonical, digest, parse_json, read_bytes, validate

REPOSITORIES = {"cve_program": "CVEProject/cvelistV5", "kev": "cisagov/kev-data",
                "sigma": "SigmaHQ/sigma", "playbook": "OTRF/ThreatHunter-Playbook",
                "otrf": "OTRF/Security-Datasets", "splunk": "splunk/attack_data"}
SOURCE_TYPES = {"cve_program": "cve", "kev": "kev", "sigma": "detection_rule",
                "playbook": "playbook", "otrf": "soc_log", "splunk": "soc_log"}


def safe_path(path):
    value = PurePosixPath(path)
    if value.is_absolute() or ".." in value.parts or "\\" in path or not path:
        raise IngestionError("Unsafe upstream path")
    return path


def fetch_file(client, repo, revision, path):
    path = safe_path(path)
    url = f"https://raw.githubusercontent.com/{repo}/{revision}/{path}"
    data = get(client, url, 64 * 1024**2)
    if data.startswith(b"version https://git-lfs.github.com/spec/v1\n"):
        pointer = data.decode("ascii")
        match = re.search(r"^oid sha256:([a-f0-9]{64})$", pointer, re.M)
        size = re.search(r"^size (\d+)$", pointer, re.M)
        if not match or not size or int(size[1]) > 64 * 1024**2:
            raise IngestionError("Unsupported or oversized Git LFS pointer")
        data = get(client, f"https://media.githubusercontent.com/media/{repo}/{revision}/{path}",
                   64 * 1024**2)
        if digest(data) != match[1] or len(data) != int(size[1]):
            raise IngestionError("Git LFS integrity mismatch")
    return data, url


def unpack(path, data):
    if not path.endswith(".zip"):
        yield path, data
        return
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        members = archive.infolist()
        if len(members) > 20:
            raise IngestionError("Too many external archive members")
        total = 0
        for member in members:
            safe_path(member.filename)
            total += member.file_size
            if member.is_dir() or not member.filename.endswith((".json", ".log", ".jsonl")):
                raise IngestionError("Unexpected external archive member")
            if total > 64 * 1024**2:
                raise IngestionError("External archive exceeds decompression budget")
            with archive.open(member) as stream:
                content = stream.read(64 * 1024**2 + 1)
            if len(content) != member.file_size:
                raise IngestionError("External archive size mismatch")
            yield path + "!" + member.filename, content


def acquire_selection(selection_path, provider, output):
    plan = parse_json(read_bytes(selection_path, 1024**2))
    config = plan["sources"][provider]
    if config["repository"] != REPOSITORIES[provider] or not re.fullmatch("[a-f0-9]{40}", config["revision"]):
        raise IngestionError("Expected an approved repository and immutable revision")
    files = config["files"]
    if not isinstance(files, list) or not 1 <= len(files) <= 50 or len(files) != len(set(files)):
        raise IngestionError("Expected 1–50 unique explicitly selected files")
    output = Path(output)
    if output.exists():
        raise IngestionError("Use a new snapshot directory")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".curated-", dir=output.parent) as temp:
        stage = Path(temp) / "snapshot"
        stage.mkdir()
        bundle, receipts, total_bytes = [], [], 0
        with httpx.Client(timeout=httpx.Timeout(60, connect=15), follow_redirects=False) as client:
            if provider == "cve_program":
                notice_url = "https://www.cve.org/Legal/TermsOfUse"
                notice = get(client, notice_url, 4 * 1024**2)
            else:
                notice, notice_url = fetch_file(client, config["repository"], config["revision"], config["notice"])
            for index, path in enumerate(files):
                raw, url = fetch_file(client, config["repository"], config["revision"], path)
                total_bytes += len(raw)
                if total_bytes > 128 * 1024**2:
                    raise IngestionError("Selected upstream files exceed total acquisition budget")
                (stage / f"upstream-{index:03d}.bin").write_bytes(raw)
                receipts.append({"path": path, "source_url": url, "sha256": digest(raw), "bytes": len(raw)})
                for member_path, data in unpack(path, raw):
                    if path.endswith(".zip"):
                        total_bytes += len(data)
                    if total_bytes > 128 * 1024**2:
                        raise IngestionError("Selected files exceed total decompression budget")
                    if len(data) > 32 * 1024**2:
                        raise IngestionError("Selected source file exceeds text budget")
                    bundle.append({"path": member_path, "source_url": url, "sha256": digest(data),
                                   "content": data.decode("utf-8-sig")})
        data = canonical({"provider": provider, "files": bundle}) + b"\n"
        if len(data) > 128 * 1024**2:
            raise IngestionError("Curated snapshot exceeds byte budget")
        checksum = digest(data)
        manifest = {"schema_version": "1.0.0", "source": SOURCE_TYPES[provider], "owner": plan["owner"],
                    "source_url": f"https://github.com/{config['repository']}/tree/{config['revision']}",
                    "upstream_version": provider + ":" + config["revision"],
                    "acquired_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
                    "sha256": checksum, "artifact_ref": "sha256:" + checksum,
                    "license_ref": notice_url, "notice_ref": "sha256:" + digest(notice),
                    "notice_sha256": digest(notice), "usage_scope": "project-retrieval"}
        validate("snapshot", manifest)
        (stage / "snapshot.json").write_bytes(data)
        (stage / "notice.txt").write_bytes(notice)
        (stage / "snapshot-manifest.json").write_bytes(canonical(manifest) + b"\n")
        (stage / "selection.json").write_bytes(canonical(plan) + b"\n")
        (stage / "acquisition.json").write_bytes(canonical({"provider": provider, "manifest": manifest,
                                                           "files": receipts, "selection_sha256": digest(canonical(plan))}) + b"\n")
        os.rename(stage, output)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", required=True)
    parser.add_argument("--provider", choices=list(REPOSITORIES), required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(canonical(acquire_selection(args.selection, args.provider, args.output)).decode())


if __name__ == "__main__":
    main()

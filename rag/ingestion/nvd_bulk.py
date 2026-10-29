"""Acquire official annual NVD feeds and normalize them without loading the feed."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import os
from pathlib import Path
import re
import sqlite3
import tempfile
import time

import httpx
import ijson

from .acquire import get
from .adapters import cve_records
from .core import IngestionError, canonical, digest, validate

MAX_FEED_BYTES = 2 * 1024**3
MAX_ARCHIVE_BYTES = 128 * 1024**2
NIST_NOTICE = ("https://www.nist.gov/open/"
               "copyright-fair-use-and-licensing-statements-srd-data-software-and-technical-series-publications")


def file_hash(path, limit=MAX_FEED_BYTES):
    hasher, size = hashlib.sha256(), 0
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024**2), b""):
            size += len(block)
            if size > limit:
                raise IngestionError("Bulk input exceeds byte limit")
            hasher.update(block)
    return hasher.hexdigest(), size


def download(client, url, path):
    size, deadline = 0, time.monotonic() + 300
    with client.stream("GET", url) as response, Path(path).open("xb") as stream:
        response.raise_for_status()
        for block in response.iter_bytes(1024**2):
            size += len(block)
            if size > MAX_ARCHIVE_BYTES or time.monotonic() > deadline:
                raise IngestionError("Bulk acquisition exceeds size/time budget")
            stream.write(block)


def acquire_year(year, output, owner="Ahmed"):
    if not re.fullmatch(r"(?:19|20)\d{2}", str(year)) or int(year) < 2002:
        raise IngestionError("Expected an NVD feed year from 2002 onwards")
    output = Path(output)
    if output.exists():
        raise IngestionError("Use a new acquisition directory")
    base = f"https://nvd.nist.gov/feeds/json/cve/2.0/nvdcve-2.0-{year}"
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".nvd-", dir=output.parent) as temp:
        stage = Path(temp) / "snapshot"
        stage.mkdir()
        with httpx.Client(timeout=httpx.Timeout(60, connect=15), follow_redirects=False) as client:
            meta_bytes = get(client, base + ".meta", 16384)
            meta = dict(line.split(":", 1) for line in meta_bytes.decode("utf-8").splitlines() if ":" in line)
            if not re.fullmatch(r"[a-fA-F0-9]{64}", meta.get("sha256", "")):
                raise IngestionError("NVD META lacks a SHA-256")
            if not 0 < int(meta["size"]) <= MAX_FEED_BYTES:
                raise IngestionError("NVD META size exceeds budget")
            download(client, base + ".json.gz", stage / "snapshot.json.gz")
            with gzip.open(stage / "snapshot.json.gz", "rb") as source, (stage / "snapshot.json").open("xb") as target:
                size = 0
                for block in iter(lambda: source.read(1024**2), b""):
                    size += len(block)
                    if size > int(meta["size"]):
                        raise IngestionError("Decompressed NVD input exceeds declared size")
                    target.write(block)
            checksum, size = file_hash(stage / "snapshot.json")
            if checksum.lower() != meta["sha256"].lower() or size != int(meta["size"]):
                raise IngestionError("NVD META integrity mismatch")
            # Refuse a feed that changed while it was being downloaded.
            if get(client, base + ".meta", 16384) != meta_bytes:
                raise IngestionError("NVD feed changed during acquisition; retry a new snapshot")
            notice = get(client, NIST_NOTICE, 4 * 1024**2)
        acquired = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        manifest = {"schema_version": "1.0.0", "source": "cve", "owner": owner,
                    "source_url": base + ".json.gz", "upstream_version": f"NVD-2.0:{year}:sha256:{checksum}",
                    "acquired_at": acquired, "sha256": checksum, "artifact_ref": "sha256:" + checksum,
                    "license_ref": NIST_NOTICE, "notice_ref": "sha256:" + digest(notice),
                    "notice_sha256": digest(notice), "usage_scope": "project-retrieval"}
        validate("snapshot", manifest)
        (stage / "notice.txt").write_bytes(notice)
        (stage / "feed.meta").write_bytes(meta_bytes)
        (stage / "snapshot-manifest.json").write_bytes(canonical(manifest) + b"\n")
        receipt = {"manifest": manifest, "meta_sha256": digest(meta_bytes), "bytes": size,
                   "archive_sha256": file_hash(stage / "snapshot.json.gz", MAX_ARCHIVE_BYTES)[0]}
        (stage / "acquisition.json").write_bytes(canonical(receipt) + b"\n")
        os.rename(stage, output)
    return manifest


def nvd_items(stream):
    """Validate streaming structure, duplicates and depth before publishing output."""
    header, maps, depth, record_size, declared_count = {}, [], 0, 0, None

    def events():
        nonlocal depth, record_size, declared_count
        for prefix, event, value in ijson.parse(stream, use_float=True):
            if event in {"start_map", "start_array"}:
                depth += 1
                if depth > 64:
                    raise IngestionError("Bulk JSON nesting limit exceeded")
                maps.append(set() if event == "start_map" else None)
            elif event in {"end_map", "end_array"}:
                depth -= 1
                maps.pop()
            elif event == "map_key":
                if depth == 1 and "." in value:
                    raise IngestionError("Ambiguous bulk envelope key")
                if value in maps[-1]:
                    raise IngestionError("Duplicate JSON object key")
                maps[-1].add(value)
            if isinstance(value, str) and len(value) > 2 * 1024**2:
                raise IngestionError("Bulk JSON string limit exceeded")
            if prefix == "vulnerabilities.item" and event == "start_map":
                record_size = 0
            if prefix.startswith("vulnerabilities.item"):
                record_size += len(value.encode()) if isinstance(value, str) else 8
                if record_size > 8 * 1024**2:
                    raise IngestionError("Bulk vulnerability exceeds parse budget")
            if prefix == "totalResults" and event == "number":
                if type(value) is not int or value < 0:
                    raise IngestionError("Invalid NVD totalResults")
                declared_count = value
            if prefix in {"format", "version"} and event == "string":
                header[prefix] = value
            if prefix == "vulnerabilities" and event == "start_array":
                header["array"] = True
            yield prefix, event, value

    try:
        count = 0
        for item in ijson.items(events(), "vulnerabilities.item"):
            count += 1
            yield item
    except (ijson.JSONError, OverflowError) as exc:
        raise IngestionError("Invalid bulk JSON") from exc
    if header != {"format": "NVD_CVE", "version": "2.0", "array": True}:
        raise IngestionError("Expected NVD CVE JSON 2.0 envelope")
    if declared_count is not None and declared_count != count:
        raise IngestionError("NVD totalResults differs from parsed record count")


def normalize_file(input_path, snapshot, staging):
    """Disk-backed identity checks and deterministic sort keep memory bounded."""
    checksum, _ = file_hash(input_path)
    if checksum != snapshot["sha256"]:
        raise IngestionError("Snapshot hash mismatch")
    excluded, accepted = Counter(), 0
    with sqlite3.connect(staging / "sort.sqlite") as database, Path(input_path).open("rb") as source:
        database.execute("CREATE TABLE records (id TEXT PRIMARY KEY, document BLOB NOT NULL)")
        try:
            for value, reason in cve_records(nvd_items(source), snapshot):
                if value is None:
                    excluded[reason] += 1
                    continue
                encoded = canonical(value)
                if len(encoded) > 8 * 1024**2:
                    raise IngestionError("Normalized vulnerability exceeds record budget")
                database.execute("INSERT INTO records VALUES (?, ?)", (value["record_id"], encoded))
                accepted += 1
        except sqlite3.IntegrityError as exc:
            raise IngestionError("Duplicate normalized record identity") from exc
        hasher = hashlib.sha256()
        with (staging / "records.jsonl").open("xb") as output:
            for (document,) in database.execute("SELECT document FROM records ORDER BY id"):
                line = document + b"\n"
                output.write(line)
                hasher.update(line)
    (staging / "sort.sqlite").unlink()
    return accepted, excluded, hasher.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    acquire = sub.add_parser("acquire")
    acquire.add_argument("--year", required=True)
    acquire.add_argument("--output", required=True)
    normalize = sub.add_parser("normalize")
    normalize.add_argument("--snapshot-dir", required=True)
    normalize.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.command == "acquire":
        result = acquire_year(args.year, args.output)
    else:
        from .pipeline import ingest
        base = Path(args.snapshot_dir)
        result = ingest(base / "snapshot.json", base / "snapshot-manifest.json",
                        base / "notice.txt", args.output, stream_nvd=True)
    print(canonical(result).decode())


if __name__ == "__main__":
    main()

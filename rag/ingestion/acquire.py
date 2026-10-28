"""Bounded public-source acquisition, separate from offline normalization.

Only the three inventory sources below are supported. Never visit advisories,
IOC URLs or source-provided links. All redirects are rejected.
"""

import argparse
from datetime import datetime, timezone
import io
import os
from pathlib import Path
import re
import sys
import tempfile
import time
import zipfile

import httpx

from .core import MAX_INPUT_BYTES, IngestionError, canonical, digest, validate


def get(client, url, limit=MAX_INPUT_BYTES):
    chunks, size = [], 0
    deadline = time.monotonic() + 180
    with client.stream("GET", url) as response:
        response.raise_for_status()
        for chunk in response.iter_bytes():
            if time.monotonic() > deadline:
                raise IngestionError("Acquisition exceeds total time limit")
            size += len(chunk)
            if size > limit:
                raise IngestionError("Acquisition exceeds byte limit")
            chunks.append(chunk)
    return b"".join(chunks)


def acquire(source, version, output, owner="Ahmed"):
    output = Path(output)
    if output.exists():
        raise IngestionError("Acquisition directory already exists")
    if source == "mitre_attack" and re.fullmatch("[a-f0-9]{40}", version):
        base = f"https://raw.githubusercontent.com/mitre-attack/attack-stix-data/{version}"
        url = base + "/enterprise-attack/enterprise-attack.json"
        notice_url = base + "/LICENSE.txt"
        filename = "snapshot.json"
    elif source == "cve" and re.fullmatch(r"CVE-\d{4}-\d{4,}", version):
        url = "https://services.nvd.nist.gov/rest/json/cves/2.0?cveId=" + version
        notice_url = ("https://www.nist.gov/open/"
                      "copyright-fair-use-and-licensing-statements-srd-data-software-and-technical-series-publications")
        filename = "snapshot.json"
    elif source == "cwe" and re.fullmatch(r"\d+\.\d+(?:\.\d+)?", version):
        url = f"https://cwe.mitre.org/data/xml/cwec_v{version}.xml.zip"
        notice_url = "https://cwe.mitre.org/about/termsofuse.html"
        filename = "snapshot.xml"
    else:
        raise IngestionError("Expected an ATT&CK commit, CVE ID or numeric CWE release")
    with httpx.Client(timeout=httpx.Timeout(60, connect=15), follow_redirects=False,
                      headers={"User-Agent": "CyberSOC-AI-S2T01/1.0 (bounded academic snapshot)"}) as client:
        data = get(client, url)
        notice = get(client, notice_url, 4 * 1024 * 1024)
    archive = None
    if source == "cwe":
        archive = data
        with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
            members = bundle.infolist()
            if len(members) != 1 or not members[0].filename.endswith(".xml"):
                raise IngestionError("Expected one CWE XML archive member")
            if members[0].file_size > MAX_INPUT_BYTES:
                raise IngestionError("CWE XML exceeds byte limit")
            with bundle.open(members[0]) as stream:
                data = stream.read(MAX_INPUT_BYTES + 1)
            if len(data) > MAX_INPUT_BYTES:
                raise IngestionError("CWE XML exceeds byte limit")
    acquired = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    manifest = {"schema_version": "1.0.0", "source": source, "owner": owner, "source_url": url,
                "upstream_version": version, "acquired_at": acquired, "sha256": digest(data),
                "artifact_ref": "sha256:" + digest(data), "license_ref": notice_url,
                "notice_ref": "sha256:" + digest(notice), "notice_sha256": digest(notice),
                "usage_scope": "project-retrieval"}
    # NVD is a mutable API response: pin its exact acquired bytes, not a claim
    # that a CVE ID alone identifies an immutable upstream revision.
    if source == "cve":
        manifest["upstream_version"] = "NVD-2.0:" + version + ":sha256:" + digest(data)
    validate("snapshot", manifest)
    receipt = {"source_url": url, "acquired_at": acquired, "snapshot_sha256": digest(data),
               "notice_url": notice_url, "notice_sha256": digest(notice),
               "archive_sha256": digest(archive) if archive is not None else None}
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".acquire-", dir=output.parent) as temp:
        staging = Path(temp) / "snapshot"
        staging.mkdir()
        (staging / filename).write_bytes(data)
        (staging / "notice.txt").write_bytes(notice)
        (staging / "snapshot-manifest.json").write_bytes(canonical(manifest) + b"\n")
        (staging / "acquisition.json").write_bytes(canonical(receipt) + b"\n")
        if archive is not None:
            (staging / "source.xml.zip").write_bytes(archive)
        os.rename(staging, output)
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=["mitre_attack", "cve", "cwe"], required=True)
    parser.add_argument("--version", required=True, help="ATT&CK commit SHA, CVE ID or CWE version")
    parser.add_argument("--output", required=True, help="New local artifact directory")
    parser.add_argument("--owner", default="Ahmed", help="Accountable snapshot owner")
    args = parser.parse_args(argv)
    try:
        manifest = acquire(args.source, args.version, args.output, args.owner)
    except IngestionError as exc:
        print(f"Acquisition failed: {exc}. No complete snapshot was published.", file=sys.stderr)
        return 1
    except httpx.HTTPStatusError as exc:
        print(f"Acquisition failed: HTTP {exc.response.status_code}; "
              "no complete snapshot was published.", file=sys.stderr)
        return 1
    except (httpx.HTTPError, OSError, zipfile.BadZipFile, ValueError):
        print("Acquisition failed; no complete snapshot was published.", file=sys.stderr)
        return 1
    print(canonical({"source": manifest["source"], "sha256": manifest["sha256"]}).decode())
    return 0


if __name__ == "__main__":
    sys.exit(main())

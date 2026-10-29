"""Bounded acquisition using mocked HTTP only; CI never contacts data providers."""

import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import httpx

from rag.ingestion.acquire import acquire, get
from rag.ingestion.core import IngestionError, digest
from rag.ingestion.prepare_lab import prepare


class AcquisitionTests(unittest.TestCase):
    def test_lab_preparation_pins_fixtures_and_publishes_only_valid_snapshots(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "snapshot"
            prepare(output, "2026-10-28T23:34:26Z")
            manifest = json.loads((output / "snapshot-manifest.json").read_bytes())
            self.assertEqual(manifest["sha256"], digest((output / "snapshot.json").read_bytes()))
            with self.assertRaises(ValueError):
                prepare(output, "2026-10-28T23:34:26Z")
            with patch("rag.ingestion.prepare_lab.PINNED_DIGESTS", ("0" * 64, "0" * 64)):
                with self.assertRaises(ValueError):
                    prepare(Path(temp) / "changed", "2026-10-28T23:34:26Z")
            self.assertFalse((Path(temp) / "changed").exists())
            with self.assertRaises(IngestionError):
                prepare(Path(temp) / "invalid", "not-a-time")
            self.assertFalse((Path(temp) / "invalid").exists())

    def test_invalid_source_versions_never_request_network(self):
        with tempfile.TemporaryDirectory() as temp:
            for source, version in (("mitre_attack", "master"), ("cwe", "latest"),
                                    ("cve", "https://example.org"), ("other", "1")):
                with patch("httpx.Client") as client:
                    with self.assertRaises(IngestionError):
                        acquire(source, version, Path(temp) / "out")
                    client.assert_not_called()

    def test_redirects_and_oversized_responses_are_rejected(self):
        for status, body in ((302, b""), (200, b"1234")):
            client = httpx.Client(transport=httpx.MockTransport(
                lambda request: httpx.Response(status, content=body,
                                              headers={"location": "https://other.invalid"})))
            with client:
                with self.assertRaises((httpx.HTTPStatusError, IngestionError)):
                    get(client, "https://example.org/data", limit=3)

    def test_streaming_deadline_is_enforced(self):
        client = httpx.Client(transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=b"response")))
        with client, patch("rag.ingestion.acquire.time.monotonic", side_effect=[0, 181]):
            with self.assertRaises(IngestionError):
                get(client, "https://example.org/data")

    def test_cwe_archive_and_notice_are_preserved_without_path_extraction(self):
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as bundle:
            bundle.writestr("../../outside.xml", b"<catalog/>")
        data = archive.getvalue()
        def handler(request):
            return httpx.Response(200, content=data if str(request.url).endswith(".zip") else b"notice")
        client = httpx.Client(transport=httpx.MockTransport(handler))
        with tempfile.TemporaryDirectory() as temp, patch("rag.ingestion.acquire.httpx.Client", return_value=client):
            output = Path(temp) / "snapshot"
            manifest = acquire("cwe", "5.0", output)
            self.assertEqual((output / "snapshot.xml").read_bytes(), b"<catalog/>")
            self.assertEqual((output / "notice.txt").read_bytes(), b"notice")
            self.assertEqual(manifest["sha256"], digest(b"<catalog/>"))
            receipt = json.loads((output / "acquisition.json").read_bytes())
            self.assertEqual(receipt["archive_sha256"], digest(data))
            self.assertFalse((Path(temp) / "outside.xml").exists())

    def test_nvd_snapshot_pins_response_bytes_and_new_notice_url(self):
        requested = []
        def handler(request):
            requested.append(str(request.url))
            return httpx.Response(200, content=b"fixture")
        client = httpx.Client(transport=httpx.MockTransport(handler))
        with tempfile.TemporaryDirectory() as temp, patch("rag.ingestion.acquire.httpx.Client", return_value=client):
            manifest = acquire("cve", "CVE-2021-44228", Path(temp) / "snapshot")
            self.assertIn(digest(b"fixture"), manifest["upstream_version"])
            self.assertIn("copyright-fair-use", requested[1])

    def test_failed_notice_request_publishes_no_partial_snapshot(self):
        def handler(request):
            return httpx.Response(503 if "nist.gov/open" in str(request.url) else 200, content=b"fixture")
        client = httpx.Client(transport=httpx.MockTransport(handler))
        with tempfile.TemporaryDirectory() as temp, patch("rag.ingestion.acquire.httpx.Client", return_value=client):
            output = Path(temp) / "snapshot"
            with self.assertRaises(httpx.HTTPStatusError):
                acquire("cve", "CVE-2021-44228", output)
            self.assertFalse(output.exists())

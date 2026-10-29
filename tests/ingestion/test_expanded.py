"""Expanded-source, streaming and exact vulnerability-join regression tests."""

import gzip
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import httpx
import yaml

from backend.validation import validate as validate_contract
from rag.ingestion.core import IngestionError, canonical, digest
from rag.ingestion.corpus import compose, lookup
from rag.ingestion.build import check_source
from rag.ingestion.curated import acquire_selection, fetch_file, safe_path
from rag.ingestion.extensions import external_event, safe_yaml
from rag.ingestion.nvd_bulk import acquire_year, nvd_items
from rag.ingestion.pipeline import ingest, normalize
from test_ingestion import NOTICE, snapshot


def nvd_item(identity="CVE-2024-6387"):
    return {"cve": {"id": identity, "published": "2024-07-01T00:00:00.000",
                    "lastModified": "2026-10-01T00:00:00.000", "vulnStatus": "Analyzed",
                    "descriptions": [{"lang": "en", "value": "Synthetic NVD description."}],
                    "metrics": {}, "affected": [{"vendor": "fixture"}]}}


def nvd_feed(*items):
    return canonical({"format": "NVD_CVE", "version": "2.0", "vulnerabilities": list(items)})


def bundle(provider, contents):
    return canonical({"provider": provider, "files": [{"path": path,
        "sha256": digest(content.encode()), "content": content,
        "source_url": "https://example.org/fixture"} for path, content in contents]})


def cve_document(identity="CVE-2024-6387", state="PUBLISHED"):
    return {"dataType": "CVE_RECORD", "dataVersion": "5.2",
            "cveMetadata": {"cveId": identity, "state": state, "datePublished": "2024-07-01T00:00:00Z",
                            "dateUpdated": "2026-10-01T00:00:00Z"},
            "containers": {"cna": {"descriptions": [{"lang": "en", "value": "Synthetic CNA description."}],
                                   "affected": [{"vendor": "fixture", "product": "fixture"}]},
                           "adp": [{"providerMetadata": {"shortName": "fixture"}}]}}


def kev_catalog():
    return {"catalogVersion": "fixture-1", "dateReleased": "2026-10-01T00:00:00Z", "count": 2,
            "vulnerabilities": [{"cveID": identity, "vulnerabilityName": "Fixture vulnerability",
                "shortDescription": "Synthetic KEV description.", "dateAdded": "2026-10-01",
                "requiredAction": "Review fixture advisory"} for identity in ("CVE-2024-6387", "CVE-2020-1234")]}


def publish(temp, name, source, data, **kwargs):
    folder = temp / (name + "-input")
    folder.mkdir()
    (folder / "data").write_bytes(data)
    (folder / "snapshot").write_bytes(canonical(snapshot(source, data)))
    (folder / "notice").write_bytes(NOTICE)
    output = temp / name
    ingest(folder / "data", folder / "snapshot", folder / "notice", output, **kwargs)
    return output


class ExpandedTests(unittest.TestCase):
    def test_streamed_and_in_memory_nvd_records_match(self):
        data = nvd_feed(nvd_item(), nvd_item("CVE-2024-3094"))
        expected, _ = normalize(data, snapshot("cve", data))
        with tempfile.TemporaryDirectory() as temp:
            output = publish(Path(temp), "bulk", "cve", data, stream_nvd=True)
            self.assertEqual((output / "records.jsonl").read_bytes(), expected)
            self.assertFalse((output / "sort.sqlite").exists())

    def test_streaming_rejects_duplicate_keys_ids_trailing_json_and_wrong_envelope(self):
        fixtures = [nvd_feed(nvd_item(), nvd_item()), b'{"format":"wrong","version":"2.0","vulnerabilities":[]}',
                    b'{"format":"NVD_CVE","format":"NVD_CVE","version":"2.0","vulnerabilities":[]}',
                    nvd_feed(nvd_item()) + b'{}', b'{"vulnerabilities":[',
                    b'{"format":"NVD_CVE","version":"2.0","vulnerabilities":[],"totalResults":1}',
                    b'{"format":"NVD_CVE","version":"2.0","vulnerabilities":[],"vulnerabilities.item":{}}']
        for index, data in enumerate(fixtures):
            with tempfile.TemporaryDirectory() as temp, self.assertRaises(IngestionError):
                publish(Path(temp), f"bad-{index}", "cve", data, stream_nvd=True)
            self.assertFalse((Path(temp) / f"bad-{index}").exists())

    def test_streaming_is_incremental_and_depth_bounded(self):
        class BoundedReader(io.BytesIO):
            def read(self, size=-1):
                if size < 0 or size > 65536:
                    raise AssertionError("Unbounded read")
                return super().read(size)
        self.assertEqual(len(list(nvd_items(BoundedReader(nvd_feed(nvd_item()))))), 1)
        data = b'{"format":"NVD_CVE","version":"2.0","vulnerabilities":[],"other":' + b'['*65 + b'0' + b']'*65 + b'}'
        with self.assertRaises(IngestionError):
            list(nvd_items(io.BytesIO(data)))

    def test_bulk_acquisition_validates_meta_and_preserves_archive(self):
        data = nvd_feed(nvd_item())
        meta = f"size:{len(data)}\nsha256:{digest(data)}\nlastModifiedDate:fixture\n".encode()
        def handler(request):
            body = meta if str(request.url).endswith(".meta") else gzip.compress(data) if str(request.url).endswith(".gz") else NOTICE
            return httpx.Response(200, content=body)
        with tempfile.TemporaryDirectory() as temp:
            client = httpx.Client(transport=httpx.MockTransport(handler))
            with patch("rag.ingestion.nvd_bulk.httpx.Client", return_value=client):
                result = acquire_year("2024", Path(temp) / "snapshot")
            self.assertEqual(result["sha256"], digest(data))
            self.assertEqual((Path(temp) / "snapshot/feed.meta").read_bytes(), meta)
            self.assertTrue((Path(temp) / "snapshot/snapshot.json.gz").exists())

    def test_bulk_meta_mismatch_publishes_nothing(self):
        data = nvd_feed(nvd_item())
        def handler(request):
            meta = f"size:{len(data)}\nsha256:{'0'*64}\n".encode()
            return httpx.Response(200, content=meta if str(request.url).endswith('.meta') else gzip.compress(data))
        with tempfile.TemporaryDirectory() as temp:
            client = httpx.Client(transport=httpx.MockTransport(handler))
            with patch("rag.ingestion.nvd_bulk.httpx.Client", return_value=client), self.assertRaises(IngestionError):
                acquire_year("2024", Path(temp) / "bad")
            self.assertFalse((Path(temp) / "bad").exists())

    def test_cve_program_preserves_cna_adp_and_excludes_rejected(self):
        data = bundle("cve_program", [("cve.json", json.dumps(cve_document())),
                                      ("rejected.json", json.dumps(cve_document("CVE-2024-3094", "REJECTED")))])
        output, report = normalize(data, snapshot("cve", data))
        item = json.loads(output)
        self.assertIn("adp", item["metadata"]["cve_program"])
        self.assertEqual(report["accepted"], 1)
        self.assertEqual(report["excluded"], {"rejected_cve": 1})

    def test_cve_and_kev_join_is_exact_and_not_duplicate_retrieval_documents(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            nvd = publish(temp, "nvd", "cve", nvd_feed(nvd_item()))
            official = publish(temp, "cve5", "cve", bundle("cve_program", [("cve.json", json.dumps(cve_document()))]))
            kev = publish(temp, "kev", "kev", bundle("kev", [("kev.json", json.dumps(kev_catalog()))]))
            result = compose([nvd, official, kev], temp / "combined")
            self.assertEqual(result["by_source"], {"cve": 1})
            self.assertEqual(result["joined_cve_records"], 1)
            self.assertEqual(result["kev_enriched_cves"], 1)
            self.assertEqual(result["kev_without_indexed_cve"], 1)
            value = lookup(temp / "combined", "CVE-2024-6387")["cve"]
            self.assertEqual(value["metadata"]["provider"], "joined")
            self.assertEqual(len(value["metadata"]["provenance_chain"]), 3)
            self.assertTrue(value["metadata"]["alternate_descriptions"])
            self.assertIsNotNone(lookup(temp / "combined", "CVE-2020-1234")["kev"])
            self.assertIsNone(lookup(temp / "combined", "CVE-2020-1234")["cve"])
            replay = compose([nvd, official, kev], temp / "replay")
            self.assertEqual(result, replay)
            self.assertEqual((temp / "combined/records.jsonl").read_bytes(), (temp / "replay/records.jsonl").read_bytes())
            self.assertEqual((temp / "combined/manifest.json").read_bytes(), (temp / "replay/manifest.json").read_bytes())

    def test_corpus_rejects_tampering_and_duplicate_provider(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            first = publish(temp, "first", "cve", nvd_feed(nvd_item()))
            second = publish(temp, "second", "cve", nvd_feed(nvd_item()))
            with self.assertRaises(IngestionError):
                compose([first, second], temp / "duplicate")
            self.assertFalse((temp / "duplicate").exists())
            (first / "records.jsonl").write_bytes(b"tampered\n")
            with self.assertRaises(IngestionError):
                compose([first], temp / "tampered")
            self.assertFalse((temp / "tampered").exists())

    def test_yaml_is_safe_and_rejects_duplicates_aliases_and_code_tags(self):
        for content in ("key: first\nkey: second", "a: &a [1]\nb: *a", "!!python/object/apply:os.system ['echo unsafe']"):
            with self.assertRaises((IngestionError, yaml.YAMLError)):
                safe_yaml(content)
        self.assertEqual(safe_yaml("date: 2026-10-29")['date'], "2026-10-29")

    def test_sigma_preserves_status_false_positives_and_never_executes(self):
        content = "id: fixture-rule\ntitle: Fixture rule\nstatus: test\ndescription: Synthetic pattern\nlogsource: {product: linux}\ndetection: {selection: {CommandLine: example}, condition: selection}\nfalsepositives: [Authorized administration]\n"
        data = bundle("sigma", [("rule.yml", content)])
        output, _ = normalize(data, snapshot("detection_rule", data))
        value = json.loads(output)
        self.assertEqual(value["metadata"]["status"], "test")
        self.assertIn("Authorized administration", value["content"])
        inactive = bundle("sigma", [("rule.yml", content.replace("status: test", "status: deprecated"))])
        _, report = normalize(inactive, snapshot("detection_rule", inactive))
        self.assertEqual(report["excluded"], {"inactive_sigma_rule": 1})

    def test_playbook_is_reference_text_and_preserves_document_identity(self):
        data = bundle("playbook", [("guide.md", "# Fixture guide\nInspect observations.\n```python\nraise RuntimeError('never execute')\n```\n")])
        output, _ = normalize(data, snapshot("playbook", data))
        value = json.loads(output)
        self.assertEqual(value["source_record_id"], "guide.md")
        self.assertEqual(value["metadata"]["usage"], "reference_only_no_execution")

    def test_external_formats_and_nested_label_exclusion(self):
        self.assertEqual(external_event('type=EXECVE msg=audit(123.45:67): argc=1 a0="arp"')["format"], "linux_auditd")
        self.assertEqual(external_event('<Event><System><EventID>1</EventID></System></Event>')["format"], "sysmon_xml")
        for line in ('{"event":{"gold_severity":"high"}}', '<Event><label>attack</label></Event>', 'unknown data'):
            with self.assertRaises(IngestionError):
                external_event(line)

    def test_external_development_policy_hash_limits_and_heldout_groups(self):
        content = 'type=EXECVE msg=audit(123.45:67): argc=1 a0="arp"\n' * 3
        data = bundle("otrf", [("events.log", content)])
        splits = canonical({"dataset_version": "fixture", "test_frozen": False,
                            "development": [], "test": [{"case_id": "T1", "group_id": "HELDOUT"}]})
        policy = {"schema_version": "1.0.0", "dataset_version": "fixture", "splits_sha256": digest(splits),
                  "assignment_ref": "fixture-assignment", "records": [{"source_record": "otrf:events.log",
                    "sha256": digest(content.encode()), "group_id": "DEVELOPMENT", "run_id": "RUN1",
                    "split": "development", "related_case_ids": [], "max_events": 2}]}
        output, report = normalize(data, snapshot("soc_log", data), policy=policy, splits_data=splits)
        self.assertEqual(len(output.splitlines()), 2)
        self.assertEqual(report["corpus_use"], "development_only")
        self.assertEqual(report["excluded"], {"external_selection_limit": 1})
        policy["records"][0]["group_id"] = "HELDOUT"
        output, report = normalize(data, snapshot("soc_log", data), policy=policy, splits_data=splits)
        self.assertEqual(output, b"")
        self.assertEqual(report["excluded"], {"excluded_external_split": 1})
        policy["records"][0]["sha256"] = "0" * 64
        with self.assertRaises(IngestionError):
            normalize(data, snapshot("soc_log", data), policy=policy, splits_data=splits)

    def test_selected_file_digest_and_archive_paths_are_checked(self):
        value = json.loads(bundle("playbook", [("guide.md", "# Guide")]))
        value["files"][0]["sha256"] = "0" * 64
        data = canonical(value)
        with self.assertRaises(IngestionError):
            normalize(data, snapshot("playbook", data))
        for path in ("../file", "/file", "a/../../b", "a\\file"):
            with self.assertRaises(IngestionError):
                safe_path(path)

    def test_git_lfs_uses_pinned_media_and_checks_oid(self):
        data = b"fixture public event"
        pointer = f"version https://git-lfs.github.com/spec/v1\noid sha256:{digest(data)}\nsize {len(data)}\n".encode()
        def handler(request):
            return httpx.Response(200, content=pointer if request.url.host == "raw.githubusercontent.com" else data)
        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            result, _ = fetch_file(client, "splunk/attack_data", "a" * 40, "events.log")
        self.assertEqual(result, data)

    def test_curated_provider_and_revision_are_not_arbitrary_download_urls(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            plan = {"owner": "fixture", "sources": {"sigma": {"repository": "unapproved/repo",
                    "revision": "a" * 40, "notice": "LICENSE", "files": ["rule.yml"]}}}
            (temp / "selection.json").write_bytes(canonical(plan))
            with self.assertRaises(IngestionError), patch("rag.ingestion.curated.httpx.Client") as client:
                acquire_selection(temp / "selection.json", "sigma", temp / "out")
            client.assert_not_called()

    def test_new_retrieval_evidence_sources_validate_in_existing_contract(self):
        for source in ("detection_rule", "playbook"):
            value = {"schema_version": "1.0.0", "request_id": "REQ-1", "trace_id": "TRACE-1", "status": "ok",
                     "evidence": [{"evidence_id": "E1", "source": source, "source_record_id": "fixture",
                        "snapshot_ref": "fixture", "content": "Reference text", "score": 0.8,
                        "score_kind": "cosine", "retrieval_method": "vector"}]}
            validate_contract("retrieval-response", value)

    def test_attck_relationships_are_exported_separately_from_vector_documents(self):
        from test_ingestion import attack_data, technique
        data = attack_data(technique(), {"type": "relationship", "id": "relationship--one",
            "relationship_type": "uses", "source_ref": "actor--one", "target_ref": "attack-pattern--one",
            "modified": "2026-01-01T00:00:00Z"})
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            source = publish(temp, "attack", "mitre_attack", data)
            report = compose([source], temp / "composed")
            self.assertEqual(report["accepted"], 1)
            self.assertEqual(report["graph_relationships"], 1)
            self.assertEqual(len((temp / "composed/relationships.jsonl").read_bytes().splitlines()), 1)

    def test_cached_sources_must_match_the_selected_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            data = nvd_feed(nvd_item())
            manifest = snapshot("cve", data)
            manifest["upstream_version"] = "NVD-2.0:2023:sha256:" + digest(data)
            (path / "snapshot-manifest.json").write_bytes(canonical(manifest))
            with self.assertRaises(IngestionError):
                check_source("nvd-2024", path, {})

"""Offline synthetic fixtures exercise the real WordPiece engine, not relevance."""

from collections import Counter
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tokenizers import Tokenizer, models, normalizers, pre_tokenizers, processors

from rag.ingestion.core import IngestionError, canonical, digest, record
from rag.vector.chunk import build
from rag.vector.chunking import Chunker, DEFAULT_CONFIG, filter_payload

NOTICE = b"Synthetic fixture, no real incident or acquired source data."


def snapshot(source):
    return dict(schema_version="1.0.0", source=source, source_url="https://example.org/fixture",
                upstream_version="synthetic-v1", acquired_at="2026-10-29T00:00:00Z",
                sha256="a" * 64, artifact_ref="fixture:" + source,
                license_ref="synthetic", notice_ref="fixture:notice", notice_sha256=digest(NOTICE),
                usage_scope="project-retrieval", owner="synthetic-test")


def cve(text="SSH authentication failure", identity="CVE-2024-1234"):
    return record(snapshot("cve"), identity, identity, text,
                  {"published": "2024-01-01", "lastModified": "2024-01-01"})


def soc():
    return record(snapshot("soc_log"), "INC-fixture", "Historical incident INC-fixture",
                  "SSH authentication failure", dict(
                      incident_id="INC-fixture", source_event_id="event-123", timestamp="2026-10-29T00:00:00Z",
                      source_severity="low", entities=[], ingestion_kind="replay", group_id="G-private",
                      run_id="run-private", sanitization_ref="private-path", assignment_ref="fixture:assignment",
                      dataset_version="fixture-v1", split="development", test_frozen=False))


class ChunkingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.tokenizer_path = self.root / "tokenizer.json"
        tokens = ["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]", "ssh", "authentication",
                  "failure", "a", "##b", "cafe", "中", "文", "cve", "-", "2024", "1234"]
        tokenizer = Tokenizer(models.WordPiece({t: i for i, t in enumerate(tokens)}, unk_token="[UNK]"))
        tokenizer.normalizer = normalizers.BertNormalizer(lowercase=True)
        tokenizer.pre_tokenizer = pre_tokenizers.BertPreTokenizer()
        tokenizer.post_processor = processors.BertProcessing(("[SEP]", 3), ("[CLS]", 2))
        tokenizer.save(str(self.tokenizer_path))
        # Only synthetic tests replace the expected artifact digest; production
        # always verifies the pinned BGE file. No download is needed in CI.
        self.pin = patch("rag.vector.chunking.TOKENIZER_SHA256", digest(self.tokenizer_path.read_bytes()))
        self.pin.start()
        self.addCleanup(self.pin.stop)
        self.chunker = Chunker(self.tokenizer_path)

    def config(self, **changes):
        config = json.loads(DEFAULT_CONFIG.read_bytes())
        config.update(changes)
        path = self.root / "custom.json"
        path.write_bytes(canonical(config))
        return path

    def assert_coverage(self, source, chunks, chunker):
        covered = 0
        for chunk in chunks:
            self.assertLessEqual(chunk["start_char"], covered)
            self.assertGreater(chunk["end_char"], covered)
            self.assertEqual(chunk["content"], source["content"][chunk["start_char"]:chunk["end_char"]])
            self.assertEqual(chunk["token_count"], chunker.count(chunk["embedding_text"]))
            self.assertLessEqual(chunk["token_count"], chunker.config["max_tokens"])
            self.assertLessEqual(len(chunk["embedding_text"]), chunker.config["max_characters"])
            covered = chunk["end_char"]
        self.assertEqual(covered, len(source["content"]))

    def test_long_text_is_bounded_overlapping_and_lossless(self):
        source = cve("SSH authentication failure " * 500)
        chunks, _ = self.chunker.chunks(source)
        self.assertGreater(len(chunks), 2)
        self.assert_coverage(source, chunks, self.chunker)
        self.assertLess(chunks[1]["start_char"], chunks[0]["end_char"])

    def test_unicode_and_subwords_preserve_original_source(self):
        source = cve("Café 中文 abbbbbbb e\u0301 SSH " * 180)
        chunks, _ = self.chunker.chunks(source)
        self.assert_coverage(source, chunks, self.chunker)
        self.assertIn("Café", chunks[0]["content"])

    def test_single_huge_unknown_token_respects_character_limit(self):
        source = cve("z" * 35000)
        chunks, _ = self.chunker.chunks(source)
        self.assertEqual(len(chunks), 3)
        self.assert_coverage(source, chunks, self.chunker)

    def test_no_overlap_configuration_progresses_without_gaps(self):
        c = Chunker(self.tokenizer_path, self.config(max_tokens=64, overlap_tokens=0))
        source = cve("SSH failure " * 150)
        chunks, _ = c.chunks(source)
        self.assert_coverage(source, chunks, c)
        self.assertEqual(chunks[1]["start_char"], chunks[0]["end_char"])

    def test_ids_are_repeatable_and_distinct_for_identical_cve_descriptions(self):
        first = self.chunker.chunks(cve())[0]
        self.assertEqual(first, self.chunker.chunks(cve())[0])
        other = self.chunker.chunks(cve(identity="CVE-2024-5678"))[0]
        self.assertNotEqual(first[0]["point_id"], other[0]["point_id"])
        changed = Chunker(self.tokenizer_path, self.config(max_tokens=256))
        self.assertNotEqual(first[0]["chunk_id"], changed.chunks(cve())[0][0]["chunk_id"])

    def test_changed_provenance_or_metadata_changes_identity(self):
        source = cve()
        original = self.chunker.chunks(source)[0][0]["chunk_id"]
        source["metadata"]["vulnStatus"] = "Deferred"
        self.assertNotEqual(original, self.chunker.chunks(source)[0][0]["chunk_id"])

    def test_placeholder_excluded_but_short_meaningful_text_retained(self):
        for text in ("## Summary", "Description", "   ", "---"):
            source = cve()
            source["content"] = text
            source["content_sha256"] = digest(text.encode())
            chunks, decision = self.chunker.chunks(source)
            self.assertFalse(chunks)
            self.assertIsNotNone(decision["excluded"])
        chunks, decision = self.chunker.chunks(cve("Information disclosure"))
        self.assertEqual(len(chunks), 1)
        self.assertEqual(decision["flags"], ["short_primary_text"])

    def test_soc_metadata_never_enters_embedding_text(self):
        source = soc()
        chunk = self.chunker.chunks(source)[0][0]
        self.assertEqual(chunk["embedding_text"], source["content"])
        self.assertEqual(chunk["metadata"], source["metadata"])
        self.assertEqual(chunk["filters"]["incident_group_id"], "G-private")
        chunk["metadata"]["group_id"] = "changed"
        self.assertEqual(source["metadata"]["group_id"], "G-private")

    def test_supplemental_facts_not_misattributed_as_primary_text(self):
        source = cve()
        source["metadata"]["kev"] = {"requiredAction": "SENTINEL supplemental claim"}
        chunk = self.chunker.chunks(source)[0][0]
        self.assertNotIn("SENTINEL", chunk["embedding_text"])
        self.assertEqual(chunk["metadata"]["kev"], source["metadata"]["kev"])

    def test_tampered_text_identity_snapshot_and_collection_fail(self):
        for key, value in [("content", "changed"), ("record_id", "DOC-" + "0" * 64),
                           ("snapshot_ref", "other"), ("collection", "soc_history")]:
            source = cve()
            source[key] = value
            with self.assertRaises(IngestionError):
                self.chunker.chunks(source)

    def test_bad_tokenizer_and_invalid_config_fail(self):
        self.tokenizer_path.write_text("{}")
        with self.assertRaisesRegex(IngestionError, "SHA-256"):
            Chunker(self.tokenizer_path)
        for changes in ({"max_tokens": 513}, {"max_tokens": True}, {"overlap_tokens": 384},
                        {"max_characters": 16001}, {"unexpected": 1}):
            with self.assertRaises(IngestionError):
                Chunker(self.tokenizer_path, self.config(**changes))

    def test_reference_header_must_leave_room(self):
        source = cve()
        source["title"] = "SSH " * 400
        with self.assertRaisesRegex(IngestionError, "header"):
            self.chunker.chunks(source)

    def test_filter_mapping_preserves_status_and_normalizes_platforms(self):
        source = cve()
        source["metadata"]["vulnStatus"] = "Deferred"
        self.assertEqual(filter_payload(source)["source_status"], "Deferred")
        source["source"] = "detection_rule"
        source["metadata"] = {"status": "test", "logsource": {"product": "Linux"}}
        self.assertEqual(filter_payload(source)["platforms"], ["linux"])

    def corpus(self, records, *, heldout=False):
        folder = self.root / "corpus"
        folder.mkdir()
        splits = {"dataset_version": "fixture-v1", "test_frozen": False,
                  "development": [], "test": [{"case_id": "P1", "group_id": "G-private"}] if heldout else []}
        splits_path = self.root / "splits.json"
        splits_path.write_bytes(canonical(splits))
        assignment = dict(incident_id="INC-fixture", record_sha256="c" * 64, group_id="G-private",
                          run_id="run-private", split="development", related_case_ids=[], sanitization_ref="private-path")
        policy = dict(schema_version="1.0.0", dataset_version="fixture-v1",
                      splits_sha256=digest(splits_path.read_bytes()), assignment_ref="fixture:assignment",
                      records=[assignment])
        policy_path = self.root / "policy.json"
        policy_path.write_bytes(canonical(policy))
        manifests = []
        for index, source in enumerate(sorted({r["source"] for r in records})):
            entry = {"snapshot": snapshot(source), "corpus_use": "development_only"}
            if source == "soc_log":
                entry.update(splits_sha256=policy["splits_sha256"], soc_policy_sha256=digest(canonical(policy)))
            manifests.append(entry)
            (folder / f"notice-{index:02d}.txt").write_bytes(NOTICE)
        data = b"".join(canonical(r) + b"\n" for r in sorted(records, key=lambda r: r["record_id"]))
        (folder / "records.jsonl").write_bytes(data)
        manifest = dict(schema_version="1.0.0", corpus_use="development_only", inputs=manifests,
                        records_sha256=digest(data), accepted=len(records),
                        by_source=dict(Counter(r["source"] for r in records)))
        (folder / "manifest.json").write_bytes(canonical(manifest))
        return dict(corpus=folder, manifest_sha256=digest(canonical(manifest)), tokenizer=self.tokenizer_path,
                    output=self.root / "output", splits=splits_path, policies=[policy_path])

    def test_build_replays_bytes_and_accounts_for_exclusions(self):
        args = self.corpus([cve(), cve("## Summary", "CVE-2024-9999"), soc()])
        first = build(**args)
        self.assertEqual(first["selected_records"], 3)
        self.assertEqual(first["excluded"], {"placeholder_text": 1})
        args["output"] = self.root / "replay"
        second = build(**args)
        self.assertEqual(first, second)
        for name in ("chunks.jsonl", "decisions.jsonl", "manifest.json"):
            self.assertEqual((self.root / "output" / name).read_bytes(), (args["output"] / name).read_bytes())
        with self.assertRaises(IngestionError):
            build(**args)

    def test_preview_still_checks_unselected_records_and_publishes_atomically(self):
        args = self.corpus([cve(), cve(identity="CVE-2024-9999")])
        args["limit_per_source"] = 1
        path = args["corpus"] / "records.jsonl"
        path.write_bytes(path.read_bytes() + b"invalid\n")
        with self.assertRaises(IngestionError):
            build(**args)
        self.assertFalse(args["output"].exists())
        self.assertFalse(list(self.root.glob(".chunks-*")))

    def test_heldout_group_is_rejected(self):
        args = self.corpus([soc()], heldout=True)
        with self.assertRaisesRegex(IngestionError, "Ineligible"):
            build(**args)
        self.assertFalse(args["output"].exists())

    def test_policy_change_requires_rebuilding_ingestion(self):
        args = self.corpus([soc()])
        path = args["policies"][0]
        policy = json.loads(path.read_bytes())
        policy["records"][0]["run_id"] = "changed"
        path.write_bytes(canonical(policy))
        with self.assertRaisesRegex(IngestionError, "rebuilding"):
            build(**args)

    def test_bad_manifest_notice_and_records_hash_fail(self):
        args = self.corpus([cve()])
        with self.assertRaisesRegex(IngestionError, "manifest SHA"):
            build(**(args | {"manifest_sha256": "0" * 64}))
        notice = args["corpus"] / "notice-00.txt"
        notice.write_bytes(b"changed")
        with self.assertRaisesRegex(IngestionError, "notice"):
            build(**args)
        notice.write_bytes(NOTICE)
        path = args["corpus"] / "records.jsonl"
        path.write_bytes(path.read_bytes().replace(b'SSH', b'ssh'))
        with self.assertRaises(IngestionError):
            build(**args)
        self.assertFalse(args["output"].exists())


if __name__ == "__main__":
    unittest.main()

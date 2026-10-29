"""Offline failure/identity tests; synthetic vectors are never quality results."""

import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rag.ingestion.core import IngestionError, canonical, digest
from rag.vector.embedding import BGEEncoder, validate_vectors
from rag.vector.embed import build, chunk_records
from rag.vector.model import verify_file, verify_model


class EmbeddingTests(unittest.TestCase):
    def test_finite_dimension_count_and_norm_required(self):
        vector = [1.0] + [0.0] * 383
        self.assertEqual(validate_vectors([vector], 1), [vector])
        for bad in (vector[:-1], [0.0] * 384, [2.0] + vector[1:], [float("nan")] + vector[1:],
                    [float("inf")] + vector[1:], [True] + vector[1:]):
            with self.assertRaises(IngestionError):
                validate_vectors([bad], 1)
        with self.assertRaises(IngestionError):
            validate_vectors([vector], 2)

    def test_model_file_verifies_git_blob_and_sha256(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "file"
            path.write_bytes(b"fixture")
            expected = {"bytes": 7, "git_blob_sha1": hashlib.sha1(b"blob 7\0fixture").hexdigest()}
            self.assertEqual(verify_file(path, expected), digest(b"fixture"))
            verify_file(path, {"bytes": 7, "sha256": digest(b"fixture")})
            path.write_bytes(b"changed")
            with self.assertRaises(IngestionError):
                verify_file(path, expected)
            path.write_bytes(b"short")
            with self.assertRaises(IngestionError):
                verify_file(path, expected)

    def test_unexpected_or_missing_model_file_rejected_before_inference(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(IngestionError, "files"):
                verify_model(tmp)

    def test_invalid_batch_and_query_rejected_before_model_access(self):
        encoder = BGEEncoder.__new__(BGEEncoder)
        for texts in ([], ["text"] * 17, [""], [" "], [123], ["x" * 16001]):
            with self.assertRaises(IngestionError):
                encoder.encode(texts)
        for query in ("", " ", None, "x" * 4001):
            with self.assertRaises(IngestionError):
                encoder.query(query)

    def test_query_prefix_is_explicit(self):
        encoder = BGEEncoder.__new__(BGEEncoder)
        with patch.object(encoder, "encode", return_value=[[1.0] + [0.0]*383]) as encode:
            encoder.query("SSH failure")
            self.assertEqual(encode.call_args.args[0],
                             ["Represent this sentence for searching relevant passages: SSH failure"])

    def test_saved_count_and_oversized_tokens_rejected_before_encoding(self):
        from types import SimpleNamespace
        encoder = BGEEncoder.__new__(BGEEncoder)
        encoder.chunker = SimpleNamespace(tokenizer=SimpleNamespace(encode=lambda _: SimpleNamespace(ids=[1, 2, 3])))
        encoder.model = SimpleNamespace(tokenizer=lambda *a, **kw: {"input_ids": [[1, 2, 3]]})
        with self.assertRaisesRegex(IngestionError, "count"):
            encoder.encode(["text"], [4])
        encoder.model.tokenizer = lambda *a, **kw: {"input_ids": [[1, 9, 3]]}
        with self.assertRaisesRegex(IngestionError, "differs"):
            encoder.encode(["text"])
        encoder.chunker.tokenizer.encode = lambda _: SimpleNamespace(ids=[1] * 513)
        encoder.model.tokenizer = lambda *a, **kw: {"input_ids": [[1] * 513]}
        with self.assertRaisesRegex(IngestionError, "512"):
            encoder.encode(["text"])

    def test_chunk_stream_hash_and_duplicates_checked(self):
        item = {"chunk_id": "CHK-" + "a" * 64, "point_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "config_sha256": "fixture", "content": "text", "content_sha256": digest(b"text"),
                "embedding_text": "text", "token_count": 3}
        line = canonical(item) + b"\n"
        manifest = {"config_sha256": "fixture", "chunks": 1,
                    "config": {"max_tokens": 384, "max_characters": 16000},
                    "output_sha256": {"chunks.jsonl": digest(line)}}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "chunks.jsonl"
            path.write_bytes(line)
            self.assertEqual(list(chunk_records(tmp, manifest)), [item])
            path.write_bytes(line + line)
            with self.assertRaises(IngestionError):
                list(chunk_records(tmp, manifest))
            path.write_bytes(line.replace(b'"text"', b'"TEXT"'))
            with self.assertRaises(IngestionError):
                list(chunk_records(tmp, manifest))

    def test_failed_embedding_never_publishes_partial_output(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "vectors"
            with patch("rag.vector.embed.read_manifest", return_value={}), \
                    patch("rag.vector.embed.BGEEncoder", return_value=SimpleNamespace()), \
                    patch("rag.vector.embed.chunk_records", side_effect=IngestionError("corrupt stream")):
                with self.assertRaises(IngestionError):
                    build(tmp, "fixture", tmp, output)
            self.assertFalse(output.exists())
            self.assertFalse(list(Path(tmp).glob(".embed-*")))


if __name__ == "__main__":
    unittest.main()

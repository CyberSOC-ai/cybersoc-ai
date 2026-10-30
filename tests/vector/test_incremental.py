"""Incremental preparation scenarios; fake vectors measure reuse, not relevance."""

from copy import deepcopy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from rag.ingestion.core import IngestionError, canonical, digest
from rag.vector.chunk import build as chunk_build
from rag.vector.chunking import Chunker, TOKENIZER_REVISION, TOKENIZER_SHA256
from rag.vector.model import WEIGHTS_SHA256
from rag.vector.prepare import DEFAULT_LIMIT, main, prepare
import test_chunking as fixtures
from test_index import FakeQdrant

cve = fixtures.cve


class IncrementalTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ChunkingTests('test_build_replays_bytes_and_accounts_for_exclusions')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.model = self.root / 'model'
        self.model.mkdir()
        (self.model / 'tokenizer.json').write_bytes(self.fixture.tokenizer_path.read_bytes())
        self.model_identity = {'model_id': 'BAAI/bge-small-en-v1.5', 'revision': TOKENIZER_REVISION,
                               'sha256': {'model.safetensors': WEIGHTS_SHA256, 'tokenizer.json': TOKENIZER_SHA256}}
        self.server = FakeQdrant()
        self.encoded = []
        self.encoder = SimpleNamespace(identity=self.model_identity, threads=4, encode=self.encode)
        self.enterContext(patch('rag.vector.prepare.verify_model', side_effect=lambda _: self.model_identity))
        self.enterContext(patch('rag.vector.embed.verify_model', side_effect=lambda _: self.model_identity))
        self.loader = self.enterContext(patch('rag.vector.embed.BGEEncoder', return_value=self.encoder))
        self.enterContext(patch('rag.vector.index.Qdrant', return_value=self.server))
        self.version = 0

    def encode(self, texts, counts):
        self.encoded.extend(texts)
        return [[1.0] + [0.0] * 383 for _ in texts]

    def corpus(self, records):
        self.version += 1
        self.fixture.root = self.root / f'input-{self.version}'
        self.fixture.root.mkdir()
        args = self.fixture.corpus(records)
        path = args['corpus'] / 'manifest.json'
        value = json.loads(path.read_bytes())
        # Support a fresh acquisition snapshot, with the same source notice.
        for entry in value['inputs']:
            entry['snapshot'] = next(r['provenance'] for r in records if r['source'] == entry['snapshot']['source'])
        path.write_bytes(canonical(value))
        return args['corpus']

    def run_version(self, records, previous=None, **kwargs):
        corpus = self.corpus(records)
        output = self.root / f'prepared-{self.version}'
        options = {'limit_per_source': None} if previous is None else {
            'previous_ready': previous / 'READY.json',
            'previous_ready_sha256': digest((previous / 'READY.json').read_bytes())}
        result = prepare(corpus, self.model, output, **(options | kwargs))
        return output, result

    def test_unchanged_records_need_no_token_splitting_or_encoder_loading(self):
        old, previous = self.run_version([cve()])
        old_data = deepcopy(self.server.data)
        self.encoded.clear()
        self.loader.reset_mock()
        with patch.object(Chunker, 'spans', side_effect=AssertionError('unchanged record was rechunked')):
            new, result = self.run_version([cve()], old)
        self.assertEqual(result['incremental']['chunking']['reused_span_records'], 1)
        self.assertEqual(result['incremental']['embedding']['encoded_texts'], 0)
        self.assertEqual(result['incremental']['embedding']['reused_vectors'], 1)
        self.loader.assert_not_called()
        self.assertEqual(self.encoded, [])
        self.assertEqual((old / 'chunks/chunks.jsonl').read_bytes(), (new / 'chunks/chunks.jsonl').read_bytes())
        self.assertEqual((old / 'embeddings/vectors.jsonl').read_bytes(), (new / 'embeddings/vectors.jsonl').read_bytes())
        self.assertIsNone(result['preview_limit_per_source'])  # Inherit full coverage, not the preview default.
        self.assertNotEqual(previous['index'], result['index'])
        for name, points in old_data.items():
            self.assertEqual(self.server.data[name], points)

    def test_add_edit_delete_only_encodes_changed_texts_and_preserves_old_version(self):
        a, b, c, d = [cve(identity=f'CVE-2024-{n}') for n in (1001, 1002, 1003, 1004)]
        old, _ = self.run_version([a, b, c])
        old_data = deepcopy(self.server.data)
        b = cve('authentication failure changed', 'CVE-2024-1002')
        self.encoded.clear()
        _, result = self.run_version([a, b, d], old)
        stats = result['incremental']
        self.assertEqual(stats['chunking']['reused_span_records'], 1)
        self.assertEqual(stats['chunking']['rechunked_records'], 2)
        self.assertEqual(stats['chunking']['removed_previously_chunked_records'], 1)
        self.assertEqual(stats['embedding']['encoded_texts'], 2)
        self.assertEqual(stats['embedding']['reused_vectors'], 1)
        self.assertEqual(len(self.encoded), 2)
        self.assertTrue(all('CVE-2024-1001' not in text for text in self.encoded))
        receipt = json.loads((Path(result['index']) / 'manifest.json').read_bytes())
        points = self.server.data[receipt['collections']['knowledge']].values()
        self.assertEqual({p['payload']['source_record_id'] for p in points},
                         {'CVE-2024-1001', 'CVE-2024-1002', 'CVE-2024-1004'})
        for name, points in old_data.items():
            self.assertEqual(self.server.data[name], points)

    def test_fresh_provenance_reuses_vectors_and_spans_but_rebinds_citations_and_ids(self):
        old, _ = self.run_version([cve()])
        changed = cve()
        changed['snapshot_ref'] = changed['provenance']['artifact_ref'] = 'fixture:fresh-acquisition'
        changed['provenance']['acquired_at'] = '2026-10-30T00:00:00Z'
        changed['metadata']['vulnStatus'] = 'Deferred'
        with patch.object(Chunker, 'spans', side_effect=AssertionError('metadata-only change was rechunked')):
            new, result = self.run_version([changed], old)
        stats = result['incremental']
        self.assertEqual(stats['chunking']['reused_span_records'], 1)
        self.assertEqual(stats['embedding']['encoded_texts'], 0)
        before = json.loads((old / 'chunks/chunks.jsonl').read_bytes())
        after = json.loads((new / 'chunks/chunks.jsonl').read_bytes())
        self.assertNotEqual(before['chunk_id'], after['chunk_id'])
        self.assertEqual(after['snapshot_ref'], changed['snapshot_ref'])
        self.assertEqual(after['filters']['source_status'], 'Deferred')
        self.assertEqual(after['embedding_text'], before['embedding_text'])

    def test_title_change_recomputes_header_and_embedding(self):
        old, _ = self.run_version([cve()])
        changed = cve()
        changed['title'] = 'New SSH investigation title'
        self.encoded.clear()
        _, result = self.run_version([changed], old)
        self.assertEqual(result['incremental']['chunking']['rechunked_records'], 1)
        self.assertEqual(result['incremental']['embedding']['encoded_texts'], 1)
        self.assertIn(changed['title'], self.encoded[0])

    def test_corrupted_previous_chunks_or_vectors_fail_without_publishing(self):
        for filename in ('chunks/chunks.jsonl', 'embeddings/vectors.jsonl'):
            with self.subTest(filename=filename):
                old, _ = self.run_version([cve()])
                old_data = deepcopy(self.server.data)
                path = old / filename
                path.write_bytes(path.read_bytes() + b'invalid\n')
                with self.assertRaises(IngestionError):
                    self.run_version([cve()], old)
                output = self.root / f'prepared-{self.version}'
                self.assertFalse((output / 'READY.json').exists())
                self.assertFalse((output / 'embeddings').exists())
                self.assertEqual(self.server.data, old_data)

    def test_changed_model_or_runtime_cannot_reuse_old_vectors(self):
        old, _ = self.run_version([cve()])
        self.model_identity = deepcopy(self.model_identity)
        self.model_identity['sha256']['additional-config'] = 'c' * 64
        with self.assertRaisesRegex(IngestionError, 'model/runtime changed'):
            self.run_version([cve()], old)
        self.assertFalse((self.root / f'prepared-{self.version}/READY.json').exists())

    def test_changed_chunk_configuration_requires_fresh_build(self):
        old, _ = self.run_version([cve()])
        config = json.loads((old / 'chunks/chunking-config.json').read_bytes())
        config['max_tokens'] = 128
        path = self.root / 'changed-config.json'
        path.write_bytes(canonical(config))
        def changed_builder(*args, **kwargs):
            return chunk_build(*args, **kwargs, config=path)
        with patch('rag.vector.prepare.chunk_build', side_effect=changed_builder):
            with self.assertRaisesRegex(IngestionError, 'configuration changed'):
                self.run_version([cve()], old)

    def test_failed_new_index_never_publishes_ready_or_changes_old_collections(self):
        old, _ = self.run_version([cve()])
        old_data = deepcopy(self.server.data)
        with patch.object(self.server, 'upsert', side_effect=IngestionError('simulated failure')):
            with self.assertRaises(IngestionError):
                self.run_version([cve(), cve(identity='CVE-2024-9999')], old)
        self.assertFalse((self.root / f'prepared-{self.version}/READY.json').exists())
        for name, points in old_data.items():
            self.assertEqual(self.server.data[name], points)
            self.assertEqual(self.server.info(name)['config']['metadata']['state'], 'ready')

    def test_previous_ready_hash_and_receipt_hash_are_required(self):
        old, _ = self.run_version([cve()])
        with self.assertRaisesRegex(IngestionError, 'READY SHA'):
            self.run_version([cve()], old, previous_ready_sha256='0' * 64)
        path = old / 'index/manifest.json'
        path.write_bytes(path.read_bytes() + b' ')
        with self.assertRaisesRegex(IngestionError, 'receipt SHA'):
            self.run_version([cve()], old)

    def test_reuse_cannot_skip_validation_of_new_corpus_tail(self):
        old, _ = self.run_version([cve()])
        corpus = self.corpus([cve()])
        path = corpus / 'records.jsonl'
        path.write_bytes(path.read_bytes() + b'invalid\n')
        output = self.root / 'invalid-tail'
        with self.assertRaises(IngestionError):
            prepare(corpus, self.model, output, previous_ready=old / 'READY.json',
                    previous_ready_sha256=digest((old / 'READY.json').read_bytes()))
        self.assertFalse((output / 'chunks').exists())
        self.assertFalse((output / 'READY.json').exists())

    def test_preview_is_inherited_and_expanding_coverage_only_encodes_missing_records(self):
        records = [cve(), cve(identity='CVE-2024-9999')]
        old, _ = self.run_version(records, limit_per_source=1)
        self.encoded.clear()
        _, bounded = self.run_version(records, old)
        self.assertEqual(bounded['preview_limit_per_source'], 1)
        self.assertEqual(bounded['points_by_collection']['knowledge'], 1)
        self.assertEqual(bounded['incremental']['embedding']['encoded_texts'], 0)
        _, expanded = self.run_version(records, old, limit_per_source=None)
        self.assertIsNone(expanded['preview_limit_per_source'])
        self.assertEqual(expanded['points_by_collection']['knowledge'], 2)
        self.assertEqual(expanded['incremental']['embedding']['encoded_texts'], 1)

    def test_cli_distinguishes_inherited_preview_and_explicit_full_coverage(self):
        for flags, expected in (([], DEFAULT_LIMIT), (['--all-records'], None), (['--limit-per-source', '7'], 7)):
            with self.subTest(flags=flags), redirect_stdout(io.StringIO()), \
                    patch('sys.argv', ['prepare', '--corpus', 'corpus', '--model', 'model', '--output', 'output', *flags]), \
                    patch('rag.vector.prepare.prepare', return_value={}) as call:
                main()
                self.assertEqual(call.call_args.kwargs['limit_per_source'], expected)

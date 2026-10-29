"""Evaluator setup linking and failure tests with synthetic inputs."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from rag.ingestion.core import IngestionError, digest
from rag.vector.prepare import prepare
import test_index as fixtures


class PrepareTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.IndexTests('test_load_preserves_payload_and_separates_collections')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.args, _, _ = self.fixture.inputs()
        self.corpus = self.fixture.root / 'corpus'
        self.corpus.mkdir()
        (self.corpus / 'manifest.json').write_bytes(b'{}')
        path = self.args['chunks'] / 'manifest.json'
        value = json.loads(path.read_bytes())
        value['corpus_manifest_sha256'] = digest(b'{}')
        path.write_text(json.dumps(value))
        self.args['chunk_sha'] = digest(path.read_bytes())
        path = self.args['vectors'] / 'manifest.json'
        self.em = json.loads(path.read_bytes())
        self.em['chunk_manifest_sha256'] = self.args['chunk_sha']
        path.write_text(json.dumps(self.em))

    def test_reused_artifacts_produce_portable_ready_record(self):
        with patch('rag.vector.prepare.verify_model', return_value=self.em['model']), \
                patch('rag.vector.index.Qdrant', return_value=self.fixture.server):
            ready = prepare(self.corpus, Path('synthetic-model'), self.fixture.root / 'prepared',
                            reuse_chunks=self.args['chunks'], reuse_vectors=self.args['vectors'])
        self.assertEqual(ready['state'], 'ready')
        self.assertEqual(ready['points_by_collection'], {'knowledge':1,'soc_history':1})
        self.assertTrue((self.fixture.root / 'prepared/READY.json').exists())

    def test_partial_reuse_and_existing_output_rejected(self):
        with self.assertRaises(IngestionError):
            prepare(self.corpus, Path('synthetic-model'), self.fixture.root / 'prepared',
                    reuse_chunks=self.args['chunks'])
        with self.assertRaises(IngestionError):
            prepare(self.corpus, Path('synthetic-model'), self.fixture.root)

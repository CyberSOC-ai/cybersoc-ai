"""Offline source/span/identity and failure-boundary regressions; no model download."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from rag.vector.data import configuration, corpus, identity, load, passages, safe_file, save, seal, verified
from rag.vector.index import point_id, read_vectors


class Characters:
    def __call__(self, text, **kwargs):
        return {'offset_mapping': [(i, i+1) for i, ch in enumerate(text) if not ch.isspace()]}


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = configuration()

    def test_chunk_spans_overlap_and_cover_every_nonspace_character(self):
        c = {**self.config, 'chunk_tokens': 12, 'overlap_tokens': 3}
        text = 'Version conditions.\n\nOnly when option is enabled.\nNo exploitation observed.'
        record = {'document_id': 'DOC-test', 'content': text, 'content_sha256': identity(text),
                  'snapshot_sha256': 'a'*64, 'title': 'Title', 'source_url': 'https://example.invalid', 'source': 'playbook'}
        chunks = passages(record, Characters(), c)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertEqual(chunk['content'], text[chunk['start']:chunk['end']])
            self.assertLessEqual(chunk['token_count'], 12)
        self.assertTrue(all(any(p['start'] <= i < p['end'] for p in chunks)
                            for i, ch in enumerate(text) if not ch.isspace()))
        self.assertEqual(chunks, passages(record, Characters(), c))
        changed = {**record, 'content': text+'x', 'content_sha256': identity(text+'x')}
        self.assertNotEqual(chunks[0]['chunk_id'], passages(changed, Characters(), c)[0]['chunk_id'])

    def test_artifact_tampering_and_symlink_escape_fail(self):
        save(self.root/'records.json', {'a': 1})
        seal(self.root, {'kind': 'test'})
        verified(self.root)
        (self.root/'records.json').write_text('{}')
        with self.assertRaises(ValueError):
            verified(self.root)
        (self.root/'link').symlink_to('/tmp')
        for name in ['../escape', '/tmp/escape', 'link/escape']:
            with self.subTest(name=name), self.assertRaises(ValueError):
                safe_file(self.root, name)

    def test_duplicate_json_nonfinite_and_output_overwrite_rejected(self):
        for text in ['{"a":1,"a":2}', '{"a":NaN}']:
            (self.root/'a.json').write_text(text)
            with self.assertRaises(ValueError):
                load(self.root/'a.json')
        with self.assertRaises(FileExistsError):
            save(self.root/'a.json', {})

    def test_bad_manifest_rejected_without_reading_corpus(self):
        save(self.root/'manifest.json', {'assets': []})
        with self.assertRaisesRegex(ValueError, 'manifest checksum'):
            corpus(self.root, self.config)

    def test_invalid_chunk_configuration_rejected(self):
        c = deepcopy(self.config)
        c['overlap_tokens'] = c['chunk_tokens']
        save(self.root/'bad.json', c)
        with self.assertRaises(ValueError):
            configuration(self.root/'bad.json')

    def test_vector_shape_and_nonfinite_payload_rejected(self):
        (self.root/'vectors.f32').write_bytes(b'\0'*4)
        seal(self.root, {'chunk_count': 1})
        with self.assertRaisesRegex(ValueError, 'shape'):
            read_vectors(self.root)
        self.assertEqual(point_id('EV-test'), point_id('EV-test'))


if __name__ == '__main__':
    unittest.main()


class GenerationTests(unittest.TestCase):
    def setUp(self):
        import json
        self.incident = json.loads(Path('tests/no_rag/fixtures/incident.json').read_text())
        self.policy = json.loads(Path('tests/no_rag/fixtures/policy.json').read_text())
        self.evidence = [{'chunk_id': 'EV-known', 'document_id': 'DOC-test', 'title': 'Reference',
                          'source_url': 'https://example.invalid/ref', 'start': 0, 'end': 28,
                          'content': 'Authentication documentation.', 'snapshot_sha256': 'a'*64,
                          'score': .8, 'source': 'playbook'}]
        self.answer = {'summary': 'Authentication reference', 'triage_verdict': 'undetermined',
                       'risk_level': 'medium', 'mitre_techniques': [], 'recommended_actions': [],
                       'citation_ids': ['R1']}

    def call(self, answer):
        import json
        from rag.vector.generation import schema, validate_decision
        return validate_decision(json.dumps(answer), schema(['R1']), self.evidence, self.incident,
                                 self.policy, 'TRC-test', 'INV-test', 'shared-dev-v1')

    def test_alias_binding_and_no_semantic_repair(self):
        result, citations = self.call(self.answer)
        self.assertEqual(result['mode'], 'vector')
        self.assertEqual(result['summary'], 'Authentication reference [EV-known]')
        self.assertEqual(result['evidence'][0]['evidence_id'], 'EV-known')
        self.assertEqual(citations['model_summary'], self.answer['summary'])
        self.assertEqual(self.answer['summary'], 'Authentication reference')

    def test_unknown_missing_duplicate_citations_fail(self):
        from ai.runtime.contracts import InvalidOutput
        for changes in [{'citation_ids': ['R9']}, {'summary': 'Reference [R1]'},
                        {'citation_ids': ['R1', 'R1']}, {'summary': 'Wrong [R9]'}]:
            with self.subTest(changes=changes), self.assertRaises(InvalidOutput):
                self.call({**self.answer, **changes})

    def test_empty_citations_do_not_force_unsupported_source_claim(self):
        result, _ = self.call({**self.answer, 'summary': 'Incident authorization is unknown.', 'citation_ids': []})
        self.assertEqual(result['summary'], 'Incident authorization is unknown.')
        self.assertEqual(len(result['evidence']), 1)  # Actual supplied context remains recorded.

    def test_proposal_without_verified_origin_scope_fails(self):
        action = {'target': 'linux-01', 'source_ip': '192.0.2.10', 'reason': 'test',
                  'expected_effect': 'test', 'risks': 'test', 'rollback_plan': 'test'}
        with self.assertRaises(ValueError):
            self.call({**self.answer, 'recommended_actions': [action]})

    def test_context_budget_rejects_without_silent_truncation(self):
        import json
        from ai.runtime.contracts import InvalidOutput
        from rag.vector.generation import prepare

        class Client:
            def _request(self, path, value, deadline):
                if path == '/apply-template':
                    yield {'prompt': json.dumps(value)}
                else:
                    yield {'tokens': list(range(len(value['content'])))}
        with self.assertRaisesRegex(InvalidOutput, 'No evidence fits'):
            prepare(Client(), self.incident, self.policy, self.evidence,
                    {'generation_passages': 1, 'generation_input_limit': 5}, 999999)
        msg, _, _, _, selected = prepare(Client(), self.incident, self.policy, self.evidence,
                    {'generation_passages': 1, 'generation_input_limit': 50000}, 999999)
        user = json.loads(msg[1]['content'])
        self.assertEqual(set(user), {'untrusted_incident', 'fixed_proposal_policy', 'reference_passages', 'required_output'})
        self.assertEqual(user['untrusted_incident'], self.incident)
        self.assertEqual(selected, self.evidence)


class RetrievalIntegrityTests(unittest.TestCase):
    def setUp(self):
        import struct
        from rag.vector.data import digest
        from rag.vector.index import payload
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.build = self.root/'build'
        self.build.mkdir()
        self.config = configuration()
        self.chunk = {'chunk_id': 'EV-known', 'document_id': 'DOC-test', 'content': 'Known text',
                      'start': 0, 'end': 10, 'source': 'playbook', 'content_sha256': 'a'*64,
                      'title': 'Test', 'source_url': 'https://example.invalid', 'snapshot_sha256': 'b'*64}
        save(self.build/'chunks.json', [self.chunk])
        save(self.build/'documents.json', [{'document_id': 'DOC-test', 'content': 'Known text'}])
        save(self.build/'configuration.json', self.config)
        (self.build/'vectors.f32').write_bytes(struct.pack('<384f', 1., *([0.]*383)))
        seal(self.build, {'chunk_count': 1, 'release_manifest_sha256': self.config['release_manifest_sha256']})
        self.build_sha = digest(self.build/'manifest.json')
        self.receipt = self.root/'receipt.json'
        save(self.receipt, {'build_sha256': self.build_sha, 'collection': 'cs_'+'a'*24})
        hit = {'id': point_id('EV-known'), 'payload': payload(self.chunk, self.build_sha),
               'vector': [1.]+[0.]*383, 'score': 1.}

        class Store:
            def ready(self):
                pass

            def info(self, name):
                return {'points_count': 1, 'config': {'params': {'vectors': {'size': 384, 'distance': 'Cosine'}}}}

            def request(self, *args, **kwargs):
                return {'result': [self.hit]}

            def query(self, *args, **kwargs):
                return [self.hit]
        self.store = Store()
        self.store.hit = hit

        class Encoder:
            def encode(self, *args, **kwargs):
                return [[1.]+[0.]*383]
        self.encoder = Encoder()

    def retriever(self):
        from rag.vector.retrieval import Retriever
        return Retriever(self.build, self.receipt, self.config, store=self.store, encoder=self.encoder)

    def test_payload_vector_score_and_filter_tampering_are_rejected(self):
        r = self.retriever()
        self.assertEqual(r.search('Question')['evidence'][0]['content'], 'Known text')
        self.store.hit['score'] = .5
        with self.assertRaisesRegex(ValueError, 'score/filter'):
            r.search('Question')
        self.store.hit['score'] = 1.
        with self.assertRaises(ValueError):
            r.search('Question', sources=['cve'])
        self.store.hit['payload']['content_sha256'] = 'c'*64
        with self.assertRaisesRegex(ValueError, 'point integrity'):
            self.retriever()

    def test_source_change_and_query_entities_are_explicit(self):
        from rag.vector.retrieval import incident_query
        sample = {'source': 'sensor:linux-files', 'description': 'Synthetic scenario. At 2026-11-01T11:05:00Z host-a reports file integrity change to /etc/example. No approval is supplied.',
                  'entities': [{'type': 'host', 'value': 'host-a'}, {'type': 'file', 'value': '/etc/example'}]}
        q = incident_query(sample)
        self.assertIn('file integrity change', q)
        self.assertNotIn('host-a', q)
        self.assertNotIn('No approval', q)
        self.assertNotIn('/etc/example', q)
        self.assertEqual(sample['entities'][0]['value'], 'host-a')


class IncrementalBuildTests(unittest.TestCase):
    def test_new_document_embeds_only_new_input_and_rejects_incompatible_reuse(self):
        from unittest.mock import patch
        from rag.vector.index import build
        config = configuration()
        text = 'A short technical reference.'

        def document(did, content):
            return {'document_id': did, 'content': content, 'content_sha256': identity(content),
                    'snapshot_sha256': 'a'*64, 'title': 'Reference',
                    'source_url': 'https://example.invalid', 'source': 'playbook'}

        class ControlledEncoder:
            tokenizer = Characters()

            def __init__(self):
                self.texts = []

            def encode(self, texts):
                self.texts.extend(texts)
                return [[1.]+[0.]*383 for _ in texts]
        with tempfile.TemporaryDirectory() as temp, patch('importlib.metadata.version', return_value='test-only'):
            root = Path(temp)
            first = ControlledEncoder()
            with patch('rag.vector.index.corpus', return_value=[document('DOC-one', text)]):
                m = build(root/'source', root/'first', config, encoder=first)
            self.assertEqual((m['new_embeddings'], len(first.texts)), (1, 1))
            second = ControlledEncoder()
            with patch('rag.vector.index.corpus', return_value=[document('DOC-one', text), document('DOC-two', 'Another new reference.')]):
                m = build(root/'source', root/'second', config, reuse=root/'first', encoder=second)
            self.assertEqual((m['reused_embeddings'], m['new_embeddings'], len(second.texts)), (1, 1, 1))
            changed = {**config, 'embedding_files_sha256': {'changed-model': 'b'*64}}
            with patch('rag.vector.index.corpus', return_value=[document('DOC-one', text)]), self.assertRaisesRegex(ValueError, 'Incompatible'):
                build(root/'source', root/'bad', changed, reuse=root/'first', encoder=ControlledEncoder())

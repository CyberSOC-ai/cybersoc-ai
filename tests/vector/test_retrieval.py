"""Contract projection, filter and failure tests using synthetic index fixtures."""

from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import httpx
from jsonschema import ValidationError

from backend.validation import validate
from rag.ingestion.core import IngestionError, digest
from rag.vector.index import build
from rag.vector.retrieve import Retriever, query_filter
import test_index as fixtures


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.IndexTests('test_load_preserves_payload_and_separates_collections')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        args, _, _ = self.fixture.inputs()
        self.args = args
        self.server = self.fixture.server
        with patch('rag.vector.index.Qdrant', return_value=self.server):
            self.report = build(**args)
        self.calls = []
        self.server.path = lambda name: '/collections/' + name
        self.server.request = self.query
        identity = json.loads((args['vectors'] / 'manifest.json').read_bytes())['model']
        self.encoder = SimpleNamespace(identity=identity, query=lambda _: [1.0] + [0.0]*383)
        self.patches = [patch('rag.vector.retrieve.Qdrant', return_value=self.server),
                        patch('rag.vector.retrieve.BGEEncoder', return_value=self.encoder)]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)
        self.reader = Retriever(args['output'], digest((args['output'] / 'manifest.json').read_bytes()),
                                args['chunks'], args['vectors'], Path('synthetic-model'), exact=True)
        self.addCleanup(self.reader.close)
        self.request = dict(schema_version='1.0.0', request_id='REQ-fixture', trace_id='TR-fixture',
                            mode='vector', query='SSH failures', top_k=10, filters={})

    def query(self, method, path, data):
        self.calls.append(deepcopy(data))
        name = path.split('/')[2]
        hits = []
        for point in self.server.data[name].values():
            include = True
            for condition in data['filter']['must']:
                value = point['payload'].get(condition['key'])
                match = condition['match']
                if ('any' in match and value not in match['any'] or
                        'value' in match and value != match['value']):
                    include = False
            if include:
                hits.append({**deepcopy(point), 'score': 1.0})
        return {'points': hits[:data['limit']]}

    def test_global_top_k_ties_and_closed_evidence_projection(self):
        result = self.reader.retrieve(self.request | {'top_k': 1})
        validate('retrieval-response', result)
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(len(result['evidence']), 1)
        self.assertEqual(result['evidence'][0]['evidence_id'], 'CHK-' + 'a'*64)
        self.assertEqual(set(result['evidence'][0]), {'evidence_id', 'source', 'source_record_id', 'snapshot_ref',
                                                     'content', 'score', 'score_kind', 'retrieval_method'})
        self.assertEqual(result['request_id'], self.request['request_id'])
        self.assertEqual(result['trace_id'], self.request['trace_id'])

    def test_filters_are_applied_before_top_k_and_rechecked(self):
        result = self.reader.retrieve(self.request | {'filters': {'sources': ['soc_log'],
                                                                'snapshot_refs': ['fixture:soc_log']}})
        self.assertEqual([e['source'] for e in result['evidence']], ['soc_log'])
        for call in self.calls:
            self.assertEqual(call['filter']['must'][0], {'key': 'source', 'match': {'any': ['soc_log']}})
            self.assertEqual(call['filter']['must'][1], {'key': 'snapshot_ref', 'match': {'any': ['fixture:soc_log']}})
        self.assertIn({'key': 'split', 'match': {'value': 'development'}}, self.calls[1]['filter']['must'])
        self.assertIn({'key': 'test_frozen', 'match': {'value': False}}, self.calls[1]['filter']['must'])

    def test_no_match_and_empty_arrays_have_explicit_semantics(self):
        for filters in ({'sources': ['graph']}, {'snapshot_refs': ['missing']}):
            result = self.reader.retrieve(self.request | {'filters': filters})
            self.assertEqual((result['status'], result['evidence']), ('ok', []))
        result = self.reader.retrieve(self.request | {'filters': {'sources': [], 'snapshot_refs': []}})
        self.assertEqual(len(result['evidence']), 2)

    def test_new_sources_are_accepted_and_do_not_fall_back_to_other_sources(self):
        result = self.reader.retrieve(self.request | {'filters': {'sources': ['detection_rule', 'playbook']}})
        self.assertEqual((result['status'], result['evidence']), ('ok', []))

    def test_unsupported_modes_return_explicit_errors_without_search(self):
        for mode in ('graph', 'hybrid'):
            result = self.reader.retrieve(self.request | {'mode': mode})
            self.assertEqual(result['error']['code'], 'validation_error')
            self.assertEqual(result['evidence'], [])
        self.assertEqual(self.calls, [])

    def test_invalid_requests_are_rejected(self):
        for changes in ({'top_k': 101}, {'query': ''}, {'filters': {'group': 'private'}}, {'filters': {'sources': ['unknown']}}):
            with self.assertRaises(ValidationError):
                self.reader.retrieve(self.request | changes)

    def test_query_overflow_does_not_search_or_return_partial_evidence(self):
        self.encoder.query = lambda _: (_ for _ in ()).throw(IngestionError('Too many tokens'))
        result = self.reader.retrieve(self.request)
        self.assertEqual(result['error']['code'], 'validation_error')
        self.assertEqual(result['evidence'], [])
        self.assertFalse(self.calls)

    def test_timeout_and_other_connection_errors_are_distinct(self):
        for error, code in ((httpx.ReadTimeout('private internal details'), 'timeout'),
                            (httpx.ConnectError('private internal details'), 'dependency_unavailable')):
            with patch.object(self.server, 'request', side_effect=error):
                result = self.reader.retrieve(self.request)
            self.assertEqual(result['error']['code'], code)
            self.assertTrue(result['error']['retryable'])
            self.assertEqual(result['evidence'], [])
            self.assertNotIn('private', result['error']['message'])

    def test_live_payload_and_vector_mutations_fail_closed(self):
        name = self.report['collections']['knowledge']
        point = next(iter(self.server.data[name].values()))
        original = deepcopy(point)
        point['payload']['content'] = 'tampered'
        self.assertEqual(self.reader.retrieve(self.request)['error']['code'], 'invalid_output')
        point.update(deepcopy(original))
        point['vector'] = [0.0, 1.0] + [0.0]*382
        self.assertEqual(self.reader.retrieve(self.request)['error']['code'], 'invalid_output')

    def test_nonfinite_scores_duplicates_and_partial_results_fail_closed(self):
        query = self.query
        for behavior in ('nonfinite', 'duplicate', 'wrong_score', 'wrong_filters'):
            def bad(method, path, data):
                result = query(method, path, data)
                if result['points']:
                    if behavior == 'nonfinite':
                        result['points'][0]['score'] = float('nan')
                    elif behavior == 'duplicate':
                        result['points'].append(result['points'][0])
                    elif behavior == 'wrong_score':
                        result['points'][0]['score'] = 0.2
                    else:
                        result['points'][0]['payload']['source'] = 'playbook'
                return result
            with patch.object(self.server, 'request', side_effect=bad):
                result = self.reader.retrieve(self.request)
            self.assertEqual((result['status'], result['evidence']), ('error', []))

    def test_changed_state_or_policy_rejects_requests(self):
        name = self.report['collections']['soc_history']
        self.server.collections[name]['config']['metadata']['state'] = 'building'
        self.assertEqual(self.reader.retrieve(self.request)['error']['code'], 'conflict')
        with patch('rag.vector.retrieve.read_manifest', side_effect=IngestionError('stale split')):
            self.assertEqual(self.reader.retrieve(self.request)['error']['code'], 'conflict')

    def test_receipt_and_model_identity_required_on_reload(self):
        receipt = self.args['output']
        checksum = digest((receipt / 'manifest.json').read_bytes())
        for expected in ('0'*64, checksum):
            if expected == checksum:
                self.encoder.identity = {'wrong': True}
            with self.assertRaises(IngestionError):
                Retriever(receipt, expected, self.args['chunks'], self.args['vectors'], Path('synthetic-model'))

    def test_filter_boolean_stays_typed(self):
        self.assertIs(query_filter({}, 'soc_history', False)['must'][1]['match']['value'], False)


if __name__ == '__main__':
    unittest.main()

"""Deterministic shared-deadline regressions: no models, sockets or sleeping."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import httpx

from backend.validation import validate
from rag.generation.pipeline import PipelineError, VectorPipeline
from rag.vector.store import Qdrant
import test_generation as generation_fixtures
import test_retrieval as retrieval_fixtures

ROOT = Path(__file__).resolve().parents[2]


class DeadlineTests(unittest.TestCase):
    def setUp(self):
        self.fixture = retrieval_fixtures.RetrievalTests(
            'test_global_top_k_ties_and_closed_evidence_projection')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.reader, self.request = self.fixture.reader, self.fixture.request
        self.now, self.elapsed_per_request = 100.0, .25
        self.transport_error = None
        self.sent = []
        self.client = Qdrant(transport=httpx.MockTransport(self.dispatch))
        self.reader.client = self.client
        clock = patch('rag.vector.store.time.monotonic', side_effect=lambda: self.now)
        clock.start()
        self.addCleanup(clock.stop)

    def dispatch(self, request):
        self.sent.append((self.now, deepcopy(request.extensions['timeout']), request.url.path))
        self.now += self.elapsed_per_request
        if self.transport_error:
            raise self.transport_error
        if request.url.path == '/':
            return httpx.Response(200, json={'version': '1.20.0'})
        name = request.url.path.split('/')[2]
        if request.url.path.endswith('/points/query'):
            result = self.fixture.query(request.method, request.url.path, json.loads(request.content))
        elif request.url.path.endswith('/points/count'):
            result = {'count': self.fixture.server.count(name)}
        else:
            result = self.fixture.server.info(name)
        return httpx.Response(200, json={'status': 'ok', 'result': result})

    def test_successful_retrieval_shares_remaining_budget_across_all_requests(self):
        deadline = 110.0
        result = self.reader.retrieve(self.request, deadline=deadline)
        validate('retrieval-response', result)
        self.assertEqual(result['status'], 'ok')
        # State verification before/after search plus both collection queries.
        self.assertEqual(len(self.sent), 12)
        for started, budgets, _ in self.sent:
            self.assertEqual(set(budgets), {'connect', 'read', 'write', 'pool'})
            self.assertTrue(all(value == deadline - started for value in budgets.values()))
        self.assertLess(self.sent[-1][1]['read'], self.sent[0][1]['read'])
        self.assertEqual(self.client.client.timeout.read, 60.0)

    def test_expired_deadline_rejects_before_storage_or_encoding(self):
        self.fixture.encoder.query = Mock()
        with patch.object(self.reader, 'check_state', wraps=self.reader.check_state) as state:
            result = self.reader.retrieve(self.request, deadline=self.now)
        self.assertEqual(result['error']['code'], 'timeout')
        self.assertTrue(result['error']['retryable'])
        self.assertEqual(result['evidence'], [])
        state.assert_not_called()
        self.fixture.encoder.query.assert_not_called()
        self.assertEqual(self.sent, [])

    def test_slow_response_is_rejected_and_no_next_request_is_sent(self):
        self.elapsed_per_request = 12
        result = self.reader.retrieve(self.request, deadline=110)
        self.assertEqual((result['status'], result['evidence']), ('error', []))
        self.assertEqual(result['error']['code'], 'timeout')
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(self.fixture.calls, [])

    def test_httpx_timeout_is_sanitized_and_distinct_from_connection_failure(self):
        for error, code in ((httpx.ReadTimeout('private socket detail'), 'timeout'),
                            (httpx.ConnectError('private socket detail'), 'dependency_unavailable')):
            with self.subTest(code=code):
                self.transport_error = error
                result = self.reader.retrieve(self.request, deadline=self.now + 10)
                self.assertEqual(result['error']['code'], code)
                self.assertTrue(result['error']['retryable'])
                self.assertNotIn('private', result['error']['message'])
                self.assertEqual(result['evidence'], [])

    def test_expiry_after_search_does_not_return_partial_evidence(self):
        # Five initial state reads + two queries + final version read consume 2s.
        result = self.reader.retrieve(self.request, deadline=102)
        self.assertEqual(len(self.sent), 8)
        self.assertEqual(len(self.fixture.calls), 2)
        self.assertEqual(result['error']['code'], 'timeout')
        self.assertEqual(result['evidence'], [])

    def test_encoding_overrun_is_detected_before_any_search(self):
        def encode(_):
            self.now += 20
            return [1.0] + [0.0] * 383
        self.fixture.encoder.query = encode
        result = self.reader.retrieve(self.request, deadline=110)
        self.assertEqual(result['error']['code'], 'timeout')
        self.assertEqual(len(self.sent), 5)
        self.assertEqual(self.fixture.calls, [])

    def test_local_manifest_overrun_prevents_next_io(self):
        def manifest(*args):
            self.now += 20
            return self.reader.cm
        with patch('rag.vector.retrieve.read_manifest', side_effect=manifest), \
                patch('rag.vector.retrieve.read_bytes') as selection:
            result = self.reader.retrieve(self.request, deadline=110)
        self.assertEqual(result['error']['code'], 'timeout')
        selection.assert_not_called()
        self.assertEqual(self.sent, [])

    def test_no_deadline_keeps_existing_timeout_and_return_contract(self):
        result = self.reader.retrieve(self.request)
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(len(self.sent), 12)
        self.assertTrue(all(set(budget.values()) == {60.0} for _, budget, _ in self.sent))

    def test_long_budget_does_not_increase_existing_per_operation_cap(self):
        self.assertEqual(self.reader.retrieve(self.request, deadline=280)['status'], 'ok')
        self.assertTrue(all(set(budget.values()) == {60.0} for _, budget, _ in self.sent))

    def test_direct_qdrant_expiry_does_not_enter_transport(self):
        with self.assertRaises(httpx.TimeoutException):
            self.client.server(deadline=self.now)
        with self.assertRaises(httpx.TimeoutException):
            self.client.request('POST', '/collections/test/points/query', {}, deadline=self.now)
        self.assertEqual(self.sent, [])

    def test_pipeline_forwards_deadline_and_maps_retriever_timeout(self):
        incident = json.loads((ROOT / 'datasets/evaluation/soc-eval-v1/inputs/P01.json').read_text())
        policy = json.loads((ROOT / 'datasets/evaluation/soc-eval-v1/protocol/runner-policy.json').read_text())
        generator = Mock()
        pipeline = VectorPipeline(self.reader, generator, ROOT)
        self.transport_error = httpx.ReadTimeout('private socket detail')
        with self.assertRaises(PipelineError) as failure:
            pipeline.investigate(incident, policy, self.request, deadline=110)
        self.assertEqual((failure.exception.code, failure.exception.stage), ('timeout', 'retrieval'))
        generator.generate.assert_not_called()
        self.assertEqual(self.sent[0][1]['read'], 10)


class PipelineDeadlineTests(unittest.TestCase):
    def setUp(self):
        self.fixture = generation_fixtures.GenerationTests()
        self.fixture.setUp()

    def test_success_preserves_deadline_for_retrieval_and_generation(self):
        f = self.fixture
        with patch('rag.generation.pipeline.time.monotonic', return_value=100):
            result, _ = f.pipeline.investigate(f.incident, f.policy, f.request, deadline=110)
        self.assertEqual(result['status'], 'ok')
        f.retriever.retrieve.assert_called_once_with(f.request, deadline=110)
        self.assertEqual(f.generator.generate.call_args.args[2], 110)

    def test_expired_pipeline_deadline_prevents_retrieval(self):
        f = self.fixture
        with patch('rag.generation.pipeline.time.monotonic', return_value=100), \
                self.assertRaises(PipelineError) as failure:
            f.pipeline.investigate(f.incident, f.policy, f.request, deadline=100)
        self.assertEqual((failure.exception.code, failure.exception.stage), ('timeout', 'retrieval'))
        f.retriever.retrieve.assert_not_called()
        f.generator.generate.assert_not_called()

    def test_direct_transport_timeout_uses_pipeline_error(self):
        f = self.fixture
        f.retriever.retrieve.side_effect = httpx.ReadTimeout('private transport detail')
        with self.assertRaises(PipelineError) as failure:
            f.run_pipeline()
        self.assertEqual((failure.exception.code, failure.exception.stage), ('timeout', 'retrieval'))
        self.assertNotIn('private', str(failure.exception))
        f.generator.generate.assert_not_called()

    def test_slow_custom_retriever_cannot_publish_late_success(self):
        f = self.fixture
        clock = [100]
        def retrieve(request, *, deadline):
            self.assertEqual(deadline, 110)
            clock[0] = 111
            return f.response
        f.retriever.retrieve.side_effect = retrieve
        with patch('rag.generation.pipeline.time.monotonic', side_effect=lambda: clock[0]), \
                self.assertRaises(PipelineError) as failure:
            f.pipeline.investigate(f.incident, f.policy, f.request, deadline=110)
        self.assertEqual((failure.exception.code, failure.exception.stage), ('timeout', 'retrieval'))
        f.generator.generate.assert_not_called()

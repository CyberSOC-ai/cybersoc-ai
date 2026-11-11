"""Offline RAG API integration checks with controlled retrieval and generation."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
import time
import unittest

from fastapi.testclient import TestClient
import httpx

from backend.app import Settings, create_app
from backend.repository import SQLiteRepository
from backend.validation import SCHEMA_DIR, validate
from backend.vector_adapter import VectorAPIAdapter
from rag.generation.pipeline import PipelineError, VectorPipeline, quotation_catalogue, render_summary

ROOT = Path(__file__).resolve().parents[2]
INCIDENT = json.loads((SCHEMA_DIR / 'examples/incident.json').read_text())
POLICY = json.loads((ROOT / 'datasets/evaluation/soc-eval-v1/protocol/runner-policy.json').read_text())
EVIDENCE = json.loads((SCHEMA_DIR / 'examples/retrieval-response.json').read_text())['evidence'][0]
EVIDENCE['content'] = 'Boundary. General SSH reference sentence.'
VERSIONS = {'model': 'controlled-test-only', 'prompt': 'vector-test', 'dataset': 'test-fixture',
            'configuration': 'test-fixture', 'commit': 'a' * 40}


class Retrieval:
    def __init__(self, *, status='ok', error_code='dependency_unavailable', block=None,
                 evidence=None):
        self.status, self.error_code, self.block = status, error_code, block
        self.evidence = deepcopy(evidence if evidence is not None else EVIDENCE)
        self.requests = []

    def retrieve(self, request, *, deadline=None):
        self.requests.append((deepcopy(request), deadline))
        if self.block:
            entered, release = self.block
            entered.set()
            release.wait(2)
        response = {'schema_version': '1.0.0', 'request_id': request['request_id'],
                    'trace_id': request['trace_id'], 'status': self.status,
                    'evidence': [] if self.status != 'ok' else [deepcopy(self.evidence)]}
        if self.status == 'error':
            response['error'] = {'code': self.error_code, 'message': 'private detail',
                                 'retryable': True}
        if self.status == 'empty':
            response['status'] = 'ok'
        return response


class Generation:
    def __init__(self, *, answer=None):
        self.answer = answer
        self.deadlines = []

    def generate(self, messages, schema, deadline):
        self.deadlines.append(deadline)
        if self.answer is not None:
            return self.answer, {}
        quotation = schema['properties']['summary']['properties']['quotation_id']['enum'][0]
        return json.dumps({'summary': {'quotation_id': quotation},
                           'triage_verdict': 'undetermined', 'risk_level': 'low',
                           'mitre_techniques': [], 'recommended_actions': []}), {}


class Baseline:
    versions = VERSIONS

    def run(self, request):
        return {'schema_version': '1.0.0', 'incident_id': request.incident['incident_id'],
                'investigation_id': request.investigation_id, 'trace_id': request.trace_id,
                'mode': 'no_rag', 'status': 'ok', 'summary': 'Controlled No-RAG result',
                'triage_verdict': 'undetermined', 'risk_level': 'low', 'evidence': [],
                'mitre_techniques': [], 'recommended_actions': []}


class VectorAPITest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings = Settings(Path(self.temp.name), inference_timeout=1)
        self.repo = SQLiteRepository(self.settings.runtime_dir)

    def adapter(self, retrieval=None, generation=None):
        retrieval = retrieval or Retrieval()
        generation = generation or Generation()
        pipeline = VectorPipeline(retrieval, generation, ROOT)
        return VectorAPIAdapter(pipeline, POLICY, VERSIONS), retrieval, generation

    def client(self, *, baseline=None, vector=None, **settings):
        app = create_app(settings=replace(self.settings, **settings), runner=baseline,
                         vector_runner=vector, repository=self.repo)
        client = TestClient(app, raise_server_exceptions=False)
        self.addCleanup(client.__exit__, None, None, None)
        client.__enter__()
        self.assertIn(client.post('/incidents', json=deepcopy(INCIDENT)).status_code, (200, 201))
        return client

    def rows(self):
        with self.repo.connection() as db:
            return [(json.loads(a), json.loads(b)) for a, b in db.execute(
                'SELECT result, trace FROM investigations ORDER BY rowid')]

    def test_both_modes_are_explicit_and_legacy_empty_body_remains_no_rag(self):
        adapter, retrieval, generation = self.adapter()
        client = self.client(baseline=Baseline(), vector=adapter)
        for body in (None, {}, {'mode': 'no_rag'}):
            response = client.post('/incidents/INC-001/investigate', json=body) if body is not None else client.post('/incidents/INC-001/investigate')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['mode'], 'no_rag')
        response = client.post('/incidents/INC-001/investigate', json={'mode': 'vector_rag'})
        self.assertEqual(response.status_code, 200)
        result = response.json()
        validate('investigation-result', result)
        self.assertEqual(result['mode'], 'vector')
        self.assertEqual(result['evidence'], [EVIDENCE])
        self.assertIn(EVIDENCE['evidence_id'], result['summary'])
        self.assertEqual(len(retrieval.requests), 1)
        request, deadline = retrieval.requests[0]
        validate('retrieval-request', request)
        self.assertEqual(request['query'], INCIDENT['description'])
        self.assertEqual(request['trace_id'], result['trace_id'])
        self.assertEqual(request['top_k'], 5)
        self.assertEqual(deadline, generation.deadlines[0])
        self.assertLessEqual(deadline - time.monotonic(), self.settings.inference_timeout)
        saved, trace = self.rows()[-1]
        self.assertEqual(saved, result)
        validate('trace', trace)
        self.assertEqual(trace['trace_id'], result['trace_id'])
        self.assertEqual(trace['mode'], 'vector')
        self.assertEqual(trace['versions'], VERSIONS)
        self.assertEqual(len(self.rows()), 4)

    def test_rendered_incident_brackets_and_markdown_links_are_preserved(self):
        linked = deepcopy(EVIDENCE)
        linked['content'] = ('Boundary. Consult [SSH guide](https://example.invalid/ssh) '
                             'for general authentication context.')
        cases = (
            ('plain', deepcopy(INCIDENT), deepcopy(EVIDENCE)),
            ('incident-brackets', {**deepcopy(INCIDENT), 'incident_id': 'INC-brackets',
                                   'source_event_id': 'EVT-brackets',
                                   'description': INCIDENT['description'] +
                                   ' Sensor [east-1] reported [7] alerts.'}, deepcopy(EVIDENCE)),
            ('markdown-link', {**deepcopy(INCIDENT), 'incident_id': 'INC-link',
                               'source_event_id': 'EVT-link'}, linked),
        )
        for label, incident, evidence in cases:
            with self.subTest(label=label):
                adapter, _, _ = self.adapter(Retrieval(evidence=evidence))
                client = self.client(vector=adapter)
                if incident['incident_id'] != INCIDENT['incident_id']:
                    self.assertEqual(client.post('/incidents', json=incident).status_code, 201)
                response = client.post(f"/incidents/{incident['incident_id']}/investigate",
                                       json={'mode': 'vector_rag'})
                self.assertEqual(response.status_code, 200)
                result = response.json()
                quote = quotation_catalogue([evidence])[0]
                self.assertEqual(result['summary'], render_summary(
                    incident['description'], quote['excerpt'], evidence['evidence_id']))
                self.assertEqual(result['evidence'], [evidence])
                saved, trace = self.rows()[-1]
                self.assertEqual(saved, result)
                validate('investigation-result', saved)
                validate('trace', trace)
                self.assertEqual(trace['status'], 'ok')
                self.assertEqual(trace['trace_id'], result['trace_id'])

    def test_unknown_and_malformed_vector_citation_markers_still_fail(self):
        class Candidate:
            versions = VERSIONS

            def __init__(self, summary):
                self.summary = summary

            def run(self, request):
                return {'schema_version': '1.0.0', 'incident_id': request.incident['incident_id'],
                        'investigation_id': request.investigation_id,
                        'trace_id': request.trace_id, 'mode': 'vector', 'status': 'ok',
                        'summary': self.summary, 'triage_verdict': 'undetermined',
                        'risk_level': 'low', 'evidence': [deepcopy(EVIDENCE)],
                        'mitre_techniques': [], 'recommended_actions': []}

        valid = f"Reference [sensor-1] [[{EVIDENCE['evidence_id']}]]"
        invalid = (
            'Reference [[UNKNOWN]]',
            f"Reference [[{EVIDENCE['evidence_id']}]",
            f"Reference [[{EVIDENCE['evidence_id']}]] trailing text",
            f"Reference [[bad] [[{EVIDENCE['evidence_id']}]]",
            f"Reference [[{EVIDENCE['evidence_id']}]] [[{EVIDENCE['evidence_id']}]]",
        )
        for summary, status in ((valid, 200), *((value, 502) for value in invalid)):
            with self.subTest(summary=summary):
                client = self.client(vector=Candidate(summary))
                response = client.post('/incidents/INC-001/investigate',
                                       json={'mode': 'vector_rag'})
                self.assertEqual(response.status_code, status)
                saved, trace = self.rows()[-1]
                self.assertEqual(saved, response.json())
                self.assertEqual(trace['trace_id'], saved['trace_id'])
                if status == 502:
                    self.assertEqual(saved['error']['code'], 'invalid_output')
                    self.assertEqual(trace['status'], 'error')
                else:
                    self.assertEqual(trace['status'], 'ok')

    def test_no_rag_summary_brackets_remain_accepted(self):
        class BracketBaseline(Baseline):
            def run(self, request):
                result = super().run(request)
                result['summary'] = 'Observed [sensor-1] and [SSH guide](https://example.invalid).'
                return result

        client = self.client(baseline=BracketBaseline())
        response = client.post('/incidents/INC-001/investigate')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.rows()[-1][0], response.json())
        self.assertEqual(self.rows()[-1][1]['mode'], 'no_rag')

    def test_invalid_modes_and_missing_index_are_sanitized(self):
        client = self.client(baseline=Baseline())
        for body in ({'mode': 'vector'}, {'mode': 1}, {'mode': None},
                     {'mode': ['vector_rag']}, {'mode': 'no_rag', 'top_k': 2}, []):
            with self.subTest(body=body):
                self.assertEqual(client.post('/incidents/INC-001/investigate', json=body).status_code, 422)
        response = client.post('/incidents/INC-001/investigate', json={'mode': 'vector_rag'})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['error']['code'], 'dependency_unavailable')
        self.assertEqual(self.rows(), [])
        self.assertEqual(client.get('/health').json()['model_dependency'], 'configured_not_probed')
        operation = client.get('/openapi.json').json()['paths'][
            '/incidents/{incident_id}/investigate']['post']
        variants = operation['requestBody']['content']['application/json']['schema']['oneOf']
        self.assertEqual(variants[1]['properties']['mode']['enum'], ['no_rag', 'vector_rag'])

    def test_retrieval_query_is_bounded_without_changing_generation_incident(self):
        adapter, retrieval, generation = self.adapter()
        client = self.client(vector=adapter)
        # New event identity keeps the accepted 8,000-character incident contract.
        long_incident = deepcopy(INCIDENT)
        long_incident.update(incident_id='INC-long', source_event_id='EVT-long',
                             description='A' * 5000)
        self.assertEqual(client.post('/incidents', json=long_incident).status_code, 201)
        response = client.post('/incidents/INC-long/investigate', json={'mode': 'vector_rag'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(retrieval.requests[0][0]['query']), 4000)
        self.assertEqual(len(generation.deadlines), 1)
        self.assertIn('A' * 5000, response.json()['summary'])

    def test_retrieval_failures_and_empty_results_never_fall_back(self):
        for retrieval, expected, code in (
            (Retrieval(status='empty'), 502, 'invalid_output'),
            (Retrieval(status='error'), 503, 'dependency_unavailable'),
            (Retrieval(status='error', error_code='timeout'), 504, 'timeout'),
            (Retrieval(status='error', error_code='conflict'), 503, 'dependency_unavailable'),
        ):
            with self.subTest(code=code, status=retrieval.status):
                adapter, _, generator = self.adapter(retrieval)
                client = self.client(vector=adapter)
                response = client.post('/incidents/INC-001/investigate', json={'mode': 'vector_rag'})
                self.assertEqual(response.status_code, expected)
                self.assertEqual(response.json()['error']['code'], code)
                self.assertNotIn('private detail', response.text)
                self.assertEqual(generator.deadlines, [])
                saved, trace = self.rows()[-1]
                self.assertEqual(saved['mode'], 'vector')
                self.assertEqual(saved['status'], 'error')
                self.assertEqual(trace['status'], 'error')
                self.assertEqual(trace['error']['code'], code)

    def test_malformed_generation_and_pipeline_timeout_are_sanitized(self):
        adapter, _, _ = self.adapter(generation=Generation(answer='private invalid output'))
        client = self.client(vector=adapter)
        response = client.post('/incidents/INC-001/investigate', json={'mode': 'vector_rag'})
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()['error']['code'], 'invalid_output')
        self.assertNotIn('private', response.text)
        class TimeoutRetrieval:
            def retrieve(self, request, *, deadline=None):
                raise httpx.TimeoutException('private timeout')
        adapter, _, _ = self.adapter(retrieval=TimeoutRetrieval())
        client = self.client(vector=adapter)
        response = client.post('/incidents/INC-001/investigate', json={'mode': 'vector_rag'})
        self.assertEqual(response.status_code, 504)
        self.assertNotIn('private', response.text)
        self.assertEqual(self.rows()[-1][0]['error']['code'], 'timeout')

    def test_expired_deadline_rejected_before_retrieval(self):
        adapter, retrieval, generation = self.adapter()
        from backend.runner import RunnerRequest, RunnerTimeout
        request = RunnerRequest(deepcopy(INCIDENT), 'INV-expired', 'TRACE-expired',
                                time.monotonic() - 1, 'vector_rag')
        with self.assertRaises(RunnerTimeout):
            adapter.run(request)
        self.assertEqual(retrieval.requests, [])
        self.assertEqual(generation.deadlines, [])

    def test_untrusted_vector_result_must_keep_evidence_and_backend_ids(self):
        class Candidate:
            versions = VERSIONS
            def __init__(self, mutate):
                self.mutate = mutate

            def run(self, request):
                result = {'schema_version': '1.0.0', 'incident_id': request.incident['incident_id'],
                          'investigation_id': request.investigation_id,
                          'trace_id': request.trace_id, 'mode': 'vector', 'status': 'ok',
                          'summary': 'Reference [[EVD-001]]', 'triage_verdict': 'undetermined',
                          'risk_level': 'low', 'evidence': [deepcopy(EVIDENCE)],
                          'mitre_techniques': [], 'recommended_actions': []}
                self.mutate(result)
                return result
        for mutation in (lambda r: r.update(trace_id='wrong'),
                         lambda r: r.update(summary='Uncited claim'),
                         lambda r: r['evidence'].append(deepcopy(EVIDENCE)),
                         lambda r: r['evidence'][0].update(retrieval_method='graph')):
            with self.subTest(mutation=mutation):
                client = self.client(vector=Candidate(mutation))
                response = client.post('/incidents/INC-001/investigate', json={'mode': 'vector_rag'})
                self.assertEqual(response.status_code, 502)
                self.assertEqual(self.rows()[-1][0]['error']['code'], 'invalid_output')

    def test_shared_pool_rejects_second_mode_while_first_is_running(self):
        entered, release = Event(), Event()
        adapter, _, _ = self.adapter(Retrieval(block=(entered, release)))
        client = self.client(baseline=Baseline(), vector=adapter)
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(lambda: client.post('/incidents/INC-001/investigate',
                                                         json={'mode': 'vector_rag'}))
            try:
                self.assertTrue(entered.wait(1))
                response = client.post('/incidents/INC-001/investigate', json={'mode': 'no_rag'})
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json()['error']['code'], 'dependency_unavailable')
            finally:
                release.set()
            self.assertEqual(future.result(timeout=2).status_code, 200)
        self.assertEqual(len(self.rows()), 1)

    def test_pipeline_error_mapping_and_configuration_validation(self):
        adapter, _, _ = self.adapter()
        with self.assertRaises(ValueError):
            VectorAPIAdapter(adapter.pipeline, POLICY, VERSIONS, top_k=True)
        with self.assertRaises(Exception):
            VectorAPIAdapter(adapter.pipeline, POLICY, VERSIONS, filters={'sources': ['unknown']})
        for code, status in [('timeout', 504), ('conflict', 503), ('invalid_output', 502)]:
            class FailingPipeline(VectorPipeline):
                def investigate(self, *args, **kwargs):
                    raise PipelineError(code, 'retrieval')
            failed = VectorAPIAdapter(FailingPipeline(Retrieval(), Generation(), ROOT), POLICY, VERSIONS)
            client = self.client(vector=failed)
            response = client.post('/incidents/INC-001/investigate', json={'mode': 'vector_rag'})
            self.assertEqual(response.status_code, status)

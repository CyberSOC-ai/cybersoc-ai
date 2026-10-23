"""Backend behavior tests; all successful inference here is controlled test data."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from threading import Event
import time
import unittest

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from backend.app import BoundedBody, Settings, create_app
from backend.repository import Conflict, SQLiteRepository
from backend.runner import RunnerRequest, RunnerPool, RunnerBusy, RunnerTimeout, RunnerUnavailable
from backend.validation import SCHEMA_DIR, SCHEMAS, validate

INCIDENT = json.loads((SCHEMA_DIR / 'examples/incident.json').read_text())
ACTION = json.loads((SCHEMA_DIR / 'examples/response-action.json').read_text())
VERSIONS = {'model': 'test-only', 'prompt': 'test-only', 'dataset': 'not_applicable',
            'configuration': 'test-only', 'commit': 'a' * 40}


class ControlledRunner:
    versions = VERSIONS

    def __init__(self, mutate=None, error=None):
        self.mutate, self.error = mutate, error
        self.seen = []

    def run(self, request):
        self.seen.append(request)
        if self.error:
            raise self.error
        result = {'schema_version': '1.0.0', 'incident_id': request.incident['incident_id'],
                  'investigation_id': request.investigation_id, 'trace_id': request.trace_id,
                  'mode': 'no_rag', 'status': 'ok', 'summary': 'Controlled test answer only',
                  'triage_verdict': 'undetermined', 'risk_level': 'low', 'evidence': [],
                  'mitre_techniques': [], 'recommended_actions': []}
        if self.mutate:
            self.mutate(result)
        # Changes must not mutate the repository or backend-owned IDs.
        request.incident['description'] = 'Runner mutation'
        return result


class APITest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings = Settings(Path(self.temp.name))
        self.repo = SQLiteRepository(self.settings.runtime_dir)

    def client(self, runner=None, repository=None, **settings):
        app = create_app(settings=replace(self.settings, **settings), runner=runner,
                         repository=repository or self.repo)
        client = TestClient(app, raise_server_exceptions=False)
        self.addCleanup(client.__exit__, None, None, None)
        client.__enter__()
        return client

    def ingest(self, client, incident=None):
        return client.post('/incidents', json=incident or deepcopy(INCIDENT))

    def investigate(self, client, incident_id='INC-001'):
        return client.post(f'/incidents/{incident_id}/investigate')

    def rows(self):
        with self.repo.connection() as db:
            return [(json.loads(r), json.loads(t)) for r, t in db.execute(
                'SELECT result, trace FROM investigations')]

    def test_health_is_independent_from_unconfigured_inference(self):
        c = self.client()
        self.assertEqual(c.get('/health').json(), {
            'status': 'ok', 'storage': 'ready', 'model_dependency': 'unconfigured',
            'runner_configured': False})
        self.assertEqual(self.ingest(c).status_code, 201)
        response = self.investigate(c)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['error']['code'], 'dependency_unavailable')
        self.assertEqual(self.rows(), [])
        self.assertEqual(self.investigate(c, 'missing').status_code, 404)

    def test_health_does_not_call_or_probe_a_configured_runner(self):
        r = ControlledRunner()
        c = self.client(r)
        self.assertEqual(c.get('/health').json()['model_dependency'], 'configured_not_probed')
        self.assertEqual(r.seen, [])

    def test_strict_validation_without_coercion(self):
        c = self.client()
        mutations = [('schema_version', '2.0.0'), ('timestamp', '2026-02-30T12:00:00Z'),
                     ('timestamp', '2026-10-13T12:00:00+00:00'), ('source_event_id', 123),
                     ('description', 'x' * 8001), ('entities', '[]'), ('extra', 'forbidden'),
                     ('incident_id', 'INC-001\n'), ('source', True), ('severity', 5)]
        for field, value in mutations:
            with self.subTest(field=field, value=str(value)[:20]):
                incident = deepcopy(INCIDENT)
                incident[field] = value
                response = self.ingest(c, incident)
                self.assertEqual(response.status_code, 422)
                if len(str(value)) > 30:
                    self.assertNotIn(str(value), response.text)
        for entities in ([{'type': 'ip', 'value': 'not-ip'}], [{'type': 'domain', 'value': 'bad domain'}]):
            incident = deepcopy(INCIDENT)
            incident['entities'] = entities
            self.assertEqual(self.ingest(c, incident).status_code, 422)
        for raw in ('[]', 'null', '123', '"incident"', '{}'):
            self.assertEqual(c.post('/incidents', content=raw,
                                   headers={'Content-Type': 'application/json'}).status_code, 422)

    def test_malformed_json_and_media_types(self):
        c = self.client()
        for raw in (b'{', b'\xff', b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1,"x":2}',
                    b'[' * 2000 + b']' * 2000, b'{"x":1e999}', b'{"x":"\\ud800"}'):
            with self.subTest(raw=raw[:20]):
                response = c.post('/incidents', content=raw,
                                  headers={'Content-Type': 'application/json'})
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()['error']['code'], 'validation_error')
        self.assertEqual(c.post('/incidents', content='{}').status_code, 415)

    def test_oversized_requests_including_without_content_length(self):
        c = self.client()
        self.assertEqual(c.post('/incidents', content=b'x' * 65537).status_code, 413)
        self.assertEqual(c.post('/incidents', content=iter([b'x' * 40000, b'x' * 40000])).status_code, 413)

    def test_duplicate_event_metadata_and_conflicting_ids(self):
        c = self.client()
        self.assertEqual(self.ingest(c).status_code, 201)
        duplicate = deepcopy(INCIDENT)
        duplicate.update(incident_id='another-delivery-id', ingestion_kind='replay',
                         raw_event_ref='https://example.invalid/never-fetch')
        response = self.ingest(c, duplicate)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['incident_id'], INCIDENT['incident_id'])
        self.assertEqual(self.repo.get('INC-001'), INCIDENT)
        duplicate['description'] = 'changed event content'
        self.assertEqual(self.ingest(c, duplicate).status_code, 409)
        duplicate = deepcopy(INCIDENT)
        duplicate['source_event_id'] = 'NEW-EVENT'
        self.assertEqual(self.ingest(c, duplicate).status_code, 409)
        with self.repo.connection() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM deliveries').fetchone()[0], 2)
        # File-backed state survives construction of a new repository.
        reloaded = SQLiteRepository(self.settings.runtime_dir)
        reloaded.initialize()
        self.assertEqual(reloaded.get('INC-001'), INCIDENT)

    def test_success_is_validated_persisted_and_correlated(self):
        runner = ControlledRunner()
        c = self.client(runner)
        self.ingest(c)
        response = self.investigate(c)
        self.assertEqual(response.status_code, 200)
        result = response.json()
        validate('investigation-result', result)
        self.assertEqual(result['risk_level'], 'low')
        self.assertEqual(self.repo.get('INC-001')['severity'], 'high')
        self.assertEqual(runner.seen[0].incident['description'], 'Runner mutation')
        self.assertEqual(self.repo.get('INC-001'), INCIDENT)
        self.assertGreater(runner.seen[0].deadline_monotonic, time.monotonic())
        saved, trace = self.rows()[0]
        self.assertEqual(saved, result)
        validate('trace', trace)
        self.assertEqual(trace['trace_id'], result['trace_id'])
        self.assertEqual(trace['workflow'], 'baseline')
        self.assertEqual(trace['versions'], VERSIONS)
        self.assertEqual(trace['steps'][0]['status'], 'ok')

    def test_unknown_routes_methods_and_investigation_inputs(self):
        c = self.client()
        self.ingest(c)
        for kwargs, expected in [({'json': {'mode': 'vector'}}, 422),
                                 ({'json': []}, 422), ({'content': '{',
                                 'headers': {'Content-Type': 'application/json'}}, 400)]:
            self.assertEqual(c.post('/incidents/INC-001/investigate', **kwargs).status_code, expected)
        self.assertEqual(c.post('/incidents/INC-001/investigate', json={}).status_code, 503)
        self.assertEqual(self.investigate(c, 'bad%20id').status_code, 422)
        for method, url, status in [('get', '/unknown', 404), ('delete', '/incidents', 405)]:
            response = getattr(c, method)(url)
            self.assertEqual(response.status_code, status)
            self.assertIn('error', response.json())

    def test_runner_exceptions_sanitized_and_durable(self):
        for error, status, code in [(RunnerUnavailable('secret-token'), 503, 'dependency_unavailable'),
                                    (RunnerTimeout('secret-token'), 504, 'timeout'),
                                    (RuntimeError('secret-token'), 502, 'invalid_output')]:
            with self.subTest(code=code):
                c = self.client(ControlledRunner(error=error))
                self.ingest(c)
                response = self.investigate(c)
                self.assertEqual(response.status_code, status)
                self.assertNotIn('secret-token', response.text)
                result, trace = self.rows()[-1]
                validate('investigation-result', result)
                validate('trace', trace)
                self.assertEqual(result['error']['code'], code)
                self.assertEqual(trace['status'], 'error')

    def test_invalid_model_outputs_never_report_success(self):
        def action(result):
            proposal = deepcopy(ACTION)
            proposal['incident_id'] = 'wrong-incident'
            result['recommended_actions'] = [proposal]

        def approved(result):
            proposal = deepcopy(ACTION)
            proposal['status'] = 'approved'
            result['recommended_actions'] = [proposal]

        mutations = [lambda r: r.update(incident_id='another'),
                     lambda r: r.update(trace_id='another'),
                     lambda r: r.update(investigation_id='another'),
                     lambda r: r.update(mode='vector'),
                     lambda r: r.update(summary='sensitive' * 20000),
                     lambda r: r.update(extra='sensitive'),
                     lambda r: r.update(summary='\ud800'),
                     lambda r: r.update(evidence=[{}]), action, approved]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                c = self.client(ControlledRunner(mutate=mutation))
                self.ingest(c)
                response = self.investigate(c)
                self.assertEqual(response.status_code, 502)
                self.assertNotIn('sensitive', response.text)
                self.assertEqual(self.rows()[-1][0]['status'], 'error')

    def test_error_candidate_message_is_not_trusted(self):
        def error(result):
            for key in ('summary', 'triage_verdict', 'risk_level', 'mitre_techniques'):
                del result[key]
            result.update(status='error', error={'code': 'timeout', 'message': 'secret-token',
                                                 'retryable': True})
        c = self.client(ControlledRunner(mutate=error))
        self.ingest(c)
        response = self.investigate(c)
        self.assertEqual(response.status_code, 504)
        self.assertNotIn('secret-token', response.text)

    def test_storage_failure_does_not_report_success(self):
        class Broken(SQLiteRepository):
            def save_investigation(self, result, trace):
                raise sqlite3.OperationalError('secret-path')
        repo = Broken(self.settings.runtime_dir)
        c = self.client(ControlledRunner(), repo)
        self.ingest(c)
        response = self.investigate(c)
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('secret-path', response.text)
        self.assertEqual(response.json()['error']['code'], 'audit_unavailable')
        with repo.connection() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM investigations').fetchone()[0], 0)

    def test_api_timeout_persisted_late_result_discarded_and_health_responsive(self):
        release, finished = Event(), Event()
        class Blocking(ControlledRunner):
            def run(self, request):
                try:
                    release.wait(2)
                    return super().run(request)
                finally:
                    finished.set()
        c = self.client(Blocking(), inference_timeout=.03)
        self.ingest(c)
        try:
            response = self.investigate(c)
            self.assertEqual(response.status_code, 504)
            self.assertEqual(c.get('/health').status_code, 200)
            self.assertEqual(self.investigate(c).status_code, 503)
            self.assertEqual(len(self.rows()), 1)
            self.assertEqual(self.rows()[0][0]['error']['code'], 'timeout')
        finally:
            release.set()
            finished.wait(1)
        self.assertEqual(self.rows()[0][0]['status'], 'error')
        self.assertEqual(len(self.rows()), 1)

    def test_storage_health_failure_sanitized(self):
        class Broken(SQLiteRepository):
            def check(self):
                raise OSError('secret-path')
        c = self.client(repository=Broken(self.settings.runtime_dir))
        response = c.get('/health')
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('secret-path', response.text)

    def test_openapi_contract_refs_are_local_and_complete(self):
        c = self.client()
        document = c.get('/openapi.json').json()
        self.assertEqual(document['openapi'], '3.1.0')
        components = document['components']['schemas']
        for name in SCHEMAS:
            Draft202012Validator.check_schema(components[name])
        def check(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key == '$ref':
                        self.assertTrue(item.startswith('#/'))
                        target = document
                        for part in item[2:].split('/'):
                            target = target[part]
                    else:
                        check(item)
            elif isinstance(value, list):
                for item in value:
                    check(item)
        check(document)
        self.assertIn('201', document['paths']['/incidents']['post']['responses'])
        self.assertIn('503', document['paths']['/incidents/{incident_id}/investigate']['post']['responses'])
        self.assertEqual(c.get('/docs').status_code, 200)


class RepositoryTest(unittest.TestCase):
    def test_concurrent_duplicate_submissions_are_atomic(self):
        with TemporaryDirectory() as directory:
            repo = SQLiteRepository(Path(directory))
            repo.initialize()
            with ThreadPoolExecutor(max_workers=8) as executor:
                outcomes = list(executor.map(lambda _: repo.ingest(deepcopy(INCIDENT)), range(16)))
            self.assertEqual(sum(created for _, created in outcomes), 1)
            with repo.connection() as db:
                self.assertEqual(db.execute('SELECT count(*) FROM incidents').fetchone()[0], 1)
                self.assertEqual(db.execute('SELECT count(*) FROM deliveries').fetchone()[0], 16)
            changed = deepcopy(INCIDENT)
            changed['description'] = 'different'
            with self.assertRaises(Conflict):
                repo.ingest(changed)

    def test_runtime_must_be_private_and_outside_source(self):
        with self.assertRaises(ValueError):
            SQLiteRepository(SCHEMA_DIR.parent).initialize()
        with TemporaryDirectory() as directory:
            root = Path(directory)
            root.chmod(0o755)
            with self.assertRaises(ValueError):
                SQLiteRepository(root).initialize()
            root.chmod(0o700)
            (root / 'cybersoc.sqlite3').symlink_to(root / 'elsewhere')
            with self.assertRaises(ValueError):
                SQLiteRepository(root).initialize()


class PoolTest(unittest.IsolatedAsyncioTestCase):
    async def test_timeout_does_not_release_running_slot(self):
        entered, release, finished = Event(), Event(), Event()
        class Blocking(ControlledRunner):
            def run(self, request):
                entered.set()
                release.wait(2)
                try:
                    return super().run(request)
                finally:
                    finished.set()
        pool = RunnerPool(Blocking(), 1)
        request = RunnerRequest(deepcopy(INCIDENT), 'INV-test', 'TRACE-test', time.monotonic() + .03)
        try:
            with self.assertRaises(RunnerTimeout):
                await pool.run(request)
            self.assertTrue(entered.is_set())
            with self.assertRaises(RunnerBusy):
                await pool.run(request)
            release.set()
            await asyncio.to_thread(finished.wait, 1)
            result = await pool.run(replace(request, deadline_monotonic=time.monotonic() + 1))
            self.assertEqual(result['status'], 'ok')
        finally:
            release.set()
            pool.close()

    async def test_cancellation_preserves_capacity_bound(self):
        release, entered = Event(), Event()
        class Blocking(ControlledRunner):
            def run(self, request):
                entered.set()
                release.wait(2)
                return super().run(request)
        pool = RunnerPool(Blocking(), 1)
        request = RunnerRequest(deepcopy(INCIDENT), 'INV-test', 'TRACE-test', time.monotonic() + 1)
        try:
            task = asyncio.create_task(pool.run(request))
            await asyncio.to_thread(entered.wait, 1)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            with self.assertRaises(RunnerBusy):
                await pool.run(request)
        finally:
            release.set()
            pool.close()

    async def test_streaming_body_limits_and_body_timeout(self):
        called = []
        async def downstream(scope, receive, send):
            called.append(True)
        scope = {'type': 'http', 'headers': [], 'method': 'POST', 'path': '/incidents'}
        async def exercise(receive, expected):
            sent = []
            async def send(message):
                sent.append(message)
            await BoundedBody(downstream, 4, .02)(scope, receive, send)
            self.assertEqual(sent[0]['status'], expected)
            self.assertEqual(called, [])
        chunks = iter([b'abc', b'def'])
        async def stream():
            return {'type': 'http.request', 'body': next(chunks), 'more_body': True}
        await exercise(stream, 413)
        async def stalled():
            await asyncio.sleep(1)
        await exercise(stalled, 408)

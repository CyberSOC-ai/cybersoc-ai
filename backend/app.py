"""Loopback development API with strict contracts and durable local storage."""
import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import time
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from jsonschema import ValidationError
from starlette.exceptions import HTTPException
from starlette.concurrency import run_in_threadpool

from backend.repository import Conflict, Repository, SQLiteRepository
from backend.runner import (BaselineRunner, RunnerBusy, RunnerPool, RunnerRequest,
                            RunnerTimeout, RunnerUnavailable)
from backend.validation import (ID_VALIDATOR, SCHEMAS, VERSIONS_VALIDATOR,
                                public_schema, validate)


@dataclass(frozen=True)
class Settings:
    runtime_dir: Path
    max_body_bytes: int = 65536
    max_output_bytes: int = 131072
    inference_timeout: float = 30.0
    body_timeout: float = 5.0
    inference_concurrency: int = 1

    def __post_init__(self):
        if not all(math.isfinite(v) and 0 < v <= 300
                   for v in (self.inference_timeout, self.body_timeout)):
            raise ValueError('Timeouts must be finite and between 0 and 300 seconds')
        if not 1 <= self.inference_concurrency <= 8:
            raise ValueError('Concurrency must be between 1 and 8')
        if not all(1 <= v <= 1048576 for v in (self.max_body_bytes, self.max_output_bytes)):
            raise ValueError('Body limits must be between 1 byte and 1 MiB')


class APIError(Exception):
    def __init__(self, status, code, message, retryable=False):
        self.status = status
        self.error = {'code': code, 'message': message, 'retryable': retryable}


def error_response(status, code, message, retryable=False):
    return JSONResponse({'error': {'code': code, 'message': message,
                                   'retryable': retryable}}, status_code=status)


class BoundedBody:
    """Enforce actual streamed bytes, not just the untrusted Content-Length."""
    def __init__(self, app, max_bytes, timeout):
        self.app, self.max_bytes, self.timeout = app, max_bytes, timeout

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        lengths = [v for k, v in scope['headers'] if k.lower() == b'content-length']
        if lengths:
            if len(lengths) != 1 or len(lengths[0]) > 20 or not lengths[0].isdigit():
                return await error_response(400, 'validation_error',
                                            'Invalid request framing.')(scope, receive, send)
            if int(lengths[0]) > self.max_bytes:
                return await error_response(413, 'validation_error',
                                            'Request body exceeds the size limit.')(scope, receive, send)
        body = bytearray()
        try:
            async with asyncio.timeout(self.timeout):
                while True:
                    message = await receive()
                    if message['type'] == 'http.disconnect':
                        return
                    chunk = message.get('body', b'')
                    if len(body) + len(chunk) > self.max_bytes:
                        return await error_response(413, 'validation_error',
                                                    'Request body exceeds the size limit.')(
                                                        scope, receive, send)
                    body.extend(chunk)
                    if not message.get('more_body', False):
                        break
        except TimeoutError:
            return await error_response(408, 'timeout', 'Request body deadline exceeded.')(
                scope, receive, send)
        if lengths and int(lengths[0]) != len(body):
            return await error_response(400, 'validation_error',
                                        'Invalid request framing.')(scope, receive, send)
        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {'type': 'http.request', 'body': bytes(body), 'more_body': False}
            return await receive()
        await self.app(scope, replay, send)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON member')
        result[key] = value
    return result


def invalid_constant(value):
    raise ValueError('Non-finite JSON number')


async def read_json(request, allow_empty=False):
    raw = await request.body()
    if not raw and allow_empty:
        return {}
    media_type = request.headers.get('content-type', '').split(';', 1)[0].strip().lower()
    if media_type != 'application/json':
        raise APIError(415, 'validation_error', 'Content-Type must be application/json.')
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=unique_object,
                           parse_constant=invalid_constant)
        pending = [(value, 0)]
        while pending:
            item, depth = pending.pop()
            if depth > 32 or (isinstance(item, float) and not math.isfinite(item)):
                raise ValueError('JSON nesting or number limit')
            if isinstance(item, str):
                item.encode('utf-8')
            if isinstance(item, dict):
                pending.extend((v, depth + 1) for v in item.values())
            elif isinstance(item, list):
                pending.extend((v, depth + 1) for v in item)
        return value
    except (ValueError, UnicodeError, RecursionError):
        raise APIError(400, 'validation_error', 'Malformed JSON body.') from None


async def stored(call, *args):
    try:
        return await run_in_threadpool(call, *args)
    except Conflict:
        raise APIError(409, 'conflict', 'Incident identity conflicts with stored content.') from None
    except Exception:
        raise APIError(503, 'audit_unavailable', 'Persistent storage is unavailable.', True) from None


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def check_candidate(candidate, invocation, limit):
    # Bound serialization and validate shape before using any candidate fields.
    if len(json.dumps(candidate, allow_nan=False, ensure_ascii=False).encode('utf-8')) > limit:
        raise ValueError('Candidate size limit')
    validate('investigation-result', candidate)
    if (candidate['incident_id'] != invocation.incident['incident_id']
            or candidate['investigation_id'] != invocation.investigation_id
            or candidate['trace_id'] != invocation.trace_id
            or candidate['mode'] != 'no_rag'):
        raise ValueError('Candidate identity mismatch')
    actions = candidate['recommended_actions']
    if len({a['action_id'] for a in actions}) != len(actions):
        raise ValueError('Repeated action identity')
    if any(a['incident_id'] != candidate['incident_id'] for a in actions):
        raise ValueError('Action identity mismatch')


def create_app(*, settings: Settings | None = None, runner: BaselineRunner | None = None,
               repository: Repository | None = None) -> FastAPI:
    settings = settings or Settings(Path(os.environ.get(
        'CYBERSOC_RUNTIME_DIR', f'/tmp/cybersoc-ai-{os.getuid()}')))
    repository = repository if repository is not None else SQLiteRepository(settings.runtime_dir)
    versions = deepcopy(runner.versions) if runner is not None else None
    if versions is not None:
        VERSIONS_VALIDATOR.validate(versions)
    pool = None

    @asynccontextmanager
    async def lifespan(app):
        nonlocal pool
        await run_in_threadpool(repository.initialize)
        pool = RunnerPool(runner, settings.inference_concurrency) if runner is not None else None
        try:
            yield
        finally:
            if pool is not None:
                pool.close()

    app = FastAPI(title='CyberSOC AI — Sprint 1 API', version='0.1.0',
                  description='Local development API. Inference is unavailable unless a real '
                              'runner is injected. All response actions are proposals only.',
                  lifespan=lifespan)
    app.add_middleware(BoundedBody, max_bytes=settings.max_body_bytes,
                       timeout=settings.body_timeout)

    @app.exception_handler(APIError)
    async def api_error(request, exc):
        return JSONResponse({'error': exc.error}, status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def request_error(request, exc):
        return error_response(422, 'validation_error', 'Request does not match the API schema.')

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return error_response(exc.status_code, 'validation_error',
                              'Resource not found.' if exc.status_code == 404 else 'Request rejected.')

    @app.get('/health', summary='API/storage health, separate from runner configuration')
    async def health():
        await stored(repository.check)
        return {'status': 'ok', 'storage': 'ready',
                'model_dependency': 'configured_not_probed' if runner is not None else 'unconfigured',
                'runner_configured': runner is not None}

    @app.post('/incidents', summary='Validate and atomically store a normalized incident')
    async def ingest(request: Request):
        incident = await read_json(request)
        if isinstance(incident, dict) and 'schema_version' in incident:
            if incident['schema_version'] != '1.0.0':
                raise APIError(422, 'unsupported_version', 'Unsupported incident schema version.')
        try:
            validate('incident', incident)
        except ValidationError:
            raise APIError(422, 'validation_error', 'Incident does not match the v1 contract.') from None
        existing, created = await stored(repository.ingest, incident)
        return JSONResponse({'schema_version': '1.0.0', 'incident_id': existing['incident_id'],
                             'created': created}, status_code=201 if created else 200)

    @app.post('/incidents/{incident_id}/investigate', summary='Run a bounded No-RAG investigation')
    async def investigate(incident_id: str, request: Request):
        try:
            ID_VALIDATOR.validate(incident_id)
        except ValidationError:
            raise APIError(422, 'validation_error', 'Invalid incident identifier.') from None
        if await read_json(request, allow_empty=True) != {}:
            raise APIError(422, 'validation_error', 'Investigation body must be empty or {}.')
        incident = await stored(repository.get, incident_id)
        if incident is None:
            raise APIError(404, 'validation_error', 'Incident not found.')
        if pool is None:
            raise APIError(503, 'dependency_unavailable', 'No baseline runner is configured.', True)
        invocation = RunnerRequest(incident, 'INV-' + uuid4().hex, 'TRACE-' + uuid4().hex,
                                   time.monotonic() + settings.inference_timeout)
        started, clock = utc_now(), time.monotonic()
        failure, status = None, 200
        try:
            candidate = await pool.run(invocation)
            check_candidate(candidate, invocation, settings.max_output_bytes)
            if candidate['status'] == 'error':
                code = candidate['error']['code']
                if code == 'dependency_unavailable':
                    raise RunnerUnavailable()
                if code == 'timeout':
                    raise RunnerTimeout()
                raise ValueError('Runner reported failure')
            result = deepcopy(candidate)
        except RunnerBusy:
            raise APIError(503, 'dependency_unavailable', 'Baseline runner is busy.', True) from None
        except RunnerUnavailable:
            failure = {'code': 'dependency_unavailable', 'message': 'Baseline runner is unavailable.',
                       'retryable': True}
            status = 503
        except RunnerTimeout:
            failure = {'code': 'timeout', 'message': 'Baseline inference deadline exceeded.',
                       'retryable': True}
            status = 504
        except Exception:
            failure = {'code': 'invalid_output', 'message': 'Baseline runner returned no valid result.',
                       'retryable': False}
            status = 502
        if failure:
            result = {'schema_version': '1.0.0', 'investigation_id': invocation.investigation_id,
                      'incident_id': incident_id, 'trace_id': invocation.trace_id, 'mode': 'no_rag',
                      'status': 'error', 'evidence': [], 'recommended_actions': [], 'error': failure}
        step = {'step': 1, 'component': 'inference', 'input_ref': f'incident:{incident_id}',
                'status': result['status'], 'latency_ms': (time.monotonic() - clock) * 1000}
        if failure:
            step['error'] = failure
        else:
            step['output_ref'] = f'investigation:{invocation.investigation_id}'
        trace = {'schema_version': '1.0.0', 'trace_id': invocation.trace_id,
                 'incident_id': incident_id, 'workflow': 'baseline', 'mode': 'no_rag',
                 'versions': versions, 'started_at': started, 'finished_at': utc_now(),
                 'status': result['status'], 'steps': [step]}
        if failure:
            trace['error'] = failure
        validate('investigation-result', result)
        validate('trace', trace)
        await stored(repository.save_investigation, result, trace)
        return JSONResponse(result, status_code=status)

    def openapi():
        if app.openapi_schema:
            return app.openapi_schema
        document = get_openapi(title=app.title, version=app.version,
                               description=app.description, routes=app.routes)
        components = document.setdefault('components', {}).setdefault('schemas', {})
        components.update({name: public_schema(name) for name in SCHEMAS})
        components['APIError'] = {'type': 'object', 'required': ['error'],
                                  'additionalProperties': False,
                                  'properties': {'error': {'$ref': '#/components/schemas/common/$defs/error'}}}
        components['IncidentReceipt'] = {
            'type': 'object', 'additionalProperties': False,
            'required': ['schema_version', 'incident_id', 'created'],
            'properties': {'schema_version': {'const': '1.0.0'},
                           'incident_id': {'$ref': '#/components/schemas/common/$defs/id'},
                           'created': {'type': 'boolean'}}}
        for path, methods in document['paths'].items():
            for method, operation in methods.items():
                if method not in {'get', 'post'}:
                    continue
                operation['responses'] = {}
                errors = [400, 408, 413, 503]
                if method == 'post':
                    errors += [404, 409, 415, 422, 502, 504]
                for code in errors:
                    schema = {'$ref': '#/components/schemas/APIError'}
                    if path.endswith('/investigate') and code in {502, 503, 504}:
                        schema = {'oneOf': [schema, {'$ref': '#/components/schemas/investigation-result'}]}
                    error_codes = {409: 'conflict', 408: 'timeout', 504: 'timeout',
                                   502: 'invalid_output', 503: 'dependency_unavailable'}
                    operation['responses'][str(code)] = {
                        'description': 'Sanitized error; no input or exception details',
                        'content': {'application/json': {'schema': schema,
                                    'example': {'error': {'code': error_codes.get(code, 'validation_error'),
                                                          'message': 'Request could not be completed.',
                                                          'retryable': code in {503, 504}}}}}}
                if path == '/health':
                    success_schema = {'type': 'object', 'properties': {
                        'status': {'const': 'ok'}, 'storage': {'const': 'ready'},
                        'model_dependency': {'enum': ['unconfigured', 'configured_not_probed']},
                        'runner_configured': {'type': 'boolean'}},
                        'required': ['status', 'storage', 'model_dependency', 'runner_configured'],
                        'additionalProperties': False}
                else:
                    name = 'investigation-result' if path.endswith('/investigate') else 'IncidentReceipt'
                    success_schema = {'$ref': f'#/components/schemas/{name}'}
                for code in ([200, 201] if path == '/incidents' else [200]):
                    operation['responses'][str(code)] = {
                        'description': 'Validated result',
                        'content': {'application/json': {'schema': success_schema}}}
                if path == '/incidents':
                    operation['requestBody'] = {'required': True, 'content': {'application/json': {
                        'schema': {'$ref': '#/components/schemas/incident'},
                        'example': json.loads((Path(__file__).parent / 'contracts/v1/examples/incident.json').read_text())}}}
                elif path.endswith('/investigate'):
                    operation['requestBody'] = {'required': False, 'content': {'application/json': {
                        'schema': {'type': 'object', 'additionalProperties': False}, 'example': {}}}}
        app.openapi_schema = document
        return document
    app.openapi = openapi
    return app

"""Trusted composition adapter for the experimental Vector-RAG pipeline."""

from copy import deepcopy
from uuid import uuid4

from ai.baseline.runner import RunnerTimeout as CoreTimeout
from ai.baseline.runner import RunnerUnavailable as CoreUnavailable
from backend.runner import RunnerInvalidOutput, RunnerRequest, RunnerTimeout, RunnerUnavailable
from backend.validation import VERSIONS_VALIDATOR, validate
from rag.generation.pipeline import PipelineError, VectorPipeline


class VectorAPIAdapter:
    """Reuse one preloaded pipeline; construct only a bounded request per call."""

    def __init__(self, pipeline: VectorPipeline, policy: dict, versions: dict,
                 *, top_k: int = 5, filters: dict | None = None):
        if not isinstance(pipeline, VectorPipeline):
            raise TypeError('Expected a configured VectorPipeline')
        if type(top_k) is not int or not 1 <= top_k <= 100:
            raise ValueError('top_k must be an integer between 1 and 100')
        from ai.baseline.runner import BaselineRunner
        BaselineRunner._check_policy(policy)
        VERSIONS_VALIDATOR.validate(versions)
        self.pipeline = pipeline
        self.policy = deepcopy(policy)
        self.versions = deepcopy(versions)
        self.top_k = top_k
        self.filters = deepcopy(filters if filters is not None else {})
        validate('retrieval-request', {
            'schema_version': '1.0.0', 'request_id': 'RET-config', 'trace_id': 'TRACE-config',
            'mode': 'vector', 'query': 'configuration check', 'top_k': top_k,
            'filters': self.filters,
        })

    def run(self, request: RunnerRequest) -> dict:
        if request.mode != 'vector_rag':
            raise RunnerInvalidOutput()
        retrieval_request = {
            'schema_version': '1.0.0', 'request_id': 'RET-' + uuid4().hex,
            'trace_id': request.trace_id, 'mode': 'vector',
            'query': request.incident['description'][:4000],
            'top_k': self.top_k, 'filters': deepcopy(self.filters),
        }
        validate('retrieval-request', retrieval_request)
        try:
            result, _ = self.pipeline.investigate(
                request.incident, self.policy, retrieval_request,
                investigation_id=request.investigation_id,
                deadline=request.deadline_monotonic,
            )
            return result
        except PipelineError as exc:
            if exc.code == 'timeout':
                raise RunnerTimeout() from exc
            if exc.code in {'dependency_unavailable', 'conflict'}:
                raise RunnerUnavailable() from exc
            raise RunnerInvalidOutput() from exc
        except CoreTimeout as exc:
            raise RunnerTimeout() from exc
        except CoreUnavailable as exc:
            raise RunnerUnavailable() from exc

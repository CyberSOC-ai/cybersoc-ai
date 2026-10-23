"""Bounded execution of the proposed S1-T03 adapter; no model implementation."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import dataclass
from threading import BoundedSemaphore
import time
from typing import Protocol


class RunnerUnavailable(Exception):
    pass


class RunnerTimeout(Exception):
    pass


class RunnerBusy(Exception):
    pass


@dataclass(frozen=True)
class RunnerRequest:
    incident: dict
    investigation_id: str
    trace_id: str
    deadline_monotonic: float


class BaselineRunner(Protocol):
    versions: dict[str, str]

    def run(self, request: RunnerRequest) -> dict: ...


class RunnerPool:
    def __init__(self, runner: BaselineRunner, concurrency: int):
        self.runner = runner
        self.slots = BoundedSemaphore(concurrency)
        self.executor = ThreadPoolExecutor(max_workers=concurrency,
                                           thread_name_prefix='baseline')

    async def run(self, request: RunnerRequest):
        if not self.slots.acquire(blocking=False):
            raise RunnerBusy()

        def invoke():
            try:
                return self.runner.run(deepcopy(request))
            finally:
                self.slots.release()
        try:
            future = self.executor.submit(invoke)
        except BaseException:
            self.slots.release()
            raise
        # shield prevents timeout/cancellation from cancelling the underlying call.
        wrapped = asyncio.wrap_future(future)
        wrapped.add_done_callback(lambda done: None if done.cancelled() else done.exception())
        try:
            return await asyncio.wait_for(asyncio.shield(wrapped),
                                          max(0, request.deadline_monotonic - time.monotonic()))
        except TimeoutError as exc:
            raise RunnerTimeout() from exc

    def close(self):
        self.executor.shutdown(wait=False, cancel_futures=True)

"""Optional adapter for Oussama's proposed S1-T04 interface (PR #79).

Backend imports are deferred: that PR is not required for pilot/CLI use.
"""

from copy import deepcopy
import re
from pathlib import Path

from .runner import RunnerTimeout, RunnerUnavailable


class APIAdapter:
    def __init__(self, core, policy, versions):
        if set(versions) != {"model", "prompt", "dataset", "configuration", "commit"}:
            raise ValueError("Five trace version keys are required")
        if (any(not isinstance(v, str) or not v or len(v) > 256 for v in versions.values())
                or not re.fullmatch(r"[0-9a-f]{40}", versions["commit"])):
            raise ValueError("Trace versions need nonempty values and a full commit SHA")
        self.core, self.policy, self.versions = core, deepcopy(policy), deepcopy(versions)

    def run(self, request):
        from backend.runner import RunnerTimeout as APITimeout, RunnerUnavailable as APIUnavailable

        try:
            return self.core.investigate(request.incident, self.policy,
                investigation_id=request.investigation_id, trace_id=request.trace_id,
                deadline=request.deadline_monotonic)[0]
        except RunnerTimeout as exc:
            raise APITimeout() from exc
        except RunnerUnavailable as exc:
            raise APIUnavailable() from exc


def compose_api(core, policy, versions, runtime_dir, *, timeout_seconds=180):
    """Compose the reviewed local dependencies with S1-T04's actual factory.

    The caller owns model loading/lifecycle outside HTTP handlers. Explicit
    settings also avoid the backend snapshot's POSIX-only default runtime path
    on Windows. This exposes no server; a host must bind only to loopback.
    """
    from backend.app import Settings, create_app

    core._check_policy(policy)
    adapter = APIAdapter(core, policy, versions)
    return create_app(settings=Settings(Path(runtime_dir), inference_timeout=timeout_seconds,
                                       inference_concurrency=1), runner=adapter)

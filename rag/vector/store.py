"""Small REST adapter for the pinned, local Qdrant server."""

from urllib.parse import urlsplit
import math
import re
import time

import httpx

from rag.ingestion.core import IngestionError


def remaining_time(deadline):
    """Check a shared monotonic deadline without changing client-wide settings."""
    if deadline is None:
        return None
    if not math.isfinite(deadline):
        raise ValueError("Expected a finite monotonic deadline")
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise httpx.TimeoutException("Retrieval deadline exceeded")
    return remaining


def timeout_options(deadline):
    if deadline is None:
        return {}  # Preserve the existing client timeout for non-deadline callers.
    return {"timeout": httpx.Timeout(min(60.0, remaining_time(deadline)))}


class Qdrant:
    def __init__(self, endpoint="http://127.0.0.1:6333", *, transport=None):
        url = urlsplit(endpoint)
        if (url.scheme != "http" or url.hostname not in {"127.0.0.1", "localhost", "::1"} or
                url.username or url.password or url.path not in {"", "/"} or url.query or url.fragment):
            raise IngestionError("Use a local loopback Qdrant HTTP endpoint")
        self.client = httpx.Client(base_url=endpoint.rstrip("/"), timeout=60, trust_env=False,
                                   transport=transport)

    def close(self):
        self.client.close()

    def request(self, method, path, data=None, *, missing=False, deadline=None):
        response = self.client.request(method, path, json=data, **timeout_options(deadline))
        remaining_time(deadline)
        if missing and response.status_code == 404:
            return None
        if response.status_code != 200:
            raise IngestionError(f"Qdrant {method} failed with HTTP {response.status_code}")
        value = response.json()
        remaining_time(deadline)
        if value.get("status") != "ok" or "result" not in value:
            raise IngestionError("Invalid Qdrant response")
        return value["result"]

    def server(self, *, deadline=None):
        response = self.client.get("/", **timeout_options(deadline))
        remaining_time(deadline)
        if response.status_code != 200 or response.json().get("version") != "1.20.0":
            raise IngestionError("Expected Qdrant server version 1.20.0")
        value = response.json()
        remaining_time(deadline)
        return value

    @staticmethod
    def path(name):
        if not re.fullmatch(r"(?:knowledge|soc_history)_[a-f0-9]{64}", name):
            raise IngestionError("Invalid versioned collection name")
        return "/collections/" + name

    def info(self, name, *, deadline=None):
        return self.request("GET", self.path(name), missing=True,
                            **({"deadline": deadline} if deadline is not None else {}))

    def create(self, name, config, metadata):
        self.request("PUT", self.path(name), {**config, "metadata": metadata})

    def field_index(self, name, field, kind):
        self.request("PUT", self.path(name) + "/index?wait=true",
                     {"field_name": field, "field_schema": kind})

    def upsert(self, name, points):
        result = self.request("PUT", self.path(name) + "/points?wait=true", {"points": points})
        if result.get("status") != "completed":
            raise IngestionError("Point write did not complete")

    def count(self, name, filters=None, *, deadline=None):
        data = {"exact": True}
        if filters is not None:
            data["filter"] = filters
        return self.request("POST", self.path(name) + "/points/count", data,
                            **({"deadline": deadline} if deadline is not None else {}))["count"]

    def points(self, name, ids):
        return self.request("POST", self.path(name) + "/points",
                            {"ids": ids, "with_payload": True, "with_vector": True})

    def ready(self, name, metadata):
        self.request("PATCH", self.path(name), {"metadata": {**metadata, "state": "ready"}})


def matches(field, value):
    return {"must": [{"key": field, "match": {"value": value}}]}

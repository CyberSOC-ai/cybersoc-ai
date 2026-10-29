"""Small REST adapter for the pinned, local Qdrant server."""

from urllib.parse import urlsplit
import re

import httpx

from rag.ingestion.core import IngestionError


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

    def request(self, method, path, data=None, *, missing=False):
        response = self.client.request(method, path, json=data)
        if missing and response.status_code == 404:
            return None
        if response.status_code != 200:
            raise IngestionError(f"Qdrant {method} failed with HTTP {response.status_code}")
        value = response.json()
        if value.get("status") != "ok" or "result" not in value:
            raise IngestionError("Invalid Qdrant response")
        return value["result"]

    def server(self):
        response = self.client.get("/")
        if response.status_code != 200 or response.json().get("version") != "1.20.0":
            raise IngestionError("Expected Qdrant server version 1.20.0")
        return response.json()

    @staticmethod
    def path(name):
        if not re.fullmatch(r"(?:knowledge|soc_history)_[a-f0-9]{64}", name):
            raise IngestionError("Invalid versioned collection name")
        return "/collections/" + name

    def info(self, name):
        return self.request("GET", self.path(name), missing=True)

    def create(self, name, config, metadata):
        self.request("PUT", self.path(name), {**config, "metadata": metadata})

    def field_index(self, name, field, kind):
        self.request("PUT", self.path(name) + "/index?wait=true",
                     {"field_name": field, "field_schema": kind})

    def upsert(self, name, points):
        result = self.request("PUT", self.path(name) + "/points?wait=true", {"points": points})
        if result.get("status") != "completed":
            raise IngestionError("Point write did not complete")

    def count(self, name, filters=None):
        data = {"exact": True}
        if filters is not None:
            data["filter"] = filters
        return self.request("POST", self.path(name) + "/points/count", data)["count"]

    def points(self, name, ids):
        return self.request("POST", self.path(name) + "/points",
                            {"ids": ids, "with_payload": True, "with_vector": True})

    def ready(self, name, metadata):
        self.request("PATCH", self.path(name), {"metadata": {**metadata, "state": "ready"}})


def matches(field, value):
    return {"must": [{"key": field, "match": {"value": value}}]}

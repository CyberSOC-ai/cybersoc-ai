"""Validate self-contained graph batches offline; never connect to Neo4j."""
import argparse
from datetime import datetime
import hashlib
import ipaddress
import json
from pathlib import Path
import re

from jsonschema import Draft202012Validator, FormatChecker, ValidationError
from referencing import Registry

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "knowledge-graph"
ONTOLOGY = json.loads((ASSETS / "schema/ontology-v1.json").read_text(encoding="utf-8"))
SCHEMA = json.loads((ASSETS / "schema/graph-batch.schema.json").read_text(encoding="utf-8"))


def reject_network(uri):
    raise ValueError("Remote schema resolution is disabled")


VALIDATOR = Draft202012Validator(
    SCHEMA, format_checker=FormatChecker(), registry=Registry(retrieve=reject_network))


def identity(parts):
    """Hash an ordered array; no trimming, case folding or implicit normalization."""
    payload = json.dumps(parts, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return "KG-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def node_uid(label, properties):
    fields = ONTOLOGY["node_types"][label]["identity_fields"]
    return identity(["node", label, *[properties[field] for field in fields]])


def relationship_uid(kind, start, end, source_record_uid):
    return identity(["relationship", kind, start, end, source_record_uid])


def check_interval(properties):
    if "valid_from" in properties and "valid_until" in properties:
        if datetime.fromisoformat(properties["valid_until"]) < datetime.fromisoformat(properties["valid_from"]):
            raise ValueError("valid_until precedes valid_from")


def check_indicator(properties):
    kind, value = properties["indicator_type"], properties["value"]
    if kind in {"ipv4", "ipv6"}:
        address = ipaddress.ip_address(value)
        if address.version != int(kind[-1]) or str(address) != value:
            raise ValueError("Indicator IP must be canonical and match its type")
    elif kind in {"md5", "sha1", "sha256"}:
        size = {"md5": 32, "sha1": 40, "sha256": 64}[kind]
        if not re.fullmatch("[a-f0-9]{" + str(size) + "}", value):
            raise ValueError("Indicator hash must be lowercase hexadecimal of the declared length")
    else:
        # v1 supports lowercase ASCII DNS names without trailing dot, wildcards or URLs.
        if (len(value) > 253 or value != value.lower()
                or not all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", part)
                           for part in value.split("."))):
            raise ValueError("Indicator domain must be a canonical ASCII DNS name")
    check_interval(properties)


def validate_batch(batch):
    """Validate shape, identities, endpoint types and provenance inside one batch.

    Does not establish factual truth, corpus eligibility or upstream authenticity.
    ETL must apply existing split policies and verify source bytes before calling.
    """
    VALIDATOR.validate(batch)
    nodes = {}
    for node in batch["nodes"]:
        uid, label, properties = node["uid"], node["label"], node["properties"]
        if uid in nodes:
            raise ValueError("Duplicate node uid")
        if uid != node_uid(label, properties):
            raise ValueError("Node uid differs from canonical identity")
        if any(isinstance(value, str) and value != value.strip() for value in properties.values()):
            raise ValueError("Properties must not have leading or trailing whitespace")
        if label == "IPAddress":
            address = ipaddress.ip_address(properties["address"])
            if address.version != properties["version"] or str(address) != properties["address"]:
                raise ValueError("IP address must be canonical and match its version")
        if label == "ThreatIndicator":
            check_indicator(properties)
        nodes[uid] = node
    for node in nodes.values():
        for source_uid in node.get("source_record_uids", []):
            if source_uid not in nodes or nodes[source_uid]["label"] != "SourceRecord":
                raise ValueError("Node provenance must resolve to SourceRecord")
    seen_edges = set()
    for edge in batch["relationships"]:
        uid, kind = edge["uid"], edge["type"]
        if uid in seen_edges or uid in nodes:
            raise ValueError("Duplicate relationship uid or node/relationship collision")
        seen_edges.add(uid)
        start, end, source = edge["from_uid"], edge["to_uid"], edge["source_record_uid"]
        if any(key not in nodes for key in (start, end, source)):
            raise ValueError("Unresolved relationship endpoint or provenance")
        if nodes[source]["label"] != "SourceRecord":
            raise ValueError("Relationship provenance must resolve to SourceRecord")
        if uid != relationship_uid(kind, start, end, source):
            raise ValueError("Relationship uid differs from canonical identity")
        rule = ONTOLOGY["relationship_types"][kind]
        if nodes[start]["label"] not in rule["from"] or nodes[end]["label"] not in rule["to"]:
            raise ValueError("Forbidden relationship endpoint labels")
        if start == end:
            raise ValueError("Self relationships are not allowed in v1")
        if kind == "REFERS_TO_IP":
            indicator, address = nodes[start]["properties"], nodes[end]["properties"]
            if (indicator["indicator_type"] != "ipv" + str(address["version"])
                    or indicator["value"] != address["address"]):
                raise ValueError("Indicator and target IP differ")
        if kind == "SUBTECHNIQUE_OF":
            child, parent = nodes[start]["properties"], nodes[end]["properties"]
            if (child["attack_domain"] != parent["attack_domain"]
                    or "." not in child["technique_id"]
                    or child["technique_id"].split(".")[0] != parent["technique_id"]):
                raise ValueError("Invalid subtechnique parent")
        check_interval(edge["properties"])
    return batch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch", type=Path)
    args = parser.parse_args()
    try:
        batch = validate_batch(json.loads(args.batch.read_text(encoding="utf-8")))
    except (ValueError, OSError) as exc:
        parser.exit(1, f"Invalid graph batch: {exc}\n")
    except ValidationError as exc:
        parser.exit(1, f"Invalid graph batch: {exc.message}\n")
    print(f"Graph batch valid: {len(batch['nodes'])} nodes, {len(batch['relationships'])} relationships")


if __name__ == "__main__":
    main()

"""Normalize upstream formats without downloading or following source links."""

import re
import xml.etree.ElementTree as ET

from backend.validation import validate as validate_contract

from .core import IngestionError, canonical, digest, parse_json, record, text, validate


def english(items):
    return " ".join(text(item["value"]) for item in items if item.get("lang") == "en")


def attack(data, snapshot):
    bundle = parse_json(data)
    if bundle.get("type") != "bundle" or not isinstance(bundle.get("objects"), list):
        raise IngestionError("Expected a STIX bundle")
    inactive = {item["id"] for item in bundle["objects"]
                if item.get("revoked", False) or item.get("x_mitre_deprecated", False)}
    for item in bundle["objects"]:
        kind = item.get("type")
        if kind not in {"attack-pattern", "relationship"}:
            yield None, "unsupported_stix_type"
            continue
        if item.get("revoked", False) or item.get("x_mitre_deprecated", False):
            yield None, "revoked_or_deprecated"
            continue
        if kind == "relationship":
            if item.get("source_ref") in inactive or item.get("target_ref") in inactive:
                yield None, "inactive_relationship_endpoint"
                continue
            metadata = {key: item[key] for key in
                        ("relationship_type", "source_ref", "target_ref", "modified")}
            title = metadata["relationship_type"]
            content = " ".join([metadata["source_ref"], title, metadata["target_ref"],
                                item.get("description", "")])
        else:
            refs = item.get("external_references", [])
            technique_ids = [r["external_id"] for r in refs
                             if r.get("source_name") == "mitre-attack"
                             and re.fullmatch(r"T\d{4}(?:\.\d{3})?", r.get("external_id", ""))]
            if len(technique_ids) != 1:
                raise IngestionError("Expected one MITRE technique identifier")
            metadata = {"technique_id": technique_ids[0], "stix_id": item["id"],
                        "modified": item["modified"], "revoked": False, "deprecated": False,
                        "platforms": item.get("x_mitre_platforms", []),
                        "tactics": item.get("kill_chain_phases", []), "references": refs}
            title = item["name"]
            content = title + ". " + text(item["description"])
        metadata["stix_type"] = kind
        yield record(snapshot, item["id"], title, content, metadata), None


def cve(data, snapshot):
    feed = parse_json(data)
    if feed.get("format") != "NVD_CVE" or feed.get("version") != "2.0":
        raise IngestionError("Expected NVD CVE JSON 2.0")
    if not isinstance(feed.get("vulnerabilities"), list):
        raise IngestionError("Missing NVD vulnerabilities")
    for wrapper in feed["vulnerabilities"]:
        item = wrapper["cve"]
        if not re.fullmatch(r"CVE-\d{4}-\d{4,}", item["id"]):
            raise IngestionError("Invalid CVE identifier")
        if item.get("vulnStatus") == "Rejected":
            yield None, "rejected_cve"
            continue
        description = english(item.get("descriptions", []))
        if not description:
            yield None, "missing_english_description"
            continue
        metadata = {key: item[key] for key in ("published", "lastModified")}
        # Preserve supplied enrichment; never synthesize a score/CWE/CPE.
        for key in ("vulnStatus", "metrics", "weaknesses", "configurations", "references"):
            if key in item:
                metadata[key] = item[key]
        yield record(snapshot, item["id"], item["id"], description, metadata), None


def cwe(data, snapshot):
    # Reject declarations before ElementTree can expand internal entities. XML
    # must be UTF-8: disallow UTF-16/32 encodings that could hide declaration bytes.
    try:
        decoded = data.decode("utf-8-sig")
    except UnicodeError as exc:
        raise IngestionError("CWE XML must be UTF-8") from exc
    if "\x00" in decoded or re.search(r"<!\s*(?:DOCTYPE|ENTITY)", decoded, re.I):
        raise IngestionError("XML declarations/entities are disabled")
    root = ET.fromstring(decoded)
    namespace = root.tag.partition("}")[0].removeprefix("{")
    ns = {"c": namespace}
    if namespace not in {"http://cwe.mitre.org/cwe-7", "http://cwe.mitre.org/cwe-8"} or root.tag != "{" + namespace + "}Weakness_Catalog":
        raise IngestionError("Expected a CWE weakness catalog")
    if root.get("Version") != snapshot["upstream_version"]:
        raise IngestionError("CWE catalog version differs from snapshot manifest")
    for item in root.findall("c:Weaknesses/c:Weakness", ns):
        if item.get("Status") in {"Deprecated", "Obsolete"}:
            yield None, "deprecated_cwe"
            continue
        if not re.fullmatch(r"\d+", item.attrib["ID"]):
            raise IngestionError("Invalid CWE identifier")
        description = item.find("c:Description", ns)
        if description is None:
            raise IngestionError("Missing CWE description")
        metadata = {"status": item.attrib["Status"],
                    "abstraction": item.attrib["Abstraction"],
                    "catalog_version": root.get("Version"), "xml_namespace": namespace,
                    "xml_schema_version": "8.0" if namespace.endswith("cwe-8") else "7",
                    "relationships": [dict(node.attrib) for node in
                                      item.findall("c:Related_Weaknesses/c:Related_Weakness", ns)]}
        extended = item.find("c:Extended_Description", ns)
        body = " ".join(description.itertext())
        if extended is not None:
            body += " " + " ".join(extended.itertext())
        yield record(snapshot, "CWE-" + item.attrib["ID"], item.attrib["Name"],
                     item.attrib["Name"] + ". " + body, metadata), None
    # Views/categories are catalog structure, never individual weaknesses.
    for _ in (root.findall("c:Categories/c:Category", ns) + root.findall("c:Views/c:View", ns)
              + root.findall("c:Groupings/c:Grouping", ns)):
        yield None, "cwe_category_or_view"


def split_guard(policy, splits, splits_data):
    validate("soc-policy", policy)
    if digest(splits_data) != policy["splits_sha256"]:
        raise IngestionError("SOC split manifest hash mismatch")
    if splits.get("dataset_version") != policy["dataset_version"]:
        raise IngestionError("SOC dataset version mismatch")
    if type(splits.get("test_frozen")) is not bool:
        raise IngestionError("Missing split freeze status")
    for split in ("development", "test"):
        if not isinstance(splits.get(split), list):
            raise IngestionError("Invalid evaluation split")
        for item in splits[split]:
            if not isinstance(item.get("case_id"), str) or not isinstance(item.get("group_id"), str):
                raise IngestionError("Invalid evaluation split identity")
    heldout = splits["test"]
    heldout_ids = {i["case_id"] for i in heldout}
    heldout_groups = {i["group_id"] for i in heldout}
    # A policy test assignment excludes the entire related run/group too.
    heldout_groups |= {i["group_id"] for i in policy["records"] if i["split"] == "test"}
    heldout_runs = {i["run_id"] for i in policy["records"] if i["split"] == "test"}
    assignments = {}
    for item in policy["records"]:
        if item["incident_id"] in assignments:
            raise IngestionError("Duplicate SOC assignment")
        assignments[item["incident_id"]] = item
    return assignments, heldout_ids, heldout_groups, heldout_runs


def soc(data, snapshot, policy, splits, splits_data):
    assignments, heldout_ids, heldout_groups, heldout_runs = split_guard(policy, splits, splits_data)
    incidents = parse_json(data)
    if not isinstance(incidents, list):
        raise IngestionError("Expected a JSON array of normalized incidents")
    blocked_content, blocked_events = set(), set()
    for item in incidents:
        validate_contract("incident", item)
        assignment = assignments.get(item["incident_id"])
        if (assignment is None or assignment["split"] != "development"
                or item["incident_id"] in heldout_ids
                or set(assignment["related_case_ids"]) & heldout_ids
                or assignment["group_id"] in heldout_groups
                or assignment["run_id"] in heldout_runs):
            blocked_content.add(digest(text(item["description"]).encode()))
            blocked_events.add((item["source"], item["source_event_id"]))
    for item in incidents:
        identity = item["incident_id"]
        assignment = assignments.get(identity)
        if assignment is None:
            yield None, "unassigned_soc_record"
            continue
        if digest(canonical(item)) != assignment["record_sha256"]:
            raise IngestionError("SOC sanitized record hash mismatch")
        if (assignment["split"] != "development" or identity in heldout_ids
                or set(assignment["related_case_ids"]) & heldout_ids
                or assignment["group_id"] in heldout_groups
                or assignment["run_id"] in heldout_runs):
            yield None, "excluded_soc_split"
            continue
        if (digest(text(item["description"]).encode()) in blocked_content
                or (item["source"], item["source_event_id"]) in blocked_events):
            yield None, "excluded_soc_duplicate"
            continue
        metadata = {"incident_id": identity, "source_event_id": item["source_event_id"],
                    "timestamp": item["timestamp"], "source_severity": item["severity"],
                    "entities": item["entities"], "ingestion_kind": item["ingestion_kind"],
                    "group_id": assignment["group_id"], "run_id": assignment["run_id"],
                    "sanitization_ref": assignment["sanitization_ref"],
                    "assignment_ref": policy["assignment_ref"],
                    "dataset_version": policy["dataset_version"],
                    "split": "development", "test_frozen": splits["test_frozen"]}
        yield record(snapshot, identity, "Historical SOC incident " + identity,
                     item["description"], metadata), None

"""Explicit source adapters for selected reference documents and public lab logs."""

from datetime import date
import re
import xml.etree.ElementTree as ET

import yaml

from .core import IngestionError, canonical, digest, parse_json, record, text


def bundle_files(data, provider):
    bundle = parse_json(data)
    if bundle.get("provider") != provider or not isinstance(bundle.get("files"), list):
        raise IngestionError("Unexpected selected-source bundle")
    paths = set()
    for item in bundle["files"]:
        if item["path"] in paths or digest(item["content"].encode()) != item["sha256"]:
            raise IngestionError("Duplicate path or mismatched selected-file digest")
        paths.add(item["path"])
        yield item


class UniqueSafeLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, (str, int, float, bool)) or key in result:
                raise IngestionError("Invalid or duplicate YAML key")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


UniqueSafeLoader.add_constructor("tag:yaml.org,2002:timestamp", lambda loader, node: loader.construct_scalar(node))


def safe_yaml(content):
    depth, count = 0, 0
    for event in yaml.parse(content):
        count += 1
        if isinstance(event, yaml.AliasEvent) or count > 100000:
            raise IngestionError("YAML aliases or excessive structure are disabled")
        if isinstance(event, (yaml.MappingStartEvent, yaml.SequenceStartEvent)):
            depth += 1
        if isinstance(event, (yaml.MappingEndEvent, yaml.SequenceEndEvent)):
            depth -= 1
        if depth > 64:
            raise IngestionError("YAML nesting limit exceeded")
    return yaml.load(content, Loader=UniqueSafeLoader)


def cve_program(data, snapshot):
    for file in bundle_files(data, "cve_program"):
        item = parse_json(file["content"].encode())
        if item.get("dataType") != "CVE_RECORD" or not str(item.get("dataVersion", "")).startswith("5."):
            raise IngestionError("Expected a CVE JSON 5 record")
        identity = item["cveMetadata"]["cveId"]
        if not re.fullmatch(r"CVE-\d{4}-\d{4,}", identity):
            raise IngestionError("Invalid CVE identifier")
        if item["cveMetadata"]["state"] == "REJECTED":
            yield None, "rejected_cve"
            continue
        cna = item["containers"]["cna"]
        descriptions = [text(d["value"]) for d in cna.get("descriptions", []) if d.get("lang", "").lower().startswith("en")]
        if not descriptions:
            yield None, "missing_english_description"
            continue
        metadata = {"published": item["cveMetadata"]["datePublished"],
                    "lastModified": item["cveMetadata"]["dateUpdated"], "provider": "cve_program",
                    "cve_program": {"metadata": item["cveMetadata"], "cna": cna,
                                    "adp": item["containers"].get("adp", [])},
                    "source_path": file["path"], "source_file_sha256": file["sha256"]}
        yield record(snapshot, identity, identity, " ".join(descriptions), metadata), None


def kev(data, snapshot):
    files = list(bundle_files(data, "kev"))
    if len(files) != 1:
        raise IngestionError("Expected one KEV catalog")
    catalog = parse_json(files[0]["content"].encode())
    if catalog["count"] != len(catalog["vulnerabilities"]):
        raise IngestionError("KEV catalog count mismatch")
    for item in catalog["vulnerabilities"]:
        if not re.fullmatch(r"CVE-\d{4}-\d{4,}", item["cveID"]):
            raise IngestionError("Invalid KEV CVE identifier")
        date.fromisoformat(item["dateAdded"])
        yield record(snapshot, item["cveID"], item["vulnerabilityName"], item["shortDescription"],
                     {"provider": "cisa_kev", "catalog_version": catalog["catalogVersion"],
                      "catalog_released": catalog["dateReleased"], "kev": item}), None


def sigma(data, snapshot):
    for file in bundle_files(data, "sigma"):
        rule = safe_yaml(file["content"])
        if rule.get("status") in {"deprecated", "unsupported"}:
            yield None, "inactive_sigma_rule"
            continue
        metadata = {"provider": "sigma", "source_path": file["path"], "source_file_sha256": file["sha256"],
                    "rule_id": rule["id"], "status": rule.get("status", "unspecified"),
                    "logsource": rule["logsource"], "detection": rule["detection"],
                    "tags": rule.get("tags", []), "falsepositives": rule.get("falsepositives", []),
                    "references": rule.get("references", [])}
        content = text(rule["title"]) + ". " + text(rule["description"])
        content += " Detection pattern: " + canonical(rule["detection"]).decode()
        if metadata["falsepositives"]:
            content += " Possible false positives: " + "; ".join(metadata["falsepositives"])
        yield record(snapshot, rule["id"], rule["title"], content, metadata), None


def playbook(data, snapshot):
    for file in bundle_files(data, "playbook"):
        body = file["content"]
        heading = re.search(r"(?m)^#\s+(.+)$", body)
        if not heading:
            raise IngestionError("Playbook needs a document heading")
        metadata = {"provider": "threat_hunter_playbook", "source_path": file["path"],
                    "source_file_sha256": file["sha256"], "platform": "windows",
                    "usage": "reference_only_no_execution"}
        yield record(snapshot, file["path"], heading[1], body, metadata), None


def external_events(data, snapshot, policy, splits, splits_data):
    from .adapters import split_guard
    provider = parse_json(data)["provider"]
    if provider not in {"otrf", "splunk"}:
        raise IngestionError("Unexpected external event provider")
    assignments, ids, groups, runs = split_guard(policy, splits, splits_data,
                                                schema="external-policy", identity_field="source_record")
    for file in bundle_files(data, provider):
        if file["path"].endswith((".yml", ".yaml")):
            yield None, "event_documentation_not_indexed"
            continue
        assignment = assignments.get(provider + ":" + file["path"])
        if assignment is None:
            yield None, "unassigned_external_file"
            continue
        if assignment["sha256"] != file["sha256"]:
            raise IngestionError("External development assignment digest mismatch")
        if (assignment["split"] != "development" or assignment["group_id"] in groups
                or assignment["run_id"] in runs or set(assignment["related_case_ids"]) & ids):
            yield None, "excluded_external_split"
            continue
        lines = [line for line in file["content"].split("\n") if line.strip()]
        if not lines:
            raise IngestionError("Empty external event file")
        for index, line in enumerate(lines):
            if index >= assignment["max_events"]:
                yield None, "external_selection_limit"
                continue
            # A public event excerpt is not assigned an invented backend severity,
            # timestamp or analyst verdict. Keep labels/technique paths as lineage.
            if len(line.encode()) > 128 * 1024:
                raise IngestionError("External event excerpt exceeds budget")
            event = external_event(line)
            identity = provider + ":" + digest(canonical([file["path"], index, event]))
            metadata = {"provider": provider, "source_path": file["path"], "source_file_sha256": file["sha256"],
                        "event_index": index, "event_sha256": digest(canonical(event)),
                        "group_id": assignment["group_id"], "run_id": assignment["run_id"],
                        "assignment_ref": policy["assignment_ref"], "dataset_version": policy["dataset_version"],
                        "split": "development", "test_frozen": splits["test_frozen"],
                        "usage": "public_lab_excerpt_no_ground_truth"}
            yield record(snapshot, identity, "Historical security event excerpt", canonical(event).decode(), metadata), None


def external_event(line):
    """Preserve observations in their actual source format, without invented labels."""
    line = line.strip()
    if line.startswith("{"):
        event = parse_json(line.encode())
        def reject_labels(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key.lower() in {"label", "attack_type", "expected_verdict", "gold_severity", "expected_actions"}:
                        raise IngestionError("Evaluator labels in external event")
                    reject_labels(item)
            elif isinstance(value, list):
                for item in value:
                    reject_labels(item)
        reject_labels(event)
        return {"format": "json_event", "observation": event}
    if line.startswith("<Event>"):
        if re.search(r"<!\s*(?:DOCTYPE|ENTITY)", line, re.I):
            raise IngestionError("XML declarations/entities are disabled")
        root = ET.fromstring(line)
        if any(node.tag.lower() in {"label", "expected_verdict", "gold_severity"} for node in root.iter()):
            raise IngestionError("Evaluator labels in external XML")
        return {"format": "sysmon_xml", "observation": line}
    match = re.match(r"type=([A-Z_]+) msg=audit\(([0-9.]+:[0-9]+)\):", line)
    if match:
        return {"format": "linux_auditd", "record_type": match[1], "audit_event_id": match[2],
                "observation": line}
    raise IngestionError("Unsupported external event format")

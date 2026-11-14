"""Common proposal-only policy and incident-bound source-role checks."""

from copy import deepcopy
import ipaddress
from uuid import uuid4


def incident_policy(policy, incident, manifest):
    """Bind input-only source annotations to verified frozen incident bytes."""
    scoped = deepcopy(policy)
    annotations = scoped.pop("source_role_annotations", {})
    role = annotations.get(incident["incident_id"])
    scoped["network_scope"] = None
    scoped["targets"] = []
    if role is not None:
        expected = next(a["sha256"] for a in manifest["assets"]
                        if a["path"] == f"incidents/inputs/{incident['incident_id']}.json")
        hosts = {e["value"] for e in incident["entities"] if e["type"] == "host"}
        ips = {e["value"] for e in incident["entities"] if e["type"] == "ip"}
        if (role["incident_sha256"] != expected or role["target"] not in hosts
                or role["source_ip"] not in ips or role["destination_ip"] not in ips
                or role["source_ip"] == role["destination_ip"] or role["service"] != "ssh"
                or role["target"] not in policy["targets"]):
            raise ValueError("Source-role annotation does not match incident/policy")
        scoped["network_scope"] = {**role, "incident_id": incident["incident_id"]}
        scoped["targets"] = [role["target"]]
    return scoped


class ProposalPolicy:
    """Validate proposals without executing them or granting new permissions."""

    @staticmethod
    def _check_source_roles(actions, incident, policy):
        """Fail closed without caller-verified, incident-specific network roles."""
        for action in actions:
            scope = policy.get("network_scope")
            if not isinstance(scope, dict) or scope.get("incident_id") != incident["incident_id"]:
                raise ValueError("Missing incident-specific source roles")
            source = str(ipaddress.IPv4Address(action["source_ip"]))
            if (source != scope.get("source_ip") or source == scope.get("destination_ip")
                    or action["target"] != scope.get("target") or scope.get("service") != "ssh"):
                raise ValueError("Proposal disagrees with observed source/service roles")

    @staticmethod
    def _check_policy(policy):
        if (policy.get("execution_enabled") is not False or policy.get("action_type") != "block_ip"
                or policy.get("response_defaults") != {"schema_version": "1.0.0", "revision": 1,
                    "requires_approval": True, "status": "proposed"}):
            raise ValueError("Only disabled-execution proposal policy is supported")
        for name in ("environment_id", "policy_version", "target_inventory_revision"):
            if not isinstance(policy.get(name), str) or not policy[name]:
                raise ValueError("Missing policy identity")
        if not isinstance(policy.get("targets"), list) or not all(isinstance(t, str) for t in policy["targets"]):
            raise ValueError("Invalid target policy")
        scope = policy["ssh_containment"]
        duration = scope["default_duration_seconds"]
        bounds = scope["duration_seconds"]
        if (type(duration) is not int or not 1 <= bounds["min"] <= duration <= bounds["max"] <= 3600
                or scope["port"] != 22 or scope["protocol"] != "tcp"):
            raise ValueError("Invalid containment scope")

    @staticmethod
    def _action(action, incident, policy):
        hosts = {e["value"] for e in incident["entities"] if e["type"] == "host"}
        ips = {str(ipaddress.ip_address(e["value"])) for e in incident["entities"] if e["type"] == "ip"}
        source = str(ipaddress.IPv4Address(action["source_ip"]))
        if action["target"] not in hosts or action["target"] not in policy["targets"] or source not in ips:
            raise ValueError("Unobserved or unregistered proposal target")
        return {
            **policy["response_defaults"], "action_id": "ACT-" + uuid4().hex,
            "incident_id": incident["incident_id"], "idempotency_key": "KEY-" + uuid4().hex,
            "action_type": "block_ip", "target": action["target"],
            **{k: policy[k] for k in ("environment_id", "target_inventory_revision", "policy_version")},
            "arguments": {"source_ip": source, "port": 22, "protocol": "tcp",
                          "duration_seconds": policy["ssh_containment"]["default_duration_seconds"]},
            **{k: action[k] for k in ("reason", "expected_effect", "risks", "rollback_plan")},
        }

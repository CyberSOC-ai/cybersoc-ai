"""Deterministic conversion; no detection, inference, persistence or network I/O."""
from datetime import datetime, timezone
import ipaddress
import json
import re
from uuid import NAMESPACE_URL, uuid5

from jsonschema import ValidationError

from backend.validation import ID_VALIDATOR, validate

MAX_BYTES = 65536
SEVERITY_POLICY = 'wazuh-level-v1'


class NormalizationError(ValueError):
    """A sanitized input/configuration error, safe to show without raw logs."""


def text(value, field, limit=1024):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise NormalizationError(f'Invalid or missing {field}.')
    try:
        value.encode('utf-8')
    except UnicodeError:
        raise NormalizationError(f'Invalid {field}.') from None
    return value


def obj(value, field):
    if not isinstance(value, dict):
        raise NormalizationError(f'Invalid or missing {field} object.')
    return value


def severity(level):
    """Project mapping v1: 0–3 info, 4–6 low, 7–9 medium, 10–12 high, 13–16 critical."""
    if type(level) is not int or not 0 <= level <= 16:
        raise NormalizationError('rule.level must be an integer between 0 and 16.')
    for maximum, label in ((3, 'informational'), (6, 'low'), (9, 'medium'),
                           (12, 'high'), (16, 'critical')):
        if level <= maximum:
            return label


def utc_timestamp(value):
    value = text(value, 'timestamp', 64)
    if not re.fullmatch(
            r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?'
            r'(?:Z|[+-]\d{2}:?\d{2})', value):
        raise NormalizationError('timestamp must include an explicit UTC offset.')
    # datetime accepts oversized offset minutes; reject them explicitly.
    offset = re.search(r'([+-])(\d{2}):?(\d{2})$', value)
    if offset and (int(offset[2]) > 23 or int(offset[3]) > 59):
        raise NormalizationError('Invalid timestamp offset.')
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)
    except (ValueError, OverflowError):
        raise NormalizationError('Invalid timestamp.') from None
    return result.isoformat(timespec='microseconds' if result.microsecond else 'seconds').replace('+00:00', 'Z')


def normalize_alert(record, *, source='wazuh:lab', ingestion_kind='replay', raw_event_ref=None):
    """Accept one OpenSearch hit or raw alert; return an incident or raise.

    source identifies a trusted detector deployment, not an input-supplied value.
    Callers transporting actual live events must explicitly request live delivery.
    """
    record = obj(record, 'alert')
    alert = obj(record['_source'], '_source') if '_source' in record else record
    source = text(source, 'source', 256)
    if ingestion_kind not in ('live', 'replay', 'synthetic'):
        raise NormalizationError('Invalid ingestion_kind.')
    event_id = text(alert.get('id'), 'id', 128)
    if not ID_VALIDATOR.is_valid(event_id):
        raise NormalizationError('Invalid source event id.')
    agent = obj(alert.get('agent'), 'agent')
    rule = obj(alert.get('rule'), 'rule')
    manager = obj(alert.get('manager'), 'manager')
    manager_name = text(manager.get('name'), 'manager.name', 256)
    agent_name = text(agent.get('name'), 'agent.name', 256)
    agent_id = text(agent.get('id'), 'agent.id', 128)
    rule_id = text(rule.get('id'), 'rule.id', 128)
    rule_description = text(rule.get('description'), 'rule.description', 2048)
    level = rule.get('level')
    normalized_severity = severity(level)
    data = obj(alert.get('data', {}), 'data')
    predecoder = obj(alert.get('predecoder', {}), 'predecoder')
    entities = []

    def entity(kind, value, field):
        value = text(value, field)
        if kind == 'ip':
            try:
                ipaddress.ip_address(value)
            except ValueError:
                raise NormalizationError(f'Invalid {field} IP address.') from None
        item = {'type': kind, 'value': value}
        if item not in entities:
            entities.append(item)
        return value

    entity('host', agent_name, 'agent.name')
    details = [f'Wazuh rule {rule_id} (level {level}): {rule_description}',
               f'Manager: {manager_name}; endpoint agent: {agent_name} ({agent_id}).']
    fields = [
        (predecoder, 'hostname', 'host', 'Observed hostname'),
        (data, 'srcip', 'ip', 'Connection source IP'),
        (data, 'dstip', 'ip', 'Connection destination IP'),
        (agent, 'ip', 'ip', 'Endpoint management IP'),
        (data, 'srcuser', 'user', 'Source user'),
        (data, 'dstuser', 'user', 'Destination user'),
        (predecoder, 'program_name', 'process', 'Log program'),
    ]
    for container, key, kind, label in fields:
        if key in container:
            value = entity(kind, container[key], key)
            details.append(f'{label}: {value}.')
    if 'full_log' in alert:
        details.append('Source log: ' + text(alert['full_log'], 'full_log', 6000))
    incident = {
        'schema_version': '1.0.0',
        'incident_id': 'INC-' + str(uuid5(NAMESPACE_URL, json.dumps(
            [source, event_id], ensure_ascii=True, separators=(',', ':')))),
        'timestamp': utc_timestamp(alert.get('timestamp')),
        'source': source,
        'source_event_id': event_id,
        'description': '\n'.join(details),
        'severity': normalized_severity,
        'entities': entities,
        'ingestion_kind': ingestion_kind,
    }
    if raw_event_ref is not None:
        incident['raw_event_ref'] = text(raw_event_ref, 'raw_event_ref')
    try:
        validate('incident', incident)
        payload = json.dumps(incident, ensure_ascii=False, allow_nan=False).encode('utf-8')
    except (ValidationError, UnicodeError, ValueError):
        raise NormalizationError('Normalized incident does not satisfy contract v1.') from None
    if len(payload) > MAX_BYTES:
        raise NormalizationError('Normalized incident exceeds the backend body limit.')
    return incident

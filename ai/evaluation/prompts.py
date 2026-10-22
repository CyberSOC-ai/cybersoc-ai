"""Prompt rendering only: no model, labels, filesystem outputs or network access."""
import hashlib
import json
from pathlib import Path

START = '<UNTRUSTED_DATA>'
END = '</UNTRUSTED_DATA>'
MARKER = '{{UNTRUSTED_DATA}}'
INCIDENT_FIELDS = {'schema_version', 'incident_id', 'timestamp', 'source', 'source_event_id',
                   'description', 'severity', 'entities', 'ingestion_kind', 'raw_event_ref'}


def _render(protocol_dir, filename, version, payload):
    raw = (Path(protocol_dir) / filename).read_bytes()
    template = raw.decode('utf-8', errors='strict')
    if template.count(MARKER) != 1 or template.count(START) != 1 or template.count(END) != 1:
        raise ValueError(f'{filename}: expected one delimited data placeholder')
    if not template.index(START) < template.index(MARKER) < template.index(END):
        raise ValueError(f'{filename}: data placeholder is outside untrusted block')
    # Encode as JSON, then escape angle brackets to prevent closing/reopening blocks.
    data = json.dumps(payload, ensure_ascii=False, allow_nan=False)
    data = data.replace('<', '\\u003c').replace('>', '\\u003e')
    return {'prompt': template.replace(MARKER, data), 'prompt_version': version,
            'template_sha256': hashlib.sha256(raw).hexdigest()}


def build_claim_extraction_prompt(protocol_dir, candidate_answer):
    if not isinstance(candidate_answer, str):
        raise ValueError('candidate_answer must be text')
    return _render(protocol_dir, 'claim_extraction_prompt.md', 'PRM-claim-extraction-v1',
                   {'candidate_answer': candidate_answer})


def build_judge_prompt(protocol_dir, incident, candidate_answer, claims,
                       retrieved_evidence=(), mode='no_rag'):
    """Supply only a normalized incident, delivered retrieval text and candidate claims.

    Closed input shapes reject evaluator bundles. This is a rendering boundary,
    not proof of judge resistance to instruction injection or trusted evidence.
    """
    if mode not in ('no_rag', 'rag'):
        raise ValueError('judge mode must be no_rag or rag')
    if not isinstance(candidate_answer, str):
        raise ValueError('candidate_answer must be text')
    if not isinstance(incident, dict) or set(incident) - INCIDENT_FIELDS:
        raise ValueError('judge incident must be an incident-only object, not evaluator metadata')
    if not {'incident_id', 'description', 'entities'} <= set(incident):
        raise ValueError('judge incident lacks required incident fields')
    if not isinstance(incident['entities'], list) or any(
            not isinstance(value, str) for key, value in incident.items() if key != 'entities'):
        raise ValueError('judge incident requires scalar text fields and an entities list')
    for entity in incident['entities']:
        if (not isinstance(entity, dict) or set(entity) != {'type', 'value'}
                or any(not isinstance(v, str) for v in entity.values())):
            raise ValueError('judge incident entities must contain only type/value')
    if mode == 'no_rag' and retrieved_evidence:
        raise ValueError('No-RAG judge packet cannot include retrieved evidence')
    evidence_ids = set()
    for item in retrieved_evidence:
        if (not isinstance(item, dict) or set(item) != {'evidence_id', 'text'}
                or any(not isinstance(item[k], str) or not item[k] for k in item)):
            raise ValueError('retrieved evidence requires only nonempty evidence_id/text')
        if item['evidence_id'] in evidence_ids:
            raise ValueError('duplicate retrieved evidence_id')
        evidence_ids.add(item['evidence_id'])
    seen = set()
    for claim in claims:
        if (not isinstance(claim, dict) or set(claim) != {'claim_id', 'text', 'evidence_ids'}
                or not isinstance(claim['claim_id'], str) or not claim['claim_id']
                or not isinstance(claim['text'], str) or not claim['text']
                or not isinstance(claim['evidence_ids'], list)
                or any(not isinstance(cid, str) for cid in claim['evidence_ids'])):
            raise ValueError('claims require claim_id, text and evidence_ids only')
        if claim['claim_id'] in seen:
            raise ValueError('duplicate claim_id')
        seen.add(claim['claim_id'])
    return _render(protocol_dir, 'faithfulness_judge_prompt.md', 'PRM-faithfulness-judge-v1',
                   {'mode': mode, 'evidence_packet': {'incident': incident,
                    'retrieved_evidence': list(retrieved_evidence)},
                    'candidate_answer': candidate_answer, 'claims': claims})

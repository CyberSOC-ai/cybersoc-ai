"""Offline schemas and relational checks for the authored pilot."""
import json
from pathlib import Path
import re

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from .hashing import read_json, verify


def reject_network(uri):
    raise RuntimeError(f"Unregistered schema reference: {uri}")


def validators(repo_root, dataset):
    schemas = [read_json(p) for p in sorted((Path(repo_root) / 'backend/contracts/v1').glob('*.schema.json'))]
    label = read_json(Path(dataset) / 'labels.schema.json')
    schemas.append(label)
    registry = Registry(retrieve=reject_network).with_resources(
        (schema['$id'], Resource.from_contents(schema)) for schema in schemas)
    result = {}
    for schema in schemas:
        Draft202012Validator.check_schema(schema)
        name = 'labels' if schema is label else schema['title']
        result[name] = Draft202012Validator(schema, registry=registry,
                                           format_checker=FormatChecker())
    return result


def resolve_pointer(document, pointer):
    if not isinstance(pointer, str) or not re.fullmatch(r'(?:/(?:[^~/]|~[01])*)*', pointer):
        raise ValueError('invalid JSON pointer')
    node = document
    for raw in pointer.split('/')[1:]:
        token = raw.replace('~1', '/').replace('~0', '~')
        if isinstance(node, list):
            if not re.fullmatch(r'0|[1-9][0-9]*', token):
                raise ValueError('JSON pointer has invalid array index')
            node = node[int(token)]
        else:
            node = node[token]
    return node


def validate_case(case, checks):
    cid = case['case_id']
    incident, label, context = case['input'], case['labels'], case['context']

    def require(condition, message):
        if not condition:
            raise ValueError(f'{cid}: {message}')

    for name, record in (('incident', incident), ('labels', label)):
        errors = list(checks[name].iter_errors(record))
        if errors:
            error = errors[0]
            raise ValueError(f'{cid}: {name} field {list(error.path)}: {error.message}')
    require(label['case_id'] == context.get('case_id') == cid,
            'filename, label and context case_id disagree')
    require(incident['incident_id'] == label['incident_id'] == context.get('incident_id'),
            'input, label and context incident_id disagree')
    require(label['group_id'] == context.get('group_id') == context.get('template_family'),
            'label group and context template family disagree')
    require(context.get('dataset_version') == label['dataset_version'], 'context dataset version differs')
    require(incident['ingestion_kind'] == 'synthetic' and context.get('synthetic') is True,
            'pilot case must be explicitly synthetic')
    if not label['mitre_techniques']:
        require(isinstance(label['mitre_reason'], str) and bool(label['mitre_reason'].strip()),
                'empty MITRE techniques need a nonempty mitre_reason')
    evidence_ids = set()
    for evidence in label['gold_evidence']:
        require(evidence['id'] not in evidence_ids, f"duplicate gold_evidence ID {evidence['id']}")
        evidence_ids.add(evidence['id'])
        pointer = evidence['locator']['json_pointer']
        try:
            value = resolve_pointer(incident, pointer)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ValueError(f'{cid}: gold_evidence locator {pointer!r} does not resolve: {exc}') from exc
        require(isinstance(value, str), f'gold_evidence locator {pointer!r} must resolve to text')
        require(evidence['locator']['quoted_substring'] in value,
                f'gold_evidence quoted substring is absent at {pointer!r}')
    for action in label['required_actions']:
        args = action['arguments']
        require(args['duration_seconds']['min'] <= args['duration_seconds']['max'],
                'required action duration min exceeds max')
        require(action['target'] == context.get('fixture_inventory', {}).get('endpoint_id'),
                'action target differs from the fixture endpoint')
        require({'type': 'host', 'value': action['target']} in incident['entities'],
                'required action target is absent from incident entities')
        require({'type': 'ip', 'value': args['source_ip']} in incident['entities'],
                'required action source_ip is absent from incident entities')
    serialized = json.dumps(incident, ensure_ascii=False)
    forbidden = ('gold_severity', 'required_actions', 'gold_evidence', 'triage_verdict',
                 'mitre_techniques', 'false_positive_type', 'adjudication_status',
                 'needs_review', 'label_author', 'label_reviewer', 'analyst_guidance')
    for token in forbidden:
        require(token not in serialized, f'model-visible input contains gold annotation field {token}')
    require(label['rationale'] not in serialized, 'model-visible input contains its gold rationale')
    require(label['verdict'] not in serialized, 'model-visible input contains its gold verdict token')
    for technique in label['mitre_techniques']:
        require(technique not in serialized, f'model-visible input contains gold technique {technique}')


def validate_dataset(repo_root, dataset, *, verify_hashes=True):
    """Return bundles after checks; pending labels allowed only in this draft pilot."""
    root = Path(dataset)
    manifest = verify(root) if verify_hashes else read_json(root / 'manifest.json')
    splits = read_json(root / 'splits.json')
    checks = validators(repo_root, root)
    files = {folder: {p.stem for p in (root / folder).glob('*.json')}
             for folder in ('inputs', 'labels', 'context')}
    if not files['inputs']:
        raise ValueError('inputs/: no cases found')
    for folder, ids in files.items():
        if ids != files['inputs']:
            raise ValueError(f"{folder}: missing or orphan case IDs {sorted(ids ^ files['inputs'])}")
    membership = {}
    groups = {}
    for split in ('development', 'test'):
        for entry in splits[split]:
            cid = entry['case_id']
            if cid in membership:
                raise ValueError(f'{cid}: must appear in exactly one split')
            membership[cid] = (split, entry['group_id'])
            group = entry['group_id']
            if group in groups and groups[group] != split:
                raise ValueError(f'{cid}: group {group} appears in development and test')
            groups[group] = split
    if set(membership) != files['inputs']:
        raise ValueError(f"splits.json: missing or unknown case IDs {sorted(set(membership) ^ files['inputs'])}")
    manifest_ids = [row['case_id'] for row in manifest['cases']]
    if len(set(manifest_ids)) != len(manifest_ids) or set(manifest_ids) != files['inputs']:
        raise ValueError(f'manifest.json: duplicate, missing or unknown case IDs {manifest_ids}')
    if manifest['dataset_version'] != splits['dataset_version']:
        raise ValueError('splits.json: dataset version differs from manifest.json')
    if type(splits.get('test_frozen')) is not bool:
        raise ValueError('splits.json: test_frozen must be a boolean')
    cases, incident_ids, event_ids = [], set(), set()
    for cid in sorted(files['inputs']):
        case = {'case_id': cid, 'input': read_json(root / 'inputs' / f'{cid}.json'),
                'labels': read_json(root / 'labels' / f'{cid}.json'),
                'context': read_json(root / 'context' / f'{cid}.json')}
        validate_case(case, checks)
        label, incident = case['labels'], case['input']
        if membership[cid] != (label['split'], label['group_id']):
            raise ValueError(f'{cid}: label split/group disagrees with splits.json')
        if label['dataset_version'] != manifest['dataset_version']:
            raise ValueError(f'{cid}: label dataset version differs from manifest.json')
        if splits['test_frozen'] and label['split'] == 'test' and label['needs_review']:
            raise ValueError(f'{cid}: frozen test case still needs review')
        if incident['incident_id'] in incident_ids:
            raise ValueError(f"{cid}: duplicate incident_id {incident['incident_id']}")
        incident_ids.add(incident['incident_id'])
        event = (incident['source'], incident['source_event_id'])
        if event in event_ids:
            raise ValueError(f'{cid}: duplicate source/source_event_id {event}')
        event_ids.add(event)
        cases.append(case)
    for name, actual in (
            ('severity_universe', {c['labels']['gold_severity'] for c in cases}),
            ('mitre_universe', {t for c in cases for t in c['labels']['mitre_techniques']})):
        declared = manifest[name]
        if len(declared) != len(set(declared)) or set(declared) != actual:
            raise ValueError(f'manifest.json: {name} does not equal pilot label coverage')
    return cases

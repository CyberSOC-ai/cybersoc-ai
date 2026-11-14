"""Verified source consumption and exact-span tokenizer-aware passage preparation."""
from hashlib import sha256, file_digest
import json
from pathlib import Path
import re

from ai.runtime.contracts import strict_json

ROOT = Path(__file__).resolve().parents[2]
CONFIG = Path(__file__).with_name('config.json')


def digest(path):
    with Path(path).open('rb') as stream:
        return file_digest(stream, 'sha256').hexdigest()


def identity(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                             ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def load(path, maximum=128 * 1024**2):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum:
        raise ValueError('Unsafe or oversized artifact')
    return strict_json(path.read_text(encoding='utf-8'))


def save(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def safe_file(root, relative):
    if Path(root).is_symlink():
        raise ValueError('Symlinked artifact root')
    root = Path(root).resolve()
    if not isinstance(relative, str) or Path(relative).is_absolute() or '..' in Path(relative).parts:
        raise ValueError('Unsafe asset path')
    path = root / relative
    if any(p.is_symlink() for p in [path, *path.parents] if p != root.parent):
        raise ValueError('Symlinked assets are forbidden')
    if not path.resolve().is_relative_to(root) or not path.is_file():
        raise ValueError('Missing asset')
    return path


def configuration(path=CONFIG):
    c = load(path)
    if (not 0 < c['overlap_tokens'] < c['chunk_tokens'] <= 384
            or c['embedding_dimension'] != 384 or c['embedding_max_tokens'] != 512
            or not 1 <= c['top_k'] <= 20 or not 1 <= c['generation_passages'] <= c['top_k']
            or not -1 <= c['score_threshold'] <= 1):
        raise ValueError('Invalid retrieval configuration')
    return c


def verify_model(config):
    path = Path(config['embedding_path'])
    if not path.is_absolute():
        path = ROOT / path
    for name, expected in config['embedding_files_sha256'].items():
        if digest(safe_file(path, name)) != expected:
            raise ValueError('Embedding artifact checksum mismatch')
    return path


def manifest(release, expected):
    path = safe_file(release, 'manifest.json')
    if digest(path) != expected:
        raise ValueError('Release manifest checksum mismatch')
    m = load(path)
    if len({a['path'] for a in m['assets']}) != len(m['assets']):
        raise ValueError('Duplicate release assets')
    return m


def asset(release, m, name):
    matches = [a for a in m['assets'] if a['path'] == name]
    if len(matches) != 1:
        raise ValueError('Undeclared source asset')
    path = safe_file(release, name)
    if digest(path) != matches[0]['sha256']:
        raise ValueError('Source asset checksum mismatch')
    return path


def corpus(release, config):
    """Only declared knowledge files; never read evaluation or incident content."""
    m = manifest(release, config['release_manifest_sha256'])
    if m['release_id'] != config['release_id']:
        raise ValueError('Release ID mismatch')
    source_rows = load(asset(release, m, 'knowledge/sources.json'))
    sources = {s['document_id']: s for s in source_rows}
    records = [strict_json(line) for line in asset(release, m, 'knowledge/records.jsonl').read_text().splitlines()]
    if not 0 < len(records) <= config['maximum_documents'] or len(sources) != len(source_rows):
        raise ValueError('Invalid corpus inventory')
    seen = set()
    for record in records:
        did = record['document_id']
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,127}', did) or did in seen:
            raise ValueError('Duplicate or unsafe document identity')
        seen.add(did)
        s = sources[did]
        if not s['text'].startswith('knowledge/text/') or not s['snapshot'].startswith('knowledge/snapshots/'):
            raise ValueError('Source is outside knowledge scope')
        text = asset(release, m, s['text'])
        snapshot = asset(release, m, s['snapshot'])
        if (digest(text) != s['text_sha256'] or digest(snapshot) != s['snapshot_sha256']
                or text.read_text(encoding='utf-8') != record['content']
                or record['source_url'] != s['source_url'] or not record['content'].strip()):
            raise ValueError('Source/record identity mismatch')
        record['content_sha256'] = sha256(record['content'].encode()).hexdigest()
        record['snapshot_sha256'] = s['snapshot_sha256']
        record['source'] = ('mitre_attack' if did.startswith('DOC-ATTACK-') or did == 'DOC-PASSWORD-GUESSING'
                            else 'cve' if did.startswith('DOC-CVE-') else 'cwe' if did.startswith('DOC-CWE-')
                            else 'playbook')
        record['usage'] = s['usage']
    if seen != set(sources):
        raise ValueError('Orphan source records')
    return records


def passages(record, tokenizer, config):
    text = record['content']
    offsets = tokenizer(text, add_special_tokens=False, truncation=False,
                        return_offsets_mapping=True, verbose=False)['offset_mapping']
    if not offsets or any(not 0 <= a < b <= len(text) for a, b in offsets):
        raise ValueError('Invalid tokenizer offsets')
    start = 0
    result = []
    while start < len(offsets):
        stop = min(start + config['chunk_tokens'], len(offsets))
        # Prefer a paragraph boundary near the end; never drop intervening tokens.
        if stop < len(offsets):
            low = start + config['chunk_tokens'] * 3 // 4
            choices = [i for i in range(low, stop) if '\n\n' in text[offsets[i-1][1]:offsets[i][0]]]
            if choices:
                stop = choices[-1]
        a, b = offsets[start][0], offsets[stop-1][1]
        content = text[a:b]
        key = identity([record['document_id'], record['content_sha256'], a, b, content])
        result.append({'chunk_id': 'EV-' + key[:40], 'document_id': record['document_id'],
                       'document_sha256': record['content_sha256'], 'start': a, 'end': b,
                       'content': content, 'content_sha256': sha256(content.encode()).hexdigest(),
                       'title': record['title'], 'source_url': record['source_url'], 'source': record['source'],
                       'snapshot_sha256': record['snapshot_sha256'], 'token_count': stop-start})
        if stop == len(offsets):
            break
        start = stop - config['overlap_tokens']
    return result


def seal(directory, metadata):
    directory = Path(directory)
    hashes = {p.name: digest(p) for p in sorted(directory.iterdir()) if p.is_file()}
    save(directory/'manifest.json', {**metadata, 'files_sha256': hashes})


def verified(directory):
    directory = Path(directory)
    m = load(directory/'manifest.json')
    for name, expected in m['files_sha256'].items():
        if digest(safe_file(directory, name)) != expected:
            raise ValueError('Artifact integrity mismatch')
    return m


def incidents(release, config):
    from ai.runtime.contracts import contract_validators
    m = manifest(release, config['release_manifest_sha256'])
    checks = contract_validators(ROOT)
    result, seen = [], set()
    for a in sorted(m['assets'], key=lambda x: x['path']):
        if not a['path'].startswith('incidents/inputs/'):
            continue
        if not re.fullmatch(r'incidents/inputs/[A-Za-z0-9._-]+\.json', a['path']):
            raise ValueError('Unsafe incident asset')
        incident = load(asset(release, m, a['path']))
        checks['incident'].validate(incident)
        if incident['incident_id'] in seen or Path(a['path']).stem != incident['incident_id']:
            raise ValueError('Duplicate/mismatched incident')
        seen.add(incident['incident_id'])
        result.append(incident)
    if not result or len(result) > config['maximum_documents']:
        raise ValueError('Invalid incident inventory')
    return result, m

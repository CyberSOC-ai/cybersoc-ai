"""soc-eval-json-v1: strict integer-only JSON, UTF-8, sorted compact keys."""
import hashlib
import json
from pathlib import Path

SCHEME = "soc-eval-json-v1"


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _reject_number(value):
    raise ValueError(f"floats and non-finite numbers are forbidden: {value}")


def parse_json(data, name="JSON"):
    """Reject duplicate keys, floats, BOMs, invalid UTF-8 and lone surrogates."""
    try:
        value = json.loads(data.decode("utf-8", errors="strict"),
                           object_pairs_hook=_pairs, parse_float=_reject_number,
                           parse_constant=_reject_number)
        canonical_bytes(value)  # Also reject escaped lone Unicode surrogates.
        return value
    except (ValueError, UnicodeError, TypeError) as exc:
        raise ValueError(f"{name}: {exc}") from exc


def read_json(path):
    path = Path(path)
    try:
        return parse_json(path.read_bytes(), str(path))
    except OSError as exc:
        raise ValueError(f"{path}: cannot read JSON: {exc}") from exc


def canonical_bytes(value):
    def check(item):
        if type(item) in (str, int, bool, type(None)):
            return
        if type(item) is list:
            for child in item:
                check(child)
            return
        if type(item) is dict and all(type(k) is str for k in item):
            for child in item.values():
                check(child)
            return
        raise ValueError("canonical JSON allows only string keys and integer numbers")
    check(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def digest(value):
    return sha256(canonical_bytes(value))


def case_digest(case_id, incident, labels, context):
    return digest({"hash_scheme": SCHEME, "case_id": case_id,
                   "input": incident, "labels": labels, "context": context})


def _asset_paths(root):
    paths = []
    for folder in ('protocol', 'validation'):
        directory = root / folder
        if directory.is_symlink():
            raise ValueError(f'{folder}: symlinked asset directory is forbidden')
        for path in directory.rglob('*'):
            if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
                raise ValueError(f'{path}: unsafe protocol/validation asset path')
            if path.is_file():
                paths.append(path.relative_to(root).as_posix())
    return sorted(paths)


def _verify_assets(root, manifest):
    records = manifest.get('assets', [])
    names = [row['path'] for row in records]
    if len(names) != len(set(names)) or sorted(names) != _asset_paths(root):
        raise ValueError('manifest.json: missing, duplicate or unlisted protocol/validation assets')
    for record in records:
        path = root / record['path']
        if sha256(path.read_bytes()) != record['raw_sha256']:
            raise ValueError(f"{record['path']}: raw SHA-256 mismatch")


def verify(dataset, expected_manifest_sha256=None):
    """Read-only integrity check; pin the manifest externally for trusted releases."""
    root = Path(dataset)
    manifest_path = root / "manifest.json"
    if expected_manifest_sha256 is not None:
        if sha256(manifest_path.read_bytes()) != expected_manifest_sha256:
            raise ValueError("manifest.json: does not match the externally pinned digest")
    manifest = read_json(manifest_path)
    if manifest.get("hash_scheme") != SCHEME:
        raise ValueError("manifest.json: unsupported hashing scheme")
    policy_path = root / "protocol/runner-policy.json"
    policy_record = manifest.get('runner_policy', {})
    if (policy_record.get('path') != 'protocol/runner-policy.json'
            or policy_path.is_symlink()
            or sha256(policy_path.read_bytes()) != policy_record.get('raw_sha256')
            or digest(read_json(policy_path)) != policy_record.get('sha256')):
        raise ValueError('protocol/runner-policy.json: missing or mismatched policy digest')
    _verify_assets(root, manifest)
    split_path = root / "splits.json"
    if sha256(split_path.read_bytes()) != manifest.get("splits_sha256"):
        raise ValueError("splits.json: raw SHA-256 does not match manifest.json")
    splits = read_json(split_path)
    if splits.get("hash_scheme") != SCHEME:
        raise ValueError("splits.json: unsupported hashing scheme")
    memberships = {}
    for split in ("development", "test"):
        for entry in splits[split]:
            cid = entry["case_id"]
            if cid in memberships:
                raise ValueError(f"{cid}: appears more than once in splits.json")
            memberships[cid] = entry
    seen = set()
    expected_paths = {folder: set() for folder in ("inputs", "labels", "context")}
    for entry in manifest["cases"]:
        cid = entry["case_id"]
        if cid in seen:
            raise ValueError(f"{cid}: duplicated in manifest.json")
        seen.add(cid)
        parts = {}
        for folder in expected_paths:
            record = entry[folder]
            relative = f"{folder}/{cid}.json"
            path = root / relative
            if (record["path"] != relative or
                    not path.resolve().is_relative_to(root.resolve()) or path.is_symlink()):
                raise ValueError(f"{cid}: unsafe or incorrect {folder} path")
            expected_paths[folder].add(path)
            parts[folder] = read_json(path)
            if sha256(path.read_bytes()) != record["raw_sha256"]:
                raise ValueError(f"{cid}: {relative} raw SHA-256 mismatch")
            if digest(parts[folder]) != record["sha256"]:
                raise ValueError(f"{cid}: {relative} canonical SHA-256 mismatch")
        actual = case_digest(cid, parts["inputs"], parts["labels"], parts["context"])
        if actual != entry["sha256"]:
            raise ValueError(f"{cid}: complete case SHA-256 mismatch in manifest.json")
        if cid not in memberships or memberships[cid]["sha256"] != actual:
            raise ValueError(f"{cid}: complete case SHA-256 missing or different in splits.json")
    if seen != set(memberships):
        raise ValueError(f"splits.json: case membership differs: {sorted(seen ^ set(memberships))}")
    for folder, expected in expected_paths.items():
        actual = set((root / folder).rglob("*.json"))
        if actual != expected:
            raise ValueError(f"{folder}: unlisted or missing case files: {sorted(str(p) for p in actual ^ expected)}")
    return manifest


def build_manifests(dataset):
    """Return refreshed manifests without writing; release metadata comes from labels.

    Caller explicitly saves splits first, then manifest. Only a development pilot
    may be regenerated here; a frozen release must never be silently rehashed.
    """
    root = Path(dataset)
    old_splits = read_json(root / 'splits.json')
    if old_splits['test_frozen'] or old_splits['test']:
        raise ValueError('splits.json: regeneration is restricted to an unfrozen development pilot')
    records, members, versions, severities, techniques = [], [], set(), set(), set()
    for path in sorted((root / 'inputs').glob('*.json')):
        cid = path.stem
        parts = {folder: read_json(root / folder / path.name)
                 for folder in ('inputs', 'labels', 'context')}
        label = parts['labels']
        if label['split'] != 'development':
            raise ValueError(f'{cid}: regeneration requires development membership')
        versions.add(label['dataset_version'])
        severities.add(label['gold_severity'])
        techniques.update(label['mitre_techniques'])
        complete = case_digest(cid, parts['inputs'], label, parts['context'])
        record = {'case_id': cid, 'sha256': complete}
        for folder, value in parts.items():
            relative = f'{folder}/{cid}.json'
            record[folder] = {'path': relative, 'sha256': digest(value),
                              'raw_sha256': sha256((root / relative).read_bytes())}
        records.append(record)
        members.append({'case_id': cid, 'group_id': label['group_id'], 'sha256': complete})
    if len(versions) != 1:
        raise ValueError('labels/: expected exactly one dataset version')
    version = versions.pop()
    splits = {'dataset_version': version, 'hash_scheme': SCHEME, 'test_frozen': False,
              'development': members, 'test': []}
    split_bytes = (json.dumps(splits, indent=2, ensure_ascii=False) + '\n').encode('utf-8')
    policy = root / 'protocol/runner-policy.json'
    manifest = {'dataset_version': version, 'status': 'synthetic_pilot_pending_review',
                'synthetic_example': True, 'hash_scheme': SCHEME,
                'splits_sha256': sha256(split_bytes),
                'runner_policy': {'path': 'protocol/runner-policy.json',
                                  'sha256': digest(read_json(policy)),
                                  'raw_sha256': sha256(policy.read_bytes())},
                'severity_universe': [s for s in ('informational', 'low', 'medium', 'high', 'critical')
                                      if s in severities],
                'mitre_universe': sorted(techniques), 'cases': records,
                'assets': [{'path': name, 'raw_sha256': sha256((root / name).read_bytes())}
                           for name in _asset_paths(root)]}
    return split_bytes, manifest

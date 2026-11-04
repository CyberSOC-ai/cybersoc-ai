"""Offline, hash-pinned document retrieval evaluation (CDC §9.8)."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from .hashing import read_json

ASSETS = {'queries.json', 'judgments.json', 'rankings.json'}
METRICS = ('precision_at_k', 'recall_at_k_known_references', 'reciprocal_rank')


def identity(hit):
    key = (hit['snapshot_ref'], hit['source_record_id'])
    if any(not isinstance(value, str) or not value.strip() for value in key):
        raise ValueError('Document identities must be nonempty strings')
    return key


def distinct(hits):
    seen, result = set(), []
    for hit in hits:
        key = identity(hit)
        if key not in seen:
            seen.add(key)
            result.append(hit)
    return result


def score(hits, judgments, k=5, *, status='ok', ranking_exhausted=False):
    """Unknown labels are not negatives; RR needs a fully judged ranking prefix."""
    if type(k) is not int or k < 1:
        raise ValueError('K must be a positive integer')
    if status not in {'ok', 'error'} or type(ranking_exhausted) is not bool:
        raise ValueError('Invalid retrieval status or exhaustion flag')
    for key, value in judgments.items():
        if (not isinstance(key, tuple) or len(key) != 2 or
                any(not isinstance(part, str) or not part.strip() for part in key) or
                type(value) is not int or value not in (0, 1)):
            raise ValueError('Invalid judgment identity or binary label')
    if status == 'error' and hits:
        raise ValueError('A failed retrieval cannot supply successful evidence')
    result = {'status': status, 'k': k, 'precision_at_k': None,
              'recall_at_k_known_references': None, 'reciprocal_rank': None,
              'relevant_top_k': None, 'known_relevant_total': sum(judgments.values()),
              'unknown_top_k': None, 'first_relevant_rank': None, 'null_reasons': {}}
    if status != 'ok':
        result['null_reasons'] = {name: 'retrieval_failed' for name in METRICS}
        return result
    ranking = distinct(hits)
    labels = [judgments.get(identity(hit)) for hit in ranking]
    top = labels[:k]
    result.update(returned_distinct_documents=len(ranking), unknown_top_k=top.count(None),
                  relevant_top_k=sum(value == 1 for value in top), missing_top_k_slots=max(0, k-len(top)))
    reason = None
    if len(top) < k and not ranking_exhausted:
        reason = 'candidate_depth_insufficient_for_document_cutoff'
    elif None in top:
        reason = 'unjudged_top_k_documents'
    if reason:
        for name in METRICS[:2]:
            result['null_reasons'][name] = reason
    else:
        result['precision_at_k'] = result['relevant_top_k'] / k
        if result['known_relevant_total']:
            result['recall_at_k_known_references'] = result['relevant_top_k'] / result['known_relevant_total']
    if not result['known_relevant_total']:
        result['null_reasons']['recall_at_k_known_references'] = 'no_known_relevant_documents'
        result['null_reasons']['reciprocal_rank'] = 'no_known_relevant_documents'
    elif 1 in labels:
        first = labels.index(1)
        if None in labels[:first]:
            result['null_reasons']['reciprocal_rank'] = 'unjudged_documents_before_first_known_positive'
        else:
            result['first_relevant_rank'] = first + 1
            result['reciprocal_rank'] = 1 / (first + 1)
    elif ranking_exhausted and None not in labels:
        result['reciprocal_rank'] = 0
    else:
        result['null_reasons']['reciprocal_rank'] = 'absence_not_established_in_candidate_window'
    return result


def aggregate(cases):
    metrics = {}
    for name in METRICS:
        values = [case[name] for case in cases if case[name] is not None]
        metrics[name] = {'mean_eligible': sum(values)/len(values) if values else None,
                         'eligible': len(values), 'intended': len(cases),
                         'excluded': len(cases)-len(values)}
    return {'intended': len(cases), 'successful': sum(c['status'] == 'ok' for c in cases),
            'failed': sum(c['status'] != 'ok' for c in cases), 'metrics': metrics}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fields(value, names):
    require(type(value) is dict and set(value) == set(names), 'Unexpected input fields')


def load_bundle(directory, expected_manifest_sha256):
    """Pin the release externally; reject tampering, duplicate JSON keys and IDs."""
    directory = Path(directory)
    require(not directory.is_symlink(), 'Symlinked bundle directory')
    require(isinstance(expected_manifest_sha256, str) and
            re.fullmatch('[a-f0-9]{64}', expected_manifest_sha256) is not None, 'Invalid manifest SHA-256')
    manifest_path = directory / 'manifest.json'
    require(not manifest_path.is_symlink(), 'Symlinked manifest')
    require(hashlib.sha256(manifest_path.read_bytes()).hexdigest() == expected_manifest_sha256,
            'Manifest digest mismatch')
    manifest = read_json(manifest_path)
    require(manifest.get('format') == 'retrieval-evaluation-v1', 'Unsupported bundle format')
    require(type(manifest.get('assets')) is dict and set(manifest['assets']) == ASSETS,
            'Unexpected bundle asset set')
    assets = {}
    for name in sorted(ASSETS):
        path = directory / name
        require(not path.is_symlink(), 'Symlinked bundle asset')
        require(hashlib.sha256(path.read_bytes()).hexdigest() == manifest['assets'][name],
                'Asset digest mismatch: ' + name)
        assets[name] = read_json(path)
    return manifest, assets


def evaluate_bundle(directory, expected_manifest_sha256):
    manifest, assets = load_bundle(directory, expected_manifest_sha256)
    queries, judgments, runs = (assets[name] for name in ('queries.json', 'judgments.json', 'rankings.json'))
    require(type(queries) is list and bool(queries), 'Empty or invalid query set')
    require(type(judgments) is list and type(runs) is list, 'Invalid judgments or runs')
    query_map = {}
    for query in queries:
        fields(query, ('query_id', 'query', 'sources'))
        require(all(type(query[name]) is str and query[name].strip() for name in ('query_id', 'query')),
                'Invalid query identity/text')
        require(type(query['sources']) is list and bool(query['sources']) and
                all(type(s) is str and s.strip() for s in query['sources']) and
                len(query['sources']) == len(set(query['sources'])), 'Invalid source filter')
        require(query['query_id'] not in query_map, 'Duplicate query ID')
        query_map[query['query_id']] = query
    labels = {qid: {} for qid in query_map}
    for judgment in judgments:
        fields(judgment, ('query_id', 'snapshot_ref', 'source_record_id', 'relevant',
                          'rationale', 'annotation_origin', 'content_sha256'))
        qid = judgment['query_id']
        require(qid in query_map, 'Unknown judgment query')
        key = identity(judgment)
        require(key not in labels[qid], 'Duplicate judgment identity')
        require(type(judgment['relevant']) is int and judgment['relevant'] in (0, 1), 'Invalid binary label')
        require(type(judgment['content_sha256']) is str and
                re.fullmatch('[a-f0-9]{64}', judgment['content_sha256']) is not None, 'Invalid content digest')
        require(all(type(judgment[name]) is str and judgment[name].strip() for name in
                    ('rationale', 'annotation_origin')), 'Missing judgment provenance')
        labels[qid][key] = judgment['relevant']
    outcomes, seen = [], set()
    k = manifest.get('k')
    require(type(k) is int and k > 0, 'Invalid manifest K')
    for run in runs:
        fields(run, ('query_id', 'query', 'sources', 'status', 'ranking_exhausted', 'documents'))
        qid = run['query_id']
        require(qid in query_map and qid not in seen, 'Unknown or duplicate run query')
        seen.add(qid)
        require(run['query'] == query_map[qid]['query'] and run['sources'] == query_map[qid]['sources'],
                'Run query/filter differs from frozen query')
        require(type(run['documents']) is list, 'Invalid document ranking')
        for hit in run['documents']:
            fields(hit, ('snapshot_ref', 'source_record_id', 'evidence_id', 'source'))
            identity(hit)
            require(type(hit['evidence_id']) is str and bool(hit['evidence_id'].strip()), 'Invalid evidence ID')
            require(hit['source'] in run['sources'], 'Evidence violates source filter')
        outcome = score(run['documents'], labels[qid], k, status=run['status'],
                        ranking_exhausted=run['ranking_exhausted'])
        outcomes.append({'query_id': qid, **outcome})
    require(seen == set(query_map), 'Run does not cover all intended queries')
    return {'classification': manifest['classification'], 'manifest_sha256': expected_manifest_sha256,
            'judgment_scope': manifest['judgment_scope'], 'counts': aggregate(outcomes), 'per_query': outcomes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', required=True, type=Path)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        result = evaluate_bundle(args.bundle, args.manifest_sha256)
        with args.output.open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f'Retrieval evaluation failed: {exc}\n')
    print(json.dumps(result['counts'], indent=2))


if __name__ == '__main__':
    main()

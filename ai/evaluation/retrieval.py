"""Dataset-independent document ranking metrics (CDC §9.8)."""
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

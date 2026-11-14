"""Explicit offline preparation, retrieval evaluation and investigation commands."""
import argparse
from datetime import datetime, timezone
from pathlib import Path

from .data import CONFIG, ROOT, asset, configuration, identity, load, manifest, save


def evaluate(release, build, receipt, config, output):
    """Evaluator-only entry point; judgments never enter encoder/generator inputs."""
    from ai.evaluation.retrieval import aggregate, score
    from .retrieval import Retriever
    m = manifest(release, config['release_manifest_sha256'])
    queries = load(asset(release, m, 'evaluation/queries.json'))
    judgments = load(asset(release, m, 'evaluation/judgments.json'))
    labels = {q['query_id']: q for q in judgments}
    if len(labels) != len(judgments) or {q['query_id'] for q in queries} != set(labels):
        raise ValueError('Query/judgment inventory mismatch')
    r = Retriever(build, receipt, config)
    outcomes, diagnostics = [], []
    for q in queries:
        packet = r.search(q['question'])
        gold = labels[q['query_id']]
        known = {(config['release_id'], d): 1 for d in gold['expected_supporting_documents']}
        known.update({(config['release_id'], d): 0 for d in gold['reviewed_non_answering_documents']})
        hits = [{'snapshot_ref': config['release_id'], 'source_record_id': c['document_id']} for c in packet['evidence']]
        outcome = score(hits, known, config['top_k'])
        outcomes.append(outcome)
        found = [e['document_id'] for e in packet['evidence']]
        diagnostics.append({'query_id': q['query_id'], 'question': q['question'],
                            'answerability': gold['answerability'], 'expected_documents': gold['expected_supporting_documents'],
                            'known_references_found': len(set(found)&set(gold['expected_supporting_documents'])),
                            'known_reference_hit': bool(set(found)&set(gold['expected_supporting_documents'])) if gold['expected_supporting_documents'] else None,
                            'retrieval': packet, 'judgment_metrics': outcome})
    answerable = [d for d in diagnostics if d['expected_documents']]
    negative = [d for d in diagnostics if not d['expected_documents']]
    result = {'evaluated_at_utc': datetime.now(timezone.utc).isoformat(),
              'configuration': config, 'configuration_sha256': identity(config), 'build_sha256': r.build_sha,
              'query_count': len(queries), 'judgment_status': 'development draft; unlisted documents unjudged',
              'known_reference_hit_at_k': {'hits': sum(d['known_reference_hit'] for d in answerable), 'eligible': len(answerable)},
              'mean_known_reference_coverage': sum(d['known_references_found']/len(d['expected_documents']) for d in answerable)/len(answerable),
              'unanswerable_cases_returning_evidence': sum(bool(d['retrieval']['evidence']) for d in negative),
              'unanswerable_cases': len(negative), 'conservative_metrics': aggregate(outcomes), 'queries': diagnostics}
    save(output, result)
    return result['known_reference_hit_at_k']


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['build', 'publish', 'snapshot', 'restore', 'evaluate', 'retrieve', 'preflight', 'investigate'])
    p.add_argument('--config', type=Path, default=CONFIG)
    p.add_argument('--release', type=Path, default=ROOT/'datasets/releases/shared-dev-v1')
    p.add_argument('--build', type=Path)
    p.add_argument('--receipt', type=Path)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--reuse', type=Path)
    p.add_argument('--snapshot', type=Path)
    p.add_argument('--packets', type=Path)
    p.add_argument('--case')
    args = p.parse_args(argv)
    c = configuration(args.config)
    if args.command == 'build':
        from .index import build
        result = build(args.release, args.output, c, reuse=args.reuse)
    elif args.command == 'publish':
        from .index import publish
        result = publish(args.build, args.output)
    elif args.command == 'snapshot':
        from .index import snapshot
        result = snapshot(args.build, args.receipt, args.output)
    elif args.command == 'restore':
        from .index import restore
        result = restore(args.build, args.snapshot, args.output)
    elif args.command == 'evaluate':
        result = evaluate(args.release, args.build, args.receipt, c, args.output)
    elif args.command == 'retrieve':
        from .retrieval import incident_packets
        result = incident_packets(args.release, args.build, args.output, args.receipt, c)
    else:
        from .generation import run
        result = run(args.release, args.build, args.packets, args.output, c, preflight=args.command=='preflight', case=args.case)
    print(result)
    if isinstance(result, dict) and (result.get('status') in {'failed', 'source_changed', 'completed_with_failures'}):
        return 1
    return 0


if __name__ == '__main__':
    try:
        status = main()
    except Exception as exc:
        print('Vector command failed: '+type(exc).__name__+'. Inspect configuration and recorded artifacts.')
        status = 2
    raise SystemExit(status)

"""Incident-bound evidence assembly, bounded local generation and strict citations."""
from pathlib import Path
import re
import os
import time
from uuid import uuid4

from jsonschema import Draft202012Validator, ValidationError

from ai.runtime import provenance as shared
from ai.runtime.configuration import configuration as runtime_configuration
from ai.runtime.policy import ProposalPolicy, incident_policy
from ai.runtime.llama_server import LlamaServer
from ai.runtime.contracts import (InvalidOutput, RunnerTimeout, RunnerUnavailable,
                                contract_validators, decision_schema, strict_json)
from ai.runtime.lifecycle import LocalRuntime
from .data import ROOT, digest, identity, incidents, load, save, seal, verified
from .retrieval import incident_query

PROMPT = Path(__file__).with_name('prompt.txt')


def schema(aliases):
    s = decision_schema()
    s['properties']['citation_ids'] = {'type': 'array', 'items': {'enum': aliases},
                                      'uniqueItems': True, 'maxItems': len(aliases)}
    s['required'].append('citation_ids')
    return s


def prepare(client, incident, policy, candidates, config, deadline):
    system = PROMPT.read_text(encoding='utf-8')
    selected = []

    def messages(evidence):
        refs = [{'reference_id': 'R'+str(i+1), 'document_id': e['document_id'],
                 'title': e['title'], 'url': e['source_url'], 'start': e['start'], 'end': e['end'],
                 'text': e['content']} for i, e in enumerate(evidence)]
        s = schema([r['reference_id'] for r in refs])
        import json
        return [{'role': 'system', 'content': system}, {'role': 'user', 'content': json.dumps({
            'untrusted_incident': incident, 'fixed_proposal_policy': policy,
            'reference_passages': refs, 'required_output': s}, ensure_ascii=False)}], s

    final = None
    for e in candidates[:config['generation_passages']]:
        trial = selected+[e]
        msg, s = messages(trial)
        formatted = next(client._request('/apply-template', {'messages': msg}, deadline))['prompt']
        tokens = next(client._request('/tokenize', {'content': formatted, 'add_special': True}, deadline))['tokens']
        if len(tokens) <= config['generation_input_limit']:
            selected = trial
            final = (msg, s, formatted, len(tokens))
    if not selected:
        raise InvalidOutput('No evidence fits input budget', stage='context_budget')
    return (*final, selected)


def validate_decision(raw, output_schema, evidence, incident, policy, trace_id, investigation_id, release_id):
    candidate = strict_json(raw)
    try:
        Draft202012Validator(output_schema).validate(candidate)
    except ValidationError as exc:
        raise InvalidOutput('Decision schema mismatch', stage='decision_schema') from exc
    aliases = {'R'+str(i+1): e for i, e in enumerate(evidence)}
    if re.search(r'\[R\d+\]', candidate['summary']):
        raise InvalidOutput('Use citation_ids as the single citation representation', stage='citations')
    if not set(candidate['citation_ids']) <= set(aliases):
        raise InvalidOutput('Unknown reference identity', stage='citations')
    ProposalPolicy._check_source_roles(candidate['recommended_actions'], incident, policy)
    actions = [ProposalPolicy._action(a, incident, policy) for a in candidate['recommended_actions']]
    if len({(a['target'], a['arguments']['source_ip']) for a in actions}) != len(actions):
        raise InvalidOutput('Duplicate response proposal', stage='proposal_policy')
    result = {k: candidate[k] for k in ['summary', 'triage_verdict', 'risk_level', 'mitre_techniques']}
    # Alias expansion is deterministic identity rendering, not semantic output repair.
    if candidate['citation_ids']:
        result['summary'] += ' ' + ' '.join('['+aliases[a]['chunk_id']+']' for a in candidate['citation_ids'])
    result.update(schema_version='1.0.0', mode='vector', status='ok', incident_id=incident['incident_id'],
                  investigation_id=investigation_id, trace_id=trace_id, recommended_actions=actions,
                  evidence=[{'evidence_id': e['chunk_id'], 'source': e['source'],
                             'source_record_id': e['document_id'], 'content': e['content'],
                             'snapshot_ref': release_id+':sha256:'+e['snapshot_sha256'],
                             'score': e['score'], 'score_kind': 'cosine', 'retrieval_method': 'vector'} for e in evidence])
    contract_validators(ROOT)['investigation-result'].validate(result)
    return result, {'model_summary': candidate['summary'], 'citation_ids': candidate['citation_ids'],
                    'alias_mapping': {a: e['chunk_id'] for a, e in aliases.items()},
                    'integrity_only': 'ID membership verified; semantic claim support requires review'}


def sources(output):
    paths = list(Path(__file__).parent.glob('*.py')) + [PROMPT, Path(__file__).with_name('config.json'),
        Path(__file__).with_name('requirements.txt'), Path(__file__).with_name('Dockerfile'), ROOT/'infrastructure/run-vector.sh']
    paths += [ROOT/p for p in shared.SOURCES]
    paths += [ROOT/'rag/__init__.py', ROOT/'ai/runtime/__init__.py']
    paths += list((ROOT/'backend/contracts/v1').glob('*.schema.json'))
    hashes = {}
    for p in sorted(set(paths)):
        if p.is_symlink():
            raise ValueError('Symlinked execution source')
        rel = p.relative_to(ROOT)
        target = output/'source'/rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(p.read_bytes())
        hashes[str(rel)] = digest(p)
    return hashes


def run(release, build, packets, output, config, *, preflight=False, case=None):
    inputs, release_manifest = incidents(release, config)
    if case:
        inputs = [i for i in inputs if i['incident_id'] == case]
        if not inputs:
            raise ValueError('Unknown selected incident')
    build_manifest = verified(build)
    pm = verified(packets)
    build_sha = digest(Path(build)/'manifest.json')
    if (pm['build_sha256'] != build_sha or pm['configuration_sha256'] != identity(config)
            or build_manifest['release_manifest_sha256'] != config['release_manifest_sha256']):
        raise ValueError('Packet/build/configuration mismatch')
    chunks = {e['chunk_id']: e for e in load(Path(build)/'chunks.json')}
    policy_path = ROOT/config['proposal_policy_path']
    llm_path = ROOT/config['llm_configuration_path']
    if digest(policy_path) != config['proposal_policy_sha256'] or digest(llm_path) != config['llm_configuration_sha256']:
        raise ValueError('Trusted policy/runtime configuration changed')
    base_policy = load(policy_path)
    ProposalPolicy._check_policy(base_policy)
    runtime = runtime_configuration(llm_path)
    if config['generation_input_limit'] > runtime['max_input_tokens']:
        raise ValueError('Context configuration exceeds runtime limit')
    client = LlamaServer(port=runtime['port'], max_input_tokens=runtime['max_input_tokens'],
                         max_output_tokens=runtime['max_output_tokens'], seed=runtime['seed'],
                         context_tokens=runtime['context_tokens'])
    output = Path(output)
    if output.resolve().is_relative_to(Path(release).resolve()):
        raise ValueError('Output cannot modify source release')
    output.mkdir(parents=True, exist_ok=False)
    freeze = {'source_sha256': sources(output), 'configuration': config,
              'configuration_sha256': identity(config), 'build_sha256': build_sha,
              'packet_manifest_sha256': digest(Path(packets)/'manifest.json'),
              'runtime': runtime, 'execution_image': os.environ.get('VECTOR_EXECUTION_IMAGE', 'not_recorded'), 'source_manifest_sha256': config['release_manifest_sha256'],
              'implementation_id': shared.IMPLEMENTATION_ID, 'frozen_at_utc': shared.utc(), 'commit': shared.git_state(), 'preflight': preflight}
    save(output/'freeze.json', freeze)
    report = {'run_id': 'RUN-'+uuid4().hex, 'mode': 'vector', 'started_at': shared.utc(), 'status': 'running',
              'counts': {'intended': len(inputs), 'attempted': 0, 'valid': 0, 'failed': 0},
              'generation_attempts': 0, 'evaluator_loaded': False, 'external_network': False, 'execution_enabled': False,
              'quality': 'Unscored; contract and citation identities do not prove reasoning correctness.'}
    versions = {'model': runtime['model_sha256'], 'prompt': digest(PROMPT),
                'dataset': config['release_manifest_sha256'], 'configuration': identity(freeze),
                'commit': freeze['commit'][0]}
    try:
        with LocalRuntime(runtime, output/'runtime.log'):
            for incident in inputs:
                iid = incident['incident_id']
                folder = output/iid
                folder.mkdir()
                started, begin = shared.utc(), time.monotonic()
                packet = load(Path(packets)/(iid+'.json'))
                if (packet['incident_id'] != iid or packet['incident_sha256'] != identity(incident)
                        or packet['query'] != incident_query(incident) or packet['build_sha256'] != build_sha
                        or packet['configuration_sha256'] != identity(config)):
                    raise ValueError('Incident retrieval binding mismatch')
                for e in packet['evidence']:
                    expected = chunks.get(e['chunk_id'])
                    if expected is None or {k: v for k, v in e.items() if k != 'score'} != expected:
                        raise ValueError('Retrieved passage differs from verified corpus')
                policy = incident_policy(base_policy, incident, release_manifest)
                save(folder/'input.json', incident)
                save(folder/'retrieval.json', packet)
                save(folder/'policy.json', policy)
                error, result, raw, measurement = None, None, None, None
                tid, inv = 'TRC-'+uuid4().hex, 'INV-'+uuid4().hex
                report['counts']['attempted'] += 1
                try:
                    if not packet['evidence']:
                        raise InvalidOutput('Empty retrieval', stage='retrieval')
                    deadline = time.monotonic()+runtime['timeout_seconds']
                    msg, output_schema, formatted, n, evidence = prepare(client, incident, policy, packet['evidence'], config, deadline)
                    save(folder/'messages.json', msg)
                    save(folder/'formatted-prompt.json', formatted)
                    save(folder/'context.json', {'input_tokens': n, 'selected_evidence': evidence,
                                                'reference_count': len(evidence), 'output_schema': output_schema})
                    if not preflight:
                        report['generation_attempts'] += 1
                        raw, measurement = client.generate(msg, output_schema, deadline)
                        result, citations = validate_decision(raw, output_schema, evidence, incident, policy,
                                                              tid, inv, config['release_id'])
                        save(folder/'result.json', result)
                        save(folder/'citations.json', citations)
                    report['counts']['valid'] += 1
                except (InvalidOutput, RunnerTimeout, RunnerUnavailable, ValueError) as exc:
                    error = {'code': 'timeout' if isinstance(exc, RunnerTimeout) else 'invalid_output',
                             'message': 'Vector investigation did not produce a verified result.',
                             'retryable': isinstance(exc, (RunnerTimeout, RunnerUnavailable))}
                    save(folder/'failure.json', {**error, 'stage': getattr(exc, 'stage', 'output_validation')})
                    report['counts']['failed'] += 1
                save(folder/'raw-output.json', raw)
                save(folder/'measurements.json', measurement)
                if not preflight:
                    step = {'step': 1, 'component': 'inference', 'input_ref': iid+'/input.json',
                            'status': 'error' if error else 'ok', 'latency_ms': (time.monotonic()-begin)*1000}
                    if error:
                        step['error'] = error
                    else:
                        step['output_ref'] = iid+'/result.json'
                    trace = {'schema_version': '1.0.0', 'trace_id': tid, 'incident_id': iid,
                             'workflow': 'baseline', 'mode': 'vector', 'versions': versions,
                             'started_at': started, 'finished_at': shared.utc(), 'status': step['status'], 'steps': [step]}
                    if error:
                        trace['error'] = error
                    contract_validators(ROOT)['trace'].validate(trace)
                    save(folder/'trace.json', trace)
                print(iid+': '+('failed' if error else 'preflight passed' if preflight else 'contract-valid'), flush=True)
    except BaseException as exc:
        report['status'] = 'failed'
        report['failure_type'] = type(exc).__name__
        raise
    finally:
        if report['status'] != 'failed':
            report['status'] = 'completed_with_failures' if report['counts']['failed'] else 'completed'
        report['finished_at'] = shared.utc()
        report['counts']['not_attempted'] = len(inputs)-report['counts']['attempted']
        for rel, expected in freeze['source_sha256'].items():
            if digest(ROOT/rel) != expected:
                report['status'] = 'source_changed'
        save(output/'report.json', report)
        seal(output, {'format_version': '1.0.0', 'run_id': report['run_id'], 'report_sha256': digest(output/'report.json')})
        # Include nested evidence and source snapshots, not only root-level metadata.
        save(output/'artifact-manifest.json', {str(p.relative_to(output)): digest(p)
             for p in sorted(output.rglob('*')) if p.is_file()})
    return report

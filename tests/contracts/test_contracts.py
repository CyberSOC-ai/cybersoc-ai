"""Offline tests for the S0-T03 interchange contracts; no runtime authorization."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / 'backend/contracts/v1'
NAMES = ('incident', 'retrieval-request', 'retrieval-response',
         'investigation-result', 'response-action', 'trace')


def reject_network(uri):
    raise RuntimeError(f'Unregistered schema reference: {uri}')


class ContractsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schemas = {p.stem.removesuffix('.schema'): json.loads(p.read_text())
                       for p in SCHEMAS.glob('*.schema.json')}
        cls.registry = Registry(retrieve=reject_network).with_resources(
            (schema['$id'], Resource.from_contents(schema))
            for schema in cls.schemas.values()
        )
        cls.validators = {
            name: Draft202012Validator(schema, registry=cls.registry,
                                       format_checker=FormatChecker())
            for name, schema in cls.schemas.items()
        }
        cls.examples = {name: json.loads((SCHEMAS / 'examples' / f'{name}.json').read_text())
                        for name in NAMES}

    def assertInvalid(self, name, value):
        self.assertTrue(list(self.validators[name].iter_errors(value)), name)

    def mutate(self, name, path, value):
        record = deepcopy(self.examples[name])
        target = record
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        self.assertInvalid(name, record)

    def test_schema_definitions(self):
        for name, schema in self.schemas.items():
            with self.subTest(schema=name):
                Draft202012Validator.check_schema(schema)

    def test_valid_examples(self):
        for name, value in self.examples.items():
            with self.subTest(contract=name):
                self.validators[name].validate(value)

    def test_retrieval_sources_match_evidence_sources(self):
        sources = self.schemas['common']['$defs']['evidence']['properties']['source']['enum']
        record = deepcopy(self.examples['retrieval-request'])
        record['filters']['sources'] = sources
        self.validators['retrieval-request'].validate(record)
        record['filters']['sources'] = ['detection_rule', 'playbook']
        self.validators['retrieval-request'].validate(record)
        for values in (['playbook', 'playbook'], ['invented']):
            record['filters']['sources'] = values
            self.assertInvalid('retrieval-request', record)

    def test_required_fields_and_closed_objects(self):
        for name in NAMES:
            for field in self.schemas[name]['required']:
                with self.subTest(contract=name, missing=field):
                    record = deepcopy(self.examples[name])
                    del record[field]
                    self.assertInvalid(name, record)
            self.mutate(name, ['unexpected'], 'not accepted')
            self.mutate(name, ['schema_version'], '2.0.0')

    def test_incident_identity_time_and_entities(self):
        for value in ('', 'id with spaces', 'x' * 129):
            self.mutate('incident', ['incident_id'], value)
        for value in ('2026-02-30T12:00:00Z', '2026-10-13T12:00:00+01:00', 'yesterday'):
            self.mutate('incident', ['timestamp'], value)
        self.mutate('incident', ['entities', 0, 'type'], 'shell')
        self.mutate('incident', ['ingestion_kind'], 'unknown')
        self.mutate('incident', ['severity'], 'urgent')
        self.mutate('incident', ['entities', 1, 'value'], 'not an IP')
        for kind, value in (('domain', 'invalid domain'), ('hash', 'not-a-digest')):
            self.mutate('incident', ['entities', 1], {'type': kind, 'value': value})

    def test_strict_identifier_boundaries(self):
        for value in ('A', 'A' * 128, 'INC-001.v1:source'):
            record = deepcopy(self.examples['incident'])
            record['incident_id'] = value
            self.validators['incident'].validate(record)
        for suffix in ('\n', '\r', '\r\n', '\u2028', '\u2029', ' ', '\t'):
            with self.subTest(suffix=repr(suffix)):
                self.mutate('incident', ['incident_id'], 'INC-001' + suffix)
                self.mutate('retrieval-response', ['evidence', 0, 'evidence_id'], 'EVD-001' + suffix)
        for value in ('', 'A' * 129, 'INC\n001', '_INC-001'):
            self.mutate('incident', ['incident_id'], value)

    def test_strict_mitre_technique_boundaries(self):
        for value in ('T1110', 'T1110.001'):
            record = deepcopy(self.examples['investigation-result'])
            record['mitre_techniques'] = [value]
            self.validators['investigation-result'].validate(record)
        for value in ('T1110\n', 'T1110.001\n', 'T1110\r\n', 'T1110\u2028',
                      ' T1110', 'T1110 ', 'T1110x001', 'T111', 'T11100', 'T1110.01'):
            with self.subTest(value=repr(value)):
                self.mutate('investigation-result', ['mitre_techniques'], [value])

    def test_strict_hash_boundaries(self):
        for length in (32, 40, 64):
            for letter in ('a', 'A'):
                valid = letter * length
                record = deepcopy(self.examples['incident'])
                record['entities'] = [{'type': 'hash', 'value': valid}]
                self.validators['incident'].validate(record)
                for suffix in ('\n', '\r\n', '\u2028', ' '):
                    with self.subTest(length=length, suffix=repr(suffix)):
                        self.mutate('incident', ['entities'], [{'type': 'hash', 'value': valid + suffix}])
        for value in ('a' * 31, 'a' * 33, 'a' * 63, 'a' * 65, 'g' * 64, 'a' * 32 + '\n' + 'a' * 32):
            self.mutate('incident', ['entities'], [{'type': 'hash', 'value': value}])

    def test_strict_digest_and_commit_boundaries(self):
        for suffix in ('\n', '\r\n', '\u2028', ' '):
            self.mutate('trace', ['versions', 'commit'], 'a' * 40 + suffix)
            record = self.approved_action()
            record['approval']['proposal_digest'] = 'a' * 64 + suffix
            self.assertInvalid('response-action', record)
        for length in (39, 41):
            self.mutate('trace', ['versions', 'commit'], 'a' * length)
        for value in ('a' * 63, 'a' * 65, 'A' * 64, 'g' * 64):
            record = self.approved_action()
            record['approval']['proposal_digest'] = value
            self.assertInvalid('response-action', record)

    def test_strict_utc_suffix(self):
        # Test the schema pattern without format checks too: the end assertion
        # must reject trailing content independently of the optional checker.
        utc = self.schemas['common']['$defs']['utc']
        validator = Draft202012Validator(utc)
        validator.validate('2026-10-14T12:00:00Z')
        for suffix in ('\n', '\r', '\r\n', '\u2028', '\u2029', ' ', 'x'):
            value = '2026-10-14T12:00:00Z' + suffix
            with self.subTest(suffix=repr(suffix)):
                self.assertTrue(list(validator.iter_errors(value)))
                self.mutate('incident', ['timestamp'], value)

    def test_bounded_typed_retrieval(self):
        for value in (0, 101, 1.5, True):
            self.mutate('retrieval-request', ['top_k'], value)
        self.mutate('retrieval-request', ['mode'], 'no_rag')
        self.mutate('retrieval-request', ['query'], 'x' * 4001)
        self.mutate('retrieval-request', ['filters', 'cypher'], 'MATCH (n) RETURN n')
        self.mutate('retrieval-request', ['filters', 'sources'], ['soc_log', 'soc_log'])

    def test_provenance_and_score_semantics(self):
        for field in ('evidence_id', 'source_record_id', 'snapshot_ref'):
            record = deepcopy(self.examples['retrieval-response'])
            del record['evidence'][0][field]
            self.assertInvalid('retrieval-response', record)
        self.mutate('retrieval-response', ['evidence', 0, 'source'], 'unknown')
        self.mutate('retrieval-response', ['evidence', 0, 'score_kind'], 'none')
        record = deepcopy(self.examples['retrieval-response'])
        record['evidence'][0].update(score=None, score_kind='none')
        self.validators['retrieval-response'].validate(record)

    def test_empty_retrieval_is_success_not_failure(self):
        record = deepcopy(self.examples['retrieval-response'])
        record['evidence'] = []
        self.validators['retrieval-response'].validate(record)
        record['status'] = 'error'
        self.assertInvalid('retrieval-response', record)
        record['error'] = {'code': 'dependency_unavailable', 'message': 'Store unavailable',
                           'retryable': True}
        self.validators['retrieval-response'].validate(record)
        record['evidence'] = self.examples['retrieval-response']['evidence']
        self.assertInvalid('retrieval-response', record)
        record.update(status='ok', evidence=[])
        self.assertInvalid('retrieval-response', record)

    def test_investigation_outcomes(self):
        self.mutate('investigation-result', ['mode'], 'no_rag')
        self.mutate('investigation-result', ['mitre_techniques'], ['Tbad'])
        self.mutate('investigation-result', ['triage_verdict'], 'malicious')
        record = deepcopy(self.examples['investigation-result'])
        record.update(mode='no_rag', evidence=[], recommended_actions=[])
        self.validators['investigation-result'].validate(record)
        for field in ('summary', 'triage_verdict', 'risk_level', 'mitre_techniques'):
            del record[field]
        record.update(status='error', error={'code': 'invalid_output',
                                           'message': 'Invalid candidate', 'retryable': False})
        self.validators['investigation-result'].validate(record)
        record['summary'] = 'Invented successful conclusion'
        self.assertInvalid('investigation-result', record)

    def test_actions_cannot_waive_approval_or_inject_commands(self):
        self.mutate('response-action', ['requires_approval'], False)
        self.mutate('response-action', ['action_type'], 'run_shell')
        self.mutate('response-action', ['arguments', 'command'], 'arbitrary command')
        self.mutate('response-action', ['arguments', 'source_ip'], 'example.com')
        for value in (0, 65536):
            self.mutate('response-action', ['arguments', 'port'], value)
        for value in (0, 3601):
            self.mutate('response-action', ['arguments', 'duration_seconds'], value)
        for field in ('revision', 'target_inventory_revision', 'environment_id',
                      'policy_version', 'idempotency_key'):
            record = deepcopy(self.examples['response-action'])
            del record[field]
            self.assertInvalid('response-action', record)

    def approved_action(self):
        record = deepcopy(self.examples['response-action'])
        record.update(status='approved', approval={
            'approval_id': 'APR-001', 'actor_id': 'analyst-example', 'decision': 'approve',
            'decided_at': '2026-10-13T12:01:00Z', 'expires_at': '2026-10-13T12:02:00Z',
            'proposal_digest': 'a' * 64, 'audit_ref': 'fixture:audit-001'})
        return record

    def test_action_state_record_requirements(self):
        record = self.approved_action()
        self.validators['response-action'].validate(record)
        invalid = deepcopy(record)
        invalid['execution_ref'] = 'fixture:premature-execution'
        self.assertInvalid('response-action', invalid)
        invalid = deepcopy(record)
        invalid['error'] = {'code': 'timeout', 'message': 'Contradictory outcome', 'retryable': False}
        self.assertInvalid('response-action', invalid)
        record['approval']['decision'] = 'reject'
        self.assertInvalid('response-action', record)
        record['status'] = 'rejected'
        self.validators['response-action'].validate(record)
        record = self.approved_action()
        record['status'] = 'executing'
        self.assertInvalid('response-action', record)
        record['execution_ref'] = 'fixture:execution-001'
        self.validators['response-action'].validate(record)
        for status in ('failed', 'unknown'):
            record['status'] = status
            self.assertInvalid('response-action', record)
        record['error'] = {'code': 'timeout', 'message': 'Reconciliation required', 'retryable': False}
        self.validators['response-action'].validate(record)
        record['status'] = 'proposed'
        self.assertInvalid('response-action', record)
        result = deepcopy(self.examples['investigation-result'])
        result['recommended_actions'] = [self.approved_action()]
        self.assertInvalid('investigation-result', result)

    def test_trace_baseline_and_agent_forms(self):
        self.mutate('trace', ['steps', 0, 'latency_ms'], -1)
        self.mutate('trace', ['versions', 'commit'], 'not-a-sha')
        self.mutate('trace', ['steps', 0, 'component'], 'agent')
        record = deepcopy(self.examples['trace'])
        record['workflow'] = 'single_agent'
        record['steps'][0].update(component='agent', agent='triage')
        self.validators['trace'].validate(record)
        record['workflow'] = 'multi_agent'
        self.validators['trace'].validate(record)
        record['steps'][0].update(status='error', error={
            'code': 'timeout', 'message': 'Tool timeout', 'retryable': True})
        record.update(status='error', error=record['steps'][0]['error'])
        self.validators['trace'].validate(record)
        del record['steps'][0]['error']
        self.assertInvalid('trace', record)

    def test_fixture_cross_references(self):
        incident = self.examples['incident']['incident_id']
        trace = self.examples['trace']['trace_id']
        for name in ('investigation-result', 'response-action', 'trace'):
            self.assertEqual(self.examples[name]['incident_id'], incident)
        for name in ('retrieval-request', 'retrieval-response', 'investigation-result'):
            self.assertEqual(self.examples[name]['trace_id'], trace)
        self.assertEqual(self.examples['retrieval-request']['request_id'],
                         self.examples['retrieval-response']['request_id'])
        self.assertEqual(self.examples['investigation-result']['recommended_actions'],
                         [self.examples['response-action']])


if __name__ == '__main__':
    unittest.main()

"""Development-only integration simulations; no model or measured quality claim."""
from copy import deepcopy
from pathlib import Path
import unittest
import re

from ai.evaluation.hashing import read_json
from ai.evaluation.loader import load_evaluator_cases, load_model_inputs
from ai.evaluation.scoring import score_cases
from ai.evaluation.validation import validate_dataset, validators

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / 'datasets/evaluation/soc-eval-v1'


def oracle_output(case):
    """Evaluator-only fake player; never use this function as a model input."""
    label = case['labels']
    policy = read_json(DATASET / 'protocol/runner-policy.json')
    result = {'schema_version': '1.0.0', 'investigation_id': 'INV-' + case['case_id'],
              'incident_id': label['incident_id'], 'trace_id': 'TRC-' + case['case_id'],
              'mode': 'no_rag', 'status': 'ok', 'summary': 'Synthetic test oracle; no model was run.',
              'triage_verdict': label['verdict'], 'risk_level': label['gold_severity'],
              'mitre_techniques': deepcopy(label['mitre_techniques']), 'evidence': [],
              'recommended_actions': []}
    for i, required in enumerate(label['required_actions']):
        action = deepcopy(required)
        action['arguments']['duration_seconds'] = required['arguments']['duration_seconds']['min']
        action.update(schema_version='1.0.0', action_id=f'ACT-{case["case_id"]}-{i}',
                      incident_id=label['incident_id'], revision=1,
                      target_inventory_revision=policy['target_inventory_revision'],
                      environment_id=policy['environment_id'],
                      policy_version=policy['policy_version'], reason='Synthetic matcher test',
                      expected_effect='Scoped fixture traffic restriction', risks='Could interrupt a fixture session',
                      rollback_plan='Fixture only; no execution occurs', requires_approval=True,
                      idempotency_key=f'KEY-{case["case_id"]}-{i}', status='proposed')
        result['recommended_actions'].append(action)
    return result


class FakePlayersTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        validate_dataset(ROOT, DATASET)
        cls.cases = load_evaluator_cases(DATASET, split='development')
        cls.manifest = read_json(DATASET / 'manifest.json')
        cls.validator = validators(ROOT, DATASET)['investigation-result']

    def score(self, predictions):
        return score_cases(self.cases, predictions, self.manifest['severity_universe'],
                           self.manifest['mitre_universe'], self.validator)

    def test_oracle_matches_every_development_label(self):
        predictions = {c['case_id']: oracle_output(c) for c in self.cases}
        for cid, result in predictions.items():
            self.assertEqual(list(self.validator.iter_errors(result)), [], f'{cid}: oracle output is not contract-valid')
        scores = self.score(predictions)
        for key, value in (('accuracy', scores['binary']['accuracy']),
                           ('severity macro-F1', scores['severity']['macro_f1']),
                           ('MITRE macro-F1', scores['mitre']['macro_f1']),
                           ('action exact match', scores['action_exact_match'])):
            self.assertEqual(value, 1.0, f'P01-P14: oracle {key} differs from 1 on declared universe')
        for cid, row in scores['per_case'].items():
            self.assertTrue(row['action_exact_match'], f'{cid}: oracle action mismatch')
        self.assertEqual(scores['counts']['valid'], 14, 'P01-P14: oracle lost a valid case')

    def test_constant_verdicts_follow_development_balance(self):
        for verdict, expected in (('true_positive', 6/14), ('false_positive', 8/14)):
            predictions = {c['case_id']: oracle_output(c) for c in self.cases}
            for result in predictions.values():
                result['triage_verdict'] = verdict
            scores = self.score(predictions)
            print(f'Baseline always_{verdict}: accuracy={scores["binary"]["accuracy"]:.6f}', flush=True)
            self.assertEqual(scores['binary']['accuracy'], expected, f'P01-P14: {verdict} differs from class balance')
            self.assertLess(scores['binary']['accuracy'], 0.8, f'P01-P14: {verdict} baseline reveals lopsided pilot')

    def test_undetermined_invalid_and_missing_counts_reconcile(self):
        undetermined = {c['case_id']: oracle_output(c) for c in self.cases}
        for result in undetermined.values():
            result['triage_verdict'] = 'undetermined'
        for name, predictions, valid, failed, not_attempted in (
                ('undetermined', undetermined, 14, 0, 0),
                ('invalid', {c['case_id']: None for c in self.cases}, 0, 14, 0),
                ('missing', {}, 0, 0, 14)):
            scores = self.score(predictions)
            counts = scores['counts']
            self.assertEqual((counts['valid'], counts['failed'], counts['not_attempted']),
                             (valid, failed, not_attempted), f'P01-P14: {name} accounting is wrong')
            self.assertEqual(counts['intended'], valid + failed + not_attempted, f'P01-P14: {name} intended mismatch')
            self.assertEqual(counts['attempted'], valid + failed, f'P01-P14: {name} attempted mismatch')
            self.assertEqual(scores['binary']['accuracy'], None if not_attempted else 0,
                             f'P01-P14: {name} incorrect verdict counted as correct')
            if failed:
                self.assertEqual(scores['action_exact_match'], 0, 'P01-P14: failed outputs received empty-action credit')
                self.assertEqual(scores['binary']['fn'], 6, 'P01-P14: failed true incidents lost FN')

    def test_wrong_incident_id_and_error_output_fail(self):
        for kind in ('wrong_id', 'error', 'invalid_action'):
            predictions = {c['case_id']: oracle_output(c) for c in self.cases}
            if kind == 'wrong_id':
                predictions['P01']['incident_id'] = 'INC-WRONG'
            elif kind == 'invalid_action':
                predictions['P01']['recommended_actions'][0]['arguments']['port'] = 0
            else:
                result = predictions['P01']
                for field in ('summary', 'triage_verdict', 'risk_level', 'mitre_techniques'):
                    del result[field]
                result.update(status='error', recommended_actions=[],
                              error={'code': 'timeout', 'message': 'Synthetic timeout', 'retryable': True})
            scores = self.score(predictions)
            self.assertEqual(scores['per_case']['P01']['status'], 'failed', f'P01: {kind} accepted as success')
            self.assertFalse(scores['per_case']['P01']['action_exact_match'], f'P01: {kind} earned action credit')
            self.assertEqual(scores['binary']['accuracy'], 13/14, f'P01: {kind} omitted from denominator')

    def test_incident_keys_and_duplicate_rejection(self):
        predictions = {c['input']['incident_id']: oracle_output(c) for c in self.cases}
        scores = self.score(predictions)
        self.assertEqual(scores['binary']['accuracy'], 1, 'P01-P14: incident-key oracle differs')
        case_keys = {c['case_id']: oracle_output(c) for c in self.cases}
        self.assertEqual(scores, self.score(case_keys), 'P01-P14: key formats change scores')
        for entries, reason in (
                ([('INC-UNKNOWN', None)], 'unknown incident_id'),
                (list(predictions.items()) + [('INC-PILOT-001', None)], 'P01: duplicate'),
                (list(predictions.items()) + [('P01', None)], 'P01: duplicate')):
            with self.assertRaisesRegex(ValueError, reason, msg='P01: invalid prediction keys accepted'):
                self.score(entries)
        cases = deepcopy(self.cases)
        cases[1]['input']['incident_id'] = cases[0]['input']['incident_id']
        with self.assertRaisesRegex(ValueError, 'P02: duplicate incident_id', msg='P02: duplicate incident accepted'):
            score_cases(cases, {}, self.manifest['severity_universe'],
                        self.manifest['mitre_universe'], self.validator)

    def test_shortcut_players_use_only_model_inputs_and_fixed_policy(self):
        # No oracle values or evaluator bundles are passed to these players.
        inputs = load_model_inputs(DATASET, 'development')
        policy = read_json(DATASET / 'protocol/runner-policy.json')
        for name in ('ticket', 'wording', 'copy_detector_severity', 'never_action', 'always_block'):
            predictions = {i['incident_id']: shortcut_output(i, policy, name) for i in inputs}
            scores = self.score(predictions)
            self.assertEqual(scores['counts']['valid'], len(inputs),
                             f'P01-P14: {name} must not get a low score from malformed outputs')
            if name in ('ticket', 'wording'):
                value = scores['binary']['accuracy']
                correct = round(value * len(inputs))
                metric = 'verdict accuracy'
            elif name == 'copy_detector_severity':
                correct = sum(predictions[c['input']['incident_id']]['risk_level'] ==
                              c['labels']['gold_severity'] for c in self.cases)
                value = correct / len(inputs)
                metric = 'severity accuracy'
                self.assertGreaterEqual(value, .2, 'P01-P14: detector agreement below owner range')
                self.assertLessEqual(value, .6, 'P01-P14: detector severity remains a shortcut')
            else:
                value = scores['action_exact_match']
                correct = round(value * len(inputs))
                metric = 'action exact match'
            print(f'Baseline {name}: {metric}={correct}/{len(inputs)}={value:.6f}', flush=True)
            self.assertLess(value, .80, f'P01-P14: {name} shortcut >= 0.80; fix the data')


def shortcut_output(incident, policy, name):
    """Input-only fake runner; policy is identical for every incident."""
    iid = incident['incident_id']
    result = {'schema_version': '1.0.0', 'investigation_id': 'INV-' + iid,
              'incident_id': iid, 'trace_id': 'TRC-' + iid, 'mode': 'no_rag',
              'status': 'ok', 'summary': 'Input-only shortcut simulation.',
              'triage_verdict': 'false_positive', 'risk_level': incident['severity'],
              'mitre_techniques': [], 'evidence': [], 'recommended_actions': []}
    text = incident['description'].lower()
    if name == 'ticket':
        result['triage_verdict'] = 'false_positive' if ('fix-' in text or 'ticket' in text) else 'true_positive'
    elif name == 'wording':
        result['triage_verdict'] = ('true_positive' if re.search(
            r'denies|not authorized|unapproved|no access was granted', text) else 'false_positive')
    elif name == 'always_block':
        # Local-only telemetry has no remote source; never invent an IP for it.
        ips = [e['value'] for e in incident['entities'] if e['type'] == 'ip']
        if ips:
            endpoint = next(e['value'] for e in incident['entities'] if e['type'] == 'host')
            rule = policy['ssh_containment']
            action = dict(policy['response_defaults'])
            action.update(action_id='ACT-' + iid, incident_id=iid, action_type=policy['action_type'],
                          target=endpoint, target_inventory_revision=policy['target_inventory_revision'],
                          environment_id=policy['environment_id'], policy_version=policy['policy_version'],
                          arguments={'source_ip': ips[0], 'port': rule['port'], 'protocol': rule['protocol'],
                                     'duration_seconds': rule['default_duration_seconds']},
                          reason='Input-only baseline', expected_effect='Scoped fixture block',
                          risks='May interrupt a session', rollback_plan='Expiry; no execution',
                          idempotency_key='KEY-' + iid)
            result['recommended_actions'] = [action]
    return result


if __name__ == '__main__':
    unittest.main()

"""Development-only integration simulations; no model or measured quality claim."""
from copy import deepcopy
from pathlib import Path
import unittest

from ai.evaluation.hashing import read_json
from ai.evaluation.loader import load_evaluator_cases
from ai.evaluation.scoring import score_cases
from ai.evaluation.validation import validate_dataset, validators

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / 'datasets/evaluation/soc-eval-v1'


def oracle_output(case):
    """Evaluator-only fake player; never use this function as a model input."""
    label, context = case['labels'], case['context']
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
                      target_inventory_revision=context['fixture_inventory']['inventory_revision'],
                      environment_id=context['fixture_inventory']['environment_id'],
                      policy_version='draft-pilot-policy', reason='Synthetic matcher test',
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
            self.assertEqual(value, 1.0, f'P01-P10: oracle {key} differs from 1 on declared universe')
        for cid, row in scores['per_case'].items():
            self.assertTrue(row['action_exact_match'], f'{cid}: oracle action mismatch')
        self.assertEqual(scores['counts']['valid'], 10, 'P01-P10: oracle lost a valid case')

    def test_constant_verdicts_follow_development_balance(self):
        for verdict, expected in (('true_positive', 0.4), ('false_positive', 0.6)):
            predictions = {c['case_id']: oracle_output(c) for c in self.cases}
            for result in predictions.values():
                result['triage_verdict'] = verdict
            scores = self.score(predictions)
            self.assertEqual(scores['binary']['accuracy'], expected, f'P01-P10: {verdict} differs from class balance')
            self.assertLess(scores['binary']['accuracy'], 0.8, f'P01-P10: {verdict} baseline reveals lopsided pilot')

    def test_undetermined_invalid_and_missing_counts_reconcile(self):
        undetermined = {c['case_id']: oracle_output(c) for c in self.cases}
        for result in undetermined.values():
            result['triage_verdict'] = 'undetermined'
        for name, predictions, valid, failed, not_attempted in (
                ('undetermined', undetermined, 10, 0, 0),
                ('invalid', {c['case_id']: None for c in self.cases}, 0, 10, 0),
                ('missing', {}, 0, 0, 10)):
            scores = self.score(predictions)
            counts = scores['counts']
            self.assertEqual((counts['valid'], counts['failed'], counts['not_attempted']),
                             (valid, failed, not_attempted), f'P01-P10: {name} accounting is wrong')
            self.assertEqual(counts['intended'], valid + failed + not_attempted, f'P01-P10: {name} intended mismatch')
            self.assertEqual(counts['attempted'], valid + failed, f'P01-P10: {name} attempted mismatch')
            self.assertEqual(scores['binary']['accuracy'], None if not_attempted else 0,
                             f'P01-P10: {name} incorrect verdict counted as correct')
            if failed:
                self.assertEqual(scores['action_exact_match'], 0, 'P01-P10: failed outputs received empty-action credit')
                self.assertEqual(scores['binary']['fn'], 4, 'P01-P10: failed true incidents lost FN')

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
            self.assertEqual(scores['binary']['accuracy'], 0.9, f'P01: {kind} omitted from denominator')


if __name__ == '__main__':
    unittest.main()

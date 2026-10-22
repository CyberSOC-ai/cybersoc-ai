"""Hand-computed metric examples, independent of authored case labels."""
from copy import deepcopy
from pathlib import Path
import unittest

from ai.evaluation.scoring import binary_metrics, macro_f1, match_actions

ROOT = Path(__file__).resolve().parents[2]
TP, FP = 'true_positive', 'false_positive'


def required_action():
    return {'action_type': 'block_ip', 'target': 'linux-01', 'arguments': {
        'source_ip': '192.0.2.10', 'port': 22, 'protocol': 'tcp',
        'duration_seconds': {'min': 300, 'max': 3600}}}


def proposed_action():
    action = required_action()
    action['arguments']['duration_seconds'] = 300
    return action


class ScoringTest(unittest.TestCase):
    def test_exact_action_ignores_generated_ids_and_wording(self):
        action = proposed_action()
        action.update(action_id='GENERATED-9', reason='Different wording', expected_effect='Different prose')
        result = match_actions([required_action()], [action])
        self.assertTrue(result['exact_match'], 'UNIT-action: exact semantic match rejected')
        self.assertEqual((result['precision'], result['recall']), (1, 1), 'UNIT-action: wrong set scores')

    def test_wrong_action_type_target_and_arguments(self):
        for key, value in (('action_type', 'quarantine'), ('target', 'soc-01'),
                           ('source_ip', '192.0.2.11'), ('port', 23), ('protocol', 'udp')):
            action = proposed_action()
            target = action if key in ('action_type', 'target') else action['arguments']
            target[key] = value
            with self.subTest(case_id='UNIT-action', field=key):
                self.assertFalse(match_actions([required_action()], [action])['exact_match'],
                                 f'UNIT-action: wrong {key} incorrectly matched')

    def test_duration_inclusive_boundaries_and_types(self):
        for duration, expected in ((299, False), (300, True), (900, True), (3600, True),
                                   (3601, False), (True, False), (300.0, False)):
            action = proposed_action()
            action['arguments']['duration_seconds'] = duration
            self.assertEqual(match_actions([required_action()], [action])['exact_match'], expected,
                             f'UNIT-action: duration {duration!r} has wrong matching result')

    def test_extra_missing_duplicate_and_empty_actions(self):
        gold, proposed = required_action(), proposed_action()
        for required, actions in (([gold], [proposed, deepcopy(proposed)]), ([gold], []), ([], [proposed])):
            self.assertFalse(match_actions(required, actions)['exact_match'],
                             'UNIT-action: missing/extra action incorrectly matched')
        result = match_actions([], [])
        self.assertTrue(result['exact_match'], 'UNIT-action: empty sets should match')
        self.assertIsNone(result['precision'], 'UNIT-action: empty precision must be null')
        self.assertIsNone(result['recall'], 'UNIT-action: empty recall must be null')
        self.assertEqual(result['null_reasons'], {'precision': 'zero_denominator', 'recall': 'zero_denominator'},
                         'UNIT-action: empty denominator reasons missing')

    def test_overlapping_ranges_use_one_to_one_maximum_match(self):
        broad, narrow = required_action(), required_action()
        narrow['arguments']['duration_seconds'] = {'min': 300, 'max': 300}
        first, second = proposed_action(), proposed_action()
        second['arguments']['duration_seconds'] = 600
        self.assertTrue(match_actions([broad, narrow], [first, second])['exact_match'],
                        'UNIT-action: greedy matching lost an available one-to-one assignment')

    def test_binary_hand_computed_confusion_with_abstentions(self):
        result = binary_metrics([TP, TP, TP, TP, FP, FP, FP, FP],
                                [TP, FP, 'undetermined', None, TP, FP, 'undetermined', None])
        self.assertEqual([result[k] for k in ('tp', 'fp', 'tn', 'fn')], [1, 1, 1, 3],
                         'UNIT-binary: expected TP=1 FP=1 TN=1 FN=3')
        self.assertEqual(result['accuracy'], 2 / 8, 'UNIT-binary: abstentions dropped from accuracy')
        self.assertEqual(result['precision'], 1 / 2, 'UNIT-binary: precision differs from confusion table')
        self.assertEqual(result['recall'], 1 / 4, 'UNIT-binary: true abstentions must add FN')
        self.assertAlmostEqual(result['f1'], 1 / 3, msg='UNIT-binary: F1 differs from hand calculation')
        self.assertEqual((result['abstentions_true_positive'], result['abstentions_false_positive']), (2, 2),
                         'UNIT-binary: abstentions must remain visible by gold class')

    def test_binary_zero_denominators_are_null(self):
        empty = binary_metrics([], [])
        for key in ('accuracy', 'precision', 'recall', 'f1'):
            self.assertIsNone(empty[key], f'UNIT-binary: empty {key} must be null')
            self.assertEqual(empty['null_reasons'][key], 'zero_denominator', f'UNIT-binary: {key} reason missing')
        result = binary_metrics([FP, FP], [FP, None])
        self.assertEqual(result['accuracy'], 0.5, 'UNIT-binary: failed benign output must be incorrect')
        for key in ('precision', 'recall', 'f1'):
            self.assertIsNone(result[key], f'UNIT-binary: benign-only {key} must be null')

    def test_severity_macro_f1_and_zero_support(self):
        result = macro_f1([{'medium'}, {'high'}, {'high'}], [{'medium'}, {'medium'}, None], ['medium', 'high'])
        self.assertAlmostEqual(result['macro_f1'], 1 / 3, msg='UNIT-severity: expected mean of 2/3 and 0')
        self.assertEqual(result['per_label']['high']['fn'], 2, 'UNIT-severity: failed output lost a FN')
        empty = macro_f1([], [], ['high'])['per_label']['high']
        self.assertEqual((empty['f1'], empty['support']), (0, 0), 'UNIT-severity: METRICS zero-support rule violated')
        self.assertIsNone(empty['precision'], 'UNIT-severity: zero precision denominator must be null')
        self.assertIsNone(empty['recall'], 'UNIT-severity: zero recall denominator must be null')

    def test_multilabel_exact_mitre_and_valid_empty_set(self):
        result = macro_f1([{'T1110'}, {'T1136.001'}, set()],
                          [{'T1110.001'}, {'T1136.001'}, {'T1110'}], ['T1110', 'T1136.001'])
        self.assertEqual(result['macro_f1'], 0.5, 'UNIT-MITRE: parent/sub-technique must not match')
        self.assertEqual(result['per_label']['T1110']['fp'], 1, 'UNIT-MITRE: valid empty gold lost false positive')
        self.assertEqual(result['per_label']['T1110']['fn'], 1, 'UNIT-MITRE: missed parent label lost false negative')
        self.assertEqual(result['out_of_universe_predictions'], ['T1110.001'], 'UNIT-MITRE: unknown prediction hidden')
        self.assertIsNone(macro_f1([set()], [set()], [])['macro_f1'], 'UNIT-MITRE: empty universe must be null')

    def test_length_mismatches_are_not_silently_truncated(self):
        with self.assertRaisesRegex(ValueError, 'lengths differ', msg='UNIT-length: unequal rows were silently truncated'):
            binary_metrics([TP], [])
        with self.assertRaisesRegex(ValueError, 'lengths differ', msg='UNIT-length: unequal rows were silently truncated'):
            macro_f1([{'high'}], [], ['high'])


if __name__ == '__main__':
    unittest.main()

"""Dataset-independent, hand-calculated ranking metric checks."""
import unittest

from ai.evaluation.retrieval import aggregate, distinct, score


def hit(record, snapshot='S1'):
    return {'snapshot_ref': snapshot, 'source_record_id': record}


class RetrievalScoringTests(unittest.TestCase):
    def test_hand_calculated_metrics(self):
        hits = [hit(x) for x in 'ABCDE']
        labels = {('S1', x): int(x in 'BCD') for x in 'ABCDE'}
        labels[('S1', 'F')] = 1
        r = score(hits, labels)
        self.assertEqual((r['precision_at_k'], r['recall_at_k_known_references'],
                          r['reciprocal_rank']), (.6, .75, .5))

    def test_deduplication_precedes_cutoff_and_keeps_snapshots_distinct(self):
        r = score([hit('A'), hit('A'), hit('B')], {('S1', 'A'): 0, ('S1', 'B'): 1}, 2)
        self.assertEqual((r['precision_at_k'], r['reciprocal_rank']), (.5, .5))
        self.assertEqual(len(distinct([hit('A'), hit('A', 'S2')])), 2)

    def test_missing_slots_only_score_when_ranking_is_exhausted(self):
        labels = {('S1', 'A'): 1}
        self.assertEqual(score([hit('A')], labels, ranking_exhausted=True)['precision_at_k'], .2)
        self.assertIsNone(score([hit('A')], labels)['precision_at_k'])

    def test_unknown_prefix_is_not_a_negative(self):
        r = score([hit('A'), hit('B')], {('S1', 'B'): 1}, 2)
        for name in ['precision_at_k', 'recall_at_k_known_references', 'reciprocal_rank']:
            self.assertIsNone(r[name])
        self.assertEqual(score([hit('A'), hit('B')], {('S1', 'A'): 1})['reciprocal_rank'], 1)

    def test_rr_is_not_cut_off_at_precision_k(self):
        r = score([hit(str(x)) for x in range(1, 9)],
                  {('S1', str(x)): int(x == 8) for x in range(1, 9)})
        self.assertEqual((r['precision_at_k'], r['recall_at_k_known_references'],
                          r['reciprocal_rank']), (0, 0, .125))

    def test_absence_and_no_relevance_are_not_conflated(self):
        r = score([], {('S1', 'A'): 1}, ranking_exhausted=True)
        self.assertEqual((r['precision_at_k'], r['recall_at_k_known_references'], r['reciprocal_rank']),
                         (0, 0, 0))
        r = score([hit('A')], {('S1', 'A'): 0}, ranking_exhausted=True)
        self.assertIsNone(r['recall_at_k_known_references'])
        self.assertIsNone(r['reciprocal_rank'])
        self.assertIsNone(score([], {('S1', 'A'): 1})['reciprocal_rank'])

    def test_failures_remain_in_coverage(self):
        r = score([], {('S1', 'A'): 1}, status='error')
        self.assertIsNone(r['precision_at_k'])
        combined = aggregate([r, score([hit('A')], {('S1', 'A'): 1}, 1)])
        self.assertEqual(combined['failed'], 1)
        self.assertEqual(combined['metrics']['precision_at_k']['excluded'], 1)
        self.assertIsNone(aggregate([])['metrics']['precision_at_k']['mean_eligible'])
        with self.assertRaises(ValueError):
            score([hit('A')], {}, status='error')

    def test_invalid_types_rejected(self):
        for k in [0, -1, True, 1.5]:
            with self.subTest(k=k), self.assertRaises(ValueError):
                score([], {}, k)
        for labels in [{('S1', 'A'): True}, {('', 'A'): 1}, {'A': 1}]:
            with self.assertRaises(ValueError):
                score([], labels)

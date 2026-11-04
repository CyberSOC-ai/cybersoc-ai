"""Hand-calculated ranking cases and release-integrity regressions."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from ai.evaluation.retrieval import aggregate, distinct, evaluate_bundle, score

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / 'datasets/evaluation/retrieval-dev-v1'
PIN = '4fae58e74a61784b62a7ffeb9e3d79080bfb19446304f26e950a2aa725f10ac6'


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


class RetrievalBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.copy = Path(self.temp.name) / 'bundle'
        shutil.copytree(BUNDLE, self.copy)

    def rewrite(self, filename, mutate):
        path = self.copy / filename
        value = json.loads(path.read_text())
        mutate(value)
        path.write_text(json.dumps(value) + '\n')
        manifest_path = self.copy / 'manifest.json'
        manifest = json.loads(manifest_path.read_text())
        manifest['assets'][filename] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest) + '\n')
        return hashlib.sha256(manifest_path.read_bytes()).hexdigest()

    def test_real_saved_run_replays(self):
        result = evaluate_bundle(BUNDLE, PIN)
        self.assertEqual(result['counts']['successful'], 10)
        metrics = result['counts']['metrics']
        self.assertAlmostEqual(metrics['precision_at_k']['mean_eligible'], .18)
        self.assertAlmostEqual(metrics['recall_at_k_known_references']['mean_eligible'], .9)
        self.assertAlmostEqual(metrics['reciprocal_rank']['mean_eligible'], .8625)
        self.assertEqual(result, evaluate_bundle(BUNDLE, PIN))

    def test_hash_tampering_and_unpinned_manifest(self):
        (self.copy / 'queries.json').write_text('[]')
        with self.assertRaisesRegex(ValueError, 'Asset digest'):
            evaluate_bundle(self.copy, PIN)
        with self.assertRaisesRegex(ValueError, 'Manifest digest'):
            evaluate_bundle(self.copy, '0' * 64)

    def test_duplicate_ids_and_extra_or_missing_queries(self):
        for filename in ['queries.json', 'judgments.json', 'rankings.json']:
            shutil.copyfile(BUNDLE / 'manifest.json', self.copy / 'manifest.json')
            with self.subTest(filename=filename):
                pin = self.rewrite(filename, lambda rows: rows.append(deepcopy(rows[0])))
                with self.assertRaises(ValueError):
                    evaluate_bundle(self.copy, pin)
                shutil.copyfile(BUNDLE / filename, self.copy / filename)
        shutil.copyfile(BUNDLE / 'manifest.json', self.copy / 'manifest.json')
        pin = self.rewrite('rankings.json', lambda rows: rows.pop())
        with self.assertRaisesRegex(ValueError, 'all intended'):
            evaluate_bundle(self.copy, pin)

    def test_mismatched_request_or_source_filter_rejected(self):
        pin = self.rewrite('rankings.json', lambda rows: rows[0].update(query='changed'))
        with self.assertRaisesRegex(ValueError, 'query/filter'):
            evaluate_bundle(self.copy, pin)
        shutil.copyfile(BUNDLE / 'rankings.json', self.copy / 'rankings.json')
        pin = self.rewrite('rankings.json', lambda rows: rows[0]['documents'][0].update(source='soc_log'))
        with self.assertRaisesRegex(ValueError, 'source filter'):
            evaluate_bundle(self.copy, pin)

    def test_unknown_labels_surface_instead_of_optimistic_scores(self):
        def remove(rows):
            rows[:] = [j for j in rows if not (j['query_id'] == 'Q02' and j['relevant'] == 0)]
        pin = self.rewrite('judgments.json', remove)
        result = evaluate_bundle(self.copy, pin)
        case = next(c for c in result['per_query'] if c['query_id'] == 'Q02')
        self.assertIsNone(case['precision_at_k'])
        self.assertIsNone(case['reciprocal_rank'])

    def test_boolean_judgments_rejected(self):
        pin = self.rewrite('judgments.json', lambda rows: rows[0].update(relevant=True))
        with self.assertRaisesRegex(ValueError, 'binary label'):
            evaluate_bundle(self.copy, pin)

    def test_duplicate_json_keys_and_symlinks_rejected(self):
        asset = self.copy / 'queries.json'
        asset.write_text('[{"query_id":"Q01","query_id":"Q02"}]')
        manifest = json.loads((self.copy / 'manifest.json').read_text())
        manifest['assets']['queries.json'] = hashlib.sha256(asset.read_bytes()).hexdigest()
        (self.copy / 'manifest.json').write_text(json.dumps(manifest))
        pin = hashlib.sha256((self.copy / 'manifest.json').read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError, 'duplicate JSON'):
            evaluate_bundle(self.copy, pin)
        asset.unlink()
        asset.symlink_to(BUNDLE / 'queries.json')
        with self.assertRaisesRegex(ValueError, 'Symlinked'):
            evaluate_bundle(self.copy, pin)

    def test_optimized_python_preserves_validation_and_cli_refuses_overwrite(self):
        output = Path(self.temp.name) / 'result.json'
        cmd = [sys.executable, '-O', '-B', '-m', 'ai.evaluation.retrieval',
               '--bundle', str(BUNDLE), '--manifest-sha256', PIN, '--output', str(output)]
        run = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        saved = output.read_bytes()
        rerun = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        self.assertNotEqual(rerun.returncode, 0)
        self.assertEqual(output.read_bytes(), saved)
        cmd[cmd.index(PIN)] = '0' * 64
        failed = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn('Manifest digest', failed.stderr)


if __name__ == '__main__':
    unittest.main()

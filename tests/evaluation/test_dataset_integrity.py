"""Read-only pilot checks; destructive examples use memory or tempfile copies."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from ai.evaluation.hashing import canonical_bytes, digest, parse_json, read_json, sha256, verify
from ai.evaluation.loader import load_evaluator_cases, load_model_inputs
from ai.evaluation.validation import resolve_pointer, validate_case, validate_dataset, validators

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / 'datasets/evaluation/soc-eval-v1'


class DatasetIntegrityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.checks = validators(ROOT, DATASET)
        cls.cases = load_evaluator_cases(DATASET)

    def test_all_input_and_label_schemas(self):
        for case in self.cases:
            cid = case['case_id']
            with self.subTest(case_id=cid):
                for schema, key in (('incident', 'input'), ('labels', 'labels')):
                    errors = [e.message for e in self.checks[schema].iter_errors(case[key])]
                    self.assertEqual(errors, [], f'{cid}: {key} schema errors: {errors}')

    def test_identity_pairing_and_dataset_relations(self):
        cases = validate_dataset(ROOT, DATASET)
        self.assertEqual([c['case_id'] for c in cases], [f'P{i:02d}' for i in range(1, 11)],
                         'P01-P10: pilot membership differs from the approved ten cases')

    def test_input_only_api_never_reads_labels_or_context(self):
        def guarded_read(path):
            path = Path(path)
            self.assertTrue(path.name == 'splits.json' or path.parent.name == 'inputs',
                            f'{path.stem}: model-input loader tried to read evaluator file {path}')
            return read_json(path)
        with patch('ai.evaluation.loader.read_json', side_effect=guarded_read):
            inputs = load_model_inputs(DATASET)
        for case, incident in zip(self.cases, inputs):
            self.assertEqual(incident, case['input'], f"{case['case_id']}: model input changed")
        inputs[0]['description'] = 'caller mutation'
        self.assertNotEqual(load_model_inputs(DATASET)[0]['description'], 'caller mutation',
                            'P01: caller mutation escaped into the dataset')
        self.assertEqual(load_model_inputs(DATASET, 'test'), [], 'test split: must be empty')

    def test_gold_annotations_and_rationale_are_not_model_visible(self):
        for case in self.cases:
            with self.subTest(case_id=case['case_id']):
                validate_case(case, self.checks)
        for text in ('required_actions', self.cases[0]['labels']['rationale'], 'T1110', 'true_positive'):
            case = deepcopy(self.cases[0])
            case['input']['description'] += ' ' + text
            with self.subTest(case_id='P01', leak=text), self.assertRaisesRegex(ValueError, 'P01:.*(gold|annotation)', msg='P01: annotation leak was not rejected'):
                validate_case(case, self.checks)

    def test_evidence_locators_resolve_and_quotes_exist(self):
        for case in self.cases:
            for evidence in case['labels']['gold_evidence']:
                locator = evidence['locator']
                value = resolve_pointer(case['input'], locator['json_pointer'])
                self.assertIn(locator['quoted_substring'], value,
                              f"{case['case_id']}: evidence {evidence['id']} quote missing")
        for pointer, quote in (('/absent', 'x'), ('/description', 'not in the incident')):
            case = deepcopy(self.cases[0])
            case['labels']['gold_evidence'][0]['locator'] = {
                'json_pointer': pointer, 'quoted_substring': quote}
            with self.subTest(case_id='P01', pointer=pointer), self.assertRaisesRegex(ValueError, 'P01:.*(locator|substring)', msg='P01: broken evidence was not rejected'):
                validate_case(case, self.checks)
        self.assertEqual(resolve_pointer({'a/b': {'~x': ['yes']}}, '/a~1b/~0x/0'), 'yes',
                         'UNIT-pointer: escaped keys must resolve')
        with self.assertRaisesRegex(ValueError, 'invalid array index', msg='UNIT-pointer: invalid index was not rejected'):
            resolve_pointer(['x'], '/01')

    def test_schema_rejects_bad_label_values(self):
        for key, value in (('verdict', 'undetermined'), ('gold_severity', 'urgent'),
                           ('false_positive_type', 'insufficient_context'),
                           ('mitre_techniques', ['T1110\n'])):
            label = deepcopy(self.cases[0]['labels'])
            label[key] = value
            with self.subTest(case_id='P01', field=key):
                self.assertTrue(list(self.checks['labels'].iter_errors(label)),
                                f'P01: invalid {key} was accepted')
        for value in (None, ''):
            label = deepcopy(self.cases[2]['labels'])
            label['mitre_reason'] = value
            self.assertTrue(list(self.checks['labels'].iter_errors(label)),
                            'P03: empty technique set accepted without a reason')
        for key, value in (('duration_seconds', {'min': 0, 'max': 3601}),
                           ('source_ip', '999.1.1.1'), ('port', 65536), ('protocol', 'icmp')):
            label = deepcopy(self.cases[0]['labels'])
            label['required_actions'][0]['arguments'][key] = value
            self.assertTrue(list(self.checks['labels'].iter_errors(label)),
                            f'P01: invalid action argument {key} accepted')

    def test_relational_errors_name_case(self):
        mutations = [
            ('identity', lambda c: c['context'].update(incident_id='INC-WRONG'), 'incident_id'),
            ('range', lambda c: c['labels']['required_actions'][0]['arguments'].update(
                duration_seconds={'min': 600, 'max': 300}), 'min exceeds max'),
            ('target', lambda c: c['labels']['required_actions'][0].update(target='soc-01'), 'target'),
            ('source', lambda c: c['labels']['required_actions'][0]['arguments'].update(
                source_ip='192.0.2.99'), 'source_ip')]
        for name, mutate, reason in mutations:
            case = deepcopy(self.cases[0])
            mutate(case)
            with self.subTest(case_id='P01', mutation=name), self.assertRaisesRegex(ValueError, 'P01:.*' + reason, msg=f'P01: {name} error was not rejected'):
                validate_case(case, self.checks)

    def test_missing_or_orphan_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'pilot'
            shutil.copytree(DATASET, root)
            (root / 'labels/P01.json').unlink()
            with self.assertRaisesRegex(ValueError, 'labels:.*P01', msg='P01: missing label was not rejected'):
                validate_dataset(ROOT, root, verify_hashes=False)

    def test_duplicate_incident_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'pilot'
            shutil.copytree(DATASET, root)
            for folder in ('inputs', 'labels', 'context'):
                path = root / folder / 'P02.json'
                data = read_json(path)
                data['incident_id'] = self.cases[0]['input']['incident_id']
                path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'P02: duplicate incident_id', msg='P02: duplicate incident was not rejected'):
                validate_dataset(ROOT, root, verify_hashes=False)

    def test_split_overlap_and_duplicate_membership_are_rejected(self):
        for duplicate in (False, True):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / 'pilot'
                shutil.copytree(DATASET, root)
                splits = read_json(root / 'splits.json')
                entry = splits['development'][1]
                if not duplicate:
                    splits['development'].remove(entry)
                splits['test'].append(entry)
                (root / 'splits.json').write_text(json.dumps(splits))
                with self.subTest(case_id='P02', duplicate=duplicate), self.assertRaisesRegex(ValueError, 'P02:.*(split|group)', msg='P02: split leakage was not rejected'):
                    validate_dataset(ROOT, root, verify_hashes=False)

    def test_label_split_disagreement_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'pilot'
            shutil.copytree(DATASET, root)
            path = root / 'labels/P01.json'
            label = read_json(path)
            label['split'] = 'test'
            path.write_text(json.dumps(label))
            with self.assertRaisesRegex(ValueError, 'P01: label split/group disagrees', msg='P01: split mismatch was not rejected'):
                validate_dataset(ROOT, root, verify_hashes=False)

    def test_hashes_and_external_manifest_pin(self):
        expected = sha256((DATASET / 'manifest.json').read_bytes())
        verify(DATASET, expected_manifest_sha256=expected)
        with self.assertRaisesRegex(ValueError, 'manifest.json:.*externally pinned', msg='manifest.json: wrong external pin was accepted'):
            verify(DATASET, expected_manifest_sha256='0' * 64)

    def test_tampering_each_component_fails_verification(self):
        for folder in ('inputs', 'labels', 'context'):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / 'pilot'
                shutil.copytree(DATASET, root)
                path = root / folder / 'P01.json'
                # Change one byte, retaining valid JSON and unchanged pinned hashes.
                path.write_bytes(path.read_bytes().replace(b'INC-PILOT-001', b'INC-PILOT-009', 1))
                with self.subTest(case_id='P01', folder=folder), self.assertRaisesRegex(ValueError, f'P01: {folder}/P01.json.*mismatch', msg=f'P01: tampered {folder} was accepted'):
                    verify(root)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'pilot'
            shutil.copytree(DATASET, root)
            path = root / 'inputs/P01.json'
            path.write_bytes(path.read_bytes() + b' ')
            with self.assertRaisesRegex(ValueError, 'P01:.*raw SHA-256 mismatch', msg='P01: raw-byte tamper was accepted'):
                verify(root)

    def test_canonical_json_is_strict_and_deterministic(self):
        self.assertEqual(canonical_bytes({'b': 2, 'a': 'é'}), b'{"a":"\xc3\xa9","b":2}',
                         'UNIT-canonical: unexpected canonical UTF-8 bytes')
        self.assertEqual(digest({'a': 1, 'b': [2, 3]}), digest({'b': [2, 3], 'a': 1}),
                         'UNIT-canonical: key order changed digest')
        self.assertNotEqual(digest([1, 2]), digest([2, 1]), 'UNIT-canonical: array order was lost')
        for data in (b'{"a":1,"a":2}', b'1.0', b'1e2', b'NaN', b'Infinity',
                     b'\xff', b'\xef\xbb\xbf{}', b'"\\ud800"'):
            with self.subTest(case_id='UNIT-canonical', data=data), self.assertRaisesRegex(ValueError, 'UNIT-canonical', msg='UNIT-canonical: forbidden JSON was accepted'):
                parse_json(data, 'UNIT-canonical')

    def test_review_queue_and_balance(self):
        labels = [case['labels'] for case in self.cases]
        for label in labels:
            cid = label['case_id']
            self.assertEqual(label['adjudication_status'], 'pending_review', f'{cid}: human review must not be invented')
            self.assertTrue(label['needs_review'], f'{cid}: review flag must remain true')
            self.assertEqual((label['label_author'], label['label_reviewer']), ('Anas', 'Oussama'),
                             f'{cid}: owner/reviewer assignment differs')
        splits = read_json(DATASET / 'splits.json')
        self.assertFalse(splits['test_frozen'], 'splits.json: pilot must not claim a frozen test')
        self.assertEqual(splits['test'], [], 'splits.json: pilot must not include test cases')
        counts = Counter(label['verdict'] for label in labels)
        self.assertEqual(dict(counts), {'true_positive': 4, 'false_positive': 6},
                         'P01-P10: class balance differs from authored pilot')
        groups = {label['group_id'] for label in labels}
        self.assertEqual(len(groups), 4, 'P01-P10: expected four template-family groups')
        print(f"\nPilot development: cases={len(labels)}, groups={len(groups)}, "
              f"true_positive={counts['true_positive']}, false_positive={counts['false_positive']}", flush=True)
        print('Gold severities: ' + json.dumps(dict(sorted(Counter(label['gold_severity'] for label in labels).items()))), flush=True)
        print('Needs review: ' + ', '.join(label['case_id'] for label in labels), flush=True)
        print('Test: cases=0; test_frozen=false (Stage C deferred)', flush=True)


if __name__ == '__main__':
    unittest.main()

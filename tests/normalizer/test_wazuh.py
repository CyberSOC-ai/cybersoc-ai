"""Real-export mapping, identity, malformed inputs, CLI and backend handoff."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from fastapi.testclient import TestClient

from backend.app import Settings, create_app
from backend.normalizer import NormalizationError, normalize_alert
from backend.normalizer.__main__ import parse_alert
from backend.normalizer.wazuh import severity, utc_timestamp
from backend.validation import validate

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'infrastructure/soc-lab/evidence'
FIXTURES = ROOT / 'tests/normalizer/fixtures'


def export(run=1):
    return json.loads((EVIDENCE / f'lab01-run0{run}-alert.json').read_text())


class NormalizerTest(unittest.TestCase):
    def test_real_exports_match_reviewable_expected_fixtures(self):
        for run in (1, 2):
            reference = f'infrastructure/soc-lab/evidence/lab01-run0{run}-alert.json'
            result = normalize_alert(export(run), raw_event_ref=reference)
            expected = json.loads((FIXTURES / f'lab01-run0{run}-incident.json').read_text())
            self.assertEqual(result, expected)
            validate('incident', result)
            self.assertEqual(result['severity'], 'low')
            self.assertEqual(result['ingestion_kind'], 'replay')

    def test_real_facts_and_address_roles(self):
        result = normalize_alert(export())
        self.assertEqual(result['source_event_id'], '1792676605.79530')
        self.assertEqual(result['timestamp'], '2026-10-22T13:43:25.130000Z')
        for kind, value in (('user', 'labtest'), ('host', 'linux-01'),
                            ('host', 'linuxsoc'), ('ip', '192.168.77.30'),
                            ('ip', '192.168.56.20'), ('process', 'sshd')):
            self.assertIn({'type': kind, 'value': value}, result['entities'])
        self.assertNotIn({'type': 'ip', 'value': '192.168.77.20'}, result['entities'])
        self.assertIn('Connection source IP: 192.168.77.30.', result['description'])
        self.assertIn('Endpoint management IP: 192.168.56.20.', result['description'])
        self.assertNotIn('mitre_techniques', result)
        self.assertNotIn('triage_verdict', result)

    def test_wrapper_and_raw_have_same_output(self):
        wrapped = export()
        self.assertEqual(normalize_alert(wrapped), normalize_alert(wrapped['_source']))

    def test_replay_and_deployment_identity(self):
        original = normalize_alert(export())
        replay = normalize_alert(export(), ingestion_kind='live', raw_event_ref='other:reference')
        self.assertEqual(original['incident_id'], replay['incident_id'])
        self.assertNotEqual(original['incident_id'], normalize_alert(export(2))['incident_id'])
        self.assertNotEqual(original['incident_id'],
                            normalize_alert(export(), source='wazuh:other-lab')['incident_id'])
        wrapped = export()
        wrapped['_id'] = 'another-index-document'
        self.assertEqual(original, normalize_alert(wrapped))

    def test_all_severity_levels_and_invalid_types(self):
        expected = ['informational'] * 4 + ['low'] * 3 + ['medium'] * 3 + ['high'] * 3 + ['critical'] * 4
        for level, label in enumerate(expected):
            self.assertEqual(severity(level), label)
        for level in (-1, 17, '5', 5.0, True, None):
            with self.subTest(level=level), self.assertRaises(NormalizationError):
                severity(level)

    def test_maximum_wazuh_level_produces_valid_critical_incident(self):
        raw = export()
        raw['_source']['rule']['level'] = 16
        result = normalize_alert(raw)
        self.assertEqual(result['severity'], 'critical')
        self.assertIn('(level 16)', result['description'])
        validate('incident', result)

    def test_offset_conversion_and_invalid_timestamps(self):
        self.assertEqual(utc_timestamp('2026-10-22T14:43:25.130+01:00'),
                         '2026-10-22T13:43:25.130000Z')
        self.assertEqual(utc_timestamp('2026-10-22T00:30:00+0100'),
                         '2026-10-21T23:30:00Z')
        self.assertEqual(utc_timestamp('2026-10-22T13:43:25Z'), '2026-10-22T13:43:25Z')
        for value in ('2026-10-22T13:43:25', 'Oct 22 13:43:23',
                      '2026-02-30T13:43:25Z', '2026-10-22T13:43:25+0060',
                      '2026-10-22T13:43:25.1234567Z', None):
            with self.subTest(value=value), self.assertRaises(NormalizationError):
                utc_timestamp(value)

    def test_required_fields_and_wrong_shapes(self):
        for path in (('id',), ('timestamp',), ('agent',), ('agent', 'name'),
                     ('agent', 'id'), ('manager',), ('manager', 'name'),
                     ('rule',), ('rule', 'id'), ('rule', 'level'), ('rule', 'description')):
            raw = export()['_source']
            target = raw
            for key in path[:-1]:
                target = target[key]
            del target[path[-1]]
            with self.subTest(path=path), self.assertRaises(NormalizationError):
                normalize_alert(raw)
        for value in ([], None, {'_source': None}, {'_source': []}):
            with self.subTest(value=value), self.assertRaises(NormalizationError):
                normalize_alert(value)

    def test_optional_fields_and_entity_deduplication(self):
        raw = export()['_source']
        for key in ('data', 'predecoder', 'full_log'):
            raw.pop(key)
        result = normalize_alert(raw)
        self.assertEqual(len(result['entities']), 2)  # agent host and management IP
        raw['data'] = {'srcip': raw['agent']['ip'], 'dstuser': 'labtest', 'srcuser': 'labtest'}
        result = normalize_alert(raw)
        self.assertEqual(len(result['entities']), 3)
        self.assertEqual(normalize_alert(raw), result)

    def test_invalid_addresses_and_fields(self):
        for container, key, value in (('data', 'srcip', '999.1.2.3'),
                                      ('data', 'dstip', ''), ('agent', 'ip', True),
                                      ('data', 'dstuser', ''), ('rule', 'description', 'x' * 2049)):
            raw = export()['_source']
            raw[container][key] = value
            with self.subTest(key=key), self.assertRaises(NormalizationError):
                normalize_alert(raw)
        raw = export()['_source']
        raw['id'] = 'bad/id'
        with self.assertRaises(NormalizationError):
            normalize_alert(raw)
        for kwargs in ({'source': ''}, {'ingestion_kind': 'unknown'}, {'raw_event_ref': ''}):
            with self.subTest(kwargs=kwargs), self.assertRaises(NormalizationError):
                normalize_alert(export(), **kwargs)

    def test_ipv6_and_no_input_mutation(self):
        raw = export()
        raw['_source']['data']['srcip'] = '2001:db8::1'
        before = deepcopy(raw)
        result = normalize_alert(raw)
        self.assertIn({'type': 'ip', 'value': '2001:db8::1'}, result['entities'])
        self.assertEqual(raw, before)

    def test_description_overflow_is_rejected_not_silently_truncated(self):
        raw = export()['_source']
        raw['rule']['description'] = 'x' * 2048
        raw['full_log'] = 'x' * 6000
        with self.assertRaises(NormalizationError):
            normalize_alert(raw)

    def test_strict_json_parser(self):
        for raw in (b'{"id":1,"id":2}', b'{"x":NaN}', b'{"x":1e999}',
                    b'\xff', b'{}{}', b'{"x":"\\ud800"}', b' ' * 65537,
                    b'[' * 34 + b'0' + b']' * 34):
            with self.subTest(raw=raw[:30]), self.assertRaises(NormalizationError):
                parse_alert(raw)

    def test_backend_accepts_replay_and_rejects_changed_event_content(self):
        with tempfile.TemporaryDirectory(prefix='cybersoc-normalizer-') as directory:
            with TestClient(create_app(settings=Settings(Path(directory)))) as client:
                first = normalize_alert(export())
                response = client.post('/incidents', json=first)
                self.assertEqual(response.status_code, 201, response.text)
                replay = normalize_alert(export(), raw_event_ref='another:location')
                response = client.post('/incidents', json=replay)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertFalse(response.json()['created'])
                raw = export()
                raw['_source']['data']['dstuser'] = 'different-account'
                response = client.post('/incidents', json=normalize_alert(raw))
                self.assertEqual(response.status_code, 409, response.text)
                self.assertEqual(client.post('/incidents', json=normalize_alert(export(2))).status_code, 201)


class CLITest(unittest.TestCase):
    def cli(self, *args, raw=None):
        return subprocess.run([sys.executable, '-B', '-m', 'backend.normalizer', *args],
                              input=raw, capture_output=True, cwd=ROOT)

    def test_saved_file_and_stdin(self):
        reference = 'infrastructure/soc-lab/evidence/lab01-run01-alert.json'
        file_result = self.cli(reference)
        self.assertEqual(file_result.returncode, 0, file_result.stderr)
        stdin_result = self.cli('-', '--raw-event-ref', reference,
                                raw=(ROOT / reference).read_bytes())
        self.assertEqual(stdin_result.returncode, 0, stdin_result.stderr)
        self.assertEqual(json.loads(file_result.stdout), json.loads(stdin_result.stdout))

    def test_failures_have_no_partial_output_or_input_leak(self):
        raw = export()
        raw['_source']['data']['srcip'] = 'PRIVATE-INPUT-CANARY'
        for payload in (json.dumps(raw).encode(), b'bad json', b'x' * 65537):
            result = self.cli('-', raw=payload)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, b'')
            self.assertNotIn(b'PRIVATE-INPUT-CANARY', result.stderr)
            self.assertNotIn(b'Traceback', result.stderr)
        result = self.cli('/missing/private-file-name.json')
        self.assertEqual(result.returncode, 2)
        self.assertNotIn(b'private-file-name', result.stderr)


if __name__ == '__main__':
    unittest.main()

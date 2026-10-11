import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[2]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


guard = module('research_guard')
output = module('research_output')


class OutputTests(unittest.TestCase):
    def setUp(self):
        self.record = json.loads((ROOT / 'examples/records/weapons.json').read_text(encoding='utf-8'))

    def audit(self, snapshot=None, online=False):
        return output.audit_record(self.record, snapshot, guard.validate(self.record, snapshot), online)

    def codes(self, result, status=None):
        return {c['code'] for c in result['audit_checks'] if status is None or c['status'] == status}

    def measurement(self, value='40000', unit='kg', formula='mass'):
        measurement = {'equipment_id': 'E01', 'quantity': '質量', 'original_value': value, 'unit': unit,
                       'value_kind': 'estimated', 'source_id': None, 'source_locator': None,
                       'conditions': '合成計算のみ', 'calculation': {
                           'inputs': [{'name': 'mass', 'value': '40', 'unit': 't', 'source_id': None, 'assumption': '合成仮定'}],
                           'formula': formula, 'rounding': '丸めなし', 'limitations': ['実物の測定ではない']}}
        self.record['findings'][0]['measurements'] = [measurement]
        return measurement

    def cli(self, record=None, command='render', extra=()):
        return subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/research_guard.py'), command,
                               '--record', '-', *extra], input=json.dumps(record or self.record, ensure_ascii=False),
                              cwd=tempfile.gettempdir(), capture_output=True, text=True, encoding='utf-8',
                              env={**os.environ, 'PYTHONIOENCODING': 'ascii', 'PYTHONUTF8': '0'})

    def test_all_modes_render_preserve_limits_and_do_not_mutate_record(self):
        for mode in ('martial', 'weapons', 'military', 'integrated'):
            self.record = json.loads((ROOT / f'examples/records/{mode}.json').read_text(encoding='utf-8'))
            before = copy.deepcopy(self.record)
            result = self.audit()
            markdown = output.render_report(self.record, result)
            self.assertEqual(self.record, before)
            for finding in self.record['findings']:
                self.assertIn(output.literal(finding['analysis']), markdown)
                for a in finding['assessments']:
                    for value in a['missing_information'] + a['conditions'] + a['additional_conditions']:
                        self.assertIn(output.literal(value), markdown)
                for value in finding['limitations'] + finding['alternative_interpretations']:
                    self.assertIn(output.literal(value), markdown)
            self.assertEqual(result['content_judgment'], 'not_evaluated')
            self.assertIn('SOURCE_TRUTH', self.codes(result, 'not_checked'))

    def test_unit_conversion_and_wrong_result_block_rendering(self):
        m = self.measurement()
        result = self.audit()
        self.assertIn('CALCULATION', self.codes(result, 'checked'))
        self.assertNotEqual(result['audit_status'], 'error')
        m['original_value'] = '400000'
        result = self.audit()
        self.assertEqual(result['record_integrity'], 'pass')
        self.assertEqual(result['audit_status'], 'error')
        with self.assertRaises(ValueError):
            output.render_report(self.record, result)
        process = self.cli()
        self.assertEqual(process.returncode, 1, process.stderr)
        self.assertIsNone(json.loads(process.stdout)['markdown'])

    def test_fraction_arithmetic_dimensions_and_rounding(self):
        m = self.measurement('0.33', '1', 'a / b')
        c = m['calculation']
        c['inputs'] = [{'name': name, 'value': value, 'unit': '1', 'source_id': None, 'assumption': '合成仮定'}
                       for name, value in [('a', '1'), ('b', '3')]]
        c.update(decimal_places=2, rounding='ROUND_HALF_UP')
        self.assertIn('CALCULATION', self.codes(self.audit(), 'checked'))
        c['inputs'][0]['value'] = '-1'
        m['original_value'] = '-0.33'
        self.assertIn('CALCULATION', self.codes(self.audit(), 'checked'))
        c['inputs'][1]['value'] = '0'
        self.assertIn('CALCULATION', self.codes(self.audit(), 'error'))
        c['inputs'][1]['value'] = '3'
        c['formula'] = 'a + b'
        c['inputs'][0]['unit'] = 'kg'
        self.assertIn('CALCULATION', self.codes(self.audit(), 'error'))

    def test_expression_limits_unknown_units_and_no_code_execution(self):
        m = self.measurement()
        c = m['calculation']
        for formula in ('__import__("os").system("exit 99")', 'mass ** 2', '[mass]', '1e99', 'mass+' * 1000, '入力と同値'):
            c['formula'] = formula
            self.assertIn('CALCULATION', self.codes(self.audit(), 'not_checked'))
        c['formula'] = 'mass'
        for value in ('約40', '30〜40', 'NaN', '9' * 100):
            c['inputs'][0]['value'] = value
            self.assertIn('CALCULATION', self.codes(self.audit(), 'not_checked'))
        c['inputs'][0]['value'] = '40'
        c['inputs'][0]['unit'] = None
        self.assertIn('CALCULATION', self.codes(self.audit(), 'not_checked'))
        c['inputs'][0]['unit'] = 't'
        c['inputs'].append(copy.deepcopy(c['inputs'][0]))
        self.assertIn('CALCULATION', self.codes(self.audit(), 'error'))

    def test_quoted_evidence_matches_current_crlf_and_rejects_changes(self):
        with tempfile.TemporaryDirectory(prefix='martial-output-') as tmp:
            path = Path(tmp) / '資料.txt'
            path.write_bytes('質量40kg。\r\n条件甲。\r\n'.encode())
            snapshot = guard.capture(Path(tmp), ['R01=資料.txt'], ['S01=R01:1:2'])
            self.record = json.loads((ROOT / 'examples/records/weapons-declared.json').read_text(encoding='utf-8'))
            self.record['snapshot_id'] = snapshot['snapshot_id']
            self.record['findings'][0]['target'] = {'type': 'question', 'text': '合成引用の照合'}
            source = self.record['sources'][0]
            source['file_id'] = 'R01'
            evidence = self.record['findings'][0]['assessments'][0]['evidence'][0]
            evidence.update(span_id='S01', quote='質量40kg。\r\n')
            result = self.audit(snapshot)
            self.assertEqual(result['record_integrity'], 'pass', result)
            self.assertIn('QUOTE_MATCH', self.codes(result, 'checked'))
            evidence['quote'] = '質量400kg。\r\n'
            result = self.audit(snapshot)
            self.assertEqual(result['audit_status'], 'blocked')
            self.assertIn('QUOTE_MISMATCH', {e['code'] for e in result['errors']})
            evidence['quote'] = '質量40kg。\r\n'
            path.write_bytes('質量41kg。\r\n条件甲。\r\n'.encode())
            self.assertEqual(self.audit(snapshot)['audit_status'], 'blocked')

    def test_comparison_and_conflict_are_review_not_falsehood_verdicts(self):
        self.record = json.loads((ROOT / 'examples/records/weapons-declared.json').read_text(encoding='utf-8'))
        values = self.record['findings'][0]['measurements']
        result = self.audit()
        self.assertIn('COMPARISON_CONDITIONS', self.codes(result, 'review_required'))
        first = values[0]
        first.update(original_value='44', conditions='同じ時点・構成')
        second = copy.deepcopy(first)
        second['original_value'] = '45'
        values[:] = [first, second]
        result = self.audit()
        self.assertIn('VALUE_CONFLICT', self.codes(result, 'review_required'))
        self.assertNotEqual(result['audit_status'], 'error')

    def test_inference_leap_causal_and_generalization_rules(self):
        finding = self.record['findings'][0]
        for kind, basis, code in [('causal', 'association', 'CAUSAL_IDENTIFICATION'),
                                  ('effectiveness', 'prediction', 'INFERENCE_LEAP'),
                                  ('effectiveness', 'normative', 'INFERENCE_LEAP'),
                                  ('generalization', 'tested', 'GENERALIZATION')]:
            finding['inference_context'] = {'claim_kind': kind, 'basis_kind': basis,
                                            'confounders': [], 'identification': None}
            result = self.audit()
            self.assertIn(code, self.codes(result, 'review_required'))
            self.assertNotEqual(result['audit_status'], 'error')
        finding['inference_context']['claim_kind'] = 'unknown'
        self.assertEqual(self.audit()['audit_status'], 'blocked')

    def test_crossref_matching_updates_and_duplicate_sources(self):
        self.record = json.loads((ROOT / 'examples/records/weapons-declared.json').read_text(encoding='utf-8'))
        s = self.record['sources'][0]
        s['bibliography'].update(doi='https://doi.org/10.1234/Example', title='Synthetic title', author='Jane Doe', year='2026')
        duplicate = copy.deepcopy(s)
        duplicate['id'] = 'W03'
        self.record['sources'].append(duplicate)
        metadata = {'DOI': '10.1234/example', 'title': ['Synthetic title'], 'author': [{'given': 'Jane', 'family': 'Doe'}],
                    'published': {'date-parts': [[2026]]}, 'update-to': [{'type': 'correction'}]}
        with mock.patch.object(output, 'fetch_crossref', return_value=(metadata, {'url': 'https://api.crossref.org/works/example'})) as fetch:
            result = self.audit(online=True)
        self.assertEqual(fetch.call_count, 1)
        self.assertIn('METADATA_TITLE', self.codes(result, 'checked'))
        self.assertIn('METADATA_AUTHOR', self.codes(result, 'checked'))
        self.assertIn('PUBLICATION_UPDATE', self.codes(result, 'review_required'))
        self.assertIn('DUPLICATE_SOURCE', self.codes(result, 'review_required'))
        self.assertEqual(result['content_judgment'], 'not_evaluated')
        s['bibliography']['title'] = 'A different work'
        with mock.patch.object(output, 'fetch_crossref', return_value=(metadata, {})):
            self.assertIn('METADATA_TITLE', self.codes(self.audit(online=True), 'review_required'))

    def test_crossref_offline_failures_and_limit_are_explicit(self):
        self.record = json.loads((ROOT / 'examples/records/weapons-declared.json').read_text(encoding='utf-8'))
        source = self.record['sources'][0]
        source['bibliography']['doi'] = '10.1234/example'
        with mock.patch.object(output, 'fetch_crossref') as fetch:
            self.assertIn('BIBLIOGRAPHY', self.codes(self.audit(), 'not_checked'))
            fetch.assert_not_called()
        with mock.patch.object(output, 'fetch_crossref', side_effect=HTTPError('url', 404, 'not registered', {}, None)):
            result = self.audit(online=True)
        self.assertIn('BIBLIOGRAPHY', self.codes(result, 'not_checked'))
        self.assertNotEqual(result['audit_status'], 'error')
        self.record['sources'] = []
        for i in range(12):
            entry = copy.deepcopy(source)
            entry['id'] = 'W' + str(i + 2).zfill(2)
            entry['bibliography']['doi'] = '10.1234/example' + str(i)
            self.record['sources'].append(entry)
        with mock.patch.object(output, 'fetch_crossref', side_effect=OSError('offline')) as fetch:
            result = self.audit(online=True)
        self.assertEqual(fetch.call_count, 10)
        self.assertIn('BIBLIOGRAPHY', self.codes(result, 'not_checked'))

    def test_fetch_crossref_validates_doi_and_bad_response_without_redirects(self):
        raw = json.dumps({'message': {'DOI': '10.1234/example', 'title': ['Synthetic']}}).encode()
        response = io.BytesIO(raw)
        opener = mock.Mock()
        opener.open.return_value = response
        with mock.patch.object(output, 'build_opener', return_value=opener):
            metadata, acquisition = output.fetch_crossref('10.1234/example')
        self.assertEqual(metadata['DOI'], '10.1234/example')
        self.assertIn('sha256', acquisition)
        request = opener.open.call_args[0][0]
        self.assertEqual(request.full_url, 'https://api.crossref.org/works/10.1234%2Fexample')
        for message in ({'DOI': '10.1234/other'}, {'DOI': '10.1234/example', 'published': {'date-parts': None}}):
            opener.open.return_value = io.BytesIO(json.dumps({'message': message}).encode())
            with mock.patch.object(output, 'build_opener', return_value=opener), self.assertRaises(ValueError):
                output.fetch_crossref('10.1234/example')
        self.assertIsNone(output.NoRedirect().redirect_request(None, None, 302, None, None, 'http://127.0.0.1'))

    def test_markdown_escapes_data_and_keeps_warnings_missing_information(self):
        self.record = json.loads((ROOT / 'examples/records/weapons-declared.json').read_text(encoding='utf-8'))
        self.record['findings'][0]['analysis'] = '\n# 偽の見出し\n[危険](javascript:alert(1))<script>実行</script>'
        self.record['sources'][0]['bibliography']['url'] = 'javascript:alert(1)'
        result = self.audit()
        markdown = output.render_report(self.record, result)
        self.assertNotIn('<script>', markdown)
        self.assertNotIn('[危険](javascript:', markdown)
        self.assertNotIn('\n# 偽の見出し', markdown)
        for check in result['audit_checks']:
            self.assertIn(output.literal(check['message']), markdown)
        self.assertIn(output.literal('SOURCE_CONTENT_UNCHECKED'), markdown)
        self.assertIn(output.literal('COMPARISON_CONDITIONS'), markdown)

    def test_cli_utf8_stdin_audit_render_and_invalid_schema(self):
        for command in ('audit', 'render'):
            process = self.cli(command=command)
            self.assertEqual(process.returncode, 0, process.stderr)
            result = json.loads(process.stdout)
            self.assertEqual(result['content_judgment'], 'not_evaluated')
            self.assertEqual('markdown' in result, command == 'render')
        self.record['unknown'] = True
        process = self.cli()
        self.assertEqual(process.returncode, 1)
        self.assertIsNone(json.loads(process.stdout)['markdown'])
        process = self.cli(extra=('--online', 'invalid'))
        self.assertEqual(process.returncode, 2)
        self.assertEqual(json.loads(process.stdout)['record_integrity'], 'input_error')

    def test_output_size_and_optional_field_types(self):
        stream = io.StringIO()
        with mock.patch.object(guard, 'load_json', return_value=self.record), mock.patch.object(guard, 'MAX_BYTES', 100), \
                mock.patch.dict(sys.modules, {'research_output': output}), mock.patch('sys.stdout', stream):
            code = guard.main(['render', '--record', '-'])
        self.assertEqual(code, 2)
        self.assertNotIn('markdown', json.loads(stream.getvalue()))
        m = self.measurement()
        for places in (True, -1, 13, '2'):
            m['calculation']['decimal_places'] = places
            self.assertEqual(self.audit()['audit_status'], 'blocked')


if __name__ == '__main__':
    unittest.main()

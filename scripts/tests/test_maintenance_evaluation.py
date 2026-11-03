import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('maintenance_eval', ROOT / 'scripts/evaluate_maintenance.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class MaintenanceEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.case = {'id': 'case', 'request': 'classify', 'facts': 'synthetic',
                     'action': 'defer', 'claims': {'verified': False}}

    def test_wrong_decision_and_lost_condition_are_scored_separately(self):
        result = MODULE.score([self.case], {'case': {'action': 'adopt', 'claims': {'verified': False}}})
        self.assertEqual(result['case'], {'action': 0, 'conditions': 1})
        result = MODULE.score([self.case], {'case': {'action': 'defer', 'claims': {'verified': True}}})
        self.assertEqual(result['case'], {'action': 1, 'conditions': 0})

    def test_missing_answers_and_boolean_strings_are_not_valid_results(self):
        for answer in [{}, {'case': {'action': 'defer', 'claims': {'verified': 'false'}}}]:
            with self.assertRaises(ValueError):
                MODULE.score([self.case], answer)

    def test_cli_error_cannot_be_counted_as_success(self):
        with self.assertRaises(ValueError):
            MODULE.parse_answer({'is_error': True, 'result': '{}'})

    def test_non_object_envelope_and_duplicate_ids_are_rejected(self):
        for envelope in [[], {'result': '{"x":{},"x":{}}'}]:
            with self.assertRaises(ValueError):
                MODULE.parse_answer(envelope)

    def test_fenced_answer_is_parsed(self):
        self.assertEqual(MODULE.parse_answer({'result': '```json\n{"x":1}\n```'}), {'x': 1})

    def test_expected_labels_do_not_enter_prompt(self):
        prompt = MODULE.prompt_for([self.case])
        data = json.loads(prompt.split('\n')[-1])
        self.assertNotIn('action', data[0])
        self.assertNotIn('claims', data[0])
        self.assertEqual(data[0]['claim_keys'], ['verified'])

    def test_ties_and_missing_usage_never_pass_the_adoption_screen(self):
        runs = []
        for trial in range(3):
            for arm in ['A', 'B1', 'B2', 'B3']:
                runs.append({'arm': arm, 'trial': trial, 'status': 'ok',
                             'scores': {'case': {'action': 1, 'conditions': 1}},
                             'model_usage': {'same-model': {}}, 'usage': {}})
        summary = MODULE.summarize({'runs': runs}, {'case'})
        self.assertTrue(summary['A']['complete'])
        for arm in ['B1', 'B2', 'B3']:
            self.assertFalse(summary[arm]['screen_passed'])
            self.assertIsNone(summary[arm]['total_tokens'])

    def test_adoption_screen_checks_benefit_safety_cost_and_model(self):
        def fixture():
            return [{'arm': arm, 'trial': trial, 'status': 'ok',
                     'scores': {'dev': {'action': int(arm != 'A'), 'conditions': 1},
                                'final': {'action': 1, 'conditions': 1}},
                     'model_usage': {'same-model': {}},
                     'usage': {'input_tokens': 100, 'output_tokens': 10,
                               'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0}}
                    for trial in range(3) for arm in ['A', 'B1', 'B2', 'B3']]
        runs = fixture()
        self.assertTrue(MODULE.summarize({'runs': runs}, {'final'})['B1']['screen_passed'])
        for failure in ['tie', 'condition_loss', 'cost', 'model']:
            runs = fixture()
            for row in runs:
                if row['arm'] != 'B1':
                    continue
                if failure == 'tie':
                    row['scores']['dev']['action'] = 0
                elif failure == 'condition_loss':
                    row['scores']['dev']['conditions'] = 0
                elif failure == 'cost':
                    row['usage']['input_tokens'] = 1000
                else:
                    row['model_usage'] = {'different-model': {}}
            self.assertFalse(MODULE.summarize({'runs': runs}, {'final'})['B1']['screen_passed'], failure)
        runs = fixture()
        for row in runs:
            row['scores']['dev']['action'] = int(row['arm'] in ['A', 'B3'])
        self.assertFalse(MODULE.summarize({'runs': runs}, {'final'})['B3']['screen_passed'])


if __name__ == '__main__':
    unittest.main()

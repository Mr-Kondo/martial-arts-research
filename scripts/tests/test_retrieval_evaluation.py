import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
SPEC = importlib.util.spec_from_file_location('retrieval_eval', ROOT / 'scripts/evaluate_retrieval.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RetrievalEvaluationTests(unittest.TestCase):
    def stream(self, path='docs/source.md', failed=False):
        return '\n'.join(json.dumps(event) for event in [
            {'type': 'assistant', 'message': {'content': [
                {'type': 'tool_use', 'id': 'read', 'name': 'Read', 'input': {'file_path': path}}]}},
            {'type': 'user', 'message': {'content': [
                {'type': 'tool_result', 'tool_use_id': 'read', 'is_error': failed, 'content': 'text'}]}},
            {'type': 'result', 'is_error': False, 'result': '{}'}])

    def test_only_successful_reads_ground_citations(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, trace = MODULE.inspect_stream(self.stream(), root)
            self.assertEqual(trace['read_paths'], ['docs/source.md'])
            self.assertEqual(trace['tool_calls'], 1)
            _, failed = MODULE.inspect_stream(self.stream(failed=True), root)
            self.assertEqual(failed['read_paths'], [])

    def test_outside_fixture_and_failed_or_missing_results_are_invalid(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for text in [self.stream('../outside.md'), '{}',
                         json.dumps({'type': 'result', 'is_error': True})]:
                with self.assertRaises(ValueError):
                    MODULE.inspect_stream(text, root)

    def test_maintenance_read_is_observed_even_when_it_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, trace = MODULE.inspect_stream(self.stream('maintenance/guide.md', failed=True), Path(temporary))
            self.assertEqual(trace['maintenance_reads'], 1)

    def test_correct_claims_cannot_hide_unread_or_noncanonical_evidence(self):
        cases = [{'id': 'x', 'claims': {'known': False}, 'sources': ['docs/source.md']}]
        answer = {'x': {'claims': {'known': False}, 'evidence': ['docs/source.md'], 'answer': 'limited'}}
        self.assertFalse(MODULE.score(cases, answer, [], ['docs/source.md'])['x']['grounded'])
        self.assertTrue(MODULE.score(cases, answer, ['docs/source.md'], ['docs/source.md'])['x']['grounded'])
        answer['x']['claims']['known'] = 'false'
        with self.assertRaises(ValueError):
            MODULE.score(cases, answer, ['docs/source.md'], ['docs/source.md'])

    def test_labels_and_source_paths_do_not_enter_task_prompt(self):
        task = {'id': 'x', 'request': 'request', 'claims': {'known': False}, 'sources': ['hidden.md']}
        data = json.loads(MODULE.prompt_for([task]).split('\n')[-1])
        self.assertEqual(set(data[0]), {'id', 'request', 'claim_keys'})

    def test_resource_win_can_exist_with_ceiling_quality_but_rejects_tradeoffs(self):
        base = {'complete': True, 'perfect': True, 'tokens': [100, 100, 100], 'seconds': [10, 10, 10]}
        self.assertTrue(MODULE.resource_win({'perfect': True, 'tokens': [85]*3, 'seconds': [10]*3}, base))
        self.assertTrue(MODULE.resource_win({'perfect': True, 'tokens': [105]*3, 'seconds': [7]*3}, base))
        for candidate in [base, {'perfect': False, 'tokens': [80]*3, 'seconds': [7]*3},
                          {'perfect': True, 'tokens': None, 'seconds': [7]*3},
                          {'perfect': True, 'tokens': [80]*3, 'seconds': [11]*3},
                          {'perfect': True, 'tokens': [120]*3, 'seconds': [7]*3}]:
            self.assertFalse(MODULE.resource_win(candidate, base))

    def test_missing_repetitions_are_not_complete_or_perfect(self):
        summary = MODULE.summary([])
        self.assertFalse(summary['A']['update']['complete'])
        self.assertFalse(summary['B3']['normal']['perfect'])
        self.assertIsNone(summary['A']['update']['tokens'])

    def test_missing_oracle_sources_are_rejected_before_model_calls(self):
        case = {'id': 'x', 'request': 'request', 'claims': {'a': True, 'b': False, 'c': True},
                'sources': ['missing.md']}
        with self.assertRaises(ValueError):
            MODULE.validate_cases({'update': [case]*3, 'normal': [case]}, {})

    def test_glob_escape_is_rejected_and_grep_regex_is_not_a_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            text = self.stream()
            event = json.loads(text.splitlines()[0])
            block = event['message']['content'][0]
            block.update(name='Glob', input={'pattern': '../outside/*'})
            escaped = json.dumps(event) + '\n' + '\n'.join(text.splitlines()[1:])
            with self.assertRaises(ValueError):
                MODULE.inspect_stream(escaped, Path(temporary))
            block.update(name='Grep', input={'pattern': '/a|../b', 'path': '.'})
            valid = json.dumps(event) + '\n' + '\n'.join(text.splitlines()[1:])
            _, trace = MODULE.inspect_stream(valid, Path(temporary))
            self.assertEqual(trace['tool_calls'], 1)

    def test_adoption_requires_normal_work_and_lazy_overhead_gates(self):
        import copy
        baseline = {'complete': True, 'perfect': True, 'tokens': [100]*3,
                    'seconds': [10]*3, 'maintenance_reads': [0]*3}
        results = {a: {'update': copy.deepcopy(baseline), 'normal': copy.deepcopy(baseline)}
                   for a in MODULE.ARMS}
        for a, tokens in [('B1', 89), ('B2', 79), ('B3', 79)]:
            results[a]['update']['tokens'] = [tokens]*3
        self.assertEqual(MODULE.adoption(results), {'B1': True, 'B2': True, 'B3': False})
        results['B3']['update']['maintenance_sources'] = [
            ['maintenance/guide.md', 'maintenance/knowledge.md'] for _ in range(3)]
        self.assertEqual(MODULE.adoption(results), {'B1': True, 'B2': True, 'B3': True})
        results['B1']['normal']['tokens'] = [111]*3
        results['B2']['normal']['perfect'] = False
        results['B3']['normal']['maintenance_reads'] = [0, 1, 0]
        self.assertEqual(MODULE.adoption(results), {'B1': False, 'B2': False, 'B3': False})
        results['B3']['normal']['maintenance_reads'] = [0]*3
        results['B3']['update']['seconds'] = [11.1]*3
        self.assertFalse(MODULE.adoption(results)['B3'])


    def test_read_only_mode_rejects_search_tools(self):
        with tempfile.TemporaryDirectory() as temporary:
            event = json.loads(self.stream().splitlines()[0])
            event['message']['content'][0].update(name='Grep', input={'pattern': 'marker'})
            with self.assertRaises(ValueError):
                MODULE.inspect_stream(json.dumps(event), Path(temporary), allowed_tools=('Read',))

    def test_inventory_is_sorted_and_contains_no_oracle_labels(self):
        case = {'id': 'x', 'request': 'question', 'claims': {'claim': True}, 'sources': ['secret.md']}
        prompt = MODULE.prompt_for([case], ['z.md', 'a.md'])
        self.assertIn('a.md\nz.md', prompt)
        self.assertNotIn('secret.md', prompt)
        self.assertNotIn('true', prompt.split('依頼:\n')[1])


if __name__ == '__main__':
    unittest.main()

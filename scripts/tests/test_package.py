import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'scripts/research_guard.py'
spec = importlib.util.spec_from_file_location('package_guard', SCRIPT)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class PackageTests(unittest.TestCase):
    def test_relative_documentation_links_resolve(self):
        paths = [ROOT / 'SKILL.md', ROOT / 'README.md', ROOT / 'CHANGELOG.md']
        for folder in ['references', 'examples', 'docs', 'adr']:
            paths.extend((ROOT / folder).rglob('*.md'))
        for path in paths:
            content = re.sub(r'```.*?```', '', path.read_text(encoding="utf-8"), flags=re.S)
            for target in re.findall(r'\]\(([^\s)]+)\)', content):
                if urlsplit(target).scheme or target.startswith(('/', '#')):
                    continue
                local = unquote(target.split('#', 1)[0])
                local = re.sub(r':\d+$', '', local)
                with self.subTest(path=path.relative_to(ROOT), target=target):
                    self.assertTrue((path.parent / local).exists())

    def test_common_frontmatter_and_python39_grammar(self):
        content = (ROOT / 'SKILL.md').read_text(encoding="utf-8")
        parts = content.split('---', 2)
        self.assertEqual(parts[0], '')
        lines = parts[1].strip().splitlines()
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], 'name: ' + ROOT.name)
        self.assertTrue(lines[1].startswith('description: '))
        self.assertLessEqual(len(lines[1]), 1024)
        self.assertLess(len(content.splitlines()), 500)
        for path in (ROOT / 'scripts').rglob('*.py'):
            with self.subTest(path=path):
                ast.parse(path.read_text(encoding="utf-8"), feature_version=(3, 9))

    def test_case_coverage_and_input_provenance(self):
        triggers = guard.load_json(str(ROOT / 'evals/trigger-cases.json'))['cases']
        tasks = guard.load_json(str(ROOT / 'evals/task-cases.json'))['cases']
        self.assertEqual(len(triggers), 40)
        self.assertGreaterEqual(len(tasks), 28)
        for cases in [triggers, tasks]:
            self.assertEqual(len(cases), len({c['id'] for c in cases}))
        self.assertEqual(sum(c['kind'] == 'implicit' for c in triggers), 36)
        self.assertEqual(sum(c['kind'] == 'implicit' and not c['should_trigger'] for c in triggers), 12)
        self.assertEqual({c['expected_mode'] for c in tasks}, set(guard.AXES))
        for mode in ['weapons', 'military']:
            self.assertEqual({c['expected_task'] for c in tasks if c['expected_mode'] == mode}, {'survey', 'compare', 'review'})
        for case in tasks:
            self.assertTrue(case['expected_observations'])
            self.assertTrue(case['forbidden_errors'])
            self.assertEqual(set(case['invocation']), {'codex', 'claude'})
            for fixture in case['fixtures']:
                self.assertTrue((ROOT / 'evals' / fixture).is_file())
        provenance = guard.load_json(str(ROOT / 'evals/fixtures/provenance.json'))
        self.assertIn('synthetic', json.dumps(provenance))

    def test_saved_examples_from_other_working_directory(self):
        for name in ['martial', 'weapons', 'military', 'integrated', 'weapons-declared', 'local-review']:
            command = [sys.executable, '-B', str(SCRIPT), 'validate', '--record', str(ROOT / f'examples/records/{name}.json')]
            if name == 'local-review':
                command.extend(['--snapshot', str(ROOT / 'examples/records/local-snapshot.json'), '--root', str(ROOT / 'evals/fixtures')])
            result = subprocess.run(command, cwd=tempfile.gettempdir(), capture_output=True, text=True, encoding="utf-8")
            with self.subTest(name=name):
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(json.loads(result.stdout)['content_judgment'], 'not_evaluated')

    def test_retained_design_inputs_unchanged(self):
        expected = {
            '01-research-report.md': '67993e1c19b09c1dfab5d66f58ab007d353617c2188936c9ac82de61b2bede93',
            '02-skill-design.md': 'd877f3ceb98430b5e91d083b1ae394bac25cfa7d28ce23c34d3b122708d0dea5',
            '03-codex-implementation-prompt.md': '9911ddfce911590f16c0f6081e43886e197b7cf96ae04451b691d87eb7516e2f',
            'codex-implementation-prompt.txt': '1b02fcb29781bf024b6b85640b9b50dbdc043466d63b295b172c9fa991ef9e69',
        }
        for name, sha in expected.items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), sha)


if __name__ == '__main__':
    unittest.main()

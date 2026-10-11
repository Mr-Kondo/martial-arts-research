import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('skill_installation', ROOT / 'scripts/skill_installation.py')
installation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installation)


class InstallationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='martial-install-test-')
        self.root = Path(self.tmp.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        for name in installation.FILES:
            (self.source / name).write_text('0.1.0\n' if name == 'VERSION' else name + '\n', encoding="utf-8")
        for name in installation.FOLDERS:
            (self.source / name).mkdir()
            (self.source / name / '日本語.txt').write_bytes('原文\r\n'.encode())
        self.targets = installation.destinations('both', self.root / 'project')

    def tearDown(self):
        self.tmp.cleanup()

    def test_install_update_stale_file_removal_and_uninstall(self):
        first = installation.install(self.source, self.targets)
        self.assertEqual([r['action'] for r in first], ['installed', 'installed'])
        for target in self.targets:
            self.assertEqual((target / 'scripts/日本語.txt').read_bytes(), '原文\r\n'.encode())
        (self.source / 'scripts/日本語.txt').unlink()
        (self.source / 'references/日本語.txt').write_text('更新', encoding="utf-8")
        (self.source / 'VERSION').write_text('0.1.1\n', encoding="utf-8")
        update = installation.install(self.source, self.targets)
        self.assertEqual([r['action'] for r in update], ['updated', 'updated'])
        for target in self.targets:
            self.assertFalse((target / 'scripts/日本語.txt').exists())
            self.assertEqual(json.loads((target / installation.MARKER).read_text(encoding="utf-8"))['version'], '0.1.1')
        installation.uninstall(self.targets)
        self.assertTrue(all(not p.exists() for p in self.targets))
        self.assertEqual(installation.uninstall(self.targets)[0]['action'], 'absent')

    def test_user_changes_added_files_and_empty_directories_are_preserved(self):
        for kind in ['edit', 'file', 'directory', 'deleted']:
            with self.subTest(kind=kind):
                target = self.root / kind / installation.NAME
                installation.install(self.source, [target])
                if kind == 'edit':
                    (target / 'SKILL.md').write_text('ユーザー編集', encoding="utf-8")
                elif kind == 'file':
                    (target / 'memo.txt').write_text('ユーザー追記', encoding="utf-8")
                elif kind == 'directory':
                    (target / 'empty-user-dir').mkdir()
                else:
                    (target / 'SKILL.md').unlink()
                before = installation.inventory(target)
                with self.assertRaises(ValueError):
                    installation.install(self.source, [target])
                with self.assertRaises(ValueError):
                    installation.uninstall([target])
                self.assertEqual(installation.inventory(target), before)

    def test_unmanaged_symlink_and_malformed_marker_refused(self):
        target = self.targets[0]
        target.mkdir(parents=True)
        (target / 'memo.txt').write_text('管理外', encoding="utf-8")
        with self.assertRaises(ValueError):
            installation.uninstall([target])
        (target / installation.MARKER).write_text('{"schema_version":1,"schema_version":2}', encoding="utf-8")
        with self.assertRaises(ValueError):
            installation.install(self.source, [target])
        linked = self.root / 'linked'
        linked.symlink_to(target, target_is_directory=True)
        with self.assertRaises(ValueError):
            installation.uninstall([linked])
        self.assertEqual((target / 'memo.txt').read_text(encoding="utf-8"), '管理外')

    def test_source_link_and_duplicate_skill_are_refused(self):
        (self.source / 'scripts/link').symlink_to(self.source / 'SKILL.md')
        with self.assertRaises(ValueError):
            installation.install(self.source, self.targets)
        (self.source / 'scripts/link').unlink()
        (self.source / 'evals/SKILL.md').write_text('archived skill', encoding="utf-8")
        with self.assertRaises(ValueError):
            installation.install(self.source, self.targets)
        self.assertTrue(all(not t.exists() for t in self.targets))

    def test_preflight_checks_all_targets_before_update(self):
        installation.install(self.source, self.targets)
        (self.targets[1] / 'memo.txt').write_text('ユーザー追記', encoding="utf-8")
        before = (self.targets[0] / 'SKILL.md').read_bytes()
        (self.source / 'SKILL.md').write_text('更新', encoding="utf-8")
        with self.assertRaises(ValueError):
            installation.install(self.source, self.targets)
        self.assertEqual((self.targets[0] / 'SKILL.md').read_bytes(), before)
        with self.assertRaises(ValueError):
            installation.uninstall(self.targets)
        self.assertTrue(self.targets[0].exists())

    def test_swap_failure_restores_previous_copy(self):
        from unittest.mock import patch
        installation.install(self.source, self.targets[:1])
        before = installation.inventory(self.targets[0])
        original = installation.os.replace
        calls = []
        def replace(source, target):
            calls.append(source)
            if len(calls) == 2:
                raise OSError('simulated swap failure')
            return original(source, target)
        with patch.object(installation.os, 'replace', side_effect=replace):
            with self.assertRaises(OSError):
                installation.install(self.source, self.targets[:1])
        self.assertEqual(installation.inventory(self.targets[0]), before)

    def test_real_cli_install_update_guard_and_uninstall_from_other_cwd(self):
        project = self.root / 'CLI プロジェクト'
        def run(name, *args):
            return subprocess.run([sys.executable, '-B', str(ROOT / 'scripts' / name), '--project', str(project), *args],
                                  cwd=tempfile.gettempdir(), capture_output=True, text=True, encoding="utf-8")
        first = run('install.py')
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertEqual(run('install.py').returncode, 0)
        target = project / '.agents/skills' / installation.NAME
        self.assertEqual([p.relative_to(target).as_posix() for p in target.rglob('SKILL.md')], ['SKILL.md'])
        guard = subprocess.run([sys.executable, '-B', str(target / 'scripts/research_guard.py'), 'validate',
                                '--record', str(target / 'examples/records/military.json')], cwd=tempfile.gettempdir(), capture_output=True)
        self.assertEqual(guard.returncode, 0, guard.stdout)
        self.assertEqual(run('uninstall.py').returncode, 0)
        self.assertEqual(run('uninstall.py').returncode, 0)
        bad = run('install.py', '--user')
        self.assertEqual(bad.returncode, 2)
        self.assertNotIn('Traceback', bad.stderr)


if __name__ == '__main__':
    unittest.main()

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
        self.write_manifest()
        self.targets = installation.destinations('both', self.root / 'project')

    def write_manifest(self):
        names = sorted(p.relative_to(self.source).as_posix()
                       for p in self.source.rglob('*') if p.is_file())
        (self.source / 'package-files.txt').write_text('\n'.join(names) + '\n', encoding='utf-8')

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
        self.write_manifest()
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
        self.write_manifest()
        with self.assertRaises(ValueError):
            installation.install(self.source, self.targets)
        (self.source / 'scripts/link').unlink()
        (self.source / 'evals/SKILL.md').write_text('archived skill', encoding="utf-8")
        self.write_manifest()
        with self.assertRaises(ValueError):
            installation.install(self.source, self.targets)
        self.assertTrue(all(not t.exists() for t in self.targets))

    def test_unlisted_private_files_are_not_distributed(self):
        for name in ['references/private.txt', 'docs/notes.local.md', 'scripts/feedback/result.json',
                     'scripts/__pycache__/cached.pyc', 'evals/unpublished-answer.md']:
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('private', encoding='utf-8')
        installation.install(self.source, self.targets)
        for target in self.targets:
            self.assertEqual(installation.inventory(target)[0].keys(),
                             set((self.source / 'package-files.txt').read_text(encoding='utf-8').splitlines()))

    def test_unsafe_missing_and_duplicate_manifest_entries_refused(self):
        original = (self.source / 'package-files.txt').read_text(encoding='utf-8')
        for entry in ['../secret', '/tmp/secret', 'scripts/../SKILL.md', 'scripts//secret',
                      'scripts/./secret', 'scripts\\secret', 'C:/secret', 'docs/notes.local.md',
                      'scripts/feedback/result.json', 'scripts/.env', 'scripts/missing.txt', 'SKILL.md']:
            with self.subTest(entry=entry):
                (self.source / 'package-files.txt').write_text(original + entry + '\n', encoding='utf-8')
                with self.assertRaises(ValueError):
                    installation.install(self.source, self.targets)
                self.assertTrue(all(not target.exists() for target in self.targets))
        (self.source / 'package-files.txt').write_text(original.replace('SKILL.md\n', ''), encoding='utf-8')
        with self.assertRaises(ValueError):
            installation.install(self.source, self.targets)

    def test_linked_parent_directory_is_refused(self):
        outside = self.root / 'outside'
        outside.mkdir()
        (outside / 'secret.txt').write_text('private', encoding='utf-8')
        (self.source / 'docs/linked').symlink_to(outside, target_is_directory=True)
        manifest = self.source / 'package-files.txt'
        manifest.write_text(manifest.read_text(encoding='utf-8') + 'docs/linked/secret.txt\n', encoding='utf-8')
        with self.assertRaises(ValueError):
            installation.install(self.source, self.targets)
        self.assertTrue(all(not target.exists() for target in self.targets))

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

    def test_manifest_accepts_utf8_bom_and_crlf(self):
        manifest = self.source / 'package-files.txt'
        names = manifest.read_text(encoding='utf-8').splitlines()
        manifest.write_bytes(('\ufeff' + '\r\n'.join(names) + '\r\n').encode('utf-8'))
        installation.install(self.source, self.targets)
        self.assertTrue(all(installation.ensure_owned(target) for target in self.targets))

    def test_manifest_rejects_case_collisions_and_windows_aliases(self):
        manifest = self.source / 'package-files.txt'
        original = manifest.read_text(encoding='utf-8')
        for entry in ['scripts/FEEDBACK/result.json', 'docs/private.LOCAL.MD', 'docs/NUL.txt',
                      'docs/NUL/a.md', 'docs/NUL .txt', 'docs/name.', 'docs/name ', 'docs/a?.md',
                      'docs/日本語.txt/child', 'scripts/Case.txt\nscripts/case.txt']:
            with self.subTest(entry=entry):
                manifest.write_text(original + entry + '\n', encoding='utf-8')
                with self.assertRaisesRegex(ValueError, '不正|重複'):
                    installation.install(self.source, self.targets)
                self.assertTrue(all(not target.exists() for target in self.targets))

    def test_lowercase_nested_skill_is_refused_on_all_platforms(self):
        (self.source / 'examples/skill.md').write_text('nested skill', encoding='utf-8')
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, 'SKILL.mdが複数'):
            installation.install(self.source, self.targets)
        self.assertTrue(all(not target.exists() for target in self.targets))

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
        rendered = subprocess.run([sys.executable, '-B', str(target / 'scripts/research_guard.py'), 'render',
                                   '--record', str(target / 'examples/records/military.json')],
                                  cwd=tempfile.gettempdir(), capture_output=True)
        self.assertEqual(rendered.returncode, 0, rendered.stdout + rendered.stderr)
        self.assertIn('不足情報', json.loads(rendered.stdout)['markdown'])
        package_tests = subprocess.run(
            [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', str(target / 'scripts/tests'),
             '-p', 'test_package.py'], cwd=tempfile.gettempdir(), capture_output=True)
        self.assertEqual(package_tests.returncode, 0, package_tests.stdout + package_tests.stderr)
        self.assertEqual(run('uninstall.py').returncode, 0)
        self.assertEqual(run('uninstall.py').returncode, 0)
        bad = run('install.py', '--user')
        self.assertEqual(bad.returncode, 2)
        self.assertNotIn('Traceback', bad.stderr)


if __name__ == '__main__':
    unittest.main()

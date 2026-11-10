"""The committed skills/ distribution must be exactly what package-files.txt lists."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('build_skills_distribution', ROOT / 'scripts/build_skills_distribution.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


def tree(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob('*')) if p.is_file()}


class SkillsDistributionTests(unittest.TestCase):
    def test_manifest_lists_only_publishable_existing_files(self):
        names = build.manifest(ROOT)
        self.assertEqual(len(names), len({name.casefold() for name in names}))
        for name in names:
            parts = Path(name).parts
            with self.subTest(name=name):
                self.assertFalse(Path(name).is_absolute() or '\\' in name, name)
                self.assertFalse(any(part.startswith('.') or part in ('..', 'feedback', '__pycache__')
                                     for part in parts), name)
                self.assertFalse(name.endswith(('.local.md', '.pyc')), name)
                self.assertTrue((ROOT / name).is_file() and not (ROOT / name).is_symlink(), name)
        self.assertEqual([n for n in names if n.casefold().endswith('skill.md')], ['SKILL.md'])

    def test_committed_distribution_matches_a_fresh_build(self):
        with tempfile.TemporaryDirectory() as temporary:
            fresh = Path(temporary) / build.NAME
            build.build(ROOT, fresh)
            expected = tree(fresh)
        self.assertEqual(sorted(expected), sorted(build.manifest(ROOT)))
        self.assertEqual([p for p in (ROOT / 'skills').rglob('*') if p.is_symlink()], [])
        # assertTrue keeps a multi-megabyte diff out of the failure message.
        self.assertTrue(tree(ROOT / 'skills' / build.NAME) == expected,
                        'Run python3 -B scripts/build_skills_distribution.py and commit skills/')


if __name__ == '__main__':
    unittest.main()

"""The committed CLI distribution must match the existing package boundary."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('skill_installation', ROOT / 'scripts/skill_installation.py')
installation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installation)


class SkillsDistributionTests(unittest.TestCase):
    def test_committed_distribution_matches_manifest_and_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            expected = Path(temporary) / installation.NAME
            installation.copy_package(ROOT, expected)
            actual = ROOT / 'skills' / installation.NAME
            self.assertTrue(installation.ensure_owned(actual))
            self.assertEqual(installation.inventory(actual), installation.inventory(expected),
                             'Run python3 -B scripts/build_skills_distribution.py')
            self.assertEqual((actual / installation.MARKER).read_bytes(),
                             (expected / installation.MARKER).read_bytes())

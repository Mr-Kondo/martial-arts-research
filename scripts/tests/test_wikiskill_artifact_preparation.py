import copy
import json
from pathlib import Path
import sys
import unittest
import tempfile
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from prepare_wikiskill_artifacts import validate, prepare, ROOT
from evaluate_maintenance import digest


class PreparationTest(unittest.TestCase):
    def test_prepare_round_trip_and_reject_existing_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)/'fresh'
            cases=ROOT/'evals/fixtures/wikiskill-artifacts/cases.json'
            with patch('evaluate_retrieval.private_output'):
                manifest=prepare(cases,out)
                self.assertEqual(json.loads((out/'frozen.json').read_text()),manifest)
                self.assertEqual(manifest['systems']['B3'],digest((out/'B3-system.md').read_text()))
                self.assertEqual((out/'cases-all.json').read_text(),cases.read_text())
                original=(out/'frozen.json').read_bytes()
                with self.assertRaises(FileExistsError):
                    prepare(cases,out)
                self.assertEqual((out/'frozen.json').read_bytes(),original)

    def test_public_cases_and_missing_or_duplicate_evidence(self):
        data=json.loads((ROOT/'evals/fixtures/wikiskill-artifacts/cases.json').read_text())
        sources={p for case in data['cases'] for p in case['sources']}
        self.assertEqual(len(validate(data,sources)),82)
        self.assertEqual(sum(c['split']=='confirmation' and c['scene']=='update'
                             for c in data['cases']),48)
        self.assertEqual(sum(c['split']=='confirmation' and c['scene']=='normal'
                             for c in data['cases']),24)
        changed=copy.deepcopy(data)
        changed['cases'].append(changed['cases'][0])
        with self.assertRaisesRegex(ValueError,'duplicate'):
            validate(changed,sources)
        with self.assertRaisesRegex(ValueError,'unavailable canonical'):
            validate(data,set())
        changed=copy.deepcopy(data)
        changed['cases'][0]['required']=['incomplete oracle']
        with self.assertRaisesRegex(ValueError,'oracle'):
            validate(changed,sources)


if __name__=='__main__':
    unittest.main()

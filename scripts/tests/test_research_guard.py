import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SKILL = Path(__file__).resolve().parents[2]
SCRIPT = SKILL / "scripts/research_guard.py"
spec = importlib.util.spec_from_file_location("research_guard", SCRIPT)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="martial-guard-")
        self.root = Path(self.tmp.name).resolve()
        self.target = self.root / "対象 文.txt"
        self.target.write_bytes("私には見えなかった。\r\n次の行。\r\n".encode())
        (self.root / "資料.txt").write_bytes("合成資料の分類。\r\n条件甲。\r\n".encode())
        self.snapshot = guard.capture(self.root, ["T01=対象 文.txt", "R01=資料.txt"], ["Q01=T01:1:1", "S01=R01:1:2"])
        self.record = json.loads((SKILL / "examples/records/martial.json").read_text())

    def tearDown(self):
        self.tmp.cleanup()

    def codes(self, snapshot=None):
        return {e["code"] for e in guard.validate(self.record, snapshot)["errors"]}

    def source(self, domain="real", status="full_text", local=False):
        s = {"id": "R01", "source_domain": domain, "source_type": "synthetic_test",
             "publisher_role": "合成試験入力", "modality": "text",
             "bibliography": {"author": None, "title": "合成資料", "year": "2026", "edition": None, "url": None, "doi": None},
             "access_status": status, "checked_on": "2026-10-11", "method": "合成テキストの読取り",
             "read_range": "全2行", "locator": "1〜2行", "limitations": ["実在資料ではない"], "file_id": "R01" if local else None}
        self.record["sources"] = [s]
        return s

    def assessment(self, verdict="supported", relation="supports", local=False):
        a = self.record["findings"][0]["assessments"][0]
        a.update(verdict=verdict, conditions=["合成資料の範囲"], additional_conditions=[], missing_information=[],
                 evidence=[{"source_id": "R01", "relation": relation, "locator": "1〜2行", "span_id": "S01" if local else None}])
        return a

    def local(self):
        self.record["snapshot_id"] = self.snapshot["snapshot_id"]
        self.record["findings"][0]["target"] = {"type": "passage", "span_id": "Q01", "quote": "私には見えなかった。\r\n"}

    def weapon(self):
        self.record = json.loads((SKILL / "examples/records/weapons.json").read_text())
        self.source()
        self.assessment()

    def military(self):
        self.record = json.loads((SKILL / "examples/records/military.json").read_text())

    def measurement(self, kind="declared"):
        self.weapon()
        m = {"equipment_id": "E01", "quantity": "質量", "original_value": "約12", "unit": "kg", "value_kind": kind,
             "source_id": "R01", "source_locator": "1〜2行", "conditions": None, "calculation": None}
        self.record["findings"][0]["measurements"] = [m]
        return m

    def test_minimal_question_without_snapshot_all_modes(self):
        for name in ("martial", "weapons", "military", "integrated"):
            with self.subTest(name=name):
                r = json.loads((SKILL / f"examples/records/{name}.json").read_text())
                self.assertEqual(guard.validate(r)["record_integrity"], "pass")

    def test_passage_requires_snapshot(self):
        self.local()
        self.assertIn("SNAPSHOT_REQUIRED", self.codes())

    def test_japanese_crlf_and_exact_quote(self):
        self.local()
        self.assertEqual(guard.validate(self.record, self.snapshot)["record_integrity"], "pass")
        self.assertEqual(self.snapshot["files"][0]["sha256"], guard.digest(self.target.read_bytes()))
        self.record["findings"][0]["target"]["quote"] = "私には見えなかった。\n"
        self.assertIn("QUOTE_MISMATCH", self.codes(self.snapshot))

    def test_modified_quote(self):
        self.local()
        self.record["findings"][0]["target"]["quote"] = "完全に消えた"
        self.assertIn("QUOTE_MISMATCH", self.codes(self.snapshot))

    def test_same_size_change_and_deleted_source(self):
        self.local()
        self.target.write_bytes(self.target.read_bytes().replace("私".encode(), "彼".encode()))
        self.assertTrue({"FILE_CHANGED", "SPAN_CHANGED"} <= self.codes(self.snapshot))
        self.target.unlink()
        self.assertIn("FILE_UNREADABLE", self.codes(self.snapshot))

    def test_corrupt_snapshot_and_rehashed_invented_span(self):
        for rehash in (False, True):
            snapshot = copy.deepcopy(self.snapshot)
            snapshot["spans"][0]["text"] = "捏造した範囲"
            if rehash:
                snapshot["spans"][0]["sha256"] = guard.digest(snapshot["spans"][0]["text"].encode())
                snapshot["snapshot_id"] = guard.fingerprint(snapshot)
            with self.subTest(rehash=rehash), self.assertRaises(guard.InputError):
                guard.validate(self.record, snapshot)

    def test_snapshot_duplicate_id_unknown_key_and_range(self):
        for mutate in (lambda s: s["files"].append(copy.deepcopy(s["files"][0])),
                       lambda s: s["spans"][0].update(end_line=999),
                       lambda s: s["files"][0].update(unknown=True),
                       lambda s: s["git"].update(head=[])):
            s = copy.deepcopy(self.snapshot)
            mutate(s)
            s["snapshot_id"] = guard.fingerprint(s)
            with self.assertRaises(guard.InputError):
                guard.snapshot_index(s)

    def test_capture_bad_ranges_duplicate_ids_and_non_utf8(self):
        for files, spans in [(["T01=対象 文.txt", "T01=資料.txt"], []),
                             (["T01=対象 文.txt"], ["Q01=T01:0:1"]),
                             (["T01=対象 文.txt"], ["Q01=T01:1:3"]),
                             (["T01=対象 文.txt"], ["Q01=X01:1:1"]),
                             (["T01=対象 文.txt"], ["Q01=T01:1:1", "Q01=T01:2:2"])]:
            with self.subTest(files=files, spans=spans), self.assertRaises(ValueError):
                guard.capture(self.root, files, spans)
        self.target.write_bytes(b"\xff\xfe")
        with self.assertRaises(UnicodeError):
            guard.capture(self.root, ["T01=対象 文.txt"], [])

    def test_empty_file_and_root_override(self):
        self.target.write_bytes(b"")
        s = guard.capture(self.root, ["T01=対象 文.txt"], [])
        self.assertEqual(s["files"][0]["line_count"], 0)
        self.record["snapshot_id"] = s["snapshot_id"]
        with tempfile.TemporaryDirectory() as relocated:
            shutil.copyfile(self.target, Path(relocated) / self.target.name)
            self.assertEqual(guard.validate(self.record, s, relocated)["record_integrity"], "pass")

    def test_external_file_and_retargeted_symlink(self):
        link = self.root / "link.txt"
        link.symlink_to(self.target.name)
        s = guard.capture(self.root, ["T01=link.txt"], [])
        self.record["snapshot_id"] = s["snapshot_id"]
        link.unlink()
        link.symlink_to("資料.txt")
        self.assertIn("FILE_CHANGED", self.codes(s))
        with tempfile.TemporaryDirectory() as other:
            p = Path(other).resolve() / "input.txt"
            p.write_text("貼付文")
            s = guard.capture(self.root, ["T01=" + str(p)], [])
            self.assertEqual(s["files"][0]["path"], str(p))

    def test_git_absent_is_unverified(self):
        with mock.patch.object(guard.subprocess, "run", side_effect=FileNotFoundError):
            s = guard.capture(self.root, ["T01=対象 文.txt"], [])
        self.assertEqual(s["git"]["state"], "unverified")
        self.assertIsNone(s["git"]["head"])

    @unittest.skipUnless(shutil.which("git"), "git unavailable")
    def test_git_status_read_only_and_head_change(self):
        env = dict(os.environ, GIT_AUTHOR_NAME="Fixture", GIT_AUTHOR_EMAIL="fixture@example.invalid",
                   GIT_COMMITTER_NAME="Fixture", GIT_COMMITTER_EMAIL="fixture@example.invalid")
        def git(*args):
            return subprocess.run(["git", "-C", str(self.root), *args], env=env, check=True, capture_output=True)
        git("init", "-q")
        s = guard.capture(self.root, ["T01=対象 文.txt"], [])
        self.assertIsNone(s["git"]["head"])
        self.assertIn("??", s["git"]["status"])
        self.record["snapshot_id"] = s["snapshot_id"]
        git("add", "--", self.target.name)
        git("-c", "commit.gpgsign=false", "commit", "-qm", "fixture")
        result = guard.validate(self.record, s)
        self.assertEqual(result["record_integrity"], "pass")
        self.assertIn("GIT_CHANGED", {x["code"] for x in result["warnings"]})

    def test_json_duplicate_keys_nonfinite_and_large_exponent(self):
        p = self.root / "bad.json"
        for raw in ('{"id":1,"id":2}', '{"v":NaN}', '{"v":Infinity}', '{"v":-Infinity}', '{"v":1e999}'):
            p.write_text(raw)
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                guard.load_json(p)

    def test_json_non_utf8_depth_and_byte_limits(self):
        p = self.root / "bad.json"
        for data in (b"\xff", b"[" * 65 + b"0" + b"]" * 65, b" " * (guard.MAX_BYTES + 1)):
            p.write_bytes(data)
            with self.assertRaises((ValueError, UnicodeError)):
                guard.load_json(p)
        self.target.write_bytes(b"a" * (guard.MAX_BYTES + 1))
        with self.assertRaises(guard.InputError):
            guard.capture(self.root, ["T01=対象 文.txt"], [])

    def test_aggregate_and_output_limits(self):
        with mock.patch.object(guard, "MAX_BYTES", 200):
            self.target.write_bytes(b"a" * 150)
            (self.root / "資料.txt").write_bytes(b"b" * 150)
            with self.assertRaises(guard.InputError):
                guard.capture(self.root, ["T01=対象 文.txt", "R01=資料.txt"], [])
            with self.assertRaises(guard.InputError):
                guard.capture(self.root, ["T01=対象 文.txt"], [])

    def test_body_support_and_external_warning(self):
        self.source()
        self.assessment()
        result = guard.validate(self.record)
        self.assertEqual(result["record_integrity"], "pass")
        self.assertEqual(result["content_judgment"], "not_evaluated")
        self.assertIn("SOURCE_CONTENT_UNCHECKED", {w["code"] for w in result["warnings"]})

    def test_local_source_span_must_be_its_own(self):
        self.local()
        self.source(local=True)
        a = self.assessment(local=True)
        self.assertEqual(guard.validate(self.record, self.snapshot)["record_integrity"], "pass")
        a["evidence"][0]["span_id"] = "Q01"
        self.assertTrue({"SOURCE_SPAN_MISMATCH", "SUPPORT_REQUIRED"} <= self.codes(self.snapshot))

    def test_local_source_requires_snapshot_even_without_evidence(self):
        self.source(local=True)
        self.assertIn("SNAPSHOT_REQUIRED", self.codes())

    def test_conditional_requires_support_and_additional_conditions(self):
        a = self.assessment("conditional")
        a["additional_conditions"] = ["条件甲が継続すること"]
        self.assertIn("SUPPORT_REQUIRED", self.codes())
        self.source()
        self.assertEqual(guard.validate(self.record)["record_integrity"], "pass")
        a["additional_conditions"] = []
        self.assertIn("ADDITIONAL_REQUIRED", self.codes())

    def test_contradicted_requires_counterevidence(self):
        self.source()
        a = self.assessment("contradicted")
        self.assertIn("COUNTEREVIDENCE_REQUIRED", self.codes())
        a["evidence"][0]["relation"] = "contradicts"
        self.assertEqual(guard.validate(self.record)["record_integrity"], "pass")

    def test_abstract_reports_cannot_be_support(self):
        self.source(status="abstract_only")
        a = self.assessment("abstract_reports", "reports")
        self.assertEqual(guard.validate(self.record)["record_integrity"], "pass")
        a["verdict"] = "supported"
        a["evidence"][0]["relation"] = "supports"
        self.assertTrue({"SUPPORT_REQUIRED", "EVIDENCE_NOT_ELIGIBLE"} <= self.codes())

    def test_search_unavailable_unverified_cannot_support(self):
        for status in ("search_only", "unavailable", "unverified"):
            self.source(status=status)
            self.assessment()
            with self.subTest(status=status):
                self.assertIn("SUPPORT_REQUIRED", self.codes())

    def test_insufficient_requires_missing_information(self):
        self.record["findings"][0]["assessments"][0]["missing_information"] = []
        self.assertIn("MISSING_INFORMATION_REQUIRED", self.codes())

    def test_not_applicable_only_subjective(self):
        a = self.record["findings"][0]["assessments"][0]
        a["verdict"] = "not_applicable"
        self.assertIn("SUBJECTIVE_REQUIRED", self.codes())
        self.record["findings"][0]["domain"] = "subjective"
        self.assertEqual(guard.validate(self.record)["record_integrity"], "pass")

    def test_real_support_rejects_fiction_design_unknown(self):
        for domain in ("fictional", "design", "unknown"):
            self.source(domain)
            self.assessment()
            with self.subTest(domain=domain):
                self.assertIn("SUPPORT_REQUIRED", self.codes())

    def test_fiction_requires_extension_and_confirmed_source(self):
        self.record["findings"][0]["domain"] = "fictional"
        s = self.source("fictional")
        self.assessment()
        self.assertIn("FICTION_REQUIRED", self.codes())
        self.record["context"]["requested_extensions"] = ["fiction"]
        for state in ("proposed", "subjective", "unknown"):
            s["source_context"] = {"setting_status": state}
            self.assertIn("SUPPORT_REQUIRED", self.codes())
        s["source_context"]["setting_status"] = "confirmed"
        self.assertEqual(guard.validate(self.record)["record_integrity"], "pass")

    def test_real_design_documents_are_allowed(self):
        self.weapon()
        self.record["sources"][0]["source_type"] = "design_document"
        self.assertEqual(guard.validate(self.record)["record_integrity"], "pass")

    def test_modes_tasks_aliases_and_axis_boundaries(self):
        for mode in ("A", "B", "C", "D", "unknown", [], True):
            self.record["context"]["mode"] = mode
            self.assertIn("INVALID_VALUE", self.codes())
        self.record["context"]["mode"] = "martial"
        self.record["context"]["task"] = "invalid"
        self.assertIn("INVALID_VALUE", self.codes())
        self.record["context"]["task"] = "survey"
        self.record["findings"][0]["assessments"][0]["axis"] = "W1"
        self.assertIn("INVALID_VALUE", self.codes())

    def test_stage_f_and_duplicate_axis_extensions(self):
        a = self.record["findings"][0]["assessments"][0]
        a["axis"] = "F"
        self.assertIn("INVALID_VALUE", self.codes())
        self.record["context"]["requested_extensions"] = ["stage"]
        self.assertEqual(guard.validate(self.record)["record_integrity"], "pass")
        self.record["findings"][0]["assessments"].append(copy.deepcopy(a))
        self.assertIn("DUPLICATE_AXIS", self.codes())
        self.record["context"]["requested_extensions"] = ["stage", "stage"]
        self.assertIn("INVALID_VALUE", self.codes())

    def test_w_axis_requires_equipment(self):
        self.weapon()
        del self.record["findings"][0]["equipment_context"]
        self.assertIn("EQUIPMENT_REQUIRED", self.codes())

    def test_measurements_reference_conditions_and_types(self):
        m = self.measurement()
        self.assertEqual(guard.validate(self.record)["record_integrity"], "pass")
        m["equipment_id"] = "E99"
        self.assertIn("UNKNOWN_EQUIPMENT", self.codes())
        m["equipment_id"] = "E01"
        m["source_id"] = "R99"
        self.assertIn("UNKNOWN_SOURCE", self.codes())
        m["original_value"] = 12
        self.assertIn("INVALID_VALUE", self.codes())

    def test_declared_tested_require_source(self):
        for kind in ("declared", "tested"):
            m = self.measurement(kind)
            m.update(source_id=None, source_locator=None)
            self.assertIn("MEASUREMENT_SOURCE_REQUIRED", self.codes())

    def test_estimates_models_require_calculation(self):
        for kind in ("estimated", "modeled"):
            m = self.measurement(kind)
            m.update(source_id=None, source_locator=None)
            self.assertIn("CALCULATION_REQUIRED", self.codes())
            m["calculation"] = {"inputs": [{"name": "入力甲", "value": "12", "unit": "kg", "source_id": None, "assumption": "合成仮定"}],
                                "formula": "入力甲そのもの", "rounding": "丸めなし", "limitations": ["合成試験"]}
            self.assertEqual(guard.validate(self.record)["record_integrity"], "pass")
            m["calculation"]["inputs"][0]["assumption"] = None
            self.assertIn("CALCULATION_ASSUMPTION", self.codes())

    def test_fictional_equipment_not_real(self):
        self.weapon()
        self.record["findings"][0]["equipment_context"][0]["status"] = "fictional"
        self.assertIn("FICTIONAL_EQUIPMENT", self.codes())

    def test_m_context_required_and_integrated_m_allowed(self):
        self.military()
        mc = self.record["findings"][0].pop("military_context")
        self.assertIn("MILITARY_REQUIRED", self.codes())
        self.record["findings"][0]["military_context"] = mc
        self.record["context"]["mode"] = "integrated"
        self.assertEqual(guard.validate(self.record)["record_integrity"], "pass")

    def test_military_axis_kind_and_levels(self):
        self.military()
        mc = self.record["findings"][0]["military_context"]
        for levels in ([], ["unknown"], ["tactical", "tactical"], ["unspecified", "tactical"], None, [True]):
            mc["analysis_levels"] = levels
            self.assertIn("MILITARY_LEVELS", self.codes())
        mc["analysis_levels"] = ["tactical"]
        mc["analysis_kind"] = "unknown"
        self.assertIn("INVALID_VALUE", self.codes())
        for axis in ("A", "W1"):
            self.record["findings"][0]["assessments"][0]["axis"] = axis
            self.assertIn("INVALID_VALUE", self.codes())

    def test_counterfactual_assumptions_and_verdicts(self):
        self.military()
        mc = self.record["findings"][0]["military_context"]
        mc["analysis_kind"] = "counterfactual"
        self.assertIn("COUNTERFACTUAL_ASSUMPTIONS", self.codes())
        mc["counterfactual_assumptions"] = ["変更：時点甲", "固定：資源甲"]
        self.assertEqual(guard.validate(self.record)["record_integrity"], "pass")
        self.source()
        a = self.assessment()
        self.assertIn("COUNTERFACTUAL_VERDICT", self.codes())
        a.update(verdict="conditional", additional_conditions=["仮定条件の成立"])
        self.assertEqual(guard.validate(self.record)["record_integrity"], "pass")
        a["evidence"] = []
        self.assertIn("SUPPORT_REQUIRED", self.codes())

    def test_duplicate_ids_unknown_references_fields(self):
        self.source()
        a = self.assessment()
        self.record["sources"].append(copy.deepcopy(self.record["sources"][0]))
        self.record["findings"].append(copy.deepcopy(self.record["findings"][0]))
        a["evidence"][0]["source_id"] = "R99"
        self.record["unknown"] = True
        self.assertTrue({"DUPLICATE_ID", "UNKNOWN_SOURCE", "UNKNOWN_FIELD"} <= self.codes())

    def test_malformed_nested_values_never_crash(self):
        self.measurement()
        self.record["context"]["mode"] = "integrated"
        self.record["findings"][0]["military_context"] = json.loads((SKILL / "examples/records/military.json").read_text())["findings"][0]["military_context"]
        original = copy.deepcopy(self.record)
        paths = [("context",), ("sources", 0), ("sources", 0, "bibliography"), ("findings", 0),
                 ("findings", 0, "target"), ("findings", 0, "assessments", 0),
                 ("findings", 0, "assessments", 0, "evidence", 0), ("findings", 0, "equipment_context", 0),
                 ("findings", 0, "measurements", 0), ("findings", 0, "military_context")]
        for path in paths:
            obj = original
            for key in path:
                obj = obj[key]
            for field in obj:
                for value in (None, [], {}, True, 123):
                    r = copy.deepcopy(original)
                    parent = r
                    for key in path:
                        parent = parent[key]
                    parent[field] = value
                    with self.subTest(path=path, field=field, value=value):
                        self.assertIn(guard.validate(r)["record_integrity"], ("pass", "fail"))

    def cli(self, args, stdin=None):
        return subprocess.run([sys.executable, "-B", str(SCRIPT), *args], input=stdin, text=True, capture_output=True)

    def test_cli_stdin_json_exit_codes_and_usage(self):
        capture = self.cli(["snapshot", "--root", str(self.root), "--file", "T01=対象 文.txt", "--span", "Q01=T01:1:1"])
        self.assertEqual(capture.returncode, 0, capture.stdout)
        s = self.root / "snapshot.json"
        s.write_text(capture.stdout)
        snap = json.loads(capture.stdout)
        self.local()
        self.record["snapshot_id"] = snap["snapshot_id"]
        good = self.cli(["validate", "--record", "-", "--snapshot", str(s)], json.dumps(self.record))
        self.assertEqual(good.returncode, 0, good.stdout)
        self.record["findings"][0]["target"]["quote"] = "偽引用"
        bad = self.cli(["validate", "--record", "-", "--snapshot", str(s)], json.dumps(self.record))
        self.assertEqual(bad.returncode, 1)
        for args, raw in [(["validate", "--record", "-"], '{"v":NaN}'), (["validate"], None),
                          (["validate", "--record", str(self.root / "missing.json")], None)]:
            error = self.cli(args, raw)
            self.assertEqual(error.returncode, 2)
            self.assertEqual(json.loads(error.stdout)["content_judgment"], "not_evaluated")
            self.assertNotIn("Traceback", error.stderr)

    def test_invalid_unicode_scalar_and_nonregular_json(self):
        for raw in ('{"unknown":"\\ud800"}', '{"\\ud800":1,"\\ud800":2}'):
            result = self.cli(["validate", "--record", "-"], raw)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)["record_integrity"], "input_error")
            self.assertNotIn("Traceback", result.stderr)
        fifo = self.root / "input.fifo"
        if hasattr(os, "mkfifo"):
            os.mkfifo(fifo)
            result = self.cli(["validate", "--record", str(fifo)])
            self.assertEqual(result.returncode, 2)

    def test_real_calculation_cannot_use_fictional_input(self):
        m = self.measurement('estimated')
        m.update(source_id=None, source_locator=None, calculation={
            'inputs': [{'name': '入力', 'value': '12', 'unit': 'kg', 'source_id': 'R01', 'assumption': None}],
            'formula': '入力と同値', 'rounding': 'なし', 'limitations': ['合成試験の式']})
        self.record['sources'][0]['source_domain'] = 'fictional'
        a = self.record['findings'][0]['assessments'][0]
        a.update(verdict='insufficient', missing_information=['実在資料'],
                 evidence=[{'source_id': 'R01', 'relation': 'context', 'locator': '1〜2行', 'span_id': None}])
        self.assertIn('MEASUREMENT_DOMAIN', self.codes())

    def test_snapshot_preserves_blank_line_span(self):
        (self.root / 'blank.txt').write_bytes(b' \r\n')
        snapshot = guard.capture(self.root, ['R01=blank.txt'], ['S01=R01:1:1'])
        self.assertEqual(snapshot['spans'][0]['text'], ' \r\n')
        self.assertEqual(guard.validate(self.record, snapshot)['errors'][0]['code'], 'SNAPSHOT_MISMATCH')
        self.record['snapshot_id'] = snapshot['snapshot_id']
        self.assertEqual(guard.validate(self.record, snapshot)['record_integrity'], 'pass')


if __name__ == "__main__":
    unittest.main()

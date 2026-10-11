#!/usr/bin/env python3
"""Schema 2 record integrity only. Python 3.9+, standard library, read-only."""
import argparse
import datetime as dt
import hashlib
import json
import math
import re
import stat
import subprocess
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath

VERSION = 2
MAX_BYTES = 16 * 1024 * 1024
MAX_DEPTH = 64
ID = r"[A-Z][A-Z0-9_-]{0,63}"
AXES = {"martial": tuple("ABCDE"), "weapons": tuple("W" + str(i) for i in range(1, 6)),
        "military": tuple("M" + str(i) for i in range(1, 7))}
AXES["integrated"] = AXES["martial"] + AXES["weapons"] + AXES["military"]
STATUSES = ("full_text", "abstract_only", "search_only", "unavailable", "unverified")
VERDICTS = ("supported", "conditional", "contradicted", "insufficient", "abstract_reports", "not_applicable")
SOURCE_CONTEXT = ("population", "sample", "task", "comparison", "resistance", "metrics", "results",
                  "generalization", "creation_date", "authorship", "purpose", "access_constraints",
                  "retrospective", "language", "translation", "cited_sources", "setting_status", "content_role")


class InputError(ValueError):
    pass


def text(value):
    return isinstance(value, str) and bool(value.strip())


def nullable(value):
    return value is None or text(value)


def strings(value):
    return isinstance(value, list) and all(text(v) for v in value)


def unique_strings(value):
    return strings(value) and len(value) == len(set(value))


def enum(*values):
    return lambda value: isinstance(value, str) and value in values


def matches(pattern):
    return lambda value: isinstance(value, str) and re.fullmatch(pattern, value) is not None


def date(value):
    if not matches(r"\d{4}-\d{2}-\d{2}")(value):
        return False
    try:
        dt.date.fromisoformat(value)
        return True
    except ValueError:
        return False


def digest(data):
    return hashlib.sha256(data).hexdigest()


def fingerprint(snapshot):
    return digest(json.dumps({k: v for k, v in snapshot.items() if k != "snapshot_id"},
                             ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                             allow_nan=False).encode("utf-8"))


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        key.encode("utf-8")
        if key in result:
            raise InputError("重複JSONキー: " + key)
        result[key] = value
    return result


def reject_constant(value):
    raise InputError("非有限数: " + value)


def finite_float(value):
    result = float(value)
    if not math.isfinite(result):
        raise InputError("非有限数: " + value)
    return result


def load_json(path):
    if path == "-":
        data = sys.stdin.buffer.read(MAX_BYTES + 1)
    else:
        source = Path(path)
        if not stat.S_ISREG(source.stat().st_mode):
            raise InputError("通常のJSONファイルが必要")
        with source.open("rb") as stream:
            data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise InputError("JSON上限16 MiB超過")
    raw = data.decode("utf-8")
    depth, quoted, escaped = 0, False, False
    for char in raw:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            depth += 1
            if depth > MAX_DEPTH:
                raise InputError("JSON入れ子上限64超過")
        elif char in "]}":
            depth -= 1
    result = json.loads(raw, object_pairs_hook=unique_pairs, parse_constant=reject_constant,
                        parse_float=finite_float)
    json.dumps(result, ensure_ascii=False, allow_nan=False).encode("utf-8")
    return result


def read_text(path):
    before = path.stat()
    if not stat.S_ISREG(before.st_mode):
        raise InputError("通常のUTF-8ファイルが必要: " + str(path))
    if before.st_size > MAX_BYTES:
        raise InputError("資料上限16 MiB超過")
    with path.open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    after = path.stat()
    if len(data) > MAX_BYTES:
        raise InputError("資料上限16 MiB超過")
    if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
        raise InputError("読取り中に資料が変更: " + str(path))
    return data, data.decode("utf-8")


def git_state(root):
    def run(*args):
        return subprocess.run(["git", "--no-optional-locks", "-C", str(root), *args],
                              check=True, capture_output=True, timeout=10).stdout.decode("utf-8")
    try:
        status = run("status", "--porcelain=v1", "-z", "--untracked-files=all")
        try:
            head = run("rev-parse", "--verify", "HEAD").strip()
        except subprocess.CalledProcessError:
            head = None
        return {"state": "available", "head": head, "status": status, "reason": None}
    except (OSError, UnicodeError, subprocess.SubprocessError):
        return {"state": "unverified", "head": None, "status": None, "reason": "Git確認不能"}


def assignment(spec):
    identifier, sep, value = spec.partition("=")
    if not sep or not matches(ID)(identifier) or not text(value):
        raise InputError("ID=値が必要: " + spec)
    return identifier, value


def capture(root, file_specs, span_specs):
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise InputError("rootはディレクトリが必要")
    files, spans, file_ids, span_ids = [], [], {}, set()
    total = 0
    for spec in file_specs:
        identifier, value = assignment(spec)
        if identifier in file_ids:
            raise InputError("重複ファイルID: " + identifier)
        path = Path(value)
        path = path if path.is_absolute() else root / path
        # Keep the leaf symlink so retargeting is detected by revalidation.
        path = path.parent.resolve(strict=True) / path.name
        data, raw = read_text(path)
        total += len(data)
        if total > MAX_BYTES:
            raise InputError("選択資料合計上限16 MiB超過")
        try:
            name = str(path.relative_to(root))
        except ValueError:
            name = str(path)
        entry = {"id": identifier, "path": name, "sha256": digest(data),
                 "text": raw, "line_count": len(raw.splitlines(keepends=True))}
        files.append(entry)
        file_ids[identifier] = entry
    if not files:
        raise InputError("fileが1件以上必要")
    for spec in span_specs:
        identifier, value = assignment(spec)
        parts = value.split(":")
        if identifier in span_ids or len(parts) != 3 or parts[0] not in file_ids:
            raise InputError("範囲は一意のID=FILE_ID:START:END: " + spec)
        start, end = int(parts[1]), int(parts[2])
        lines = file_ids[parts[0]]["text"].splitlines(keepends=True)
        if not 1 <= start <= end <= len(lines):
            raise InputError("行範囲外: " + spec)
        raw = "".join(lines[start - 1:end])
        spans.append({"id": identifier, "file_id": parts[0], "start_line": start,
                      "end_line": end, "text": raw, "sha256": digest(raw.encode("utf-8"))})
        span_ids.add(identifier)
    result = {"schema_version": VERSION, "root": str(root),
              "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
              "git": git_state(root), "files": files, "spans": spans,
              "record_integrity": "captured", "errors": [], "warnings": [], "content_judgment": "not_evaluated"}
    result["snapshot_id"] = fingerprint(result)
    if len(json.dumps(result, ensure_ascii=False).encode("utf-8")) > MAX_BYTES:
        raise InputError("snapshot JSON上限16 MiB超過。資料・範囲を減らしてください")
    return result


class Checks:
    def __init__(self):
        self.errors, self.warnings = [], []

    def add(self, code, at, message, warning=False):
        (self.warnings if warning else self.errors).append({"code": code, "at": at, "message": message})

    def obj(self, value, required, optional, at):
        if not isinstance(value, dict):
            self.add("OBJECT_REQUIRED", at, "オブジェクトが必要")
            return {}
        for key in value.keys() - required.keys() - optional.keys():
            self.add("UNKNOWN_FIELD", at + "." + key, "未知フィールド")
        for key, rule in {**required, **optional}.items():
            if key not in value:
                if key in required:
                    self.add("MISSING_FIELD", at + "." + key, "必須項目なし")
            elif not rule(value[key]):
                self.add("INVALID_VALUE", at + "." + key, "型または値が契約外")
        return value

    def entries(self, value, at, nonempty=False):
        if not isinstance(value, list) or (nonempty and not value):
            self.add("LIST_REQUIRED", at, "配列が必要" + ("（1件以上）" if nonempty else ""))
            return []
        return value

    def index(self, entries, at, id_pattern=ID):
        result = {}
        for i, item in enumerate(entries):
            identifier = item.get("id") if isinstance(item, dict) else None
            if not matches(id_pattern)(identifier):
                self.add("INVALID_ID", f"{at}[{i}].id", "不正ID")
            elif identifier in result:
                self.add("DUPLICATE_ID", f"{at}[{i}].id", "重複ID")
            else:
                result[identifier] = item
        return result

    def outcome(self):
        return {"schema_version": VERSION, "record_integrity": "fail" if self.errors else "pass",
                "errors": self.errors, "warnings": self.warnings, "content_judgment": "not_evaluated"}


def snapshot_index(snapshot):
    c = Checks()
    s = c.obj(snapshot, {"schema_version": lambda v: type(v) is int and v == VERSION,
                         "snapshot_id": matches(r"[0-9a-f]{64}"), "root": text, "created_at": text,
                         "git": lambda v: isinstance(v, dict), "files": lambda v: isinstance(v, list),
                         "spans": lambda v: isinstance(v, list), "record_integrity": enum("captured"),
                         "errors": lambda v: v == [], "warnings": lambda v: v == [],
                         "content_judgment": enum("not_evaluated")}, {}, "snapshot")
    if not c.errors:
        try:
            created = dt.datetime.fromisoformat(s["created_at"])
            if created.tzinfo is None or not (PurePosixPath(s["root"]).is_absolute() or PureWindowsPath(s["root"]).is_absolute()):
                raise ValueError()
        except ValueError:
            c.add("SNAPSHOT_FORMAT", "snapshot", "日時またはrootが不正")
        if s["snapshot_id"] != fingerprint(s):
            c.add("SNAPSHOT_HASH", "snapshot", "snapshotハッシュ不一致")
    g = c.obj(s.get("git"), {"state": enum("available", "unverified"),
                            "head": lambda v: v is None or matches(r"[0-9a-f]{40,64}")(v),
                            "status": lambda v: v is None or isinstance(v, str), "reason": nullable}, {}, "snapshot.git")
    if g.get("state") == "unverified" and (g.get("head") is not None or g.get("status") is not None):
        c.add("SNAPSHOT_FORMAT", "snapshot.git", "未確認状態にHEAD/statusは指定不可")
    files = c.index(c.entries(s.get("files"), "snapshot.files", True), "snapshot.files")
    spans = c.index(c.entries(s.get("spans"), "snapshot.spans"), "snapshot.spans")
    for identifier, entry in files.items():
        before = len(c.errors)
        c.obj(entry, {"id": matches(ID), "path": text, "sha256": matches(r"[0-9a-f]{64}"),
                      "text": lambda v: isinstance(v, str), "line_count": lambda v: type(v) is int and v >= 0}, {}, "snapshot.files." + identifier)
        if len(c.errors) == before:
            if digest(entry["text"].encode("utf-8")) != entry["sha256"] or len(entry["text"].splitlines(keepends=True)) != entry["line_count"]:
                c.add("SNAPSHOT_FORMAT", identifier, "保存本文・ハッシュ・行数不一致")
    for identifier, entry in spans.items():
        before = len(c.errors)
        c.obj(entry, {"id": matches(ID), "file_id": matches(ID), "start_line": lambda v: type(v) is int,
                      "end_line": lambda v: type(v) is int, "text": lambda v: isinstance(v, str) and bool(v), "sha256": matches(r"[0-9a-f]{64}")}, {}, "snapshot.spans." + identifier)
        if len(c.errors) == before:
            f = files.get(entry["file_id"])
            if not f or not isinstance(f.get("text"), str) or type(f.get("line_count")) is not int:
                c.add("SNAPSHOT_FORMAT", identifier, "未知または不正なファイル")
            elif not 1 <= entry["start_line"] <= entry["end_line"] <= f["line_count"]:
                c.add("SNAPSHOT_FORMAT", identifier, "行範囲外")
            elif entry["text"] != "".join(f["text"].splitlines(keepends=True)[entry["start_line"] - 1:entry["end_line"]]) or digest(entry["text"].encode("utf-8")) != entry["sha256"]:
                c.add("SNAPSHOT_FORMAT", identifier, "範囲本文不一致")
    if c.errors:
        raise InputError("snapshot破損: " + json.dumps(c.errors, ensure_ascii=False))
    return files, spans


def validate(record, snapshot=None, root_override=None):
    c = Checks()
    files, spans = snapshot_index(snapshot) if snapshot is not None else ({}, {})
    if snapshot is not None:
        root = Path(root_override or snapshot["root"]).resolve()
        current_git = git_state(root)
        if current_git["state"] == "unverified" or snapshot["git"]["state"] == "unverified":
            c.add("GIT_UNVERIFIED", "snapshot.git", "Git未確認", True)
        elif current_git != snapshot["git"]:
            c.add("GIT_CHANGED", "snapshot.git", "Git状態変更。本文は別途照合", True)
        for identifier, entry in files.items():
            path = Path(entry["path"])
            try:
                data, raw = read_text(path if path.is_absolute() else root / path)
                if digest(data) != entry["sha256"]:
                    c.add("FILE_CHANGED", identifier, "原資料変更。再読・再分析が必要")
                for span in spans.values():
                    if span["file_id"] == identifier and span["text"] != "".join(raw.splitlines(keepends=True)[span["start_line"] - 1:span["end_line"]]):
                        c.add("SPAN_CHANGED", span["id"], "引用範囲変更")
            except (OSError, ValueError, UnicodeError) as error:
                c.add("FILE_UNREADABLE", identifier, "原資料読取り不能: " + type(error).__name__)
    r = c.obj(record, {"schema_version": lambda v: type(v) is int and v == VERSION,
                       "snapshot_id": lambda v: v is None or matches(r"[0-9a-f]{64}")(v),
                       "context": lambda v: isinstance(v, dict), "sources": lambda v: isinstance(v, list),
                       "findings": lambda v: isinstance(v, list)}, {}, "record")
    if r.get("snapshot_id") != (snapshot["snapshot_id"] if snapshot is not None else None):
        c.add("SNAPSHOT_MISMATCH", "record.snapshot_id", "snapshotの有無またはID不一致")
    ctx = c.obj(r.get("context"), {"mode": enum(*AXES), "task": enum("survey", "compare", "review"),
                                "question": text, "scope": text, "conditions": strings, "assumptions": strings,
                                "checked_on": date, "requested_extensions": unique_strings},
                {"fiction_context": lambda v: isinstance(v, dict)}, "context")
    extensions = ctx.get("requested_extensions") if strings(ctx.get("requested_extensions")) else []
    if any(e not in ("fiction", "stage") for e in extensions):
        c.add("EXTENSION", "context.requested_extensions", "fiction/stageのみ")
    if "fiction_context" in ctx:
        c.obj(ctx["fiction_context"], {"story_point": nullable}, {}, "context.fiction_context")
        if "fiction" not in extensions:
            c.add("FICTION_REQUIRED", "context.fiction_context", "fictionの明示依頼が必要")
    mode = ctx.get("mode")
    allowed_axes = AXES.get(mode, ()) if isinstance(mode, str) else ()
    allowed_axes += ("F",) if "stage" in extensions else ()
    sources = c.index(c.entries(r.get("sources"), "sources"), "sources")
    for sid, source in sources.items():
        at = "sources." + sid
        c.obj(source, {"id": matches(ID), "source_domain": enum("real", "fictional", "design", "unknown"),
                       "source_type": text, "publisher_role": text, "modality": enum("text", "video", "image", "audio", "dataset", "mixed", "unknown"),
                       "bibliography": lambda v: isinstance(v, dict), "access_status": enum(*STATUSES),
                       "checked_on": lambda v: v is None or date(v), "method": nullable,
                       "read_range": nullable, "locator": nullable, "limitations": strings, "file_id": lambda v: v is None or matches(ID)(v)},
              {"source_context": lambda v: isinstance(v, dict)}, at)
        c.obj(source.get("bibliography"), {k: nullable for k in ("author", "title", "year", "edition", "url", "doi")}, {}, at + ".bibliography")
        if "source_context" in source:
            sc = c.obj(source["source_context"], {}, {k: lambda v: nullable(v) or strings(v) for k in SOURCE_CONTEXT}, at + ".source_context")
            if "setting_status" in sc and not enum("confirmed", "proposed", "subjective", "unknown")(sc["setting_status"]):
                c.add("SETTING_STATUS", at, "設定はconfirmed/proposed/subjective/unknown")
        if source.get("file_id") is not None:
            if snapshot is None:
                c.add("SNAPSHOT_REQUIRED", at, "ローカル出典にsnapshotが必要")
            if not isinstance(source["file_id"], str) or source["file_id"] not in files:
                c.add("UNKNOWN_FILE", at, "出典ファイル参照なし")
        status = source.get("access_status")
        if status in STATUSES[:-1] and (not date(source.get("checked_on")) or not text(source.get("method"))):
            c.add("ACQUISITION_REQUIRED", at, "確認・取得試行日と方法が必要")
        if status in ("full_text", "abstract_only"):
            bib = source.get("bibliography")
            if not isinstance(bib, dict) or not text(bib.get("title")) or not text(source.get("read_range")) or not text(source.get("locator")):
                c.add("LOCATION_REQUIRED", at, "資料名・閲覧範囲・箇所が必要")
            if source.get("file_id") is None:
                c.add("SOURCE_CONTENT_UNCHECKED", at, "外部本文の取得状態は申告。機械未照合", True)
    findings = c.index(c.entries(r.get("findings"), "findings", True), "findings", r"F\d{2,}")
    for fid, finding in findings.items():
        at = "findings." + fid
        c.obj(finding, {"id": matches(r"F\d{2,}"), "target": lambda v: isinstance(v, dict),
                        "domain": enum("real", "fictional", "subjective"), "facts": strings, "analysis": text,
                        "alternative_interpretations": strings, "assessments": lambda v: isinstance(v, list), "limitations": strings},
              {"revision": nullable, "equipment_context": lambda v: isinstance(v, list), "measurements": lambda v: isinstance(v, list),
               "military_context": lambda v: isinstance(v, dict)}, at)
        domain = finding.get("domain")
        if domain == "fictional" and "fiction" not in extensions:
            c.add("FICTION_REQUIRED", at, "fictional findingにはfictionが必要")
        target = finding.get("target")
        target = target if isinstance(target, dict) else {}
        if target.get("type") == "question":
            c.obj(target, {"type": enum("question"), "text": text}, {}, at + ".target")
        elif target.get("type") == "passage":
            c.obj(target, {"type": enum("passage"), "span_id": matches(ID), "quote": text}, {}, at + ".target")
            span = spans.get(target.get("span_id")) if isinstance(target.get("span_id"), str) else None
            if snapshot is None:
                c.add("SNAPSHOT_REQUIRED", at, "passageにsnapshotが必要")
            if span is None:
                c.add("UNKNOWN_SPAN", at, "対象範囲参照なし")
            elif text(target.get("quote")) and target["quote"] not in span["text"]:
                c.add("QUOTE_MISMATCH", at, "逐語引用が原文に不一致")
        else:
            c.add("TARGET_TYPE", at + ".target", "question/passageが必要")
        assessments = c.entries(finding.get("assessments"), at + ".assessments", True)
        axes, all_evidence = set(), []
        for i, assessment in enumerate(assessments):
            aa = at + f".assessments[{i}]"
            a = c.obj(assessment, {"axis": enum(*allowed_axes), "verdict": enum(*VERDICTS),
                                   "evidence": lambda v: isinstance(v, list), "conditions": strings,
                                   "additional_conditions": strings, "missing_information": strings}, {}, aa)
            axis = a.get("axis")
            if isinstance(axis, str):
                if axis in axes:
                    c.add("DUPLICATE_AXIS", aa, "同findingの同軸重複")
                axes.add(axis)
            eligible = []
            for j, evidence in enumerate(c.entries(a.get("evidence"), aa + ".evidence")):
                ea = aa + f".evidence[{j}]"
                e = c.obj(evidence, {"source_id": matches(ID), "relation": enum("supports", "contradicts", "reports", "context"),
                                     "locator": nullable, "span_id": lambda v: v is None or matches(ID)(v)}, {}, ea)
                sid = e.get("source_id")
                source = sources.get(sid) if isinstance(sid, str) else None
                if source is None:
                    c.add("UNKNOWN_SOURCE", ea, "未知の出典参照")
                    continue
                all_evidence.append(e)
                span_id = e.get("span_id")
                span = spans.get(span_id) if isinstance(span_id, str) else None
                local_ok = True
                if source.get("file_id") is not None:
                    if span is None or span["file_id"] != source["file_id"]:
                        c.add("SOURCE_SPAN_MISMATCH", ea, "ローカル出典は同ファイルの範囲が必要")
                        local_ok = False
                elif span_id is not None:
                    c.add("SOURCE_SPAN_MISMATCH", ea, "範囲を参照する出典にfile_idが必要")
                    local_ok = False
                status, relation = source.get("access_status"), e.get("relation")
                sc = source.get("source_context")
                sc = sc if isinstance(sc, dict) else {}
                domain_ok = (domain == "real" and source.get("source_domain") == "real") or (
                    domain == "fictional" and source.get("source_domain") == "fictional" and sc.get("setting_status") == "confirmed")
                if relation in ("supports", "contradicts") and (status != "full_text" or not domain_ok or not text(e.get("locator"))):
                    c.add("EVIDENCE_NOT_ELIGIBLE", ea, "支持/反証は同domainの本文と箇所（創作は確定設定）が必要")
                if relation == "reports" and (status != "abstract_only" or domain != "real" or source.get("source_domain") != "real" or not text(e.get("locator"))):
                    c.add("REPORTS_NOT_ELIGIBLE", ea, "reportsはrealの抄録と箇所が必要")
                if local_ok and text(e.get("locator")) and domain_ok:
                    eligible.append((status, relation))
            verdict = a.get("verdict")
            if verdict in ("supported", "conditional"):
                if ("full_text", "supports") not in eligible:
                    c.add("SUPPORT_REQUIRED", aa, "本文supportsが必要")
                if not strings(a.get("conditions")) or not a["conditions"]:
                    c.add("CONDITIONS_REQUIRED", aa, "具体的適用条件が必要")
            if verdict == "conditional" and (not strings(a.get("additional_conditions")) or not a["additional_conditions"]):
                c.add("ADDITIONAL_REQUIRED", aa, "具体的追加条件が必要")
            if verdict == "contradicted" and ("full_text", "contradicts") not in eligible:
                c.add("COUNTEREVIDENCE_REQUIRED", aa, "本文contradictsが必要")
            if verdict == "insufficient" and (not strings(a.get("missing_information")) or not a["missing_information"]):
                c.add("MISSING_INFORMATION_REQUIRED", aa, "不足情報が必要")
            if verdict == "abstract_reports" and ("abstract_only", "reports") not in eligible:
                c.add("ABSTRACT_REQUIRED", aa, "抄録reportsが必要")
            if verdict == "not_applicable" and domain != "subjective":
                c.add("SUBJECTIVE_REQUIRED", aa, "not_applicableは主観・比喩の説明のみ")
        equipment = c.index(c.entries(finding.get("equipment_context", []), at + ".equipment_context"), at + ".equipment_context")
        if any(axis in AXES["weapons"] for axis in axes) and not equipment:
            c.add("EQUIPMENT_REQUIRED", at, "W軸は装備1件以上が必要")
        for eid, eq in equipment.items():
            c.obj(eq, {"id": matches(ID), "name": text, **{k: nullable for k in ("variant", "region", "era", "configuration")},
                       "status": enum("historical", "adopted", "prototype", "proposed", "fictional", "unknown")}, {}, at + ".equipment_context." + eid)
            if eq.get("status") == "fictional" and (domain != "fictional" or "fiction" not in extensions):
                c.add("FICTIONAL_EQUIPMENT", at, "架空装備はfictional findingとfictionで扱う")
        for i, measurement in enumerate(c.entries(finding.get("measurements", []), at + ".measurements")):
            ma = at + f".measurements[{i}]"
            m = c.obj(measurement, {"equipment_id": matches(ID), "quantity": text, "original_value": text,
                                   "unit": nullable, "value_kind": enum("declared", "tested", "estimated", "modeled"),
                                   "source_id": lambda v: v is None or matches(ID)(v), "source_locator": nullable,
                                   "conditions": nullable, "calculation": lambda v: v is None or isinstance(v, dict)}, {}, ma)
            eid = m.get("equipment_id")
            if not isinstance(eid, str) or eid not in equipment:
                c.add("UNKNOWN_EQUIPMENT", ma, "同findingの装備IDが必要")
            sid = m.get("source_id")
            if m.get("value_kind") in ("declared", "tested") and (not isinstance(sid, str) or sid not in sources or not text(m.get("source_locator"))):
                c.add("MEASUREMENT_SOURCE_REQUIRED", ma, "公称/試験値は出典IDと箇所が必要")
            if sid is not None:
                if not isinstance(sid, str) or sid not in sources:
                    c.add("UNKNOWN_SOURCE", ma, "測定の出典参照なし")
                elif not any(e.get("source_id") == sid and e.get("locator") == m.get("source_locator") for e in all_evidence):
                    c.add("MEASUREMENT_EVIDENCE_REQUIRED", ma, "測定出典・箇所をevidenceにも参照")
                elif domain == "real" and sources[sid].get("source_domain") != "real":
                    c.add("MEASUREMENT_DOMAIN", ma, "現実の数値に現実資料が必要")
            elif m.get("source_locator") is not None:
                c.add("MEASUREMENT_SOURCE_REQUIRED", ma, "source_idなしではlocatorもnull")
            calculation = m.get("calculation")
            if m.get("value_kind") in ("estimated", "modeled") and calculation is None:
                c.add("CALCULATION_REQUIRED", ma, "推定/モデルには入力・式・限界が必要")
            if calculation is not None:
                ca = c.obj(calculation, {"inputs": lambda v: isinstance(v, list) and bool(v), "formula": text,
                                         "rounding": text, "limitations": lambda v: strings(v) and bool(v)}, {}, ma + ".calculation")
                for j, inp in enumerate(c.entries(ca.get("inputs"), ma + ".calculation.inputs", True)):
                    ia = ma + f".calculation.inputs[{j}]"
                    p = c.obj(inp, {"name": text, "value": text, "unit": nullable,
                                    "source_id": lambda v: v is None or matches(ID)(v), "assumption": nullable}, {}, ia)
                    ps = p.get("source_id")
                    if ps is not None and (not isinstance(ps, str) or ps not in sources or not any(e.get("source_id") == ps for e in all_evidence)):
                        c.add("CALCULATION_SOURCE", ia, "入力出典をevidenceにも参照")
                    elif ps is not None and domain == "real" and sources[ps].get("source_domain") != "real":
                        c.add("MEASUREMENT_DOMAIN", ia, "現実の計算入力に現実資料が必要")
                    if ps is None and not text(p.get("assumption")):
                        c.add("CALCULATION_ASSUMPTION", ia, "入力には出典または仮定が必要")
        military = finding.get("military_context")
        if any(axis in AXES["military"] for axis in axes) and military is None:
            c.add("MILITARY_REQUIRED", at, "M軸にはmilitary_contextが必要")
        if "military_context" in finding:
            mc = c.obj(military, {"analysis_kind": enum("terminology", "historical", "decision", "causal", "counterfactual"),
                                  "analysis_levels": unique_strings, "subject": text,
                                  **{k: nullable for k in ("period", "geography", "decision_point", "available_information", "resources", "constraints", "observed_outcome")},
                                  **{k: strings for k in ("actors", "objectives", "counterfactual_assumptions")},
                                  "knowledge_basis": enum("contemporary", "reconstructed", "mixed", "unknown")}, {}, at + ".military_context")
            levels = mc.get("analysis_levels")
            if not unique_strings(levels) or not levels or any(l not in ("tactical", "operational", "strategic", "grand_strategic", "unspecified") for l in levels) or ("unspecified" in levels and len(levels) != 1):
                c.add("MILITARY_LEVELS", at, "階層は既知の一意配列。unspecifiedは単独")
            if mc.get("analysis_kind") == "counterfactual":
                if not strings(mc.get("counterfactual_assumptions")) or not mc["counterfactual_assumptions"]:
                    c.add("COUNTERFACTUAL_ASSUMPTIONS", at, "変更/固定する仮定が必要")
                for a in assessments:
                    if isinstance(a, dict) and a.get("verdict") not in ("conditional", "insufficient"):
                        c.add("COUNTERFACTUAL_VERDICT", at, "反実仮想はconditional/insufficientのみ")
    return c.outcome()


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise InputError(message)


def main(argv=None):
    try:
        parser = Parser(description="記録の整合性検証。内容の正しさは未評価")
        commands = parser.add_subparsers(dest="command", required=True)
        snap = commands.add_parser("snapshot")
        snap.add_argument("--root", required=True)
        snap.add_argument("--file", action="append", required=True)
        snap.add_argument("--span", action="append", default=[])
        check = commands.add_parser("validate")
        check.add_argument("--record", required=True)
        check.add_argument("--snapshot")
        check.add_argument("--root")
        args = parser.parse_args(argv)
        if args.command == "snapshot":
            result, code = capture(args.root, args.file, args.span), 0
        else:
            if args.snapshot == "-":
                raise InputError("snapshotは保存したファイルを指定")
            snapshot = load_json(args.snapshot) if args.snapshot else None
            result = validate(load_json(args.record), snapshot, args.root)
            code = 0 if result["record_integrity"] == "pass" else 1
    except (InputError, OSError, ValueError, UnicodeError, RecursionError) as error:
        result = {"schema_version": VERSION, "record_integrity": "input_error", "errors": [{"code": "INPUT_ERROR", "at": "input", "message": str(error)}],
                  "warnings": [], "content_judgment": "not_evaluated"}
        code = 2
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return code


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(main())

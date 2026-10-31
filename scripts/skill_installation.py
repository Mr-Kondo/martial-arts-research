"""Copy deployment shared by install.py and uninstall.py; standard library only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

NAME = 'martial-arts-research'
MARKER = '.martial-arts-research-install.json'
FILES = ('SKILL.md', 'README.md', 'VERSION', 'CHANGELOG.md', '01-research-report.md',
         '02-skill-design.md', '03-codex-implementation-prompt.md', 'codex-implementation-prompt.txt',
         'package-files.txt')
FOLDERS = ('references', 'scripts', 'examples', 'evals', 'docs', 'adr')


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def inventory(root):
    files, directories = {}, []
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError('シンボリックリンクは管理しません: ' + str(path))
        name = path.relative_to(root).as_posix()
        if path.is_dir():
            directories.append(name)
        elif path.is_file():
            if name != MARKER:
                files[name] = digest(path)
        else:
            raise ValueError('通常ファイル以外があります: ' + str(path))
    return files, directories


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('管理記録のJSONキー重複')
        result[key] = value
    return result


def ensure_owned(destination):
    if destination.is_symlink():
        raise ValueError('リンク配置を上書き・削除しません: ' + str(destination))
    if not destination.exists():
        return False
    marker = destination / MARKER
    if not destination.is_dir() or marker.is_symlink() or not marker.is_file():
        raise ValueError('管理記録のない配置です。別途バックアップして比較してください: ' + str(destination))
    if marker.stat().st_size > 2 * 1024 * 1024:
        raise ValueError('管理記録のサイズ上限超過')
    record = json.loads(marker.read_text(encoding='utf-8'), object_pairs_hook=unique_pairs)
    if (not isinstance(record, dict) or set(record) != {'schema_version', 'name', 'version', 'files', 'directories'}
            or type(record['schema_version']) is not int or record['schema_version'] != 1
            or record['name'] != NAME or not isinstance(record['version'], str)
            or not isinstance(record['files'], dict) or 'SKILL.md' not in record['files']
            or not isinstance(record['directories'], list)):
        raise ValueError('管理記録が不正です: ' + str(marker))
    files, directories = inventory(destination)
    if files != record['files'] or directories != record['directories']:
        raise ValueError('配置に変更・追加・削除があります。更新・削除を中止: ' + str(destination))
    return True


def destinations(target, project=None, user=False):
    base = Path.home() if user else Path(project or Path.cwd()).expanduser().resolve()
    surfaces = {'codex': ('.agents',), 'claude': ('.claude',), 'both': ('.agents', '.claude')}[target]
    return [base / surface / 'skills' / NAME for surface in surfaces]


def copy_package(source, stage):
    source = Path(source).resolve()
    version = (source / 'VERSION').read_text(encoding='utf-8').strip()
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version):
        raise ValueError('VERSIONはmajor.minor.patchが必要')
    manifest = source / 'package-files.txt'
    if manifest.is_symlink():
        raise ValueError('配布一覧にリンクは使えません')
    names = manifest.read_text(encoding='utf-8-sig').splitlines()
    folded_names = {name.casefold() for name in names}
    if len(names) != len(folded_names) or not set(FILES).issubset(names):
        raise ValueError('配布一覧に重複または必須ファイルの欠落があります')
    for name in names:
        path = Path(name)
        if (not name or path.is_absolute() or path.as_posix() != name
                or any(part in ('', '.', '..') or part.startswith('.') or part.endswith((' ', '.'))
                       or part.casefold() in ('feedback', '__pycache__')
                       or re.fullmatch(r'(?i)(con|prn|aux|nul|conin\$|conout\$|com[1-9¹²³]|lpt[1-9¹²³]) *(\..*)?', part)
                       for part in name.split('/'))
                or re.search(r'[<>"|?*\x00-\x1f]', name) or '\\' in name or ':' in name
                or name.casefold().endswith(('.local.md', '.pyc'))
                or any('/'.join(path.parts[:i]).casefold() in folded_names
                       for i in range(1, len(path.parts)))
                or (name not in FILES and path.parts[0] not in FOLDERS)):
            raise ValueError('配布一覧のパスが不正です: ' + name)
        # Check each parent before copying; copy2 follows directory links too.
        if ((source / path).resolve() != source / path
                or any(parent.is_symlink() for parent in (source / path, *(source / path).parents)
                       if parent != source and source in parent.parents)):
            raise ValueError('配布元にリンクがあります: ' + name)
        if not (source / path).is_file():
            raise ValueError('配布元ファイルが不足: ' + name)
    stage.mkdir()
    for name in FOLDERS:
        (stage / name).mkdir()
    for name in names:
        target = stage / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / name, target)
    if [p.relative_to(stage).as_posix() for p in stage.rglob('*')
            if p.name.casefold() == 'skill.md'] != ['SKILL.md']:
        raise ValueError('配布物に検出対象のSKILL.mdが複数あります')
    files, directories = inventory(stage)
    record = {'schema_version': 1, 'name': NAME, 'version': version,
              'files': files, 'directories': directories}
    (stage / MARKER).write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return record


def install(source, targets):
    source = Path(source).resolve()
    for destination in targets:
        if source != destination and source.is_relative_to(destination):
            raise ValueError('配布元の親ディレクトリは置換しません')
        ensure_owned(destination)
    results = []
    for destination in targets:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.martial-install-', dir=destination.parent) as temporary:
            stage, backup = Path(temporary) / NAME, Path(temporary) / 'previous'
            record = copy_package(source, stage)
            exists = ensure_owned(destination)
            if exists:
                os.replace(destination, backup)
            try:
                os.replace(stage, destination)
            except OSError:
                if exists:
                    os.replace(backup, destination)
                raise
            results.append({'path': str(destination), 'action': 'updated' if exists else 'installed',
                            'version': record['version'], 'files': len(record['files'])})
    return results


def uninstall(targets):
    for destination in targets:
        ensure_owned(destination)
    results = []
    for destination in targets:
        if ensure_owned(destination):
            shutil.rmtree(destination)
            action = 'uninstalled'
        else:
            action = 'absent'
        results.append({'path': str(destination), 'action': action})
    return results


def parser(description):
    result = argparse.ArgumentParser(description=description)
    result.add_argument('--target', choices=('codex', 'claude', 'both'), default='both')
    scope = result.add_mutually_exclusive_group()
    scope.add_argument('--project', type=Path, help='プロジェクトのパス。既定は現在のディレクトリ')
    scope.add_argument('--user', action='store_true', help='個人用配置を明示的に選択')
    return result

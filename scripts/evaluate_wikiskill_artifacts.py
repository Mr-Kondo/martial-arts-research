#!/usr/bin/env python3
"""Run frozen maintenance tasks with audited fixture-only search/read tools."""
import argparse
from collections import Counter
import json
import os
import posixpath
import signal
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from evaluate_maintenance import digest, parse_answer
from evaluate_retrieval import private_output

ROOT = Path(__file__).resolve().parents[1]
TOOLS = {'mcp__evidence__find_evidence', 'mcp__evidence__open_evidence'}
MODEL = 'claude-sonnet-5-5'
MAX_TURNS = 24
COMMON_CONTEXT = ('SKILL.md', 'docs/feedback.md', 'docs/templates/problem-report.md')


def supplied_sources(system, fixture):
    if not all(fixture.get(name) for name in COMMON_CONTEXT):
        return []
    # Match the exact ordered document concatenation used by systems(), rather
    # than an incidental quotation of a short document elsewhere in the prompt.
    base = '\n\n'.join(fixture[name] for name in COMMON_CONTEXT)
    return sorted(COMMON_CONTEXT) if system.startswith(base) else []


def citation_flags(citations, reads, supplied, rejected=0):
    return {'unverified_citations': sorted(set(citations)-set(reads)-set(supplied)),
            'empty_citations': not any(not p.startswith('maintenance/') for p in citations),
            'cli_rejected_calls': rejected}


class AnswerError(ValueError):
    pass


class EvaluationTimeout(AnswerError):
    pass


class TurnLimitError(AnswerError):
    """Explicit max-turn envelope; a nonzero CLI exit is expected."""


def save_streams(out, stdout, stderr, prefix=''):
    """Keep original process bytes even after interruption or invalid UTF-8."""
    decoded = []
    valid = True
    for name, data in [('stdout', stdout), ('stderr', stderr)]:
        (out/(prefix+name+'.bin')).write_bytes(data)
        try:
            text = data.decode('utf-8')
        except UnicodeDecodeError:
            text = data.decode('utf-8', errors='replace')
            valid = False
        (out/(prefix+name+'.log')).write_text(text, encoding='utf-8')
        decoded.append(text)
    return *decoded, valid


def request_for(cases):
    visible = [{k: c[k] for k in ('id', 'scene', 'request', 'draft', 'observations')} for c in cases]
    return ('各依頼の実際の成果物を作成してください。更新依頼ではこのスキル自体の改訂本文を、'
            '通常依頼では研究回答または問題報告本文を作成します。'
            '正本は必要に応じてfind_evidence/open_evidenceで検索・参照できます。'
            'ソースへの書込は不要です。確認した根拠の相対パスを引用してください。'
            '最終回答はJSONのみ。各idをキーとし、値は'
            '{"decision":"判断", "text":"完成した本文", "evidence":["相対パス"],'
            '"limits":"未確認事項・適用限界"}としてください。\n'
            + json.dumps(visible, ensure_ascii=False))


def inspect(text, audit):
    events = [json.loads(line) for line in text.splitlines() if line.strip()]
    initial = [e for e in events if e.get('type') == 'system' and e.get('subtype') == 'init']
    if len(initial) != 1 or set(initial[0].get('tools', [])) != TOOLS:
        raise ValueError('unexpected or missing tool inventory')
    inventory = initial[0]
    if ([(s.get('name'), s.get('status')) for s in inventory.get('mcp_servers', [])]
            != [('evidence', 'connected')] or inventory.get('skills') or inventory.get('slash_commands')
            or any(p.get('path') != 'builtin' for p in inventory.get('plugins', []))):
        raise ValueError('unexpected connected context inventory')
    calls = []
    rejected = set()
    models = set()
    finals = []
    for event in events:
        message = event.get('message') or {}
        if event.get('type') == 'assistant' and message.get('model'):
            models.add(message['model'])
        if event.get('type') == 'result':
            finals.append(event)
        content = message.get('content', [])
        if isinstance(content, list):
            calls.extend(b for b in content if b.get('type') == 'tool_use')
            rejected.update(b['tool_use_id'] for b in content
                            if b.get('type') == 'tool_result' and b.get('is_error'))
    calls = list({c['id']: c for c in calls}.values())
    unknown = [c for c in calls if c['name'] not in TOOLS]
    if any(c['id'] not in rejected for c in unknown):
        raise ValueError('forbidden tool call without verified CLI rejection')
    if len(finals) != 1:
        raise ValueError('failed or missing final result')
    final = finals[0]
    if final.get('is_error') or final.get('subtype') != 'success':
        message = str(final.get('result', ''))
        if final.get('subtype') == 'error_max_turns':
            raise TurnLimitError('model exhausted turn limit: '+message[:200])
        # Unknown CLI/API errors are not evidence of a model quality failure.
        raise ValueError('CLI infrastructure error: '+message[:200])
    if models != {MODEL} or set(final.get('modelUsage', {})) != {MODEL}:
        raise ValueError('unverified model report')
    records = [json.loads(line) for line in audit.read_text(encoding='utf-8').splitlines()] if audit.exists() else []
    # Count a tool only when the local server actually executed it. Reconcile both traces.
    allowed_calls = [c for c in calls if c['name'] in TOOLS]
    expected = [(c['name'].removeprefix('mcp__evidence__'), c.get('input', {})) for c in allowed_calls]
    actual = [(r['name'], r['arguments']) for r in records]
    signature = lambda rows: Counter(json.dumps(row, sort_keys=True) for row in rows)
    missing = signature(expected)-signature(actual)
    rejected_signatures = signature([(c['name'].removeprefix('mcp__evidence__'), c.get('input', {}))
                                     for c in allowed_calls if c['id'] in rejected])
    # Conservatively disallow ambiguous duplicate signatures, including successful
    # executions whose CLI result was an error. They cannot excuse another missing call.
    rejected_signatures -= signature(actual)
    if signature(actual)-signature(expected) or missing-rejected_signatures:
        raise ValueError('model/server tool audit mismatch')
    if unknown:
        raise AnswerError('model requested a forbidden tool; CLI rejected it without execution')
    final['_cli_rejected_calls'] = sum(missing.values())
    final['_context_inventory'] = {k: inventory.get(k) for k in
                                  ('mcp_servers', 'skills', 'plugins', 'agents', 'slash_commands')}
    return final, records


def execute(frozen, cases, arm, out):
    if len(cases) != 1:
        raise ValueError('one independent task per session is required')
    private_output(out)
    out.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((frozen/'frozen.json').read_text(encoding='utf-8'))
    if 'cases_sha256' in manifest:
        registered = json.loads((frozen/'cases-all.json').read_text(encoding='utf-8'))['cases']
        if digest((frozen/'cases-all.json').read_text(encoding='utf-8')) != manifest['cases_sha256']:
            raise ValueError('case registry drift')
        if cases[0] not in registered:
            raise ValueError('case not in frozen registry')
    system = (frozen/(arm+'-system.md')).read_text(encoding='utf-8')
    if digest(system) != manifest['systems'][arm]:
        raise ValueError('system drift')
    fixture = {}
    for name, expected in manifest['corpus'].items():
        if (Path(name).is_absolute() or '..' in Path(name).parts
                or not Path(name).parts or Path(name).parts[0] == 'maintenance'
                or Path(name).suffix not in ('.md', '.json', '.txt')):
            raise ValueError('unsafe corpus manifest path')
        body = (frozen/'corpus'/name).read_text(encoding='utf-8')
        if digest(body) != expected:
            raise ValueError('corpus drift')
        fixture[name] = body
    if arm == 'B3':
        for name in ('guide.md', 'knowledge.md'):
            body = (frozen/name).read_text(encoding='utf-8')
            if digest(body) != manifest['candidate'][name]:
                raise ValueError('candidate drift')
            fixture['maintenance/'+name] = body
    prompt = request_for(cases)
    supplied = supplied_sources(system, fixture)
    (out/'request.md').write_text(prompt, encoding='utf-8')
    env = os.environ.copy()
    row = {'arm': arm, 'ids': [c['id'] for c in cases], 'system_sha256': digest(system),
           'request_sha256': digest(prompt), 'status': 'incomplete', 'failure_class': 'infra',
           'system_characters': len(system), 'max_turns': MAX_TURNS,
           'supplied_sources': supplied,
           'corpus_sha256': digest(json.dumps(manifest['corpus'], sort_keys=True)),
           'fixture_sha256': digest(json.dumps({k: digest(v) for k,v in fixture.items()}, sort_keys=True)),
           'runner_sha256': digest(Path(__file__).read_text(encoding='utf-8')),
           'server_sha256': digest((ROOT/'scripts/evaluation_evidence_server.py').read_text(encoding='utf-8')),
           'cli': '/opt/homebrew/bin/claude'}
    start = time.monotonic()
    try:
        settings = Path.home()/'.claude/settings.json'
        if settings.exists():
            env.update({k: str(v) for k,v in json.loads(settings.read_text(encoding='utf-8')).get('env', {}).items()})
        env.pop('CLAUDECODE', None)
        env.pop('CLAUDE_CODE_SIMPLE', None)
        row['cli_version'] = subprocess.run([row['cli'], '--version'], capture_output=True,
                                            text=True, encoding='utf-8', timeout=15, check=True).stdout.strip()
        with tempfile.TemporaryDirectory(prefix='wikiskill-artifact-') as temporary:
            workspace = Path(temporary)
            evidence_root = workspace/'evidence'
            evidence_root.mkdir()
            cwd = workspace/'cwd'
            cwd.mkdir()
            for name, body in fixture.items():
                path = evidence_root/name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(body, encoding='utf-8')
            (out/'allowed.json').write_text(json.dumps(sorted(fixture)), encoding='utf-8')
            config = {'mcpServers': {'evidence': {'command': sys.executable,
                      'args': [str(ROOT/'scripts/evaluation_evidence_server.py'), '--root', str(evidence_root),
                               '--audit', str(out/'audit.jsonl'), '--allowlist', str(out/'allowed.json')]}}}
            command = ['/opt/homebrew/bin/claude', '--print', '--model', MODEL, '--effort', 'medium',
                       '--tools', '', '--allowedTools', 'mcp__evidence__*', '--setting-sources', '',
                       '--disable-slash-commands', '--settings', '{"disableAllHooks":true}',
                       '--strict-mcp-config', '--mcp-config', json.dumps(config),
                       '--no-session-persistence', '--verbose', '--output-format', 'stream-json',
                       '--max-turns', str(MAX_TURNS),
                       '--system-prompt', system]
            process = subprocess.Popen(command, cwd=cwd, env=env,
                                       stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, start_new_session=True)
            try:
                stdout, stderr = process.communicate(prompt.encode('utf-8'), timeout=300)
                row['process_returncode'] = process.returncode
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                stdout, stderr = process.communicate()
                row['process_returncode'] = process.returncode
                save_streams(out, stdout, stderr, 'partial-')
                raise EvaluationTimeout('evaluation timeout; process group terminated') from None
            finally:
                if process.poll() is None:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    partial_out, partial_err = process.communicate()
                    row['process_returncode'] = process.returncode
                    save_streams(out, partial_out, partial_err, 'partial-')
            stdout, stderr, valid_utf8 = save_streams(out, stdout, stderr)
            (out/'stream.jsonl').write_text(stdout, encoding='utf-8')
            (out/'stderr.log').write_text(stderr, encoding='utf-8')
            if not valid_utf8:
                raise ValueError('invalid UTF-8 process output; original bytes preserved')
            # Inspect error envelope even for nonzero exits, preserving reset/transport evidence.
            try:
                final, audit = inspect(stdout, out/'audit.jsonl')
            except AnswerError as error:
                if process.returncode and not isinstance(error, TurnLimitError):
                    raise ValueError('nonzero CLI exit with incomplete model answer') from None
                raise
            if process.returncode:
                raise ValueError('nonzero CLI exit')
            row['failure_class'] = 'answer'
            answer = parse_answer(final)
            if not isinstance(answer, dict) or set(answer) != set(row['ids']):
                raise ValueError('answer case IDs mismatch')
            for value in answer.values():
                if (not isinstance(value, dict) or any(not isinstance(value.get(k), str)
                        for k in ('decision', 'text', 'limits')) or not value['text'].strip()
                        or not isinstance(value.get('evidence'), list)
                        or any(not isinstance(p, str) for p in value['evidence'])):
                    raise ValueError('malformed artifact')
            reads = sorted({r['path'] for r in audit if r['name'] == 'open_evidence' and r['success']})
            hits = {p for r in audit for p in r.get('hit_paths', [])}
            citation_status = {}
            for key, value in answer.items():
                normalized = [posixpath.normpath(p.strip()) for p in value['evidence'] if p.strip()]
                value['evidence'] = normalized
                citation_status[key] = {p: ('read' if p in reads else 'supplied' if p in supplied else 'search_only' if p in hits
                    else 'unread' if p in fixture else 'nonexistent') for p in normalized}
            row.update(status='ok', failure_class='none', answer=answer, usage=final.get('usage', {}),
                       model_usage=final['modelUsage'], audit=audit, reads=reads,
                       context_inventory=final['_context_inventory'],
                       returned_characters=sum(r.get('returned_characters', 0) for r in audit),
                       citation_status=citation_status,
                       answer_flags={k: citation_flags(v['evidence'],reads,supplied,final['_cli_rejected_calls'])
                                     for k,v in answer.items()})
    except (ValueError, OSError, TypeError, KeyError, AttributeError, subprocess.SubprocessError) as error:
        if isinstance(error, AnswerError):
            row['failure_class'] = 'answer'
        if isinstance(error, EvaluationTimeout):
            row['failure_class'] = 'timeout'
        row['error'] = str(error)
        if isinstance(error, subprocess.TimeoutExpired):
            for key, value in [('partial-stdout', error.stdout), ('partial-stderr', error.stderr)]:
                if isinstance(value, bytes):
                    value = value.decode(errors='replace')
                (out/(key+'.log')).write_text(value or '', encoding='utf-8')
    row['elapsed_seconds'] = round(time.monotonic()-start, 3)
    (out/'result.json').write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding='utf-8')
    return row


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frozen', type=Path, required=True)
    parser.add_argument('--cases', type=Path, required=True)
    parser.add_argument('--arm', choices=('A', 'B1', 'B2', 'B3'), required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = execute(args.frozen.resolve(), json.loads(args.cases.read_text(encoding='utf-8'))['cases'], args.arm,
                     args.out.resolve())
    print(result['status'])
    raise SystemExit(result['status'] != 'ok')

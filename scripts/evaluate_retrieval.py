#!/usr/bin/env python3
"""Observe bounded read-only evidence retrieval. See adr/wikiskill-retrieval-evaluation.md."""
import argparse
import json
import os
from pathlib import Path
import statistics
import subprocess
import tempfile
import time

from evaluate_maintenance import digest, parse_answer

ROOT = Path(__file__).resolve().parents[1]
USAGE_KEYS = ('input_tokens', 'output_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens')
ARMS = ('A', 'B1', 'B2', 'B3')
ORDERS = (('B2', 'A', 'B3', 'B1'), ('A', 'B1', 'B3', 'B2'), ('B3', 'B2', 'B1', 'A'))


def corpus():
    """Only explicitly selected tracked public evidence; never copy feedback or settings."""
    paths = subprocess.run(['git', 'ls-files', '--', 'SKILL.md', 'docs', 'references',
                            'examples', 'adr/explicit-package-boundary.md',
                            'adr/format-preservation-ab.md', 'adr/private-feedback-regression.md',
                            'adr/three-environment-delivery.md', 'evals/results/format-preservation-ab.md'],
                           cwd=ROOT, check=True, capture_output=True, text=True).stdout.splitlines()
    result = {name: (ROOT / name).read_text(encoding='utf-8') for name in paths
              if Path(name).suffix in ('.md', '.json', '.txt')}
    required = {'SKILL.md', 'docs/feedback.md', 'docs/templates/problem-report.md',
                'adr/explicit-package-boundary.md', 'adr/three-environment-delivery.md',
                'evals/results/format-preservation-ab.md', 'references/evidence-policy.md',
                'references/research-methods.md'}
    if not required <= set(result):
        raise ValueError('required public evidence missing')
    return result


def validate_cases(cases, evidence):
    if not isinstance(cases, dict) or set(cases) != {'update', 'normal'}:
        raise ValueError('invalid scenes')
    ids = []
    for scene, count in [('update', 3), ('normal', 1)]:
        if not isinstance(cases[scene], list) or len(cases[scene]) != count:
            raise ValueError('invalid case count')
        for case in cases[scene]:
            ids.append(case['id'])
            claims, sources = case['claims'], case['sources']
            if (not isinstance(case['request'], str) or not case['request'].strip()
                    or not isinstance(claims, dict) or not 3 <= len(claims) <= 4
                    or any(type(v) is not bool for v in claims.values())
                    or not isinstance(sources, list) or not sources
                    or any(p not in evidence for p in sources)):
                raise ValueError('invalid oracle or unavailable canonical source')
    if len(set(ids)) != len(ids):
        raise ValueError('duplicate case ID')


def private_output(out):
    try:
        out.resolve().relative_to((ROOT / 'feedback').resolve())
    except ValueError:
        raise ValueError('execution output must be under feedback') from None
    if subprocess.run(['git', 'check-ignore', '--quiet', str(out / 'probe')], cwd=ROOT).returncode:
        raise ValueError('execution output is not Git-ignored')


def systems(candidate):
    base = '\n\n'.join((ROOT / p).read_text(encoding='utf-8') for p in
                          ('SKILL.md', 'docs/feedback.md', 'docs/templates/problem-report.md'))
    guide = (candidate / 'guide.md').read_text(encoding='utf-8')
    knowledge = (candidate / 'knowledge.md').read_text(encoding='utf-8')
    return {'A': base, 'B1': base + '\n' + guide, 'B2': base + '\n' + guide + '\n' + knowledge,
            'B3': base + '\n' + (candidate / 'lazy-entry.md').read_text(encoding='utf-8')}


def freeze(candidate, out):
    private_output(out)
    out.mkdir(parents=True, exist_ok=False)
    evidence = corpus()
    prompts = systems(candidate)
    frozen = {'corpus': {p: digest(v) for p, v in evidence.items()},
              'systems': {p: digest(v) for p, v in prompts.items()},
              'candidate': {p.name: digest(p.read_text(encoding='utf-8'))
                            for p in candidate.glob('*.md')}}
    for name, body in evidence.items():
        path = out / 'corpus' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding='utf-8')
    for arm, body in prompts.items():
        (out / (arm + '-system.md')).write_text(body, encoding='utf-8')
    for name in ('guide.md', 'knowledge.md'):
        (out / name).write_text((candidate / name).read_text(encoding='utf-8'), encoding='utf-8')
    (out / 'frozen.json').write_text(json.dumps(frozen, indent=2), encoding='utf-8')
    return frozen


def relative_path(value, workspace):
    path = Path(value)
    path = path if path.is_absolute() else workspace / path
    try:
        return path.resolve().relative_to(workspace.resolve()).as_posix()
    except ValueError:
        raise ValueError('tool accessed a path outside the fixture') from None


def inspect_stream(text, workspace, allowed_tools=('Read', 'Grep', 'Glob')):
    """Count actual tool requests and successful explicit Read results; require final CLI success."""
    events = [json.loads(line) for line in text.splitlines() if line.strip()]
    calls = {}
    successful = set()
    final = None
    assistant_models = set()
    for event in events:
        if event.get('type') == 'assistant' and (event.get('message') or {}).get('model'):
            assistant_models.add(event['message']['model'])
        if event.get('type') == 'result':
            final = event
        content = (event.get('message') or {}).get('content', [])
        if not isinstance(content, list):
            continue
        for block in content:
            if block.get('type') == 'tool_use':
                name = block['name']
                if name not in allowed_tools:
                    raise ValueError('unexpected tool: ' + name)
                args = block.get('input', {})
                value = args.get('file_path') if name == 'Read' else args.get('path', '.')
                pattern_keys = ('glob',) if name == 'Grep' else ('pattern',) if name == 'Glob' else ()
                for key in pattern_keys:
                    pattern = args.get(key)
                    if isinstance(pattern, str):
                        if '../' in pattern or pattern == '..':
                            raise ValueError('parent traversal in tool pattern')
                        relative_path(pattern, workspace)
                calls[block['id']] = {'name': name, 'path': relative_path(value or '.', workspace)}
            elif block.get('type') == 'tool_result' and not block.get('is_error', False):
                successful.add(block['tool_use_id'])
    if final is None or final.get('is_error') or final.get('subtype', 'success') != 'success':
        raise ValueError('missing or failed CLI result')
    read_paths = sorted({row['path'] for key, row in calls.items()
                         if key in successful and row['name'] == 'Read'})
    return final, {'tool_calls': len(calls), 'read_paths': read_paths,
                   'assistant_models': sorted(assistant_models),
                   'maintenance_reads': sum(row['name'] == 'Read' and row['path'].startswith('maintenance/')
                                            for row in calls.values()),
                   'tools': list(calls.values())}


def prompt_for(cases, paths=()):
    visible = [{'id': c['id'], 'request': c['request'], 'claim_keys': list(c['claims'])} for c in cases]
    return ('手元の正本ファイルを調べ、各依頼に答えてください。書込は不要です。'
            '使用するツールはReadのみ。現在の作業ディレクトリ配下だけに使ってください。'
            '引用する根拠はReadで本文を実際に開いて確認してください。'
            '最終回答はJSONのみ。キーはid、値は'
            '{"claims":{"各claim_key":trueまたはfalse},"evidence":["正本の相対パス"],'
            '"answer":"根拠と限界を含む短い回答"}です。\n'
            + '全条件共通の正本ファイル一覧:\n' + '\n'.join(sorted(paths))
            + '\n依頼:\n' + json.dumps(visible, ensure_ascii=False))


def score(cases, answer, reads, available):
    if not isinstance(answer, dict) or set(answer) != {c['id'] for c in cases}:
        raise ValueError('missing or unexpected answer IDs')
    result = {}
    for case in cases:
        row = answer[case['id']]
        if not isinstance(row, dict) or not isinstance(row.get('answer'), str) or not row['answer'].strip():
            raise ValueError('missing answer text')
        claims = row.get('claims')
        if (not isinstance(claims, dict) or set(claims) != set(case['claims'])
                or any(type(v) is not bool for v in claims.values())):
            raise ValueError('invalid claims')
        cited = row.get('evidence')
        if not isinstance(cited, list) or not cited or any(not isinstance(p, str) for p in cited):
            raise ValueError('invalid evidence list')
        grounded = (set(cited) <= set(reads) & set(available)
                    and set(case['sources']) <= set(cited))
        result[case['id']] = {'correct_claims': sum(claims[k] == v for k, v in case['claims'].items()),
                              'total_claims': len(claims), 'grounded': grounded}
    return result


def summary(runs):
    result = {}
    for arm in ARMS:
        result[arm] = {}
        for scene in ('update', 'normal'):
            rows = [r for r in runs if r['arm'] == arm and r['scene'] == scene]
            valid = len(rows) == 3 and all(r.get('status') == 'ok' for r in rows)
            usage_known = valid and all(all(type(r.get('usage', {}).get(k)) is int for k in USAGE_KEYS)
                                        for r in rows)
            perfect = valid and all(s['correct_claims'] == s['total_claims'] and s['grounded']
                                    for r in rows for s in r['scores'].values())
            result[arm][scene] = {'complete': valid, 'perfect': perfect,
                'seconds': [r['elapsed_seconds'] for r in rows],
                'tool_calls': [r.get('trace', {}).get('tool_calls') for r in rows],
                'maintenance_reads': [r.get('trace', {}).get('maintenance_reads') for r in rows],
                'maintenance_sources': [[p for p in r.get('trace', {}).get('read_paths', [])
                                         if p.startswith('maintenance/')] for r in rows],
                'tokens': [sum(r['usage'][k] for k in USAGE_KEYS) for r in rows] if usage_known else None}
    return result


def resource_win(candidate, baseline):
    if not candidate['perfect'] or not baseline['complete'] or not candidate['tokens'] or not baseline['tokens']:
        return False
    ct, bt = statistics.median(candidate['tokens']), statistics.median(baseline['tokens'])
    cs, bs = statistics.median(candidate['seconds']), statistics.median(baseline['seconds'])
    return (ct <= .9 * bt and cs <= bs) or (
        cs <= .8 * bs and ct <= 1.1 * bt
        and sum(c < b for c, b in zip(candidate['seconds'], baseline['seconds'])) >= 2)


def adoption(results):
    """Predeclared resource and normal-work gates, applied before any delivery decision."""
    base = results['A']
    def normal_ok(arm):
        row = results[arm]['normal']
        return bool(row['perfect'] and row['tokens'] and base['normal']['complete']
                    and base['normal']['tokens'] and row['maintenance_reads'] == [0, 0, 0]
                    and statistics.median(row['tokens']) <= 1.1 * statistics.median(base['normal']['tokens']))
    decisions = {'B1': normal_ok('B1') and resource_win(results['B1']['update'], base['update']),
                 'B2': normal_ok('B2') and resource_win(results['B2']['update'], base['update'])
                       and resource_win(results['B2']['update'], results['B1']['update'])}
    lazy, inline = results['B3']['update'], results['B2']['update']
    required = {'maintenance/guide.md', 'maintenance/knowledge.md'}
    activated = (len(lazy.get('maintenance_sources', [])) == 3
                 and all(required <= set(paths) for paths in lazy['maintenance_sources']))
    comparable = bool(lazy['tokens'] and inline['tokens'] and lazy['complete'] and inline['complete'])
    decisions['B3'] = bool(activated and normal_ok('B3') and resource_win(lazy, base['update']) and comparable
        and statistics.median(lazy['seconds']) <= 1.1 * statistics.median(inline['seconds'])
        and statistics.median(lazy['tokens']) <= 1.1 * statistics.median(inline['tokens']))
    return decisions


def run(frozen, cases_file, out, cli):
    private_output(out)
    out.mkdir(parents=True, exist_ok=False)
    cases = json.loads(cases_file.read_text(encoding='utf-8'))
    evidence = {p.relative_to(frozen / 'corpus').as_posix(): p.read_text(encoding='utf-8')
                for p in (frozen / 'corpus').rglob('*') if p.is_file()}
    manifest = json.loads((frozen / 'frozen.json').read_text(encoding='utf-8'))
    if {p: digest(v) for p, v in evidence.items()} != manifest['corpus']:
        raise ValueError('corpus changed since freeze')
    validate_cases(cases, evidence)
    prompts = {a: (frozen / (a + '-system.md')).read_text(encoding='utf-8') for a in ARMS}
    if {a: digest(v) for a, v in prompts.items()} != manifest['systems']:
        raise ValueError('systems changed since freeze')
    env = os.environ.copy()
    env.pop('CLAUDECODE', None)
    metadata = {'runs': [], 'cases_sha256': digest(cases_file.read_text(encoding='utf-8')),
                'runner_sha256': digest(Path(__file__).read_text(encoding='utf-8')),
                'frozen': manifest, 'model': 'claude-sonnet-5-5', 'effort': 'medium',
                'retrieval_mode': 'Read-only with identical canonical file inventory',
                'cli_version': subprocess.run([cli, '--version'], capture_output=True,
                                               text=True, timeout=15).stdout.strip()}
    for trial, order in enumerate(ORDERS, 1):
        for arm in order:
            for scene in (('update', 'normal') if trial % 2 else ('normal', 'update')):
                name = f'{trial}-{arm}-{scene}'
                row = {'trial': trial, 'arm': arm, 'scene': scene}
                with tempfile.TemporaryDirectory(prefix='martial-retrieval-') as temporary:
                    workspace = Path(temporary)
                    fixture = dict(evidence)
                    if arm == 'B3':
                        for file in ('guide.md', 'knowledge.md'):
                            body = (frozen / file).read_text(encoding='utf-8')
                            if digest(body) != manifest['candidate'][file]:
                                raise ValueError('candidate changed since freeze')
                            fixture['maintenance/' + file] = body
                    for file, body in fixture.items():
                        path = workspace / file
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_text(body, encoding='utf-8')
                    command = [cli, '--print', '--model', metadata['model'], '--effort', 'medium',
                        '--tools', 'Read', '--allowedTools', 'Read',
                        '--disable-slash-commands', '--safe-mode', '--setting-sources', 'user',
                        '--settings', '{"disableAllHooks":true}', '--strict-mcp-config',
                        '--mcp-config', '{"mcpServers":{}}', '--no-session-persistence',
                        '--verbose', '--output-format', 'stream-json', '--system-prompt', prompts[arm]]
                    started = time.monotonic()
                    try:
                        response = subprocess.run(command, input=prompt_for(cases[scene], evidence), cwd=workspace,
                            env=env, text=True, encoding='utf-8', capture_output=True, timeout=180)
                        (out / (name + '.jsonl')).write_text(response.stdout, encoding='utf-8')
                        (out / (name + '-stderr.log')).write_text(response.stderr, encoding='utf-8')
                        row['exit_code'] = response.returncode
                        if response.returncode:
                            raise ValueError('nonzero CLI exit')
                        envelope, trace = inspect_stream(response.stdout, workspace, allowed_tools=('Read',))
                        row.update(trace=trace, usage=envelope.get('usage') or {},
                                   model_usage=envelope.get('modelUsage'), cost_usd=envelope.get('total_cost_usd'))
                        if (set((envelope.get('modelUsage') or {})) != {metadata['model']}
                                or set(trace['assistant_models']) != {metadata['model']}):
                            raise ValueError('missing or mismatched reported model')
                        answer = parse_answer(envelope)
                        row['scores'] = score(cases[scene], answer, trace['read_paths'], evidence)
                        row['answer'] = answer
                        row['status'] = 'ok'
                    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
                        row.update(status='incomplete', error=str(error))
                        if isinstance(error, subprocess.TimeoutExpired):
                            for suffix, output in [('partial-stdout', error.stdout), ('partial-stderr', error.stderr)]:
                                if output:
                                    if isinstance(output, bytes):
                                        output = output.decode('utf-8', errors='replace')
                                    (out / (name + '-' + suffix + '.log')).write_text(output, encoding='utf-8')
                    row['elapsed_seconds'] = round(time.monotonic() - started, 3)
                metadata['runs'].append(row)
                (out / 'metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
                print(name + ': ' + row['status'], flush=True)
                if row['status'] != 'ok':
                    (out / 'summary.json').write_text(json.dumps(summary(metadata['runs']), indent=2), encoding='utf-8')
                    return 1
    results = summary(metadata['runs'])
    (out / 'summary.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    (out / 'adoption.json').write_text(json.dumps(adoption(results), indent=2), encoding='utf-8')
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate-dir', type=Path)
    parser.add_argument('--freeze', type=Path, required=True)
    parser.add_argument('--cases', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--cli', default='/opt/homebrew/bin/claude')
    args = parser.parse_args()
    if args.candidate_dir:
        freeze(args.candidate_dir, args.freeze)
    elif args.cases and args.out:
        raise SystemExit(run(args.freeze, args.cases, args.out, args.cli))
    else:
        parser.error('provide candidate-dir to freeze, or cases and out to run')

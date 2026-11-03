#!/usr/bin/env python3
"""Private-fixture read/search MCP server for evaluation; never serves the source checkout."""
import argparse
import json
from pathlib import Path
import sys
import time


def resolve_file(root, name, allowed=None):
    root = root.resolve()
    if (root / name).is_symlink():
        raise ValueError('symlink files are not served')
    path = (root / name).resolve()
    if (not path.is_relative_to(root.resolve()) or not path.is_file()
            or path.suffix not in ('.md', '.json', '.txt')):
        raise ValueError('file outside fixture or unavailable')
    if allowed is not None and path.relative_to(root).as_posix() not in allowed:
        raise ValueError('file not in fixture manifest')
    return path


def serve(root, audit, allowed=None):
    tools = [
        {'name': 'find_evidence', 'description': 'Search canonical text files for a literal phrase, case-insensitive. Maintenance guides are read directly, not searched. Use offset for more matches.',
         'inputSchema': {'type': 'object', 'properties': {'query': {'type': 'string'}, 'offset': {'type': 'integer', 'minimum': 0}},
                         'required': ['query'], 'additionalProperties': False}},
        {'name': 'open_evidence', 'description': 'Read a fixture-relative file; returns numbered lines.',
         'inputSchema': {'type': 'object', 'properties': {'path': {'type': 'string'}},
                         'required': ['path'], 'additionalProperties': False}}]
    for raw in sys.stdin:
        try:
            request = json.loads(raw)
            if not isinstance(request, dict):
                raise ValueError('request must be an object')
        except ValueError:
            print(json.dumps({'jsonrpc': '2.0', 'id': None,
                              'error': {'code': -32700, 'message': 'invalid request JSON'}}), flush=True)
            continue
        if 'id' not in request or 'method' not in request:
            continue
        method = request.get('method')
        try:
            if method == 'initialize':
                requested = request['params']['protocolVersion']
                result = {'protocolVersion': requested if requested in ('2024-11-05', '2025-03-26', '2025-06-18', '2025-11-25') else '2025-11-25',
                          'capabilities': {'tools': {}},
                          'serverInfo': {'name': 'wikiskill-fixture', 'version': '1.0'}}
            elif method == 'ping':
                result = {}
            elif method == 'tools/list':
                result = {'tools': tools}
            elif method == 'tools/call':
                start = time.monotonic()
                args = request['params'].get('arguments', {})
                name = request['params']['name']
                record = {'name': name, 'arguments': args, 'success': False}
                try:
                    if not isinstance(args, dict):
                        raise ValueError('arguments must be an object')
                    if name == 'find_evidence':
                        query = args['query']
                        if not isinstance(query, str) or not 2 <= len(query) <= 160:
                            raise ValueError('query must contain 2..160 characters')
                        offset = args.get('offset', 0)
                        if type(offset) is not int or offset < 0:
                            raise ValueError('offset must be a nonnegative integer')
                        hits = []
                        for path in sorted(root.rglob('*')):
                            if (path.is_file() and not path.is_symlink()
                                    and path.resolve().is_relative_to(root.resolve())
                                    and path.relative_to(root).parts[0] != 'maintenance'
                                    and (allowed is None or path.relative_to(root).as_posix() in allowed)
                                    and path.suffix in ('.md', '.json', '.txt')):
                                for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
                                    if query.casefold() in line.casefold():
                                        position = line.casefold().find(query.casefold())
                                        begin = max(0, position - 150)
                                        hits.append({'path': path.relative_to(root).as_posix(),
                                                     'line': number, 'text': line[begin:begin+400]})
                        body = json.dumps({'matches': hits[offset:offset+40], 'total': len(hits)}, ensure_ascii=False)
                        record['matches'] = len(hits)
                        record['hit_paths'] = sorted({h['path'] for h in hits[offset:offset+40]})
                    elif name == 'open_evidence':
                        path = resolve_file(root, args['path'], allowed)
                        text = path.read_text(encoding='utf-8')
                        if len(text) > 60000:
                            raise ValueError('fixture file exceeds read limit')
                        body = '\n'.join(f'{n}: {line}' for n, line in enumerate(text.splitlines(), 1))
                        record['path'] = path.relative_to(root).as_posix()
                    else:
                        raise ValueError('unknown tool')
                    record.update(success=True, returned_characters=len(body))
                    result = {'content': [{'type': 'text', 'text': body}]}
                except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
                    result = {'content': [{'type': 'text', 'text': str(error)}], 'isError': True}
                    record['error'] = str(error)
                record['seconds'] = time.monotonic() - start
                with audit.open('a', encoding='utf-8') as output:
                    output.write(json.dumps(record, ensure_ascii=False) + '\n')
            else:
                raise ValueError('unsupported method')
            response = {'jsonrpc': '2.0', 'id': request['id'], 'result': result}
        except (KeyError, TypeError, ValueError, AttributeError, OSError) as error:
            response = {'jsonrpc': '2.0', 'id': request['id'],
                        'error': {'code': -32602, 'message': str(error)}}
        print(json.dumps(response, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--allowlist', type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    checkout = Path(__file__).resolve().parents[1]
    if (not root.is_dir() or root.is_relative_to(checkout) or checkout.is_relative_to(root)
            or args.audit.resolve().is_relative_to(root)):
        parser.error('provide an isolated fixture directory')
    allowed = set(json.loads(args.allowlist.read_text())) if args.allowlist else None
    serve(root, args.audit.resolve(), allowed)

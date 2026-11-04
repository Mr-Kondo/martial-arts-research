"""Actual subprocess protocol and fixture-boundary regression checks."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SERVER = Path(__file__).resolve().parents[1] / 'evaluation_evidence_server.py'


class EvidenceServerTest(unittest.TestCase):
    def test_utf8_protocol_overrides_non_utf8_console_locale(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            root = parent/'fixture'
            root.mkdir()
            (root/'日本語.md').write_text('日本語の正本\n', encoding='utf-8')
            allowed = parent/'allow.json'
            allowed.write_text(json.dumps(['日本語.md'], ensure_ascii=False), encoding='utf-8')
            wire = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                               'params': {'name': 'open_evidence',
                                          'arguments': {'path': '日本語.md'}}}, ensure_ascii=False)+'\n'
            env = dict(os.environ, PYTHONIOENCODING='ascii', PYTHONUTF8='0')
            result = subprocess.run([sys.executable, str(SERVER), '--root', str(root),
                                     '--audit', str(parent/'audit.jsonl'), '--allowlist', str(allowed)],
                                    input=wire.encode('utf-8'), capture_output=True,
                                    check=True, timeout=10, env=env)
            reply = json.loads(result.stdout.decode('utf-8'))
            self.assertEqual(reply['result']['content'][0]['text'], '1: 日本語の正本')
            audit = json.loads((parent/'audit.jsonl').read_text(encoding='utf-8'))
            self.assertTrue(audit['success'])
            self.assertEqual(audit['path'], '日本語.md')

    def test_protocol_search_and_boundaries(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            root = parent / 'fixture'
            root.mkdir()
            (root / 'source.md').write_text('Alpha\n' * 45)
            (root / 'large.md').write_text('z' * 60001)
            (parent / 'private.txt').write_text('secret Alpha')
            (root / 'escape.md').symlink_to(parent / 'private.txt')
            (root / 'maintenance').mkdir()
            (root / 'maintenance/guide.md').write_text('Alpha hidden guide')
            audit = parent / 'audit.jsonl'
            calls = [
                ('initialize', {'protocolVersion': '2025-11-25'}),
                ('tools/list', {}),
                ('tools/call', {'name': 'find_evidence', 'arguments': {'query': 'alpha'}}),
                ('tools/call', {'name': 'open_evidence', 'arguments': {'path': 'source.md'}}),
                ('tools/call', {'name': 'open_evidence', 'arguments': {'path': '../private.txt'}}),
                ('tools/call', {'name': 'open_evidence', 'arguments': {'path': 'escape.md'}}),
                ('tools/call', {'name': 'open_evidence', 'arguments': {'path': 'large.md'}}),
                ('tools/call', {'name': 'find_evidence', 'arguments': {'query': 'a'}}),
                ('tools/call', {'name': 'execute', 'arguments': {}}),
                ('unsupported', {}), ('ping', {})]
            wire = 'invalid\n' + json.dumps({'jsonrpc': '2.0', 'method': 'notifications/initialized'}) + '\n'
            wire += '\n'.join(json.dumps({'jsonrpc': '2.0', 'id': i, 'method': method,
                                         'params': params}) for i, (method, params) in enumerate(calls)) + '\n'
            result = subprocess.run([sys.executable, str(SERVER), '--root', str(root),
                                     '--audit', str(audit)], input=wire, text=True,
                                    capture_output=True, check=True, timeout=10)
            replies = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertEqual(replies[0]['error']['code'], -32700)
            replies = replies[1:]
            self.assertEqual(replies[0]['result']['protocolVersion'], '2025-11-25')
            self.assertEqual({t['name'] for t in replies[1]['result']['tools']},
                             {'find_evidence', 'open_evidence'})
            search = json.loads(replies[2]['result']['content'][0]['text'])
            self.assertEqual(search['total'], 45)
            self.assertEqual(len(search['matches']), 40)
            self.assertEqual({hit['path'] for hit in search['matches']}, {'source.md'})
            self.assertTrue(replies[3]['result']['content'][0]['text'].startswith('1: Alpha\n2: Alpha'))
            self.assertTrue(all(replies[i]['result']['isError'] for i in range(4, 9)))
            self.assertIn('error', replies[9])
            self.assertEqual(replies[10]['result'], {})
            records = [json.loads(line) for line in audit.read_text().splitlines()]
            self.assertEqual(len(records), 7)
            self.assertEqual([r['success'] for r in records], [True, True] + [False] * 5)
            self.assertTrue(all('seconds' in r for r in records))

    def test_unsafe_roots_and_audit_are_rejected(self):
        checkout = SERVER.parents[1]
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            fixture = parent/'fixture'
            fixture.mkdir()
            for root, audit in [(checkout, parent/'audit'), (checkout.parent, parent/'audit'),
                                (checkout/'scripts', parent/'audit'), (fixture, fixture/'audit')]:
                result = subprocess.run([sys.executable, str(SERVER), '--root', str(root),
                                         '--audit', str(audit)], input='', text=True,
                                        capture_output=True, timeout=10)
                self.assertNotEqual(result.returncode, 0)

    def test_allowlist_pagination_and_direct_maintenance(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent=Path(temporary)
            root=parent/'fixture'
            root.mkdir()
            (root/'source.md').write_text('Alpha\n'*45)
            (root/'unlisted.md').write_text('Alpha forbidden')
            (root/'maintenance').mkdir()
            (root/'maintenance/guide.md').write_text('Alpha maintenance')
            allowed=parent/'allow.json'
            allowed.write_text(json.dumps(['source.md','maintenance/guide.md']))
            arguments=[('find_evidence',dict(query='alpha',offset=40)),
                       ('open_evidence',dict(path='maintenance/guide.md')),
                       ('open_evidence',dict(path='unlisted.md'))]
            wire='\n'.join(json.dumps(dict(jsonrpc='2.0',id=i,method='tools/call',
                         params=dict(name=name,arguments=args))) for i,(name,args) in enumerate(arguments))+'\n'
            result=subprocess.run([sys.executable,str(SERVER),'--root',str(root),
                                   '--audit',str(parent/'audit'),'--allowlist',str(allowed)],
                                  input=wire,text=True,capture_output=True,check=True,timeout=10)
            replies=[json.loads(line)['result'] for line in result.stdout.splitlines()]
            search=json.loads(replies[0]['content'][0]['text'])
            self.assertEqual(search['total'],45)
            self.assertEqual([m['line'] for m in search['matches']],list(range(41,46)))
            self.assertIn('maintenance',replies[1]['content'][0]['text'])
            self.assertTrue(replies[2]['isError'])


if __name__ == '__main__':
    unittest.main()

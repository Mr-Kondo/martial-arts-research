import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluate_wikiskill_artifacts import inspect, request_for, execute, MODEL, TOOLS, ROOT, supplied_sources, citation_flags, COMMON_CONTEXT
from evaluate_maintenance import digest


def init():
    return dict(type='system', subtype='init', tools=list(TOOLS),
                mcp_servers=[dict(name='evidence', status='connected')])


class ArtifactTest(unittest.TestCase):
    def test_common_system_sources_are_available_without_duplicate_tool_read(self):
        fixture={name:'FULL SOURCE '+name for name in COMMON_CONTEXT}
        base='\n\n'.join(fixture[name] for name in COMMON_CONTEXT)
        self.assertEqual(supplied_sources(base+'\nextra',fixture),sorted(COMMON_CONTEXT))
        self.assertEqual(supplied_sources('quote '+base,fixture),[])
        self.assertEqual(supplied_sources(base[:-1],fixture),[])
        self.assertEqual(supplied_sources(base,{'SKILL.md':'FULL SOURCE'}),[])
        flags=citation_flags(['SKILL.md','unread.md','maintenance/guide.md'],
                             ['maintenance/guide.md'],supplied_sources(base,fixture))
        self.assertEqual(flags['unverified_citations'],['unread.md'])
        self.assertFalse(flags['empty_citations'])
        self.assertTrue(citation_flags(['maintenance/guide.md'],['maintenance/guide.md'],[])['empty_citations'])
    def test_oracle_not_in_request(self):
        case = dict(id='x', scene='update', request='edit', draft='old', observations='new',
                    required=['SECRET_ORACLE'], forbidden=['BAD_ORACLE'], sources=['hidden.md'])
        prompt = request_for([case])
        for private in ('SECRET_ORACLE', 'BAD_ORACLE', 'hidden.md'):
            self.assertNotIn(private, prompt)
        self.assertIn('old', prompt)

    def test_trace_must_match_actual_execution_and_model(self):
        events = [init(),
                  dict(type='assistant', message=dict(model=MODEL, content=[
                      dict(type='tool_use', id='one', name='mcp__evidence__open_evidence',
                           input={'path': 'source.md'})])),
                  dict(type='result', subtype='success', is_error=False, modelUsage={MODEL: {}},
                       result='{}')]
        with tempfile.TemporaryDirectory() as temporary:
            audit = Path(temporary)/'audit.jsonl'
            wire = lambda: '\n'.join(map(json.dumps, events))
            with self.assertRaisesRegex(ValueError, 'audit mismatch'):
                inspect(wire(), audit)
            audit.write_text(json.dumps(dict(name='open_evidence', arguments={'path': 'source.md'},
                                             path='source.md', success=True))+'\n')
            final, records = inspect(wire(), audit)
            self.assertFalse(final['is_error'])
            self.assertEqual(len(records), 1)
            events[1]['message']['content'][0]['name'] = 'Bash'
            with self.assertRaisesRegex(ValueError, 'forbidden tool'):
                inspect(wire(), audit)
            events[1]['message']['content'][0]['name'] = 'mcp__evidence__open_evidence'
            events[1]['message']['model'] = 'different'
            with self.assertRaisesRegex(ValueError, 'unverified model'):
                inspect(wire(), audit)

    def test_execute_separates_failures_and_arm_fixtures(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'feedback',prefix='unit-artifact-') as temporary:
            root=Path(temporary)
            frozen=root/'frozen'
            (frozen/'corpus').mkdir(parents=True)
            (frozen/'corpus/source.md').write_text('public evidence')
            manifest={'systems':{},'corpus':{'source.md':digest('public evidence')},'candidate':{}}
            for arm in ('A','B1','B2','B3'):
                (frozen/(arm+'-system.md')).write_text('system '+arm)
                manifest['systems'][arm]=digest('system '+arm)
            for name in ('guide.md','knowledge.md'):
                (frozen/name).write_text(name)
                manifest['candidate'][name]=digest(name)
            (frozen/'frozen.json').write_text(json.dumps(manifest))
            case=dict(id='x',scene='update',request='revise',draft='old',observations='new')
            cited=[]
            for arm in ('A','B1','B2','B3'):
                def fake_popen(command,**kwargs):
                    self.assertNotIn('CLAUDECODE',kwargs['env'])
                    self.assertNotIn('CLAUDE_CODE_SIMPLE',kwargs['env'])
                    config=json.loads(command[command.index('--mcp-config')+1])
                    args=config['mcpServers']['evidence']['args']
                    fixture=Path(args[args.index('--root')+1])
                    self.assertNotEqual(fixture,kwargs['cwd'])
                    self.assertEqual((fixture/'maintenance/guide.md').exists(),arm=='B3')
                    self.assertEqual((fixture/'maintenance/knowledge.md').exists(),arm=='B3')
                    events=[init(),
                            dict(type='assistant',message=dict(model=MODEL,content=[])),
                            dict(type='result',subtype='success',is_error=False,modelUsage={MODEL:{}},
                                 result=json.dumps({'x':dict(decision='revise',text='done',limits='none',evidence=cited)}))]
                    self.assertIn('--max-turns', command)
                    return SimpleNamespace(returncode=0,poll=lambda:0,
                                           communicate=lambda *a,**k:('\n'.join(map(json.dumps,events)),''))
                with patch('evaluate_wikiskill_artifacts.subprocess.run',return_value=SimpleNamespace(stdout='test-version',returncode=0)),\
                     patch('evaluate_wikiskill_artifacts.subprocess.Popen',side_effect=fake_popen):
                    row=execute(frozen,[case],arm,root/arm)
                self.assertEqual(row['status'],'ok')
                self.assertEqual(row['process_returncode'],0)
                self.assertTrue(row['answer_flags']['x']['empty_citations'])
            for name in COMMON_CONTEXT:
                path=frozen/'corpus'/name
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text('FULL '+name)
                manifest['corpus'][name]=digest('FULL '+name)
            base='\n\n'.join((frozen/'corpus'/name).read_text() for name in COMMON_CONTEXT)
            (frozen/'A-system.md').write_text(base)
            manifest['systems']['A']=digest(base)
            (frozen/'frozen.json').write_text(json.dumps(manifest))
            cited=['SKILL.md','unread.md']
            arm='A'
            with patch('evaluate_wikiskill_artifacts.subprocess.run',return_value=SimpleNamespace(stdout='v',returncode=0)),\
                 patch('evaluate_wikiskill_artifacts.subprocess.Popen',side_effect=fake_popen):
                row=execute(frozen,[case],'A',root/'provided')
            self.assertEqual(row['citation_status']['x']['SKILL.md'],'supplied')
            self.assertEqual(row['answer_flags']['x']['unverified_citations'],['unread.md'])
            self.assertEqual(row['supplied_sources'],sorted(COMMON_CONTEXT))
            def nonzero_popen(*args,**kwargs):
                process=fake_popen(*args,**kwargs)
                process.returncode=7
                process.poll=lambda:7
                return process
            with patch('evaluate_wikiskill_artifacts.subprocess.run',return_value=SimpleNamespace(stdout='v',returncode=0)),\
                 patch('evaluate_wikiskill_artifacts.subprocess.Popen',side_effect=nonzero_popen),\
                 patch('evaluate_wikiskill_artifacts.Path.home',return_value=root):
                row=execute(frozen,[case],'A',root/'nonzero-missing-settings')
            self.assertEqual(row['process_returncode'],7)
            self.assertEqual(row['failure_class'],'infra')
            from evaluate_wikiskill_artifacts import TurnLimitError
            with patch('evaluate_wikiskill_artifacts.subprocess.run',return_value=SimpleNamespace(stdout='v',returncode=0)),\
                 patch('evaluate_wikiskill_artifacts.subprocess.Popen',side_effect=nonzero_popen),\
                 patch('evaluate_wikiskill_artifacts.inspect',side_effect=TurnLimitError('model exhausted turn limit')):
                row=execute(frozen,[case],'A',root/'nonzero-max-turns')
            self.assertEqual(row['failure_class'],'answer')
            self.assertEqual(row['process_returncode'],7)
            from evaluate_wikiskill_artifacts import AnswerError
            with patch('evaluate_wikiskill_artifacts.subprocess.run',return_value=SimpleNamespace(stdout='v',returncode=0)),\
                 patch('evaluate_wikiskill_artifacts.subprocess.Popen',side_effect=nonzero_popen),\
                 patch('evaluate_wikiskill_artifacts.inspect',side_effect=AnswerError('rejected model call')):
                row=execute(frozen,[case],'A',root/'nonzero-answer')
            self.assertEqual(row['failure_class'],'infra')
            self.assertEqual(row['process_returncode'],7)
            (root/'.claude').mkdir()
            (root/'.claude/settings.json').write_text(json.dumps({'env':{'CLAUDECODE':'1','CLAUDE_CODE_SIMPLE':'1'}}))
            with patch('evaluate_wikiskill_artifacts.subprocess.run',return_value=SimpleNamespace(stdout='v',returncode=0)),\
                 patch('evaluate_wikiskill_artifacts.subprocess.Popen',side_effect=fake_popen),\
                 patch('evaluate_wikiskill_artifacts.Path.home',return_value=root):
                row=execute(frozen,[case],'A',root/'sanitized-settings')
            self.assertEqual(row['status'],'ok')
            for error, classification in [(KeyError('bad envelope'),'infra'),
                                           (AttributeError('bad envelope'),'infra')]:
                with patch('evaluate_wikiskill_artifacts.subprocess.run',return_value=SimpleNamespace(stdout='v',returncode=0)),\
                     patch('evaluate_wikiskill_artifacts.subprocess.Popen',side_effect=error):
                    row=execute(frozen,[case],'A',root/(classification+type(error).__name__))
                self.assertEqual(row['failure_class'],classification)
                self.assertTrue((root/(classification+type(error).__name__)/'result.json').exists())
            process=SimpleNamespace(pid=123,returncode=-9,poll=lambda:-9)
            from unittest.mock import Mock
            process.communicate=Mock(side_effect=[subprocess.TimeoutExpired('model',300),('partial','timeout')])
            with patch('evaluate_wikiskill_artifacts.subprocess.run',return_value=SimpleNamespace(stdout='v',returncode=0)),\
                 patch('evaluate_wikiskill_artifacts.subprocess.Popen',return_value=process),\
                 patch('evaluate_wikiskill_artifacts.os.killpg') as terminate:
                row=execute(frozen,[case],'A',root/'timeout')
            self.assertEqual(row['failure_class'],'timeout')
            self.assertEqual(row['process_returncode'],-9)
            terminate.assert_called_once()
            self.assertEqual((root/'timeout/partial-stdout.log').read_text(),'partial')
            process.communicate=Mock(side_effect=[subprocess.TimeoutExpired('model',300),('partial after exit','timeout')])
            with patch('evaluate_wikiskill_artifacts.subprocess.run',return_value=SimpleNamespace(stdout='v',returncode=0)),\
                 patch('evaluate_wikiskill_artifacts.subprocess.Popen',return_value=process),\
                 patch('evaluate_wikiskill_artifacts.os.killpg',side_effect=ProcessLookupError):
                row=execute(frozen,[case],'A',root/'timeout-race')
            self.assertEqual(row['failure_class'],'timeout')
            self.assertEqual((root/'timeout-race/partial-stdout.log').read_text(),'partial after exit')
            self.assertEqual(row['process_returncode'],-9)
            process.poll=lambda:None
            process.communicate=Mock(side_effect=[KeyboardInterrupt(),('partial','interrupted')])
            with patch('evaluate_wikiskill_artifacts.subprocess.run',return_value=SimpleNamespace(stdout='v',returncode=0)),\
                 patch('evaluate_wikiskill_artifacts.subprocess.Popen',return_value=process),\
                 patch('evaluate_wikiskill_artifacts.os.killpg') as terminate:
                with self.assertRaises(KeyboardInterrupt):
                    execute(frozen,[case],'A',root/'interrupted')
            terminate.assert_called_once()
            (frozen/'cases-all.json').write_text(json.dumps({'cases':[case]}))
            manifest['cases_sha256']=digest((frozen/'cases-all.json').read_text())
            (frozen/'frozen.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'not in frozen registry'):
                execute(frozen,[dict(case,observations='modified')],'A',root/'case-drift')
            (frozen/'cases-all.json').write_text(json.dumps({'cases':[dict(case,id='other')]}))
            with self.assertRaisesRegex(ValueError,'case registry drift'):
                execute(frozen,[case],'A',root/'registry-drift')
            manifest.pop('cases_sha256')
            (frozen/'frozen.json').write_text(json.dumps(manifest))
            (frozen/'corpus/source.md').write_text('changed')
            with self.assertRaisesRegex(ValueError,'corpus drift'):
                execute(frozen,[case],'A',root/'drift')

    def test_quota_is_infrastructure_and_turn_limit_is_answer(self):
        from evaluate_wikiskill_artifacts import AnswerError
        with tempfile.TemporaryDirectory() as temporary:
            audit=Path(temporary)/'audit'
            events=[init(),
                    dict(type='result',subtype='success',is_error=True,
                         result="You've hit your 5-hour limit")]
            with self.assertRaisesRegex(ValueError,'infrastructure'):
                inspect('\n'.join(map(json.dumps,events)),audit)
            events[1]['result']='Cannot produce requested artifact'
            events[1]['subtype']='error_max_turns'
            with self.assertRaises(AnswerError):
                inspect('\n'.join(map(json.dumps,events)),audit)

    def test_rejected_unknown_tool_is_answer_failure_only_after_full_audit(self):
        from evaluate_wikiskill_artifacts import AnswerError
        with tempfile.TemporaryDirectory() as temporary:
            audit=Path(temporary)/'audit'
            events=[init(),dict(type='assistant',message=dict(model=MODEL,content=[
                dict(type='tool_use',id='unknown',name='DeferredToolPlaceholder',input={})])),
                dict(type='user',message=dict(content=[dict(type='tool_result',tool_use_id='unknown',is_error=True)])),
                dict(type='result',subtype='success',is_error=False,modelUsage={MODEL:{}},result='{}')]
            with self.assertRaises(AnswerError):
                inspect('\n'.join(map(json.dumps,events)),audit)
            audit.write_text(json.dumps(dict(name='DeferredToolPlaceholder',arguments={}))+'\n')
            with self.assertRaisesRegex(ValueError,'audit mismatch') as error:
                inspect('\n'.join(map(json.dumps,events)),audit)
            self.assertNotIsInstance(error.exception,AnswerError)
            audit.unlink()
            events[2]['message']['content'][0]['is_error']=False
            with self.assertRaisesRegex(ValueError,'without verified CLI rejection'):
                inspect('\n'.join(map(json.dumps,events)),audit)

    def test_server_failure_cannot_mask_missing_second_call(self):
        with tempfile.TemporaryDirectory() as temporary:
            audit=Path(temporary)/'audit.jsonl'
            audit.write_text(json.dumps(dict(name='open_evidence',arguments={'path':'missing.md'},success=False))+'\n')
            events=[init(),
                    dict(type='assistant',message=dict(model=MODEL,content=[
                        dict(type='tool_use',id='one',name='mcp__evidence__open_evidence',input={'path':'missing.md'}),
                        dict(type='tool_use',id='two',name='mcp__evidence__open_evidence',input={'path':'missing.md'})])),
                    dict(type='user',message=dict(content=[dict(type='tool_result',tool_use_id='one',is_error=True)])),
                    dict(type='result',subtype='success',is_error=False,modelUsage={MODEL:{}},result='{}')]
            with self.assertRaisesRegex(ValueError,'audit mismatch'):
                inspect('\n'.join(map(json.dumps,events)),audit)
            # A successful execution plus an errored CLI result is equally ambiguous.
            record=json.loads(audit.read_text())
            record['success']=True
            audit.write_text(json.dumps(record)+'\n')
            with self.assertRaisesRegex(ValueError,'audit mismatch'):
                inspect('\n'.join(map(json.dumps,events)),audit)

    def test_context_inventory_is_checked(self):
        with tempfile.TemporaryDirectory() as temporary:
            events=[init(),dict(type='assistant',message=dict(model=MODEL,content=[])),
                    dict(type='result',subtype='success',is_error=False,modelUsage={MODEL:{}},result='{}')]
            events[0]['skills']=['unexpected']
            with self.assertRaisesRegex(ValueError,'context inventory'):
                inspect('\n'.join(map(json.dumps,events)),Path(temporary)/'audit')

    def test_multiple_tasks_are_rejected(self):
        with self.assertRaisesRegex(ValueError,'one independent task'):
            execute(Path('unused'),[{},{}],'A',Path('unused'))


if __name__ == '__main__':
    unittest.main()

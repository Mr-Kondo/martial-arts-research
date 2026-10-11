from pathlib import Path
import hashlib
import json
import shutil
import subprocess

ROOT = Path('/tmp/martial-independent-eval')
ORIGIN = Path('/Volumes/SSD/Programming/martial-arts-research')
DAY = '2026-10-11'
ROOT.mkdir(parents=True, exist_ok=True)
read_files = ['SKILL.md', 'references/research-methods.md', 'references/evidence-policy.md',
    'references/record-contract.md', 'references/weapons-methods.md',
    'references/weapons-source-catalog.md', 'references/military-methods.md',
    'references/military-source-catalog.md', 'references/optional-fiction.md',
    'scripts/research_guard.py']
fixtures = ['synthetic.txt', 'passage.txt', 'fiction.txt', 'provenance.json']
for name in read_files:
    destination = ROOT / 'skill-used' / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ORIGIN / name, destination)
for name in fixtures:
    destination = ROOT / 'sources' / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ORIGIN / 'evals/fixtures' / name, destination)

def save(name, value):
    (ROOT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

guard = str(ROOT / 'skill-used/scripts/research_guard.py')
command = ['rtk', 'python3', guard, 'snapshot', '--root', str(ROOT),
    '--file', 'SYN=sources/synthetic.txt', '--file', 'PAS=sources/passage.txt',
    '--file', 'FIC=sources/fiction.txt', '--file', 'PRO=sources/provenance.json',
    '--span', 'EQUIP_A=SYN:5:5', '--span', 'EQUIP_B=SYN:6:6',
    '--span', 'CAMPAIGN=SYN:8:8', '--span', 'MIL_TARGET=PAS:3:3',
    '--span', 'FICTION_CONF=FIC:2:2', '--span', 'FICTION_PROP=FIC:3:3',
    '--span', 'FICTION_SUBJ=FIC:4:4']
capture = subprocess.run(command, capture_output=True, text=True, check=True)
snapshot = json.loads(capture.stdout)
save('snapshot.json', snapshot)
assert snapshot['record_integrity'] == 'captured'
assert snapshot['content_judgment'] == 'not_evaluated'

def source(identifier, filename, file_id, locator):
    return {'id': identifier, 'source_domain': 'unknown',
        'source_type': 'synthetic_evaluation_fixture',
        'publisher_role': '合成評価資料の作成者。実在対象の研究者・製造者・同時代当事者ではない',
        'modality': 'text', 'bibliography': {'author': 'implementation evaluation',
            'title': filename, 'year': '2026', 'edition': None, 'url': None, 'doi': None},
        'access_status': 'full_text', 'checked_on': DAY,
        'method': '指定ローカルファイルを読取り。provenance.jsonで合成資料と確認',
        'read_range': '全行', 'locator': locator,
        'limitations': ['合成評価資料。実在研究・史実・装備性能・ユーザー採用設定の証拠ではない'],
        'file_id': file_id}

def context(mode, task, question, scope):
    return {'mode': mode, 'task': task, 'question': question, 'scope': scope,
        'conditions': ['外部取得不可', '指定された合成評価資料だけでの分析'],
        'assumptions': ['合成資料を実在証拠として分類しない'],
        'checked_on': DAY, 'requested_extensions': []}

def evidence(span, locator):
    return {'source_id': 'S01', 'relation': 'context', 'locator': locator, 'span_id': span}

def insufficient(axis, evidences, missing):
    return {'axis': axis, 'verdict': 'insufficient', 'evidence': evidences,
        'conditions': ['合成資料の記載範囲に限定'], 'additional_conditions': [],
        'missing_information': missing}

equipment = [
    {'id': 'EQ_A', 'name': '模擬装備甲（訓練用小道具）', 'variant': None,
        'region': None, 'era': None, 'configuration': '構成甲', 'status': 'prototype'},
    {'id': 'EQ_B', 'name': '模擬装備乙（訓練用小道具）', 'variant': None,
        'region': None, 'era': None, 'configuration': '構成乙', 'status': 'proposed'}]
eq_evidence = [evidence('EQUIP_A', 'synthetic.txt:5'), evidence('EQUIP_B', 'synthetic.txt:6')]
record_b = {'schema_version': 2,
    'context': context('weapons', 'compare', '模擬装備甲と乙の質量を同条件で比較できるか',
        'W1・W2・W3。型式、構成、値の状態、質量定義、条件の一致確認'),
    'snapshot_id': snapshot['snapshot_id'],
    'sources': [source('S01', 'synthetic.txt', 'SYN', '5–6行')],
    'findings': [{'id': 'F01', 'target': {'type': 'question', 'text': '甲乙の質量の同条件比較'},
        'domain': 'real', 'facts': [
            '合成資料5行：甲は訓練用小道具、試作、構成甲、公称「約12 kg」、試験条件未記載。',
            '合成資料6行：乙は訓練用小道具、提案、構成乙、モデル「10–14 kg」、入力条件未記載。',
            '型式、地域、年代、質量の対象構成詳細は両者とも記載がない。'],
        'analysis': '公称概数と入力不明のモデル範囲は同じ状態の値ではない。構成甲と構成乙の同等性も不明であり軽重を断定できない。12が10–14の範囲内であることは測定同等性を示さず、概数を精密な12へ置き換えて差を算出しない。現実命題としては実在資料がなく不足。',
        'alternative_interpretations': ['記載値だけを紹介する比較表は作れるが、同条件での性能比較とは区別する。'],
        'assessments': [insufficient('W2', eq_evidence,
            ['同定できる型式・版', '質量の定義と構成部品', '同一の測定条件・測定状態', '実在対象の原資料']),
            insufficient('W3', eq_evidence, ['甲の試験条件・実測', '乙のモデル入力・式・限界'])],
        'equipment_context': equipment,
        'limitations': ['schema 2にsyntheticのdomainはないためunknownとしてcontext参照する。',
            'measurementsは省略。現実数値にreal資料を要求する規則と、modeledに入力・式を要求する規則を満たせない。元値・単位・値の状態はfactsと回答に保全。',
            'equipment statusは合成資料の記載分類であり、実在する開発状態の証明ではない。']}]}
save('01-weapons-record.json', record_b)

military = {'analysis_kind': 'causal', 'analysis_levels': ['tactical', 'strategic'],
    'subject': '合成戦役甲', 'period': None, 'geography': None,
    'actors': [], 'objectives': ['停戦交渉の成立'],
    'decision_point': '命令時。日時・具体的命令内容は不明',
    'available_information': '命令時に補給不足の報告あり。当事者の受領・認識内容は不明',
    'resources': None, 'constraints': '補給不足の報告。物資量・不足期間・輸送条件は不明',
    'observed_outcome': '局地戦では勝利。停戦は成立せず。いずれも合成資料の記載',
    'knowledge_basis': 'unknown', 'counterfactual_assumptions': []}
record_c = {'schema_version': 2,
    'context': context('military', 'review', '局地戦勝利から政治目的達成を導けるか',
        'passage.txtの3行目。当時情報・兵站・結果と因果の区別'),
    'snapshot_id': snapshot['snapshot_id'],
    'sources': [source('S01', 'synthetic.txt', 'SYN', '8行')],
    'findings': [{'id': 'F01', 'target': {'type': 'passage', 'span_id': 'MIL_TARGET',
        'quote': '合成戦役甲は局地戦に勝ったので政治目的も達成した。'},
        'domain': 'real', 'facts': [
            '合成資料8行では目的は停戦交渉の成立。',
            '命令時に補給不足の報告あり。報告の受領・認識は未記載。',
            '局地戦では勝利したが停戦は成立せずと記載。'],
        'analysis': '合成資料内では政治目的達成という対象文は「停戦は成立せず」と食い違う。局地戦の結果と政治目的達成は異なる評価対象であり、その間の因果は記載されない。補給不足が未達の原因だった、判断者が知っていた、判断が不合理だったという別命題にも根拠がない。合成資料は実在史実の反証に使えないため機械記録の判定はinsufficient。',
        'alternative_interpretations': [
            '「政治目的」を別の目的と解釈する余地はあるが、その別目的は資料に記載がない。',
            '未達に相手の判断・交渉条件・別の制約が関係した可能性はあるが、どれも未確認。'],
        'assessments': [insufficient('M6', [evidence('CAMPAIGN', 'synthetic.txt:8')],
            ['実在の原史料', '局地戦と交渉結果をつなぐ記録', '判断時の情報受領・認識', '兵站量・期間と結果の関係'])],
        'military_context': military,
        'limitations': ['合成資料内の不整合指摘と実在史実の反証を区別する。',
            '同時代報告そのもの、命令内容、通信、当事者、時期、地域は取得できない。'],
        'revision': '合成戦役甲は局地戦に勝利したが、目的とされた停戦交渉は成立しなかった。'}]}
save('02-military-record.json', record_c)

answers = {
'01-weapons-answer.md': '''# 文脈
採用：mode B（weapons）／task compare。W1〜W3を使い、模擬装備甲・乙の質量を比較します。外部取得不可であり、以下は合成評価資料の記載比較です。実在装備の性能ではありません。

# 核心的な論理
証拠：synthetic.txtの5〜6行に次の記載があります。

| 比較項目 | 甲 | 乙 | 同条件か |
|---|---|---|---|
| 用途 | 訓練用小道具 | 訓練用小道具 | 記載上は共通 |
| 型式・版／地域・年代 | 未記載 | 未記載 | 不明 |
| 開発状態 | 試作 | 提案 | 異なる |
| 構成 | 構成甲 | 構成乙 | 同等性不明 |
| 質量 | 公称「約12 kg」 | モデル「10–14 kg」 | 値の状態が異なる |
| 質量の対象部品・装備状態 | 未記載 | 未記載 | 不明 |
| 条件 | 試験条件未記載 | モデル入力条件未記載 | 揃えられない |

分析：甲が乙より軽い／重いとは断定できません。公称概数を実測値へ、モデル範囲を実物のばらつきへ読み替えられません。
反論：記載の12は10–14内ですが、それだけでは構成・質量定義・値の状態が同じとはいえません。概数から精密な差や割合も算出しません。

# 重要ポイント
- 元値・単位・公称／モデルの区別を保全しました。
- 同条件比較の判定はinsufficientです。型式、構成内訳、共通の質量定義、甲の試験情報、乙の入力・式が不足します。
- schema 2に合成資料のdomainはないためunknown、evidenceはcontextで記録しました。実在証拠へ格上げしていません。
- measurementsは入力・出典条件を満たせないため省略し、値と状態をfactsに保存しました。

# 具体例
この表は「資料に何が書かれているか」の比較として使えます。「乙を選ぶと2 kg軽い」という結論には使えません。

# 平易な説明
わかりやすく言うと、数字は並べられるが、同じ条件で測った重さとして比べる根拠がないということである。

# 自己批判的考察
記載整理への信頼度は0.95です。実在装備の質量への信頼度は評価不能です。JSONの検証合格は記録整合性だけを意味します。

# 結論
条件を揃える情報が不足しており、軽重は保留します。記録・snapshot・選択資料を保存しました。

# 参考文献
[合成資料5〜6行](/tmp/martial-independent-eval/sources/synthetic.txt:5)、[来歴](/tmp/martial-independent-eval/sources/provenance.json)、[schema 2記録](/tmp/martial-independent-eval/01-weapons-record.json)、[snapshot](/tmp/martial-independent-eval/snapshot.json)。

未確認：実在資料・外部情報・同条件実測。リスク：合成数値を実機性能として再利用しないでください。
''',
'02-military-answer.md': '''# 文脈
採用：mode C（military）／task review。対象はpassage.txtの3行目「合成戦役甲は局地戦に勝ったので政治目的も達成した。」です。戦術的な局地成果と、戦略的な政治目的を区別します。対象は合成資料です。

# 核心的な論理
証拠：synthetic.txtの8行には「目的は停戦交渉の成立」「命令時に補給不足の報告あり」「局地戦では勝利」「停戦は成立せず」と記載されています。

| 区分 | 確認できた記載 | 不明なこと |
|---|---|---|
| 当時の情報 | 命令時に補給不足の報告が存在 | 判断者の受領・認識、通信、報告時刻 |
| 兵站 | 補給不足という報告 | 物資量、不足期間、輸送能力、持続への影響 |
| 局地結果 | 勝利 | 戦闘経過、損害、勝利の定義 |
| 政治目的と結果 | 停戦交渉の成立が目的、停戦は不成立 | 交渉経過、相手の目的、未成立の理由 |

分析：合成資料内では対象文の「政治目的も達成した」は「停戦は成立せず」と食い違います。局地戦勝利だけから政治目的達成は導けません。
反論：戦闘勝利が交渉に有利に働いた可能性や、別の政治目的を達成したという解釈は考えられます。しかし、どちらもこの資料には根拠がありません。

# 重要ポイント
- 補給不足の報告があったことと、指揮官が知っていたことを分けました。
- 停戦不成立から、補給不足が原因だった／判断が不合理だったとは断定しません。
- schema 2では資料をunknown、evidenceをcontext、実在命題の判定をinsufficientとしました。合成資料内の食い違いはanalysisに残しました。

# 具体例
最小の説明修正案：「合成戦役甲は局地戦に勝利したが、目的とされた停戦交渉は成立しなかった。」優先順位は結果の混同解消を第一とします。因果説明の追記は史料調査と文章量が必要になるため、この資料だけでは追加しません。原文は編集していません。

# 平易な説明
わかりやすく言うと、一つの戦闘に勝ったことと、戦争で目指した政治的な結果を得たことは別だということである。

# 自己批判的考察
合成資料内の不整合判定への信頼度は0.95です。実在史実・指揮判断・未達原因の評価は不能です。guardは歴史や因果を評価せず、content_judgmentはnot_evaluatedです。

# 結論
対象文は提供された合成資料と整合しません。当時情報と兵站の因果は保留し、局地勝利と停戦不成立を分けて記述できます。

# 参考文献
[対象文3行](/tmp/martial-independent-eval/sources/passage.txt:3)、[合成資料8行](/tmp/martial-independent-eval/sources/synthetic.txt:8)、[来歴](/tmp/martial-independent-eval/sources/provenance.json)、[schema 2記録](/tmp/martial-independent-eval/02-military-record.json)、[snapshot](/tmp/martial-independent-eval/snapshot.json)。

未確認：同時代史料・外部情報・未達の原因。リスク：合成戦役の結果を実在史実の証拠へ置き換えないでください。
''',
'03-integrated-fiction-answer.md': '''# 文脈
採用：mode D（integrated）／task review／fiction。人物の能力（B・C・D・E）、槍・防具（W2・W3・W5）、部隊行動（M3・M4）とその関係を検討します。fiction.txtは合成設定であり、実在作品やユーザーの採用設定ではありません。物語時点は不明です。

# 核心的な論理
証拠と位置づけ：

| 原文 | 状態 | 許される扱い |
|---|---|---|
| 人物甲は指定条件で動作を即時再現できる | 合成設定内の採用済み | その条件下で成立する作品前提として受け入れる |
| 架空防具甲は全条件で無傷 | 未採用の提案 | 確定した防護能力に使わない |
| 人物乙には予備動作が見えなかった | 人物の主観 | 観察者の見え方として扱う |
| 槍、部隊の具体的行動 | 記載なし | 構造・能力・編制・命令を補作しない |

分析：即時再現能力を、実在流派の特性や抵抗下の成功率として説明する根拠はありません。「指定条件」の内容も不明です。槍の長さ・質量・把持・距離、防具の採否と可動条件、人物甲への命令・通信・味方の行動がないため、能力→槍の実行→部隊成果の関係はinsufficientです。
反論：能力が槍の動作にも適用されるなら関係を検討できるという読みはあります。しかし適用範囲は未記載であり、新設定として追加できません。「人物乙には見えない」ことも、動作自体が存在しない／全員に見えないという意味にはなりません。

# 重要ポイント
- 採用済み能力は否定せず、記載された範囲で受け入れます。
- 全条件無傷の防具は提案のままです。能力の成立根拠にも使いません。
- 予備動作の見え方は人物乙の主観に限定します。
- 槍の記載不足は武器として不成立という反証ではありません。
- 部隊の指揮・連携・兵站・結果は不明であり、個人能力から組織の成功を保証しません。

# 具体例
資料のまま成立する説明は「人物甲は指定条件で動作を即時再現でき、人物乙には予備動作が見えなかった」です。ここへ「槍で必ず命中する」「防具により全環境で無傷」「部隊が必勝」を足す根拠はありません。

# 平易な説明
わかりやすく言うと、人物の確定能力、装備の案、観察者の印象を分けないと、書かれていない戦闘能力や部隊の成功を作ってしまうということである。

# 自己批判的考察
設定の区分整理への信頼度は0.95です。槍・防具・部隊行動の成立性への信頼度は評価不能です。具体的条件が不足しており、身体実行や軍事運用の正しさは検証していません。

# 結論
人物甲の即時再現は合成設定内の前提です。槍への適用、防具の採用、部隊との関係は情報不足で保留します。設定・本文は編集していません。

# 参考文献
[合成設定2〜4行](/tmp/martial-independent-eval/sources/fiction.txt:2)、[来歴](/tmp/martial-independent-eval/sources/provenance.json)、[処理記録](/tmp/martial-independent-eval/execution-log.json)。

未確認：槍の仕様・能力の指定条件・防具の採否・部隊行動。リスク：未採用案や人物の主観を確定設定へ格上げしないでください。
'''}
for name, answer in answers.items():
    (ROOT / name).write_text(answer, encoding='utf-8')

processes = [{'process': 'snapshot', 'argv': command, 'exit_code': capture.returncode}]
for prefix in ('01-weapons', '02-military'):
    command = ['rtk', 'python3', guard, 'validate', '--record', str(ROOT / (prefix + '-record.json')),
        '--snapshot', str(ROOT / 'snapshot.json')]
    result = subprocess.run(command, capture_output=True, text=True)
    parsed = json.loads(result.stdout)
    save(prefix + '-validation.json', parsed)
    processes.append({'process': 'validate', 'argv': command, 'exit_code': result.returncode})
    assert result.returncode == 0 and parsed['record_integrity'] == 'pass'
    assert parsed['content_judgment'] == 'not_evaluated'
    assert not parsed['errors']

files = []
for relative in read_files:
    data = (ROOT / 'skill-used' / relative).read_bytes()
    files.append({'path': str(ORIGIN / relative), 'saved_copy': str(ROOT / 'skill-used' / relative),
        'read_range': '全体。ただしresearch_guard.pyは初回表示が切れたため1–390行を追加で再読',
        'sha256': hashlib.sha256(data).hexdigest()})
for name in fixtures:
    data = (ROOT / 'sources' / name).read_bytes()
    files.append({'path': str(ORIGIN / 'evals/fixtures' / name), 'saved_copy': str(ROOT / 'sources' / name),
        'read_range': '全体', 'sha256': hashlib.sha256(data).hexdigest()})
save('execution-log.json', {'checked_on': DAY, 'read_files': files,
    'instruction_read': '/Users/masatomiwada/.codex/RTK.md',
    'scope_resolution': '実際に読み込んだSKILL.mdの所在を基準に相対参照を解決',
    'search': {'date': DAY, 'destination': '指定ローカル資料',
        'query': ['模擬装備甲・乙の質量', '合成戦役甲の局地戦勝利・停戦', '人物甲の能力・槍・防具・部隊行動'],
        'external_search': '依頼条件により未実施'},
    'selection': {'adopted': fixtures,
        'reasons': ['synthetic.txt:装備・戦役の記載', 'passage.txt:検証対象の原文',
            'fiction.txt:採用済み・提案・主観の分類', 'provenance.json:合成資料の来歴'],
        'not_read': ['abstract.txt', 'conflict.txt', 'evals/task-cases.json', 'evals/trigger-cases.json', 'docs/validation.md'],
        'exclusion_reason': '今回の問いに不要な資料、または禁止された評価期待資料'},
    'tasks': [
        {'task': 1, 'mode': 'weapons', 'task_type': 'compare', 'evidence_ranges': ['synthetic.txt:5–6', 'provenance.json:全体'],
            'actions': ['元値と値の状態を抽出', '比較条件を照合', '不足条件を判定', 'schema 2と回答を保存', 'guardで再読・検証']},
        {'task': 2, 'mode': 'military', 'task_type': 'review', 'evidence_ranges': ['passage.txt:3', 'synthetic.txt:8', 'provenance.json:全体'],
            'actions': ['原文を逐語引用', '情報・兵站・結果を区別', '合成資料内の不整合と現実史実の判断を区別', 'schema 2と回答を保存', 'guardで再読・検証']},
        {'task': 3, 'mode': 'integrated', 'task_type': 'review', 'extensions': ['fiction'],
            'evidence_ranges': ['fiction.txt:1–4', 'provenance.json:全体'],
            'actions': ['採用済み・未採用・主観を分類', '槍・部隊の欠落を確認', '関係の保留を明記', '独立回答を保存']}],
    'executed_processes': processes,
    'limitations': ['外部検索・取得なし', '合成資料を現実証拠に分類せず、B/Cのrecord判定はinsufficient',
        'modeledの入力・式を補作せず、measurementsは省略', 'guardは内容判定を実施しない',
        'コピー先にGit管理はなく、GIT_UNVERIFIED警告は許容', 'スキル原本・ユーザー設定・対象原文は未編集']})
print(json.dumps({'outputs': sorted(p.name for p in ROOT.iterdir()),
    'validation': '2件pass、content_judgment=not_evaluated'}, ensure_ascii=False))

# 検証記録と再実行

実施日：2026-10-11。機械検査、独立回答評価、Codex CLI、Claude Codeの結果を分ける。記録整合性の合格から内容の正解を認定しない。

## オフライン機械検査

実行環境：macOS、Python 3.14.8、標準ライブラリのみ。以下を正本で実行する。

```sh
python3 -B -m unittest discover -s scripts/tests -v
python3 -B scripts/research_guard.py validate --record examples/records/martial.json
python3 -B scripts/research_guard.py validate --record examples/records/weapons.json
python3 -B scripts/research_guard.py validate --record examples/records/military.json
python3 -B scripts/research_guard.py validate --record examples/records/integrated.json
python3 -B scripts/research_guard.py validate --record examples/records/weapons-declared.json
python3 -B scripts/research_guard.py validate --record examples/records/local-review.json --snapshot examples/records/local-snapshot.json --root evals/fixtures
```

テスト対象：日本語・CRLF、引用・同サイズ変更・削除・破損、JSONキー／ID／参照／未知キー／型／不正Unicode／非有限数／サイズ・深さ上限、本文／抄録、現実と設定、モード／軸／拡張、装備／測定／計算、軍事階層／反実仮想、Gitなし・Git変更、標準入力・JSON・終了0/1/2。文書検査は相対リンク、fixture来歴、40起動ケース、28タスク、記録例の実行を確認する。最新の件数と結果は[results/verification.json](../evals/results/verification.json)に保存する。

CLIの結果はJSON。`pass`／`captured`でも`content_judgment=not_evaluated`。外部出典の本文を申告した記録にはSOURCE_CONTENT_UNCHECKED、GitなしにはGIT_UNVERIFIEDが出る。これらを根拠確認の成功として集計しない。

skill-creator付属のquick_validate.pyは通常PythonとバンドルPythonの両方で起動したが、PyYAML不足で検証に到達しなかった。スキルの依存関係を増やさず、共通frontmatter・名前・長さ・相対リンクは標準ライブラリのpackageテストと両製品の検出で確認した。

## 独立した回答評価

skill-creatorの独立前向き評価手順に従い、別コンテキストのCodexサブエージェントへSKILL.mdと選択資料の所在だけを渡した。採点用task/trigger casesは読ませていない。ネット取得なし、合成入力、原文編集なし。保存時のスキル・資料・snapshotと回答を[results/independent](../evals/results/independent/execution-log.json)へ保全した。

| 条件 | 観察した結果 | 判定と限界 |
| --- | --- | --- |
| B/weapons・compare | 公称概数とモデル範囲、試作と提案、構成と未知条件を分離。数値差・ランキングを捏造せず保留 | 観点を満たす。実在数値の検証ではない |
| C/military・review | 局地勝利と政治目的を分離。補給報告の存在と指揮官の認識、未達原因を分離 | 観点を満たす。歴史・因果の実証ではない |
| D/integrated・review・fiction | 採用済み能力・未採用防具案・人物主観、装備と部隊の不足情報を分離 | 観点を満たす。設定の追加・採択なし |
| A/martial・survey | 合成分類表の技甲に質問を限定し、原稿の提出を要求しない | 保存した追加回答を参照。実在分類の検証ではない |

B/Cの記録はguardでもpass。合成資料はunknown、evidenceはcontextとし、realの支持へ格上げしていない。測定契約を満たす入力がない数値はfactsに保持。これは記録構造の適切な保留であり、合成資料にrealと虚偽申告したテストを現実の証拠扱いしていない。

保存後のB/C記録も正本guardで`--root evals/results/independent`を指定して再検証した。snapshotの相対パスは`sources/…`なので、rootをsourcesディレクトリ自体にはしない。raw回答と処理記録には実行時の一時パスが残るが、再照合に必要な本文・snapshot・利用スキルは同梱した。評価後の変更は入力防御、現実の計算入力のdomain検査と軍事台帳の閲覧範囲表記で、過去の保存スキルを最新版として偽らない。

両CLIの自動発見・明示展開・自然言語起動・スキルなし比較を、このサブエージェント評価で代替したとは扱わない。最終回答に固定見出し等がある場合は今回のユーザー出力指定によるもの。本スキルの既定書式ではない。

## 製品CLIの実施結果

| 環境 | 条件・結果 | 完了範囲 |
| --- | --- | --- |
| Codex CLI 0.155.1 | 一時プロジェクトの`.agents/skills/`へコピー。新しいephemeralセッション、read-only、既定モデル。HTTP 400、`gpt-6.1-sol`が当該アカウントで非対応 | モデルなしのapp-server `skills/list`でenabled/repo検出のみ確認。回答未完了 |
| Claude Code 2.1.285 | 一時プロジェクトの`.claude/skills/`へコピー。新しいセッション、project設定、hooks無効、MCPなし、限定ツール。通常サンドボックスは認証不可。既存認証へアクセス可能な実行でHTTP 429、週間上限 | skillsとslash_commandsへの登録を確認。回答未完了 |

関連イベントを[results/runtime-events.json](../evals/results/runtime-events.json)へ保存。認証情報や無関係なMCPログは同梱しない。ユーザーのモデル・認証・グローバル設定を変更していない。上限の解除待ちや別モデルの試行は行わなかった。

未実施：両CLIでの全タスク回答、自然言語起動36件、明示呼出し4件の回答確認、スキルなし比較。未実施項目は合格率の分母・分子へ入れない。検出確認と明示実行成功は別である。

## 評価者向け再実行手順

[trigger-cases.json](../evals/trigger-cases.json)は40件（暗黙36、明示4）、[task-cases.json](../evals/task-cases.json)は28件。共通依頼を使い、製品別のprefixだけを変更する。T20/T28のargument_variantsも別セッションで実行する。

次の例はT14を実行する一時プロジェクトとプロンプトを作る。コピーの有無以外を揃えたbaselineも作る。ケースID／suiteを変えて全件へ適用する。期待結果はコピーせず、実行モデルへ渡さない。

```sh
python3 - <<'PY'
from pathlib import Path
import json, shutil, tempfile
source = Path.cwd()
suite, case_id = 'task', 'T14'
cases = json.loads((source / f'evals/{suite}-cases.json').read_text())['cases']
case = next(c for c in cases if c['id'] == case_id)
base = Path(tempfile.mkdtemp(prefix='martial-evaluation-'))
for environment, surface in [('codex', '.agents'), ('claude', '.claude')]:
    for condition in ['skill', 'baseline']:
        project = base / environment / condition
        project.mkdir(parents=True)
        shutil.copytree(source / 'evals/fixtures', project / 'fixtures')
        if condition == 'skill':
            skill = project / surface / 'skills/martial-arts-research'
            skill.mkdir(parents=True)
            shutil.copy2(source / 'SKILL.md', skill / 'SKILL.md')
            for name in ['references', 'scripts']:
                shutil.copytree(source / name, skill / name,
                                ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        explicit = suite == 'task' or case.get('kind') == 'explicit'
        prefix = case.get('invocation', {}).get(environment, '') if explicit and condition == 'skill' else ''
        constraints = '\n利用資料はfixtures/。外部取得不可。合成資料を実在証拠にしない。原文は編集しない。'
        (project / 'prompt.txt').write_text((prefix + ' ' + case['request']).strip() + constraints)
print(base)
PY
```

baselineでは明示スキルprefixを除くがmode/task等の共通指定を保持する。ユーザー配置の同名スキルが別にある場合はbaselineの条件が崩れるので、その環境を評価記録に残し、比較を未確認とする。ユーザー設定を消してbaselineを作らない。

各projectに移動し、プロンプトを渡す。以下のPATHは上記出力先を指定する。新しいプロセスを各ケース・各条件に使い、失敗や利用制限が出たら終了してその状態を記録する。

```sh
codex exec --ephemeral --sandbox read-only --skip-git-repo-check --json -C /path/to/codex/skill - < /path/to/codex/skill/prompt.txt > /path/to/codex/skill/result.jsonl 2> /path/to/codex/skill/result.stderr
```

```sh
cd /path/to/claude/skill
claude -p --no-session-persistence --output-format stream-json --verbose --setting-sources project --strict-mcp-config --mcp-config '{"mcpServers":{}}' --settings '{"disableAllHooks":true}' --tools Read,Glob,Grep,Skill,Bash --allowedTools Read,Glob,Grep,Skill 'Bash(python3 *)' --permission-mode dontAsk < prompt.txt > result.jsonl 2> result.stderr
```

Claudeの限定ツールは一時評価だけに適用する。スキルによる無依頼編集を合格にしないため、評価前後にfixtureバイトを照合する。guardで保存する資料・snapshotは削除せず、移動時は`--root`を対応させる。状態・stdout・stderr・版・依頼本文・ファイルhash・読込履歴・手動採点を保全する。回答の文面一致は要求しない。

最低の再実行セットはT01〜T03、T09、T12〜T19、T21〜T28と暗黙の非起動ケースR25〜R36。これで全モード、全作業、装備と軍事の各survey/compare/review、統合、取得不能、任意創作を含む。必要な資料がない場合に資料を捏造せず保留することも有用性の一部として採点する。

起動評価は「該当SKILLを読んだか」で採点し、モード選択や内容評価と分ける。負例は語を含む推敲・翻訳・新規執筆等。呼出しを付けて負例を自動起動試験へ変えない。T/Rケースの期待観点と禁止する誤りを回答・資料・ログに照合し、引用、範囲、適切な保留、有用性を手動確認する。捏造・誤引用・無依頼編集は重大不合格。単語一致・guard合格・検出成功だけで正答としない。

## 0.1.0の配置スクリプト検証

新規配置、同版の再配置、版更新、旧ファイル除去、削除・再削除、CRLF、日本語パス、手編集・追加・空ディレクトリ・削除の保護、管理記録なし・不正記録・リンク拒否、両対象の事前確認、置換失敗時の復元を試験する。別cwdから実際のCLIで両配置を作り、配置先のguardを実行してから削除する。すべて一時プロジェクトで実施し、個人配置は実行しない。

評価保存スキルはSKILL.md.txtに改名した。保存バイトは同じで、raw回答・当時のログの旧パス表記は保持する。過去の77ファイル一致は当時の結果であり、最新版の件数とは分ける。

## Windows CI

GitHub Actionsの[Windows CI](https://github.com/Mr-Kondo/martial-arts-research/actions/workflows/windows.yml)を追加。windows-latest上でPython 3.9／3.14のマトリクスを使い、guardとインストール・更新・削除の全機械テストを実行する。設定は[GitHub公式のPython CI手順](https://docs.github.com/en/actions/tutorials/build-and-test-code/python)とactions/checkout、actions/setup-pythonの公式READMEを2026-10-11に確認した。

検査準備として/tmp固定をOSの一時ディレクトリへ変更し、テストのファイルI/OとCLI出力をUTF-8に固定した。snapshotの保存rootはPOSIXとWindowsの両絶対パス形式を受け入れ、別OSの資料には--rootで移動先を指定する。.gitattributesは自動改行変換を無効化して保存hashを保全する。

[実行38126044942](https://github.com/Mr-Kondo/martial-arts-research/actions/runs/38126044942)は両ジョブ成功。コミットb394f9bで各57件を通過し、skipはない。[保存した実測結果](../evals/results/windows-ci.json)を参照。これらの修正を0.1.1に同梱し、既存の0.1.0タグと添付ZIPは変更しない。アプリのモデル回答や個人配置はこのCIに含めない。

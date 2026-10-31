# 検証記録と再実行

## 配布一覧の検証（0.2.1）

2026-10-31、macOSのPython 3.15.2で76件に合格。配布一覧外の私的原稿、*.local.md、feedback/、キャッシュの混入防止、BOM/CRLF、不正パス・名前衝突・予約名・リンクの拒否を確認した。Gitのない一時配置で導入・更新・削除とguard/renderを実行し、配置後の文書リンクも検査した。旧インストーラとの合成比較は私的ファイルの混入3件から0件で、既存の配布対象を保持した。新しい一覧とADRを加え、配布物は98ファイル。

Claude Code（Sonnet 5.5、medium）の静的レビューと補強後の再レビューを実施し、ブロックする指摘なし。採否は[ADR](../adr/explicit-package-boundary.md)に記録した。実行ログはGit対象外のfeedback/に保存する。Windows/LinuxのCI結果は[PR #5](https://github.com/Mr-Kondo/martial-arts-research/pull/5)で確認する。今回の配布テストや静的レビューから、モデル回答の品質や3環境の互換性を推定しない。

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

テスト対象：日本語・CRLF、引用・同サイズ変更・削除・破損、JSONキー／ID／参照／未知キー／型／不正Unicode／非有限数／サイズ・深さ上限、本文／抄録、現実と設定、モード／軸／拡張、装備／測定／計算、軍事階層／反実仮想、Gitなし・Git変更、標準入力・JSON・終了0/1/2。文書検査は相対リンク、fixture来歴、40起動ケース、28タスク、記録例の実行を確認する。初回の結果は[results/verification.json](../evals/results/verification.json)、追加監査の結果は[output-audit-verification.json](../evals/results/output-audit-verification.json)に保存する。

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

GitHub ActionsにWindows CIを追加し、その後[Python CI](https://github.com/Mr-Kondo/martial-arts-research/actions/workflows/ci.yml)へ統合。ubuntu-latest／windows-latestとPython 3.9／3.14の4通りで、guardとインストール・更新・削除の全機械テストを実行する。設定は[GitHub公式のPython CI手順](https://docs.github.com/en/actions/tutorials/build-and-test-code/python)とactions/checkout、actions/setup-pythonの公式READMEを2026-10-11に確認した。

検査準備として/tmp固定をOSの一時ディレクトリへ変更し、テストのファイルI/OとCLI出力をUTF-8に固定した。snapshotの保存rootはPOSIXとWindowsの両絶対パス形式を受け入れ、別OSの資料には--rootで移動先を指定する。.gitattributesは自動改行変換を無効化して保存hashを保全する。

[実行38126044942](https://github.com/Mr-Kondo/martial-arts-research/actions/runs/38126044942)は両ジョブ成功。コミットb394f9bで各57件を通過し、skipはない。[保存した実測結果](../evals/results/windows-ci.json)を参照。これらの修正を0.1.1に同梱し、既存の0.1.0タグと添付ZIPは変更しない。アプリのモデル回答や個人配置はこのCIに含めない。

## Linux CI

[実行38127240113](https://github.com/Mr-Kondo/martial-arts-research/actions/runs/38127240113)はLinux／Windows × Python 3.9／3.14の4ジョブすべて成功。Ubuntu 24.04上のPython 3.9.25／3.14.8で各57件を通過し、skipはない。guard・配置・更新・削除を含む同じテストを使い、Linux向けのコード修正は不要だった。実行対象コミットc8df6b4、実際の版・件数・結果を[linux-ci.json](../evals/results/linux-ci.json)に保存した。

この検証はmainの機械テストで、モデル回答・個人配置・他のディストリビューションを検証しない。検証記録と共通CI設定を0.1.2に同梱し、既存の0.1.1タグとZIPは変更しない。

## 回答生成・規則監査（0.2.0）

2026-10-11、macOS Python 3.14.8で70件を通過。既存57件に加え、同一記録の検証から回答生成、単位換算の不一致による停止、四則演算・次元・丸め・ゼロ除算・入力名重複・未対応式、危険な式の不実行、引用改変とCRLF、出典重複・比較条件・数値矛盾・推論規則、Crossrefの取得不能／応答異常／10 DOI上限、UTF-8・stdin・JSON・終了0/1/2・出力上限を確認。配置後のrenderも実行した。[実行ログ](../evals/results/output-audit-tests.log)と[保存記録](../evals/results/output-audit-verification.json)を参照。

Crossref公式APIへ既存台帳のDOIを実際に問い合わせ、登録DOIと出版年の一致、短縮題名と副題付き登録題名の差によるreview_requiredを確認した。通信へ送ったのはDOIだけで、研究内容の真偽は未評価。取得URL・時刻・応答hash・比較値を保存した。

[実行38129938207](https://github.com/Mr-Kondo/martial-arts-research/actions/runs/38129938207)では、コミットafcb33cのLinux／Windows × Python 3.9／3.14の4ジョブすべてで各70件を通過し、skipはない。実際のPython版・イメージ・ジョブURLは上記保存記録、テスト件数と結果の抜粋は[output-audit-ci.log](../evals/results/output-audit-ci.log)に保全した。CIのCrossref試験は模擬応答を使い、上記の実通信確認とは分ける。

独立したCodexサブエージェントへスキル所在と計算記録のみを渡し、期待結果・実装説明を渡さず前向き評価した。誤った換算値をrenderが終了1／markdown=nullで止め、原記録を変更せず一時領域に修正案を作り、再実行でCALCULATION=checkedを得た。生成回答はそのまま保存され、review_requiredとnot_checkedを維持した。[保全した入力・提案・回答](../evals/results/output-forward/input-record.json)を参照。製品CLIによる自然言語起動評価の代替とはしない。

skill-creatorのquick_validateは今回もPyYAML不足で検査に到達しなかった。依存関係は増やさず、frontmatter・長さ・参照・3.9文法を既存のpackageテストで確認した。構造化分類の自己申告と、取得した資料自体の真偽は機械保証しない。

保存JSONの`release_status`は検証時点の記録であり、当時の最新公開版は0.1.2だった。検証対象の機能は0.2.0に同梱した。
# 2026-10-31：3環境の導入対応（0.2.2）

78件のローカルテストに成功。Codex/Claude/Antigravityの個人配置、共有プロジェクト先の重複除去、導入・更新・削除と手編集拒否を検証した。既定bothは変更していない。

新規セッションの短い明示呼出しではCodex CLI 0.164.0（gpt-6.1-sol、medium）とAntigravity CLIの双方がnameとreferences/evidence-policy.mdを返し、未取得資料を確認済みにしないと回答した。Codexは44,414トークンを使用し、全体スキル一覧の予算超過警告も出た。Antigravityは版・モデル・利用量が出力されず、固定条件の本比較には進めない。これはタスク全体・自然言語起動の合格ではない。

Claude Code 2.1.314（Sonnet 5.5、medium）の読取専用レビューは重大指摘なし。その制限セッションでは対象スキルの発見を確認できなかったが、Skillツールを含めた別の新規セッションでは明示依頼に対しnameとreferences/evidence-policy.mdを返し、未取得資料は未確認と回答した。これは明示読込の確認であり、自律起動の確認ではない。IDEの新規GUIセッションは未確認。

全40起動・28タスクのあり/なし評価は未実施。上限60,000既知トークンに対しCodexのスモークだけで44,414を使用し、他製品の使用量も不明なため、136回×3製品の評価を追加しない。モデル・版・使用量を固定して記録可能な独立環境を用意し、同じ資料と各1試行で再実行する。未実施は0点でも合格でもなくnot_runとする。起動/誤起動/条件保持/根拠対応は独立採点する。

レビューで指摘された個人配置説明と検証表不足を修正した。共有配置削除の注意はcompatibilityに記載済み。CLI出力への追加警告は既存JSON出力の変更を避けて不採用。実測ログは非公開feedback/に保存する。

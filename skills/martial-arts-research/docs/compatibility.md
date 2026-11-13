# 配置・呼出し・互換性

## skills CLIによる導入・更新

`skills` 1.7.6のCLIで検証する。必要なNode.jsの版は[公式案内](https://github.com/vercel-labs/skills)で確認する。実行時のPython guardには従来どおりPython 3.9以上が必要。

```sh
npx skills add https://github.com/Mr-Kondo/martial-arts-research/tree/main/skills/martial-arts-research --skill martial-arts-research -a codex claude-code antigravity
npx skills update martial-arts-research
npx skills remove martial-arts-research
```

初回登録後は`npx skills update`でも更新できる。名前を省略すると他の登録スキルも対象になる。個人用は各コマンドに`-g`を付ける。CLIが保存するlock情報で更新元を追跡するため、Pythonや手動コピーだけで導入した配置は自動登録されない。更新先はmainであり、VERSIONやGitHub Releaseの最新タグを比較する方式ではない。

配布元URLには必ず`skills/martial-arts-research`まで含める。CLIは`package-files.txt`を解釈しないため、ルートからの導入は開発・評価資料もコピーする。専用フォルダは配布一覧の39ファイルから`scripts/build_skills_distribution.py`で生成し、スキルの内容は正本と同じにする。CLIの既定のリンク配置と`--copy`の選択はCLIに任せる。

配布元の変更後は次を実行して生成物もコミットする。既存CIのテストが欠落・余分なファイル・内容差を検出する。

```sh
python3 -B scripts/build_skills_distribution.py
python3 -B -m unittest discover -s scripts/tests -v
```

設計と検証範囲は[ADR](https://github.com/Mr-Kondo/martial-arts-research/blob/main/adr/skills-cli-update.md)を参照。

2026-10-31更新。共通本体はルートの[SKILL.md](../SKILL.md)。実行時に参照するファイルは同じコピーへ揃え、修正は正本で行う。プロジェクト配置を基本とし、グローバル設定・モデル指定・認証設定を変更しない。

| 利用先 | コピー先 | 明示呼出し（チャットの本文） | 自然言語起動 |
| --- | --- | --- | --- |
| Codex | `<project>/.agents/skills/martial-arts-research/` | `$martial-arts-research --mode B --task compare 10式と90式の公開諸元を比較して` | スキル未指定で「戦術・作戦・戦略の用法を調べて」等 |
| Claude Code | `<project>/.claude/skills/martial-arts-research/` | `/martial-arts-research --mode C --task survey 軍略の用法を調べて` | 同じ自然言語本文を使う |
| Gemini Antigravity（IDE・CLI） | `<project>/.agents/skills/martial-arts-research/`（Codexと共有） | `martial-arts-researchを使って軍略の用法を調べて` | 同じ自然言語本文を使う |

Antigravityの個人用配置は`~/.gemini/config/skills/martial-arts-research/`で、IDEとCLIが共有する。[公式仕様](https://antigravity.google/docs/skills)を2026-10-31に確認。旧CLI専用配置へ新しい重複コピーは作らない。配置仕様への対応はモデル回答の検証とは別である。

配置と起動表記の根拠：[Codex公式](https://learn.chatgpt.com/docs/build-skills)、[Claude Code公式](https://code.claude.com/docs/en/skills)、[共通仕様](https://agentskills.io/specification)。ページの必要箇所を2026-10-11に確認。Codexの旧公式URLは前記ページへ転送された。発見済みのスキルが表示されない場合は新しいセッションで確認する。

個人用のコピー先はCodexが`~/.agents/skills/martial-arts-research/`、Claude Codeが`~/.claude/skills/martial-arts-research/`、Antigravityが`~/.gemini/config/skills/martial-arts-research/`。個人配置はskills CLIの`-g`で選ぶ。今回そこへの新規導入は行っていない。Codexのスキル選択は`/skills`または`$`による選択で、Claude Codeのスラッシュ名をCodexで使えるとは仮定しない。

`--mode`、`--task`、`--fiction`、`--stage`はスキルへのプロンプト指定。`codex exec --mode ...`のような製品CLIの引数ではない。製品のプロンプト引数や標準入力に渡す。A/B/C/Dはmartial/weapons/military/integratedの別名。taskは独立してsurvey/compare/reviewを選ぶ。未知値・欠落・重複は確認を求める。

## 配布物の範囲

配布物は[package-files.txt](../package-files.txt)に記載されたファイルだけで、Gitは不要。`skills/martial-arts-research`はこの一覧から生成する。`feedback/`、隠しパス、`*.local.md`、Pythonキャッシュ、重複、存在しないファイルは一覧に入れられず、CIのテストが拒否する。既存の公開検証資料は一覧で明示して保持し、新しい実行記録はGit対象外の`feedback/`へ保存する。

`.git`／`.agents`／`.claude`／キャッシュを配布元に含めない。評価用の保存スキルはSKILL.md.txtへ改名してバイトを保全し、検出対象のSKILL.mdはルートの1件だけにする。修正は正本で行い、生成し直してコミットする。シンボリックリンクは必須にしない。アプリ設定・認証・モデル設定は変更しない。

## 旧Pythonインストーラーからの移行

0.3.1までの`install.py`で入れた配置には`.martial-arts-research-install.json`がある。0.4.0で`install.py`・`uninstall.py`は廃止した。移行するときは、その配置を別の場所にバックアップして削除し、上のskills CLIの`add`で入れ直す。手編集があれば、削除前にバックアップと比較して必要な変更を移す。以後の更新・削除にはskills CLIだけを使う。旧版のインストーラーが必要なら、タグv0.3.1から取得できる。

相対参照は読み込んだSKILL.mdの所在から解決する。Pythonを使う場合は、その配置の`research_guard.py`を絶対パスで実行する。対象の`--root`と`--record`等は対象資料のパスを指定する。

```sh
python3 /path/to/project/.claude/skills/martial-arts-research/scripts/research_guard.py validate --record /path/to/project/.claude/skills/martial-arts-research/examples/records/military.json
```

Python 3.9以上の標準ライブラリのみ。Pythonがなければ調査と説明は可能だがguardは未実施とする。特定MCP、学術API、APIキー、有料検索、モデル、エージェント委譲は必須にしない。取得できない資料はunavailable等に記録し、本文確認済みにしない。

## 今回の実機確認と未確認

| 環境・版 | 検出 | 回答実行 | 原因・残る未確認 |
| --- | --- | --- | --- |
| Codex CLI 0.155.1 | app-serverの`skills/list`で正本コピーをrepoスコープ・enabledとして検出 | 未完了 | 設定済み`gpt-6.1-sol`がChatGPTアカウントで非対応としてHTTP 400。モデルを変更していない |
| Claude Code 2.1.285 | initのskills／slash_commandsに名称を確認 | 未完了 | 通常サンドボックスでは認証不可。既存認証へアクセス可能な実行では週間利用上限によるHTTP 429。既定`claude-opus-5-5`の応答は得ていない |
| Python 3.14.8 | guard・記録例の機械検査 | オフライン検査を実施 | 初回検証は3.9文法チェックのみ。その後Windows CIで3.9／3.14各57件を通過（下記） |
| 独立したCodexサブエージェント | スキルを明示して別コンテキストで読込 | 合成資料で実施 | 製品CLIの発見・自然言語起動・スキルなし比較の代替試験とはしない |

実行条件、保全証拠、採点と再実行手順は[validation.md](https://github.com/Mr-Kondo/martial-arts-research/blob/main/docs/validation.md)。自然言語の起動／非起動と全タスクの両CLI評価、スキルなし比較は未実施。コピー一致やJSON合格からモデル回答の互換性を推定しない。

## Windows CIで確認した範囲

2026-10-11、[Windows CI実行38126044942](https://github.com/Mr-Kondo/martial-arts-research/actions/runs/38126044942)でPython 3.9／3.14各57件に合格。guardとコピー配置・更新・削除、手編集の保護、日本語パス・CRLF・別OSのsnapshotを検証した。Windows上のCodex／Claude Codeモデル回答、個人用配置は未確認。

検証対象は互換修正後のmainコミットb394f9b。これらの修正は0.1.1に同梱する。公開済み0.1.0タグとZIPは変更していない。

## Linux CIで確認した範囲

2026-10-11、[Python CI実行38127240113](https://github.com/Mr-Kondo/martial-arts-research/actions/runs/38127240113)でUbuntu 24.04、Python 3.9.25／3.14.8各57件に合格。既存のWindows側も各57件に合格した。guardとコピー配置・更新・削除、手編集の保護、日本語パス・CRLF・別OSのsnapshotを検証した。[実測記録](https://github.com/Mr-Kondo/martial-arts-research/blob/main/evals/results/linux-ci.json)を参照。

検証対象はmainコミットc8df6b4。Linuxの検証記録と共通CI設定は0.1.2に同梱する。公開済み0.1.1タグ・ZIPは変更していない。Linux上のCodex／Claude Codeモデル回答、個人用配置、他のLinuxディストリビューションは未確認。

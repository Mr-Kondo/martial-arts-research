# 配置・呼出し・互換性

2026-10-11。共通本体はルートの[SKILL.md](../SKILL.md)。実行時に参照するファイルは同じコピーへ揃え、修正は正本で行う。プロジェクト配置を基本とし、グローバル設定・モデル指定・認証設定を変更しない。

| 利用先 | コピー先 | 明示呼出し（チャットの本文） | 自然言語起動 |
| --- | --- | --- | --- |
| Codex | `<project>/.agents/skills/martial-arts-research/` | `$martial-arts-research --mode B --task compare 10式と90式の公開諸元を比較して` | スキル未指定で「戦術・作戦・戦略の用法を調べて」等 |
| Claude Code | `<project>/.claude/skills/martial-arts-research/` | `/martial-arts-research --mode C --task survey 軍略の用法を調べて` | 同じ自然言語本文を使う |

配置と起動表記の根拠：[Codex公式](https://learn.chatgpt.com/docs/build-skills)、[Claude Code公式](https://code.claude.com/docs/en/skills)、[共通仕様](https://agentskills.io/specification)。ページの必要箇所を2026-10-11に確認。Codexの旧公式URLは前記ページへ転送された。発見済みのスキルが表示されない場合は新しいセッションで確認する。

個人用のコピー先はCodexが`~/.agents/skills/martial-arts-research/`、Claude Codeが`~/.claude/skills/martial-arts-research/`。個人配置を明示的に選ぶ場合だけ、下のコピー手順のdestinationを該当パスへ置き換えて同じfiles／ディレクトリをコピーする。今回そこへのインストールは行っていない。Codexのスキル選択は`/skills`または`$`による選択で、Claude Codeのスラッシュ名をCodexで使えるとは仮定しない。

`--mode`、`--task`、`--fiction`、`--stage`はスキルへのプロンプト指定。`codex exec --mode ...`のような製品CLIの引数ではない。製品のプロンプト引数や標準入力に渡す。A/B/C/Dはmartial/weapons/military/integratedの別名。taskは独立してsurvey/compare/reviewを選ぶ。未知値・欠落・重複は確認を求める。

## コピー配置

インストールと更新は同じ[install.py](../scripts/install.py)を使う。最新版のチェックアウトまたは解凍したリリースから実行する。配布元はスクリプトの所在から解決する。

```sh
python3 scripts/install.py --project /path/to/project --target both
python3 scripts/install.py --project /path/to/project --target codex
python3 scripts/install.py --user --target both
```

`--target`はcodex／claude／both（既定both）。`--project`の既定は現在のディレクトリ。`--user`は個人用を明示選択し、projectと併用不可。個人配置は利用者がこのコマンドを選んだ場合だけ実行する。今回の作業ではプロジェクト配置を更新した。

削除は[uninstall.py](../scripts/uninstall.py)で同じ配置先を選ぶ。

```sh
python3 scripts/uninstall.py --project /path/to/project --target both
python3 scripts/uninstall.py --user --target claude
```

インストールはファイルとディレクトリをコピーし、VERSIONとSHA-256を`.martial-arts-research-install.json`に記録する。更新前・削除前に全対象を照合する。手編集、追加ファイル、空ディレクトリの追加、管理記録なし、リンク配置があれば停止する。変更を別途保全して元の配置へ戻してから再実行する。無条件上書き・強制削除オプションはない。存在しない配置の削除は成功扱い。

更新は同じ親ディレクトリの一時コピーを置換し、旧版にだけあった管理対象ファイルも除く。置換失敗時は旧コピーを戻す。両配置は順番に更新するため、ディスク障害等では片方だけ更新済みになり得る。実行中に同じ配置を別プロセスで編集しない。アプリ設定・認証・モデル設定は変更しない。

`.git`／`.agents`／`.claude`／キャッシュを配布元に含めない。評価用の保存スキルはSKILL.md.txtへ改名してバイトを保全し、検出対象のSKILL.mdはルートの1件だけにする。正本を更新してから両配置へ同じスクリプトで同期する。シンボリックリンクは必須にしない。

旧方式で作成した今回の2コピーは、変更前の正本77ファイルとのバイト一致を確認して管理記録を付けた。一般の管理記録のない配置を自動採用する処理はない。

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

実行条件、保全証拠、採点と再実行手順は[validation.md](validation.md)。自然言語の起動／非起動と全タスクの両CLI評価、スキルなし比較は未実施。コピー一致やJSON合格からモデル回答の互換性を推定しない。

## Windows CIで確認した範囲

2026-10-11、[Windows CI実行38126044942](https://github.com/Mr-Kondo/martial-arts-research/actions/runs/38126044942)でPython 3.9／3.14各57件に合格。guardとコピー配置・更新・削除、手編集の保護、日本語パス・CRLF・別OSのsnapshotを検証した。Windows上のCodex／Claude Codeモデル回答、個人用配置は未確認。

検証対象は互換修正後のmainコミットb394f9b。これらの修正は0.1.1に同梱する。公開済み0.1.0タグとZIPは変更していない。

## Linux CIで確認した範囲

2026-10-11、[Python CI実行38127240113](https://github.com/Mr-Kondo/martial-arts-research/actions/runs/38127240113)でUbuntu 24.04、Python 3.9.25／3.14.8各57件に合格。既存のWindows側も各57件に合格した。guardとコピー配置・更新・削除、手編集の保護、日本語パス・CRLF・別OSのsnapshotを検証した。[実測記録](../evals/results/linux-ci.json)を参照。

検証対象はmainコミットc8df6b4。Linuxの検証記録と共通CI設定は0.1.2に同梱する。公開済み0.1.1タグ・ZIPは変更していない。Linux上のCodex／Claude Codeモデル回答、個人用配置、他のLinuxディストリビューションは未確認。

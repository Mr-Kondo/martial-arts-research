# martial-arts-research

バージョン：0.3.1。

添付仕様に基づく実装を作成した（2026-10-11）。[スキル本体](SKILL.md)が正本。Codex／Claude Code／Gemini Antigravity向けに同じ内容を配置できる。Antigravityの配置仕様と判断は[ADR](https://github.com/Mr-Kondo/martial-arts-research/blob/main/adr/three-environment-delivery.md)を参照。

- [配置・呼出し・実機の確認範囲](docs/compatibility.md)
- [検証結果・未実施項目・再実行手順](https://github.com/Mr-Kondo/martial-arts-research/blob/main/docs/validation.md)
- [記録契約schema 2](references/record-contract.md)／[標準ライブラリguard](scripts/research_guard.py)
- [ツールによる監査・回答生成](references/output-audit.md)：計算・引用・比較条件・推論・書誌の確認範囲を回答に保持
- [来歴・変更範囲・ライセンス](https://github.com/Mr-Kondo/martial-arts-research/blob/main/docs/provenance.md)
- [非公開の問題報告と合成回帰ケース](docs/feedback.md)：依頼時だけ保存し、自動送信しない
- [形式保持のA/B評価](https://github.com/Mr-Kondo/martial-arts-research/blob/main/evals/results/format-preservation-ab.md)：改善を確認できず候補不採用
- [呼出し例](examples/codex-invocation.md)／[起動評価40件](https://github.com/Mr-Kondo/martial-arts-research/blob/main/evals/trigger-cases.json)／[タスク評価28件](https://github.com/Mr-Kondo/martial-arts-research/blob/main/evals/task-cases.json)

skills CLIで導入する場合（Node.jsが必要）：

```sh
npx skills add https://github.com/Mr-Kondo/martial-arts-research/tree/main/skills/martial-arts-research --skill martial-arts-research -a codex claude-code antigravity
npx skills update martial-arts-research
npx skills remove martial-arts-research
```

初回の`add`で更新元を登録する。以後は`npx skills update`でも更新できる。他のスキルも対象になるため、このスキルだけなら上の名前指定を使う。個人用は`add`に`-g`を付け、更新・削除にも`-g`を指定する。最新版はGitHubの`main`で、リリースタグの選択ではない。必ず上の専用フォルダURLを使う（ルートURLは開発・評価資料も含む）。既存のPython配置からの移行とCLIの検証版は[互換性](docs/compatibility.md#skills-cliによる導入更新)を参照。

Pythonによるインストール・更新とアンインストール（Python 3.9以上）：

```sh
python3 scripts/install.py --project /path/to/project --target both
python3 scripts/uninstall.py --project /path/to/project --target both
python3 scripts/install.py --project /path/to/project --target all
```

個人用は`--project`の代わりに`--user`を明示する。bothは従来の2製品、allは3製品、antigravityはAntigravityだけを選ぶ。CodexとAntigravityのプロジェクト配置は共有する。更新もinstall.pyを使う。管理済みファイルに変更・追加があれば保全のため停止する。[詳細](docs/compatibility.md)、[リリース履歴](CHANGELOG.md)。

```text
Codex: $martial-arts-research --mode B --task compare 10式と90式の公称重量を比較して
Claude Code: /martial-arts-research --mode C --task survey 戦術・作戦・戦略・軍略の用法を調べて
自然言語: 武器の性質と操作者の知覚・技能の関係を根拠付きで調べて
```

`--mode`と`--task`はチャットの依頼本文で指定する。A/martial、B/weapons、C/military、D/integratedとsurvey/compare/reviewを独立に選ぶ。通常の推敲・単純翻訳・新規シーン執筆は自動起動の対象外。

```sh
# 配布元リポジトリで実行（テストは配布物に含まない）
python3 -B -m unittest discover -s scripts/tests -v
python3 -B scripts/research_guard.py validate --record examples/records/military.json
python3 -B scripts/research_guard.py render --record examples/records/calculation-audit.json
```

機械検査の合格は記録整合性のみ。意味・歴史・因果・性能・最終回答の正確性は自動保証しない。両CLIでのスキル検出を確認したが、Codexの設定モデル非対応とClaude Codeの週間利用上限により、両CLIの回答評価は未完了。別コンテキストの合成資料評価は実施した。

## 配布と検証ログ

配布対象は[package-files.txt](package-files.txt)で明示する。一覧外の私的原稿や追加ファイルはコピーしない。GitのないZIP展開先でも導入・更新・削除できる。配布対象は実行時に必要なものだけ（SKILL.md、references、scripts、examples、docs、導入用ファイル）。設計資料・ADR・評価と実行記録・テストは配布元リポジトリにだけ置く。配布対象を追加するときは一覧も更新する。設計判断は[一覧方式](https://github.com/Mr-Kondo/martial-arts-research/blob/main/adr/explicit-package-boundary.md)と[実行時最小への絞り込み](https://github.com/Mr-Kondo/martial-arts-research/blob/main/adr/runtime-only-package.md)を参照。

今後の実行記録・検証ログはGit対象外の`feedback/`に保存する。既存の公開済み合成評価・検証資料は再現用に残す。秘密情報・個人情報・未公開原稿は記録せず、自動送信もしない。

## 既存の設計資料

WikiSkillによる更新管理の4案は[最終採否](https://github.com/Mr-Kondo/martial-arts-research/blob/main/adr/wikiskill-final-decision.md)まで検証した。B1（ガイド）・B2（索引）・B3（条件付き入口）は、事前の採用基準を満たす効果を確認できなかったため実行用スキルへ採用しない。B4（比較・監査基盤）は評価専用の基盤として維持する。評価用コードと記録を通常のスキル実行へ混入させない。

追加51課題の安全性確認段階は102割付け・100有効回答の二系統監査と裁定まで完了した。続く前向き確認は、最初の統計判定に408ペアを要する一方、17ペアの監査完了時点でも採用基準を満たす新しい証拠が得られず、次の単位も基盤上限で未完了となった。反復の機会費用が増分情報を上回ると判断して終了した。これはB2の無効性や安全性の証明ではなく、現候補を採用しないという製品判断である。

2026-10-11。Defyの `defy-martial-review` を一般化し、CodexとClaude Codeの両方で利用するAgent Skill `martial-arts-research` として設計した。実装者はCodex。モードA〜Dと両環境の互換性を含む更新版。

- [01 調査報告](https://github.com/Mr-Kondo/martial-arts-research/blob/main/01-research-report.md): 元スキル、既存スキル、武術・装備・軍事思想・戦史資料と確認範囲。
- [02 スキル設計](https://github.com/Mr-Kondo/martial-arts-research/blob/main/02-skill-design.md): モードA〜D、作業指定、A〜E/W1〜W5/M1〜M6、出典規則、記録・検証、両環境の配置・呼出し・評価。
- [03 Codex向け実装プロンプト](https://github.com/Mr-Kondo/martial-arts-research/blob/main/03-codex-implementation-prompt.md): 「ここから」〜「ここまで」をCodexへ渡し、CodexとClaude Codeの両方で利用するスキルを実装できる。
- [貼り付け用の指示文](https://github.com/Mr-Kondo/martial-arts-research/blob/main/codex-implementation-prompt.txt): 前書き・境界表示を除いた実装指示の全文。このファイルの内容をそのままCodexへ渡せる。

考証対象を選ぶ `--mode` と、作業を選ぶ `--task survey|compare|review`（調査／比較／主張検証）を分ける。

| モードの指定 | 内部名 | 考証対象 |
| --- | --- | --- |
| `--mode A` | `martial` | 武術・身体動作・技能 |
| `--mode B` | `weapons` | 武器・兵器の歴史・構造・公開性能・運用 |
| `--mode C` | `military` | 戦術・戦略・軍略、作戦、指揮・情報・兵站・政治目的 |
| `--mode D` | `integrated` | 依頼された複数の観点とその関係 |

内部名も入力に使える。たとえば `--mode C` と `--mode military` は同等。任意拡張は `--fiction`（作品設定）と `--stage`（殺陣・撮影）。

共通のSKILL.md・references・scriptsを一つの原本として管理する。実装後の配置・明示呼出しは次のとおり。各環境でdescriptionに基づく自然言語起動も受け付ける。

| 利用環境 | プロジェクト用 | 個人用 | 明示呼出し |
| --- | --- | --- | --- |
| Codex | `.agents/skills/martial-arts-research/` | `~/.agents/skills/martial-arts-research/` | `$martial-arts-research` |
| Claude Code | `.claude/skills/martial-arts-research/` | `~/.claude/skills/martial-arts-research/` | `/martial-arts-research` |

Codexの想定呼出し例（Codexに渡すプロンプト内の指定。シェルコマンドではない）:

```text
$martial-arts-research --mode A --task survey 無拍子という語の用法を調べてください。
$martial-arts-research --mode B --task compare 10式と90式の公開諸元を比較し、条件不明の項目を示してください。
$martial-arts-research --mode C --task review --fiction この戦役描写を、政治目的、指揮、情報、兵站、当時の判断条件から考証してください。
$martial-arts-research --mode D --task review --fiction この場面の槍の扱いと防具・部隊行動を、確定設定と現実の根拠を分けて考証してください。
```

Claude Codeの想定呼出し例:

```text
/martial-arts-research --mode A --task survey 無拍子という語の用法を、流派の説明と知覚・運動研究を分けて調べてください。

/martial-arts-research --mode B --task compare 10式と90式の公開諸元を比較し、型式・構成・測定条件が不明な項目を示してください。

/martial-arts-research --mode C --task survey 戦術・作戦・戦略・軍略という語を、時代と資料ごとの用法を分けて調べてください。

/martial-arts-research --mode military --task compare 二つの歴史的戦役を、目的・判断時点の情報・兵站・結果の範囲を揃えて比較してください。

/martial-arts-research --mode C --task review --fiction この戦役描写を、政治目的、指揮、情報、兵站、当時の判断条件から考証してください。

/martial-arts-research --mode D --task review --fiction この場面の槍の扱いと防具・部隊行動を、確定設定と現実の根拠を分けて考証してください。
```

指定はスキルが依頼文字列から解釈するもので、CodexまたはClaude Code本体のCLIオプションではない。引数のない自然言語依頼も受け付ける。明示指定を優先し、未指定なら依頼から選び、曖昧な対象は武術を既定とする。共通本体はClaude Code固有の変数展開やツールに依存させず、相対参照は読み込んだSKILL.mdの所在を基準に解決する。

モードCは、軍略の用法を資料ごとに確認し、当時の情報・資源・目的と事後の結果、教範の規範と史実、因果説明と反実仮想を分ける。モードCと、武術の分析軸Cは別の識別子である。

Pythonの機械テスト、Codexでのスキル実行評価、Claude Codeでのスキル実行評価を分け、環境ごとの版・実行条件・確認状態を記録する。配置・呼出しの根拠は [Codex公式](https://developers.openai.com/codex/skills/) と [Claude Code公式](https://code.claude.com/docs/en/skills) を2026-10-11に確認した。実装時にも対象の版を再確認する。

以下の資料は実装前の調査・設計・実装指示として保全した。現在の実装と実施状況は冒頭のリンクを参照する。元スキルの機械テスト32件の成功は、新スキルの検証済み実績ではない。

# martial-arts-research

バージョン：0.1.2。

添付仕様に基づく実装を作成した（2026-10-11）。[スキル本体](SKILL.md)が正本で、Codex／Claude Code向けのプロジェクトコピーを同じ内容で配置した。

- [配置・呼出し・実機の確認範囲](docs/compatibility.md)
- [検証結果・未実施項目・再実行手順](docs/validation.md)
- [記録契約schema 2](references/record-contract.md)／[標準ライブラリguard](scripts/research_guard.py)
- [ツールによる監査・回答生成](references/output-audit.md)：計算・引用・比較条件・推論・書誌の確認範囲を回答に保持
- [来歴・変更範囲・ライセンス](docs/provenance.md)
- [呼出し例](examples/codex-invocation.md)／[起動評価40件](evals/trigger-cases.json)／[タスク評価28件](evals/task-cases.json)

インストール・更新とアンインストール（Python 3.9以上）：

```sh
python3 scripts/install.py --project /path/to/project --target both
python3 scripts/uninstall.py --project /path/to/project --target both
```

個人用は`--project`の代わりに`--user`を明示する。更新もinstall.pyを使う。管理済みファイルに変更・追加があれば保全のため停止する。[詳細](docs/compatibility.md)、[リリース履歴](CHANGELOG.md)。

```text
Codex: $martial-arts-research --mode B --task compare 10式と90式の公称重量を比較して
Claude Code: /martial-arts-research --mode C --task survey 戦術・作戦・戦略・軍略の用法を調べて
自然言語: 武器の性質と操作者の知覚・技能の関係を根拠付きで調べて
```

`--mode`と`--task`はチャットの依頼本文で指定する。A/martial、B/weapons、C/military、D/integratedとsurvey/compare/reviewを独立に選ぶ。通常の推敲・単純翻訳・新規シーン執筆は自動起動の対象外。

```sh
python3 -B -m unittest discover -s scripts/tests -v
python3 -B scripts/research_guard.py validate --record examples/records/military.json
python3 -B scripts/research_guard.py render --record examples/records/calculation-audit.json
```

機械検査の合格は記録整合性のみ。意味・歴史・因果・性能・最終回答の正確性は自動保証しない。両CLIでのスキル検出を確認したが、Codexの設定モデル非対応とClaude Codeの週間利用上限により、両CLIの回答評価は未完了。別コンテキストの合成資料評価は実施した。

## 既存の設計資料

2026-10-11。Defyの `defy-martial-review` を一般化し、CodexとClaude Codeの両方で利用するAgent Skill `martial-arts-research` として設計した。実装者はCodex。モードA〜Dと両環境の互換性を含む更新版。

- [01 調査報告](01-research-report.md): 元スキル、既存スキル、武術・装備・軍事思想・戦史資料と確認範囲。
- [02 スキル設計](02-skill-design.md): モードA〜D、作業指定、A〜E/W1〜W5/M1〜M6、出典規則、記録・検証、両環境の配置・呼出し・評価。
- [03 Codex向け実装プロンプト](03-codex-implementation-prompt.md): 「ここから」〜「ここまで」をCodexへ渡し、CodexとClaude Codeの両方で利用するスキルを実装できる。
- [貼り付け用の指示文](codex-implementation-prompt.txt): 前書き・境界表示を除いた実装指示の全文。このファイルの内容をそのままCodexへ渡せる。

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

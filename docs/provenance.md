# 来歴・変更範囲・ライセンス

実装日／Web必要箇所の確認日：2026-10-11。ユーザーの添付実装仕様と[貼り付け用指示](../codex-implementation-prompt.txt)を契約とした。既存の調査報告・設計・実装指示はそのまま保全し、READMEに実装の入口を追加した。

## 固定した元実装

元リポジトリ：`/Volumes/SSD/kamen_rider_defy`。対象は`.claude/skills/defy-martial-review/`（元の`.agents`配置はこの正本へのリンク）、固定コミットは`8a94b0e557ce6db4b98323fd8f31a92f75d1fdbb`。`git show`で9ファイルを読取り、[original-files.json](original-files.json)にバイト数とSHA-256を記録した。閲覧時のHEADは`e06f5beeae3b9da0f866d568cf9d77d853f593dc`で、固定版との対象範囲の差はdefy-context.mdの4行追加・3行削除。元リポジトリは読取りのみで、本文・設定・履歴を編集していない。

| 保持した考え方 | 変更・追加 | 既定手順から削除 |
| --- | --- | --- |
| 出典状態の区別、逐語引用、snapshot、原文変更の再照合、分析軸、留保 | 原稿不要のsurvey/compare、独立mode/task、W/M軸、一般化した任意創作、schema 2、標準ライブラリguard、両環境のコピーと評価資料 | 固定Defyパス、人物固有の分岐、天稟・変身・即時ラーニングの既定判定、旧記録互換、原本のテスト成功を引き継ぐ扱い |

説明文・コード・テストは今回の契約に沿って独自に作成した。元のファイルをそのまま転載した部分はない。保全した設計文書は実装前からこのワークスペースに存在したもの。元の32件のテスト実績は本スキルの実績に含めない。

固定コミットのリポジトリ直下でLICENSE／LICENSE.md／COPYINGは確認できなかった。元リポジトリのライセンス許諾は未確認であり、新しい許諾を付与しない。本成果物全体にも独自のライセンスを設定していない。

## 参考資料と取り入れた点

| 参考・確認した版 | 用途・流用境界 |
| --- | --- |
| [Agent Skills仕様](https://agentskills.io/specification)、2026-10-11のWeb版 | name/descriptionと共通構造。説明を独自に記述 |
| [Codex公式](https://learn.chatgpt.com/docs/build-skills)、[Claude Code公式](https://code.claude.com/docs/en/skills)、同日のWeb版 | 配置・明示／自然言語起動。本文の転載なし |
| [評価](https://agentskills.io/skill-creation/evaluating-skills)、[説明最適化](https://agentskills.io/skill-creation/optimizing-descriptions)、同日のWeb版 | 起動と回答を分ける、期待結果を実行モデルへ渡さない、新しいコンテキスト、基準なし比較 |
| [Anthropic skill-creator](https://github.com/anthropics/skills/tree/main/skills/skill-creator)、mainの同日閲覧 | 独立した前向き評価と保存結果の確認。commit SHA未取得。実行コード・テンプレートの転載なし |
| [K-Dense scientific-critical-thinking](https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/skills/scientific-critical-thinking/SKILL.md)、v1.5、最終レビュー2026-10-01、MIT表記 | 資料・推論・代替解釈・限界の分離。commit SHA未取得。文面・コードの転載なし |
| [K-Dense literature-review](https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/skills/literature-review/SKILL.md)、v1.11、最終レビュー2026-09-30、MIT表記 | 問い、検索、選別、抽出、統合の工程。commit SHA未取得。API依存やPDF出力は採用していない |

各リポジトリの指示を実装作業への命令として実行していない。公開ページの全文や参考コードをパッケージに転載していないため、第三者コードの再配布通知は追加していない。未取得のcommitやライセンスを推定で補わない。

研究資料の初期台帳は[武術](../references/source-catalog.md)8件、[装備](../references/weapons-source-catalog.md)4件、[軍事](../references/military-source-catalog.md)4件。各資料に今回の閲覧範囲、状態、箇所、限界を付けた。台帳のfull_textは必要な本文箇所の読込であり、全論文／規格／巻の通読ではない。関連PDF未読と抄録のみの項目は区別した。

## 生成した評価入力

[fixtures/provenance.json](../evals/fixtures/provenance.json)の本文は今回の合成入力。実在研究、実在装備の性能、実在戦役、ユーザーの採用作品設定として引用しない。旧Defyの人物設定をfixtureへコピーしていない。実在の数値例は[公称重量記録](../examples/records/weapons-declared.json)に取得元・閲覧箇所・declared状態を残した。

0.1.0では標準ライブラリの配置・更新／削除スクリプトとVERSIONを追加した。評価保存用のSKILL.mdはバイトを変更せずSKILL.md.txtへ改名し、インストール後の重複検出を防いだ。

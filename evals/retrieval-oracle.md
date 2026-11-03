# 根拠探索評価の採点根拠

[固定課題](retrieval-cases.json)の命題は、次の公開正本と対応させる。数値と否定命題は原文を確認した。候補に合わせて正解を変更しない。

| 課題ID | 正本と確認箇所 | 判断の範囲 |
|---|---|---|
| update-format-ab-adoption | [形式保持比較](results/format-preservation-ab.md)の比較表、制約、採否 | 過去の限定試行の結果。製品の自律起動や一般品質の証明ではない |
| update-package-private-feedback | [配布境界ADR](../adr/explicit-package-boundary.md)の配布一覧・非機能要件 | 明示一覧と拒否規則。既存公開資料の保持と新規ログの扱いを区別する |
| update-validation-claims | [3環境ADR](../adr/three-environment-delivery.md)の評価モデル | 件数・上限は当時の計画の記述。現在の全プロジェクト共通予算へ一般化しない。配置成功は品質証明ではない |
| normal-evidence-distinctions | [証拠方針](../references/evidence-policy.md)の資料状態・関係型、[研究手順](../references/research-methods.md)の動作観察・知覚判断 | 抄録、未取得、動画未視聴、キー押し実験の適用限界 |

課題は候補・前回課題を渡さないClaude呼出しで生成した。同じモデル系列による生成であり、人間の独立評価とは呼ばない。生成出力に根拠パス欄が欠けていたため、再生成せず上表の正本を実装者が対応付けた。歴史的予算を現在の予算と混同しないよう、該当依頼と命題の表現だけを限定した。

回答には正解値と指定正本を隠し、命題の文面を渡す。このため選択式の手掛かりがあり、自由回答や実務全体の品質評価ではない。指定正本を実際にReadし引用したかも別に採点する。Read成功は資料の熟読や回答文全体の意味的正確性までは証明しない。

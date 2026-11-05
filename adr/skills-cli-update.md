# skills CLIで更新元を登録する

日付: 2026-11-05。状態: 採用（公開後の更新実測を残す）。関連: Issue #18。

## 文脈と仮説

既存のルートSKILL.mdはskills CLIに認識されるが、CLIはpackage-files.txtを使わずディレクトリをコピーする。ルートのままでは実行時最小配布の決定に反する。配布一覧から生成した専用フォルダをGitHubのtree URLで登録すれば、実行用配布を保ったまま標準のupdateを利用できると仮定する。

## 決定と実装計画

- scripts/build_skills_distribution.pyから既存installを呼び、skills/martial-arts-researchへ生成する。独自の更新・lock実装を作らない。
- READMEとdocs/compatibility.mdに専用URL、初回add、update、remove、個人用-g、旧配置のバックアップと管理方式の分離を記載する。
- tests/test_skills_distribution.pyで正本から作った一時配布とコミット済み生成物を照合する。既存CIが実行する。
- runtimeの指示、frontmatter、参考資料は変更しない。版は配布機能追加の0.3.1。

## 成功指標・撤退条件

隔離環境でCLIが1スキルを検出し、導入物が配布一覧と一致すること、GitHub URL由来のlock情報を作りupdateを実行できることを確認する。最新版はmainを意味する。更新元のパスを保持しない、または配布外資料をコピーする場合は対応済みとしない。既存全テストも成功を要する。スキルの回答品質を変えないため内容A/B評価は対象外。

## 非機能要件と機会費用

依存追加なし。CLI導入にはNode.jsとネットワークが必要。検証ではDISABLE_TELEMETRY=1を設定し、ログはignored feedback/へ保存する。秘密情報・個人情報は生成物に含めない。既存の配布一覧検査を再利用する。CLIはユーザー変更を上書きし得るため移行前にバックアップする。コマンド例はテキストで閲覧・コピーできる。

41ファイルを重複して保持する費用は発生するが、既存の正本・呼出しを移動する大きな改修と独自更新機構を避けられる。同期漏れはCIで拒否する。ルートURLを誤って指定する問題は案内で明示する。参考にしたskill-creatorの段階的な情報開示とfind-skillsの標準CLI利用を採用し、評価用の補助構造は導入しない。

## 検証・レビュー

120件の単体テストとgit diff --checkが成功。skills 1.7.6のローカルパス導入でcodex/claude-code/antigravityを指定し、生成物とのファイル・ハッシュ・管理記録一致を確認、removeも成功。ローカルパス由来の登録はupdateで対象とならなかったため、これをGitHub更新成功の根拠にはしない。mainへの公開後にGitHub tree URLで初回登録・update・配置一致を実測するまでIssueを閉じない。

Claude Code（claude-sonnet-5-5、medium）の差分レビューで重大な指摘なし。採用: 管理記録もコピーされることを案内へ明記。不採用: skills直下の他のフォルダを禁止する検査（指定した専用tree URLの外側なので今回の導入へ影響せず、将来の無関係なスキルを不必要に禁止する）。「Pythonが検証なしで上書きする」という説明は既存ensure_ownedの実装と異なるため採用しない。Antigravityは最初のレビューでコマンド拒否・空回答、その後は利用上限のためレビュー未完了。成功と数えない。

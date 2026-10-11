# Defy武術スキルの一般化に向けた調査報告

調査日: 2026-10-11。目的は武術を調査・分析するAgent Skillの設計と実装プロンプトの作成である。同日の追加要望を反映し、武器・兵器と、モードCの戦術・戦略・軍略の考証を設計に加えた。実装者はCodex、スキルの利用先はCodexとClaude Codeの両方とする。

## 1. 推奨する方針

元の `defy-martial-review` は、現実の根拠と作品設定を分ける監修手順として設計されている。流派・動作・相互作用・習得を分ける分析と、引用・出典の追跡は一般化できる。

新しい `martial-arts-research` は、**技法・文献の調査、条件を揃えた比較、既存主張の検証**を主用途にする。Defyの人物・能力・参照ファイルを削除し、創作の設定整合性は明示依頼時だけ扱う。引用対象のない質問にも対応させることが、名称変更だけでは済まない主な設計変更である。

## 2. 調査範囲と原本

接続済みGitHubから [Mr-Kondo/Project_Defy](https://github.com/Mr-Kondo/Project_Defy) を特定し、以下の固定版を読んだ。

- コミット: `8a94b0e557ce6db4b98323fd8f31a92f75d1fdbb`。
- 対象: `.claude/skills/defy-martial-review/` のSKILL.md、5参照文書、guard、テスト、表示metadata。
- 周辺: AGENTS.md、README.md、`defy-science-review`と`defy-novelize`のSKILL.md、戦闘スタイルの元ネタ資料。
- ローカルの選択スナップショット: `/workspace/research/defy-source/`。全リポジトリのcheckoutではなく、今回の調査に必要な選択ファイルである。

元スキルや元リポジトリへの変更、commit、pushは行っていない。元の文献台帳は2026-10-09の記録を含むが、その日付を今回の閲覧結果へ読み替えていない。

## 3. 元スキルの内容と抽出判断

| 元の要素 | 一般化の判断 | 理由 |
| --- | --- | --- |
| A 流派・用語・歴史 | 保持 | 名称・系統・時代と資料の支持範囲を区別できる |
| B 身体・武器の動作 | 保持 | 姿勢・接触・把持・距離・連続性を追える |
| C 攻防・戦術 | 知覚・判断・相互作用へ整理 | 予測、反応、実行、相手の抵抗を別に分析できる |
| D 習得・実行能力 | 技能獲得・転移へ整理 | 知識、協力下の実演、抵抗下の使用を混同しない |
| E 作品設定・装備・AI | 環境・装備・技術支援を一般部分へ | 作品独自の能力や時点は任意拡張へ切り出せる |
| 任意F 殺陣 | 明示依頼時の拡張として保持 | 見せる動作の成立と抵抗下の有効性を区別する |
| 出典の状態・箇所・限界 | 保持 | 閲覧状態を主張の正しさへ置き換えない |
| snapshot / validate | 条件付きで使用 | 原文引用の整合性には有用。全質問に強制すると過大 |
| Defy設定表D01〜D09、固定引継ぎ | 削除・入力条件へ置換 | 別作品や現実の調査に固有パスが不要 |
| 物語時点、修正案、場面テンポ | 任意創作へ移動 | 一般的な文献調査では必須にならない |
| 固定八要素・定型の説明句 | 簡潔な可変出力へ変更 | 短い分類確認にも大きな報告書を要求しない |

主な原本: [SKILL.md](https://github.com/Mr-Kondo/Project_Defy/blob/8a94b0e557ce6db4b98323fd8f31a92f75d1fdbb/.claude/skills/defy-martial-review/SKILL.md)、[監修手順](https://github.com/Mr-Kondo/Project_Defy/blob/8a94b0e557ce6db4b98323fd8f31a92f75d1fdbb/.claude/skills/defy-martial-review/references/review-methods.md)、[記録契約](https://github.com/Mr-Kondo/Project_Defy/blob/8a94b0e557ce6db4b98323fd8f31a92f75d1fdbb/.claude/skills/defy-martial-review/references/review-record.md)。

### 元のguardで分かったこと

原文ハッシュ、引用一致、参照ID、取得状態の申告、判定に必要な項目を検査し、内容判断は `not_evaluated` としている。この境界は維持する。

一方、旧契約は対象引用と物語時点を必須にする。また「追加条件があれば成立する」は追加条件の文字列があれば通り、支持根拠は必須ではない。通常の支持判定も、現実の主張と作品資料の意味的な対応を機械保証しない。新契約では、問い/引用の型を分け、条件付き支持にも根拠を要求し、現実/作品/設計資料の誤流用を防ぐ。

今回、Python 3.12.14で元の [test_review_guard.py](https://github.com/Mr-Kondo/Project_Defy/blob/8a94b0e557ce6db4b98323fd8f31a92f75d1fdbb/.claude/skills/defy-martial-review/scripts/tests/test_review_guard.py) を実行し、32件が成功した。これは引用・記録・CLI等の検査であり、武術判断の正確さや新スキルの成功を示さない。Claude Codeでの元スキルの自動起動・出力評価は今回行っていない。

## 4. 既存スキル・公式仕様との比較

確認状態は各スキル本文・必要な参照/ライセンスの閲覧であり、これらのスキルを今回インストール・実行して評価したものではない。可変main/Web文書は2026-10-11の閲覧内容である。

| 既存実装・仕様 | 参考にする点 | 今回は取り込まない点 |
| --- | --- | --- |
| [Anthropic skill-creator](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md) | 実例を実行して評価・改訂する進め方、短い入口と参照資料の分離 | 作成ツール一式への必須依存 |
| [K-Dense scientific-critical-thinking](https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/skills/scientific-critical-thinking/SKILL.md) | 問い・単位を固定し、証拠を抽出してから解釈、限界を評価する | 医療向け評価尺度の武術全体への一律適用 |
| [K-Dense literature-review](https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/skills/literature-review/SKILL.md) | 検索・選別・抽出・統合・引用確認の分離、検索記録 | 有料API、PDF・図生成、網羅的レビューの常時要求 |
| [action-choreography-reference](https://github.com/snowfrost/skill-movie/blob/main/action-choreography-reference/SKILL.md) | 支持点、接触、動作連続性の観察。任意創作の参考 | 映像生成プロンプトを武術の実証資料として扱うこと |
| [Agent Skills仕様](https://agentskills.io/specification) / [Codex公式](https://developers.openai.com/codex/skills/) / [Claude Code公式](https://code.claude.com/docs/en/skills) | name/description、必要時の参照読込、共通本体、環境別の配置と呼出し | 独自ラッパー、モデル指定、特定MCPへの依存 |

検索は「scientific-critical-thinking」「martial」「SKILL.md」等で近接実装を探索し、作者のリポジトリ本文を確認した。全スキル市場の網羅検索ではない。確認した近接例からは、本件の分析手順をそのまま置換するより、Defyの分析核へ研究手順を足す方が適切と判断した。

参考実装のライセンスは、[Anthropic skill-creatorがApache-2.0](https://github.com/anthropics/skills/blob/main/skills/skill-creator/LICENSE.txt)、[K-DenseがMIT](https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/LICENSE.md)。action-choreography-referenceのライセンスは今回未確認のため、説明文・コードの転載を前提にしない。

起動試験は関連する非起動例も含め、出力試験は新しいコンテキストでskillあり/なしを比較する設計とした。[公式の出力評価指針](https://agentskills.io/skill-creation/evaluating-skills)、[description評価指針](https://agentskills.io/skill-creation/optimizing-descriptions)

## 5. 武術・動作・学習の文献

文献の今回の確認内容は、以下に資料ごとに記録する。文献は分析上の区別を支える材料であり、新スキルの五軸・判定手順全体の正答率を実証するものではない。

確認日はすべて2026-10-11。取得にはWeb閲覧のHTML/PDF抽出を使った。「本文確認」は下記の必要箇所の閲覧を意味し、全ページ・全補足資料・リンク動画を読んだという意味ではない。

### 5.1 名称・系統・競技規則

| ID・資料 | 今回の確認 | 設計に使えることと限界 |
| --- | --- | --- |
| L01 講道館『[柔道 技名称一覧](https://kdkjudo.org/技/柔道-技名称一覧/)』 | 本文確認。腰技の見出しと払腰の項目、名称分類。HTMLの公開・更新日は未確認。リンク動画は未閲覧 | 技の分類を当該団体の用法として確認できる。分類の確認だけで、抵抗下の成功率や古流柔術全体の定義は判断しない |
| L02 日本古武道協会『[天真正伝香取神道流剣術](https://www.nihonkobudokyoukai.org/martialarts/024/)』 | 本文確認。「由来」「系譜」「流儀の特徴」。公開・更新日は未確認 | 掲載系統の構成、伝承と自己説明を確認する入口。伝承の記載を独立した歴史検証や全門流共通の事実へ置き換えない |
| L03 全日本剣道連盟『[剣道試合・審判規則／同細則](https://www.kendo.or.jp/wp/wp-content/uploads/2026/06/kendo-shiai_regulations-R8_passnashi.pdf)』 | 書庫の現行リンクからPDF本文確認。規則第12・14・17条、細則第10条。第12条は印刷p.8／PDFの11ページ目。正式な改定・施行日は未確認 | 有効打突・刃筋・打突部位・禁止行為を競技の条件へ対応させる。規則上の有効・反則を規則外の物理的不可能性や勝敗へ一般化しない |

### 5.2 動作・知覚・学習

**L04 — Imamura, R., Iteya, M., Hreljac, A., & Escamilla, R. (2007).** *A Kinematic Comparison of the Judo Throw Harai-Goshi during Competitive and Non-Competitive Conditions.* Journal of Sports Science and Medicine, 6, Combat Sports Special Issue 2, 15–22。[原文](https://jssm.org/jssm-06-CSSI2-15.xml-Fulltext)

- 今回: 本文確認。Methods、Results、Discussion、Conclusion。
- 内容: 同じ取りによる払腰について、競技と非競技で動作のタイミング・大きさの差が観察された。
- 限界: 取りは1人で、受けは条件ごとに別の2人。受け・場面・抵抗の違いを分離した実験ではない。
- 設計への反映: 動作と相手の応答を一緒に追う。協力練習の観察を競技一般の成功条件にせず、限られた比較を抵抗の普遍的な因果効果にしない。

**L05 — Maloney, M. A., Renshaw, I., Headrick, J., Martin, D. T., & Farrow, D. (2018).** *Taekwondo Fighting in Training Does Not Simulate the Affective and Cognitive Demands of Competition: Implications for Behavior and Transfer.* Frontiers in Psychology, 9:25。DOI: [10.3389/fpsyg.2018.00025](https://doi.org/10.3389/fpsyg.2018.00025)

- 今回: 本文確認。Participants、Experimental Task、Procedure、Conclusion。
- 内容: 国際水準の選手10人を対象に、通常の練習と訪問チーム相手の模擬競技の認知・感情・行動条件を比較している。
- 限界: 一合宿の比較で、相手、観衆、審判、報酬等も変わる。真剣勝負や戦場の研究ではなく、特定要因だけの効果を示さない。
- 設計への反映: 抵抗だけでなく、相手への慣れ・課題の目的・環境も抽出する。練習での成績と別の条件への転移を別の問いにする。

**L06 — Incognito, M. R., Watson, T., Weidemann, G., & Steel, K. A. (2024).** *The role of the opponent's head in perception of kick target location in martial arts.* Frontiers in Sports and Active Living, 6:1468209。DOI: [10.3389/fspor.2024.1468209](https://doi.org/10.3389/fspor.2024.1468209)

- 今回: 本文確認。Participants、Materials、Procedure、Results、Discussion。
- 内容: 頭・顔の可視性を操作した蹴りの映像について、頭/胸への標的をキー入力で判断する課題。今回の課題では熟練群の有意な優越は示されていない。
- 限界: 実際の防御・勝敗は測定しない。応答時間は映像再生開始基準で静止画提示を含む。参加者・除外人数の記述は節ごとに食い違いがあり、独断で統合しない。
- 設計への反映: 刺激、観察、判断、応答方法、身体での実行を分ける。「有意差なし」を効果ゼロとせず、個別課題の結果を人間の反応時間の定数にしない。

**L07 — Zhang, Z., Piras, A., Chen, C., Kong, B., & Wang, D. (2022).** *A comparison of perceptual anticipation in combat sports between experts and non-experts: A systematic review and meta-analysis.* Frontiers in Psychology, 13:961960。DOI: [10.3389/fpsyg.2022.961960](https://doi.org/10.3389/fpsyg.2022.961960)

- 今回: 部分本文確認。AbstractとLimitations。収集した個別研究の本文、全表、補足資料は未確認。
- 内容: 要旨は27研究の統合で熟練者と非熟練者の予測課題成績の差を報告する。Limitationsは競技、課題、測定、熟練者の定義等の不均一性を挙げる。
- 限界: 要旨の効果量を再検証したものではない。熟練者の群間差は特定訓練の因果効果や、あらゆる防御成功の実証ではない。
- 設計への反映: 総説を入口に使いつつ、個別主張に必要な課題・測定条件へ戻る。L06のように結果が違う個別研究を黙って排除しない。

**L08 — Czyż, S. H., Wójcik, A. M., & Solarská, P. (2024).** *The effect of contextual interference on transfer in motor learning — a systematic review and meta-analysis.* Frontiers in Psychology, 15:1377122。DOI: [10.3389/fpsyg.2024.1377122](https://doi.org/10.3389/fpsyg.2024.1377122)

- 今回: 部分本文確認。Abstract、Introductionの保持/転移の説明、Limitations。元研究や全計算の再検証は未実施。
- 内容: 練習順序と転移の研究を統合し、実験室/応用場面や年齢によって結果が違うことを要旨で報告する。
- 限界: 著者自身が研究の品質、異質性、同一研究の複数効果量を独立に扱った点を限界として記す。武術に固有の万能な練習法を示す資料ではない。
- 設計への反映: 練習中の成績・保持・転移を分け、総説の研究数や効果量だけで結論を強めない。重複・非独立の証拠を点検する。

### 5.3 探索方法と限界

最初にDefyの出典台帳を入口として公式・出版元の原文を再取得した。追加探索では `perceptual anticipation combat sports systematic review meta analysis 2022 Zhang` と `contextual interference motor learning transfer systematic review meta-analysis 2024` をWeb検索し、出版元の要旨と関連する本文箇所を確認した。

採用は、名称/伝承、抵抗・場面の差、知覚と身体実行、学習の転移という設計上の区別に関係することを基準にした。転載・一般解説は結論の根拠にせず、課題の異なる文献を網羅的に集める作業は行っていない。独立した武術史研究、各地域の全流派、武器別の全研究を網羅した調査ではない。初期台帳はこの8資料を入口にし、利用時の問いに合わせて資料を追加する設計とする。

## 6. 設計へ反映したこと

- 現実の調査を中心にし、創作の前提は任意入力へ分離した。
- 引用対象のない問いを受け取れる三つの作業（survey/compare/review）を設け、考証対象のモード（martial/weapons/military/integrated）とは独立して指定できるようにした。
- 根拠の取得状態と支持範囲を分け、抄録の限定紹介を許しつつ本文支持と区別した。
- 条件付き支持にも根拠を要求し、単なる成立仮説を判断保留へ分けた。
- 全件JSON/機械検証を強制せず、原文引用と構造化成果物に重点を置いた。
- 新しい記録契約と、調査・比較・起動境界を含む評価を実装プロンプトへ含めた。

詳細は [スキル設計](02-skill-design.md)、実装に渡す文面は [Codex向けプロンプト](03-codex-implementation-prompt.md) を参照。今回は設計・実装指示の完成までであり、新スキル本体の作成・インストール・実行評価は行っていない。

## 7. 追加要望: 武器・兵器の考証モード

武器を扱う身体動作の分析だけでは、装備の型式、歴史、構造、性能の測定条件、運用・維持を十分に扱えない。そこで既存の調査/比較/検証を「作業」、考証対象を「モード」に分けた。スキル名は `martial-arts-research` を維持する。

- `--mode martial`: 人の技法・知覚・技能を中心にA〜Eで分析する。
- `--mode weapons`: 装備自体をW1〜W5（歴史・同定、構造・作動、性能・測定・防護、運用・維持、システムの関係）で考証する。
- `--mode integrated`: 武術・装備・軍事のうち依頼された観点と、操作者・環境との関係を考証する。
- `--task survey|compare|review`: いずれのモードにも使える作業指定。明示指定を優先し、未指定なら依頼から判断する。

創作拡張は `--fiction` 等の明示依頼で追加し、現実の装備と作品内の装備を別のfindingにする。装備名・派生型・時代・構成と、数値の出典・単位・測定条件を記録へ加える。最大射程/有効射程、理論速度/持続速度、公称/試験/推定、規格要件/製品適合を区別し、比較条件の不明は保留にする。

### 7.1 追加で確認した資料

確認日: 2026-10-11。下記はWeb解説の必要箇所を確認した範囲であり、全装備の文献調査、性能の実測、規格PDF・追補本文の全条項確認は行っていない。

| ID・資料 | 今回の確認 | 設計への反映と限界 |
| --- | --- | --- |
| W01 Royal Armouries『[Explore the collection](https://royalarmouries.org/collection)』 | Collection highlightsの日本甲冑、戈、狩猟槍、伝クロムウェル所用剣の年代・地域・材料・来歴の解説を本文確認。公開・更新日は未確認 | 所蔵品の説明には年代・産地の推定や伝承がある。収蔵解説の断定度を保ち、個体から全同型品の性能へ一般化しない。戈の個体ページは抽出結果に資料本文がなく、詳細記録は未確認 |
| W02 陸上自衛隊『[車両](https://www.mod.go.jp/gsdf/equipment/ve/)』 | 10式/90式戦車の概要、乗員・重量・寸法・最高速度・武装等の公開諸元を本文確認。公開・更新日は未確認 | 発行元の公開諸元として記録できる。測定条件や独立試験を確認したものではない。C4Iの説明から個別の判断・命中成功を保証せず、概数と値の表記を保つ |
| W03 NIJ『[Ballistic Resistance of Body Armor, Standard 0101.07](https://nij.ojp.gov/topics/equipment-and-technology/ballistic-resistance-body-armor-nij-standard-010107)』 | 公式Web解説の適用対象、規格の役割、関連規格、追補案内を本文確認。ページ表示日は2025-12-01 | 胴体用防弾装備の性能要件・試験方法という対象範囲と、追補を含めた確認の必要性を設計へ反映。規格PDF・追補本文、個別製品の適合記録は今回未確認 |
| W04 NIJ『[Specification for Ballistic Protection Levels and Associated Test Threats, Standard 0123.00](https://nij.ojp.gov/topics/equipment-and-technology/specification-nij-ballistic-protection-levels-and-associated-test-threats-nij-standard-012300)』 | 公式Web解説の目的、関連規格との役割分担、区分表、追補案内を本文確認。ページ表示日は2025-07-08 | 防護区分・試験脅威の定義と性能要件・試験方法を別文書で扱う。等級だけで製品適合や全条件の防護を認定しない。規格PDF・追補本文の全条項は未確認 |

これらのページ表示日を、規格の初版発行日・施行日と同一視しない。実行時には対象の版・追補・適合情報を再確認する。初期台帳は資料種別の入口であり、独立した歴史研究や公開試験報告等を個別の問いに応じて追加する。

### 7.2 探索記録と実装への反映

Web検索で `site.royalarmouries.org collections Japanese spear yari date`、`site.nij.ojp.gov 0101.07 ballistic resistance body armor 0123.00 threat levels standard`、`site.mod.go.jp gsdf 10式戦車 主要諸元 全備重量` 等を使い、上記の発行元ページへ進んだ。日本の槍の個体記録を確認できたという意味ではない。米空軍のF-16資料も探索したが、公式ページ本文は取得エラー、博物館ページは403で取得できなかったため、性能の支持根拠には採用しなかった。

設計書と実装プロンプトには、明示モード選択、W軸、武器・兵器用の参照資料、装備・数値の記録契約、モード外の軸の検査、武器・兵器/統合の使用例と評価ケースを追加した。この更新でも成果物は設計文書と実装指示であり、新スキルの実行評価は未実施である。

## 8. 追加要望: モードC「戦術・戦略・軍略」

モードCを `military` として追加し、`--mode C` と `--mode military` を同等の入力指定にする。モードAはmartial、Bはweapons、Dはintegratedとし、構造化記録には正規名を保存する。実装者はCodex、スキルの利用先はCodexとClaude Codeの両方である。

個人の技法の成立、装備の性能、組織的な軍事判断は根拠と分析単位が異なるため、モードCを独立させた。分析軸はM1 用語・思想・制度・史料、M2 目的・方法・資源・政治、M3 組織・指揮・情報・判断、M4 戦術・作戦・戦役の連接、M5 兵站・持続・負担、M6 結果・因果・代替解釈とする。

### 8.1 用語の設計判断

戦術、作戦・作戦術、戦略、大戦略は対象の目的と役割を整理するために区別するが、固定された人数・距離・期間で振り分けない。「軍略」は全資料で共通の第三階層とせず、兵法・用兵・軍事上の計略・戦争指導等のどの用法を問うかを特定する。これは本スキルの作業上の整理であり、全地域・全時代共通の定義を確認したという意味ではない。

判断時点の情報・目的・資源と、後世に知られた結果を分ける。局地的勝利、戦役上の成果、政治目的の達成を別に追い、勝敗だけで判断の合理性を認定しない。教範の規範、史料に記録された出来事、研究者の因果説明、反実仮想の仮定を分離する。

### 8.2 今回確認した資料

確認日: 2026-10-11。Web/PDF抽出で下記の箇所を確認した。個別戦役の全史料調査・実証や、全文献の網羅的レビューは行っていない。

| ID・資料 | 今回の確認 | 設計への反映と限界 |
| --- | --- | --- |
| S01 NATO『[AJP-01, Allied Joint Doctrine](https://www.gov.uk/government/publications/ajp-01-d-allied-joint-doctrine)』Edition F Version 1 + UK national elements | 公式紹介とリンクPDFの2.36〜2.43を部分本文確認。階層の記載は印刷pp.58〜59／PDFの76〜77ページ目。2022年版の案内で、Web入口の更新日は2025-04-01 | 戦術と戦略を作戦で結び、目的・方法・資源と結果評価を区別する入口。NATO/英国の当該版の規範として扱い、成功の実証や全時代共通の定義にしない。全244ページは未確認 |
| S02 齋藤大介（2026年3月）「[『作戦術』とは何か―戦略と戦術の媒介の意味の多義性―](https://www.nids.mod.go.jp/publication/security/pdf/2026/202603_02.pdf)」『安全保障戦略研究』6巻2号 | 要旨と冒頭の印刷pp.21〜23／PDFの1〜3ページ目を部分本文確認 | 作戦術の意味・定義の歴史的変化を論じる研究の入口。用語を版・組織・時代で追う設計へ反映する。引用された教範・全論文の再検証は未実施 |
| S03 Clausewitz『[On War, Book I Chapter 1](https://www.clausewitzstudies.org/readings/OnWar1873/BK1ch01.html)』J. J. Graham英訳（1873） | 訳版の注記と第11・23・24節の必要箇所を部分本文確認。原著は1832年刊。Web公開・更新日は未確認 | 政治目的と軍事手段の関係を読む古典の入口。ドイツ語原典・現代訳は未確認で、訳語や古典の理論を現在の統一的な規範・史実にしない |
| S04 防衛研究所『[戦史叢書](https://www.nids.mod.go.jp/military_archives/senshi_sousyo.html)』紹介 | 編纂と使用資料、オンライン公開の紹介本文を確認。Web公開・更新日は未確認 | 公刊戦史と、その基礎となった文書・口述等の史料を区別する入口。個別巻・戦役の記述内容は今回未確認で、紹介ページだけで戦史上の事実を確定しない |

### 8.3 探索記録と反映内容

Web検索では `site.gov.uk AJP-01 Allied Joint Doctrine levels tactical operational strategic`、`site.clausewitz.com On War book 1 chapter 1 policy political object`、`site.nids.mod.go.jp 戦略 戦術 作戦 軍事史 史料` を使い、出版元・紹介元の本文へ進んだ。AJP-01は公式ページの現行リンクからPDFを読み、版・該当節を追った。

設計とCodex向け実装プロンプトには、C別名の正規化、M1〜M6、軍事用参照文書、判断時点・情報の来歴・分析階層を持つmilitary_context、反実仮想の仮定と判定条件、軍事モードの調査・比較・検証例を追加した。評価仕様は起動/非起動約40件、出力28件とし、当時の判断と結果、教範と史実、兵站の欠落、因果と反実仮想、軸Cとの混同を確認する。これは評価ケースの実装要求であり、今回28件を実行して成功したという意味ではない。

この更新は設計・実装指示までであり、スキル本体の実装・インストール・CodexまたはClaude Codeでの実行評価は未実施である。

## 9. CodexとClaude Codeの両対応

2026-10-11に、両環境で使うための配置・呼出し・共通形式を公式文書で確認した。Codexの作業環境で実装するという指定に加え、Codex自体も完成スキルの利用先とする。

| 資料 | 実際に確認した範囲 | 設計への反映と確認限界 |
| --- | --- | --- |
| OpenAI [Codexのスキル文書](https://developers.openai.com/codex/skills/)（閲覧時は [Build skills](https://learn.chatgpt.com/docs/build-skills) へ転送） | 共通SKILL.md形式、明示/自動起動、ローカル読込場所、任意metadataの節 | name/description、`.agents/skills` と `~/.agents/skills`、プロンプト内の `$` によるスキル指定を採用。`agents/openai.yaml` は任意とする。文書の必要箇所の確認であり、新スキルの検出・実行や全UIの操作確認ではない |
| Anthropic [Claude Codeのスキル文書](https://code.claude.com/docs/en/skills) | スキルの配置、明示/自動起動、引数受渡し、リンクされたスキルの扱いの必要箇所 | `.claude/skills` と `~/.claude/skills`、`/martial-arts-research` を採用。共通本体に固有変数や動的展開を必須にしない。文書確認であり、新スキルの実行互換性の実測ではない |

共通のSKILL.md・references・scriptsを一つの原本で管理し、環境別に考証手順・記録契約・guardを分岐させない。READMEに両環境の配置・呼出し、予定ファイルとしてdocs/compatibility.mdとexamples/codex-invocation.md、両環境での同条件の評価を加えた。検索取得は各環境で利用可能なツールを使い、固有ツール名や外部サービスを必須にしない。

今回の変更は設計と実装指示である。Pythonの機械テスト、Codexでのスキル実行評価、Claude Codeでのスキル実行評価は別に記録する仕様とし、各環境の版・実行条件・結果・未実施項目を残す。一方の成功やCLIの存在を、両方での確認済み実績へ置き換えない。

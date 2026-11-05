# ツールによる監査と回答生成

Python 3.9以上、標準ライブラリのみ。既存のschema 2記録に任意項目を追加した。旧記録も読み込める。ルートのresearch_guard.pyから使用し、research_output.pyを単独実行しない。

```sh
python3 -B scripts/research_guard.py audit --record examples/records/calculation-audit.json
python3 -B scripts/research_guard.py render --record examples/records/calculation-audit.json
python3 -B scripts/research_guard.py render --record examples/records/local-review.json --snapshot examples/records/local-snapshot.json --root evals/fixtures
```

実際の配置先ではresearch_guard.pyを絶対パスで実行する。recordは`-`で標準入力可。標準出力はUTF-8のJSONのみ。renderのmarkdownは、その実行内で読み込んで検証した同じオブジェクトから作る。入力記録・原資料は書き換えない。出典・判定・条件・仮定・不足情報・代替解釈・限界を保持し、データ中のMarkdown／HTMLをエスケープする。危険なURLをリンク化しない。ローカルsnapshotは外部Webの真正性を証明しない。

## 状態と回答の使用

| 項目 | 意味 |
| --- | --- |
| record_integrity | 既存validateによる構造・参照・保存原文との整合性 |
| audit_checks[].status=checked | 明示された規則の範囲で通過。内容全体の正解ではない |
| error | 実行可能な計算の不一致・不正。終了1、markdown=null |
| review_required | 条件の違い、重複、書誌差、推論の飛躍等。原資料で要確認 |
| not_checked | 不明・未対応・未取得・検査対象外。合格扱いしない |
| audit_status=blocked | validate失敗。監査・回答生成を行わず終了1 |
| content_judgment | 常にnot_evaluated。内容の正しさは未判定 |

要確認・未検証だけなら終了0でmarkdownを返す。audit_statusはreview_requiredになる。SOURCE_TRUTHは必ずnot_checkedであり、内容全体の「合格」は出さない。入出力異常は終了2。出力JSONも16 MiBまで。

各チェックにcode・status・at・message・detailsを残す。record_sha256は、ソート済みの読込記録JSONに対するSHA-256で、資料の真正性や回答の正確性の証明ではない。

ツール実行結果の終了値・errors・audit_statusを読み、markdown=nullなら回答として使わない。入力ミスは原資料を確認して直し、同じコマンドで再検証する。根拠の削除・判定弱化・ハッシュ更新だけでエラーを隠さない。解消不能なら原因と不足情報を報告する。review_required／not_checkedを含む回答では、その表示を残す。生成後の自由な書き換えを検査済み出力とは称しない。

## 規則の範囲

- 根拠引用：evidence.quoteがローカルspanに存在すればQUOTE_MATCH。引用がなければQUOTE_UNCHECKED。原文との不一致は既存validateのQUOTE_MISMATCHで停止。意味上の支持は未判定。
- 数値：保存済み根拠引用と出典・箇所が対応する場合だけ原表記のトークンを照合。SOURCE_VALUE_TOKENは文字列の存在検査で、対象・属性の一致は保証しない。不在は表記差も考慮し要確認。
- 重複：正規化したDOI、HTTP(S) URL（fragment除外）、保存本文のhashが一致した出典をDUPLICATE_SOURCEとする。翻訳・転載・共通元の完全検出はしない。source_context.cited_sourcesに別出典IDを明記した場合はCOMMON_ORIGINとして独立性を確認する。
- 比較：compareの同一quantityについて条件不明／違い、値種別の混在を警告。条件の文字列一致は、型式・時点・方法の同等性の証明ではない。同装備・量・申告条件・値種別の対応数値が違えばVALUE_CONFLICTで要確認。
- 推論：inference_contextなしは未検証。因果申告は交絡・識別の確認、一般化は適用範囲の確認を要求する。予測・規範・公称・モデル・関連を根拠に実効性を申告した場合はINFERENCE_LEAP。自然文から分類を推定して合格を出さない。

## 計算・単位

formulaは入力name、数値、括弧、単項+/-、四則演算のみ。ASTを検査して計算し、eval・exec・関数呼出し・属性・累乗は使わない。式512文字／64ノードまで。nameは一意の識別子。数値はASCII十進表記40文字まで、指数の絶対値12まで。概数・範囲は未検証。

対応単位：1（明示的無次元）、kg、g、t、m、cm、mm、km、s、ms、min、h、m/s、km/h、N、J。nullは不明で無次元ではない。入力を基準単位へ換算し、質量・長さ・時間の次元を伴う有理数で計算して出力単位に戻す。加減算の次元不一致、出力単位の次元不一致、ゼロ除算、入力名重複はerror。入力名に対応しない式の語句は、旧記録の自由記述もあり得るため未検証とする。

単位換算は式自体に換算係数を重ねない。入力mass=40 t、formula=mass、出力単位kgなら計算値は40000 kg。formula=mass*1000は、その物理量をさらに1000倍する別の計算になる。既存の自由記述式はvalidate可能だが、未対応の式をauditで実行済みにしない。

丸めなしはroundingを「なし」「丸めなし」「none」とする。丸める場合はdecimal_places=0〜12、rounding=ROUND_HALF_UPを明示。半端値は符号に関係なく絶対値を大きくする側へ丸める。他の丸めは未対応。計算通過でも入力値の真偽・仮定・式の物理的妥当性は未検証。

## 外部書誌照合

既定は通信なし。ネットワーク利用が可能な環境で、外部書誌を確認するときだけaudit／renderに`--online`を付ける。DOIの識別子だけをCrossref公式HTTPS APIへ送り、原稿・質問・記録本文は送らない。1実行10種類のDOIまで、同じDOIは再利用、各リクエストtimeout=5秒、応答1 MiBまで。自動リダイレクトと任意URL取得はしない。Crossref必須ではなく、他の登録機関・DOIなし資料は別途確認する。

DOI応答との一致、題名・著者・登録された出版年との正規化一致を別々に記録する。略記・翻訳題名・出版年の違いで不一致になり得るため、書誌差はreview_required。取得URL・時刻・応答hashを保存する。更新・撤回関連の情報があれば原資料の関係と該当主張を確認し、論文全体を虚偽と判定しない。404、通信失敗、未登録、異常応答はnot_checked。

仕様の根拠：[Crossref公式REST API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/)。API登録情報・分類の申告・取得できた資料自体が誤っている可能性は、この検査で解決しない。

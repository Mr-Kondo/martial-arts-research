# Schema 2：記録とsnapshotの契約

本書を型・列挙値・必須／任意・nullの正本とする。Python 3.9以上の標準ライブラリだけを使う。旧JSON互換・移行はない。すべてのオブジェクトで未知キーを拒否する。特記した任意項目以外は必須。

共通型：`text`は空白だけでない文字列。`nullable text`はtextまたはnull（不明・非該当）。文字列配列は各要素がtext、空配列可。IDは`[A-Z][A-Z0-9_-]{0,63}`、finding IDは`F`+2桁以上の数字。同一種類のIDは一意、装備IDと軸はfinding内で一意。日付は実在する`YYYY-MM-DD`。数値を文字列で記録する欄に数値型を入れない。

## 最上位とcontext

必須：`schema_version`（整数2、bool不可）、`context`（下記）、`snapshot_id`（SHA-256の64桁小文字16進、なしはnull）、`sources`（配列、空可）、`findings`（1件以上）。

contextの必須：

| キー | 型・値 |
| --- | --- |
| mode | martial / weapons / military / integrated。A/B/C/Dは依頼解釈時だけ使用し、記録では拒否 |
| task | survey / compare / review |
| question, scope | text |
| conditions, assumptions | 文字列配列 |
| checked_on | 日付 |
| requested_extensions | fiction / stageのみの重複しない配列。通常は空配列を明記 |

任意`fiction_context`：`{"story_point": nullable text}`。fictionが指定された場合だけ使用可。時点不明はnull。一般調査に要求しない。

## sources

| 必須キー | 型・値 |
| --- | --- |
| id | ID |
| source_domain | real / fictional / design / unknown |
| source_type, publisher_role | text。資料種別と発行主体の関係を別に記述。固定の品質順位なし |
| modality | text / video / image / audio / dataset / mixed / unknownという文字列 |
| bibliography | 下記6キーのオブジェクト |
| access_status | full_text / abstract_only / search_only / unavailable / unverified |
| checked_on | 日付またはnull。unverified以外は日付必須 |
| method | nullable text。unverified以外はtext必須 |
| read_range, locator | nullable text。full_text/abstract_onlyは実際の範囲・箇所のtext必須 |
| limitations | 文字列配列 |
| file_id | snapshotのIDまたはnull。非nullならsnapshotが必要 |

bibliographyの必須6キー：`author`, `title`, `year`, `edition`, `url`, `doi`。すべてnullable text、yearも文字列。full_text/abstract_onlyではtitle必須。URL/DOIは所在の申告であり、形式・存在・本文との対応を支持条件としない。

任意`source_context`は以下のキーのみ許可。各値はnullable textまたは文字列配列。ただしsetting_statusは下記列挙文字列のみ。

- 研究：population, sample, task, comparison, resistance, metrics, results, generalization。
- 史料：creation_date, authorship, purpose, access_constraints, retrospective, language, translation, cited_sources, content_role。
- 作品：setting_status = confirmed / proposed / subjective / unknown。

必要な資料にだけsource_contextを使う。designは未採用の創作案。実在の設計図・特許・計画書はrealとし、意図と製造・配備・性能を分析上分ける。

## findingsとtarget

必須：`id`、`target`、`domain`（real / fictional / subjective）、`facts`（文字列配列）、`analysis`（text）、`alternative_interpretations`（文字列配列）、`assessments`（1件以上）、`limitations`（文字列配列）。任意：`revision`（nullable textの説明修正案）、`equipment_context`、`measurements`、`military_context`。fictional findingにはfiction拡張が必要。

targetは型によって必須キーを切り替える。余分なキーは不可。

- `{"type":"question","text":text}`：問い／分析命題。対象原稿やsnapshot不要。
- `{"type":"passage","span_id":ID,"quote":text}`：snapshot必須。quoteは指定範囲に連続して存在する逐語文字列。CRLF・空白を変更せず、省略記号を挿入しない。

## assessmentsとevidence

各assessmentの必須：axis、verdict、evidence（配列、空可）、conditions、additional_conditions、missing_information（各文字列配列）。軸はmartial=A〜E、weapons=W1〜W5、military=M1〜M6、integrated=その集合。stage明示時だけFを追加する。全軸を要求しない。

evidenceの必須：`source_id`（出典ID）、`relation`（supports / contradicts / reports / context）、`locator`（nullable text）、`span_id`（snapshotの範囲IDまたはnull）。ローカル出典のevidenceは同file_idのspan_idが必要。外部出典にはspan_idを付けない。contextのlocatorだけは不明でnull可。

| verdict | 機械検査する最低条件 |
| --- | --- |
| supported | full_textのsupportsとtextの箇所、conditionsが1件以上 |
| conditional | supportedと同じ根拠と条件に加えadditional_conditionsが1件以上 |
| contradicted | full_textのcontradictsとtextの箇所 |
| insufficient | missing_informationが1件以上 |
| abstract_reports | real資料のabstract_onlyのreportsとtextの箇所 |
| not_applicable | domain=subjectiveとanalysisで主観・比喩を位置づける場合のみ |

supports/contradictsはreal findingにreal資料、fictional findingにfictionalかつsetting_status=confirmed資料を要求する。design/unknown、人物の主観、提案は支持・反証に不可。reportsは抄録紹介用で、supports/contradictsへ流用不可。条件や分類の意味は機械判定しない。

## equipment_contextとmeasurements

W軸assessmentがあるfindingにはequipment_contextを1件以上要求。それ以外は任意。各装備の必須キー：id、name（text）、variant、region、era、configuration（nullable text）、status（historical / adopted / prototype / proposed / fictional / unknown）。fictional装備はfictional findingかつfiction拡張のみ。status申告は成立根拠ではない。

measurementsは数値考証時の任意配列。各項目の必須：

| キー | 型・値 |
| --- | --- |
| equipment_id | 同findingの装備ID |
| quantity, original_value | text。概数・範囲を元表記のまま残す |
| unit | nullable text。不明nullを無次元とはしない |
| value_kind | declared / tested / estimated / modeled |
| source_id | 出典IDまたはnull |
| source_locator, conditions | nullable text。未記載条件はnull |
| calculation | 下記オブジェクトまたはnull |

declared/testedには出典IDと箇所が必須。参照出典・箇所はevidenceにも記録する。現実数値にはreal資料が必要。未取得資料の値の実質的正しさは保証しない。estimated/modeledにはcalculationが必須。自己計算ならsource_id/locatorを両方nullにできる。

calculationの必須キー：`inputs`（1件以上の配列）、`formula`（text）、`rounding`（text、丸め不要も明記）、`limitations`（文字列配列1件以上）。inputsの各項目はname、value（text）、unit（nullable text）、source_id（IDまたはnull）、assumption（nullable text）が必須。入力には出典または仮定が必要。用いた出典は当該findingのevidenceにも参照し、real findingの出典付き計算入力にはreal資料を要求する。換算でも入力・式・丸めを記録する。

## military_context

M軸assessmentがあるfindingで必須。それ以外は任意。全キー必須：

| キー | 型・値 |
| --- | --- |
| analysis_kind | terminology / historical / decision / causal / counterfactual |
| analysis_levels | tactical / operational / strategic / grand_strategic / unspecifiedの一意で非空配列。unspecifiedは単独 |
| subject | text |
| period, geography | nullable text |
| actors, objectives | 文字列配列。不明・非該当は空 |
| decision_point, available_information, resources, constraints, observed_outcome | nullable text。不明・非該当はnull |
| knowledge_basis | contemporary / reconstructed / mixed / unknown |
| counterfactual_assumptions | 文字列配列。非該当は空 |

兵数・物資量等はresources/constraintsに原単位・時点・定義・不確実性を保って記録しmeasurementsは不要。来歴・各記述の根拠をevidence/source_contextへ対応させる。counterfactualでは変更・固定仮定1件以上と、finding全assessmentのconditional/insufficientを要求する。仮定だけでは原資料supportsを満たさない。既知事実・定義・矛盾は別finding。

## snapshotとCLI

```sh
python3 scripts/research_guard.py snapshot --root evals/fixtures --file T01=passage.txt --file R01=synthetic.txt --span Q01=T01:1:1 --span S01=R01:1:2 > /tmp/martial-snapshot.json
python3 scripts/research_guard.py validate --record examples/records/martial.json
python3 scripts/research_guard.py validate --record - < examples/records/military.json
```

ローカル記録は取得したsnapshot_idに対応させて`validate --record FILE --snapshot SNAPSHOT [--root 移動先]`を使う。保存済み記録のfixture例は[local-review.json](../examples/records/local-review.json)、snapshotは[local-snapshot.json](../examples/records/local-snapshot.json)。資料は削除せず保全する。

snapshotはschema_version、snapshot_id、root（絶対パス）、created_at（UTC・時差付きISO日時）、git、files、spansに加え、record_integrity=captured、errors=[]、warnings=[]、content_judgment=not_evaluatedを出力する。snapshot_idはそれ自身を除く全内容のソート済みJSONのSHA-256。filesの各項目はid/path/sha256/text/line_count。UTF-8をバイト読取りし、改行・空白を保存。spansはid/file_id/start_line/end_line/text/sha256で1始まりの両端包含。空ファイルは可、空範囲は不可。snapshotの範囲本文では空白だけの行もそのまま保全する。target.quoteのtextは空白だけでは不可。

gitはstate（available / unverified）、head（40〜64桁16進またはnull）、status（porcelain v1 -z文字列またはnull）、reason（nullable text）。Gitは読取りのみ。Gitなし・確認失敗はunverifiedでありcleanとはしない。root外の明示ファイルは絶対パス、root内は相対パス。移動先rootは相対ファイルにだけ適用し、末端symlinkは再照合時にも辿る。

validateでは保存本文・ハッシュ・行数・範囲・ID・未知キーを検査し、現在の選択資料を再読する。内容変更・削除・引用不一致は終了1、Gitだけの変化・Git未確認は警告。外部本文申告はSOURCE_CONTENT_UNCHECKED警告。

入力JSONと各UTF-8資料は16 MiB以下、選択資料合計と出力snapshot JSONも16 MiB以下、JSON入れ子は64以下。重複キー、NaN/Infinity、浮動小数オーバーフロー、非UTF-8、通常ファイル以外を拒否。非有限数を無視しない。

結果はJSONのrecord_integrity、errors、warnings、content_judgment。通常の標準出力はJSONのみ（--helpは使用法テキスト）。終了0=pass/captured、1=記録不整合・現在資料変更／削除、2=JSON／CLI入力異常・読取り不能・破損snapshot。予期される異常でtracebackを出さない。snapshotにstdinは不可、recordは`-`で可。

## 機械保証の境界

ハッシュは自己整合性であり真正性の証明ではない。意味・歴史・因果・当時情報の再構成・合理性・反実仮想結果・型式・性能・単位換算や試験条件の物理妥当性・資料の実質支持・設定採択・URL本文対応・最終回答の正確性を保証しない。content_judgmentは常にnot_evaluated。原資料変更後は再読・再検討する。

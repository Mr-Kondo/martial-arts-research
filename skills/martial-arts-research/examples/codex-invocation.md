# Codexの明示指定・自然言語

以下はプロンプトでありシェルコマンドではない。

```text
$martial-arts-research --mode A --task survey 無拍子の用法を調べてください。
$martial-arts-research --mode B --task compare 10式と90式の公開諸元を比較してください。
$martial-arts-research --mode C --task survey 軍略と戦略の用法を調べてください。
$martial-arts-research --mode D --task review --fiction 槍の技法、防具、部隊行動の関係を考証してください。
```

自然言語例：

```text
剣術の間合いと予測について、資料の根拠と条件を確認してください。
古代の戈の名称・年代・材料を収蔵資料から調べてください。
この戦役の目的、当時の情報、補給条件と結果を検証してください。
槍の重さ、操作者の技能、部隊行動の関係を比較してください。
```

採用mode/taskを冒頭で示す。/martial-arts-researchはClaude Codeの入口でありCodexのスラッシュコマンドとして仮定しない。[互換性](../docs/compatibility.md)。

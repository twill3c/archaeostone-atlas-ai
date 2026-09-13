# ArchaeoStone Atlas AI

日本の**黒曜石原産地**を、産総研 20 万分の 1 日本シームレス地質図 V2 と重ねて配る
研究・教育向けアトラス。あわせてヒスイの出土集成と全国の発掘調査報告書の分布を、
**根拠の階段(Evidence Ladder)ごとに分けて**同じ地図に載せる。

```
ArchaeoStone Atlas AI は研究・教育・探索支援ツールです。
AI によるモデル推定は学術的な確定判定ではありません。
開発・土地取引・文化財行政上の照会には、各自治体・所管機関の正式情報を利用してください。
```

## このアトラスが測ること

> 黒曜石の原産地の足もとの地質は、無作為に選んだ陸地点と比べて、どれだけ偏っているか。

原産地の一覧は考古・岩石学の文献から編み、地質図はそれとは独立に産総研が作っている。
だから両者を突き合わせても循環しない。**有意でなければ、有意でなかったと書く。**

## 構想書との差(実測 2026-09-08)

構想書は「石材の出土分布のアトラス」を求めていたが、**出土分布を配ることができない**。

| 源 | 到達 | 再配布 |
|---|---|---|
| 産総研 シームレス地質図 V2 | ✅ | ✅ 政府標準利用規約 2.0 |
| 国土地理院 タイル・地名検索 | ✅ | ✅ 公共データ利用規約 1.0 |
| 全国遺跡報告総覧 OAI-PMH | ✅ | ✅ 索引メタデータは自由利用 |
| 糸魚川市 ヒスイ集成表 | ✅ HTTP 200 / 230,912 B | ❌ 無断転載・複製・改変不可 |
| 明治大 COLS 黒曜石分析リスト | ✅ | ❌ 明示ライセンス無し |
| ジャパンサーチ 検索 API | ❌ robots.txt が当該 URL を Disallow | — |

**到達できることと、配れることは別の検査である。** 詳細と実測引用は
[`SPEC.md`](SPEC.md) §2 と、アプリの「出典と権利」の頁にある。

再配布できない源は、公開ビルドへ**一行も入らない**(fail-closed・検査 G-01)。
ヒスイについては取得器・解析器・検査だけをリポジトリに置き、公開するのは集計統計のみ。

## 使い方

```bash
# Python 側
python -m venv .venv && .venv/Scripts/python -m pip install -e ".[dev]"
python -m pytest
python harness/text_hygiene.py

# 公開データを作る
python -m pipeline.export_licenses

# Web 側
npm install
npm run typecheck
npm run build
npm run dev
```

公開データの一連(再配布可の源のみ):

```bash
python -m pipeline.acquisition.nabunken       # OAI-PMH 全件収穫(約 3,100 ページ・時間がかかる)
python -m pipeline.build_source_areas         # 黒曜石原産地(座標は地理院の地名検索から)
python -m pipeline.build_control_points       # 対照群(面積の重みで抽出した陸地点)
python -m pipeline.build_geology_stats        # 地質の偏りの検定
python -m pipeline.build_documents            # 文献の分布
python -m pipeline.build_model_cards          # AI ラボ(G-10 の判定と XRF の No-Go)
```

再配布できない源は手元で取得する(リポジトリには入っていない)。

```bash
python -m pipeline.acquisition.itoigawa
python -m pipeline.build_jade_aggregate       # 集計だけを書き出す
```

## AI ラボについて

分類器(地質から「原産地らしさ」を当てる)は、**学習した組み合わせが訓練側で選んだ
単一規則を超えるか**だけを問う。判定規則は SPEC §12 に**モデルを走らせる前に**書いた。
同じデータ・同じ計器から作った特徴なので、分類器が当たることは地質の偏り(H-01〜H-03)の
確認にはならない。

蛍光X線による原産地推定は、構想書 §34 の Go 基準を項目ごとに判定して **No-Go** とし、
モデルカードだけを出している。

## 構成

```
archaeostone/     … 源の登録簿・辞書・外部 API の取得器(純関数と I/O を分ける)
pipeline/         … 取得 → 正規化 → 検査 → 出荷形の書き出し
app/ components/ lib/  … Next.js(App Router)
config/           … sources.yaml / materials.yaml / periods.yaml
tests/            … pytest(フィクスチャは実測を落としたもの)
docs/             … 構想書(原本)
logs/loops/       … 構造化ループログ
```

## 文書

- [`SPEC.md`](SPEC.md) — 実測で上書きした仕様。§2 が構想書との差分
- [`TEST_SPEC.md`](TEST_SPEC.md) — 各ケースの期待値の出所と、対照の有無
- [`AGENTS.md`](AGENTS.md) — 共通規律(スキャフォールド管理領域)

## ライセンス

MIT。第三者データの権利は各源に従う([`app/licenses`](app/licenses) の頁を参照)。

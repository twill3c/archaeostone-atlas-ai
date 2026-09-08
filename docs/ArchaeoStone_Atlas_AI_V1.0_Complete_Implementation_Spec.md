# ArchaeoStone Atlas AI V1.0 完全実装仕様書

**文書バージョン:** 1.0.0  
**作成日:** 2026-09-07  
**対象:** 日本全国の遺跡から出土する黒曜石・ヒスイ等の考古石材を、公開情報から収集・正規化し、GIS・統計・機械学習・深層学習・グラフ分析によって可視化するWebアプリケーション  
**仮称:** ArchaeoStone Atlas AI  
**公開形態:** GitHub + Vercel を基本とするノーコスト/低コスト構成  
**実装方針:** 「観測・文献上の事実」と「AI推定・研究仮説」をUI・データモデル・APIの全層で分離する

---

## 0. 文書の目的

本仕様書は、ArchaeoStone Atlas AI V1.0 を実装・検証・公開するために必要な要件を一本化した実装仕様である。

対象は主として次の考古石材とする。

- 黒曜石（obsidian / volcanic glass）
- ヒスイ・硬玉（jadeite jade）
- サヌカイト
- チャート
- 碧玉
- メノウ
- 蛇紋岩
- 水晶・石英
- 安山岩・玄武岩等の石器石材

V1.0 の最優先対象は **黒曜石 + ヒスイ** とし、その他石材はスキーマとUIに受け皿を用意した上で段階的に追加する。

本仕様でいう「鉱物」はユーザー向けの便宜的表現であり、黒曜石は厳密には鉱物ではなく火山ガラスである。内部データモデルでは上位概念を **Archaeological Lithic Material（考古石材）** とする。

---

# 1. プロダクトコンセプト

## 1.1 目的

全国の考古資料について、次の連鎖を一つの画面で探索可能にする。

```text
原産地・地質環境
      ↓
石材・鉱物
      ↓
遺跡・出土地
      ↓
時代・型式
      ↓
器種・点数・出土状況
      ↓
文献・分析法
      ↓
流通・移動ネットワーク
      ↓
AI推定・異常検知・研究仮説
```

単なる遺跡検索サイトではなく、考古学・地質学・GIS・データサイエンスを横断する **研究探索型アトラス** とする。

## 1.2 主要ユーザー

- 考古学・文化財研究者
- 地質学・地球科学研究者
- 博物館・教育委員会職員
- 大学・高校の教育利用者
- 歴史地理・考古学に関心を持つ一般利用者
- データサイエンス教材として利用する開発者・学生

## 1.3 V1.0 の成功条件

V1.0 は最低限、次を満たしたとき公開可能とする。

1. 全国の黒曜石・ヒスイ関連地点を地図表示できる。
2. 時代・石材・器種・地域で絞り込める。
3. ヒスイ集成表を正規化して地図と統計に利用できる。
4. GSJ地質レイヤーを重ねられる。
5. 文献由来の事実とAI推定を明確に区別できる。
6. 原産地―遺跡ネットワークを表示できる。
7. 少なくとも1種類のPyTorchモデルを実データに対して利用できる。
8. モデル評価値・学習データ来歴・制約を表示できる。
9. ライセンス未確認データを再配布可能データとして公開しない。
10. GitHubからVercelへ継続デプロイできる。

---

# 2. V1.0 スコープ

## 2.1 必須機能

### Map

- 全国地図
- 遺跡ポイント
- 原産地ポイント/範囲
- 石材別レイヤー
- 地質レイヤー
- ヒートマップ
- クラスタリング
- 流通ネットワーク
- AI推定ネットワーク
- 時間スライダー
- レイヤーマネージャ

### Search / Filter

- 遺跡名
- 都道府県
- 市区町村
- 時代
- 細期
- 石材
- 器種
- 出土状況
- 原産地
- 分析方法
- データソース
- エビデンス種別
- AI信頼度

### Analysis

- 石材別出土件数
- 時代別件数
- 都道府県別件数
- 器種別件数
- 原産地別件数
- 原産地からの直線距離
- 時系列拡散可視化
- ネットワーク中心性
- 埋め込みクラスタ
- 異常候補

### AI

- 発掘報告書等からの考古石材情報抽出
- 化学組成が利用可能な場合の原産地分類
- グラフ埋め込み/リンクスコア
- 異常検知

## 2.2 V1.0 非対象

- AI結果を学術的「確定」と表示すること
- 写真だけから黒曜石原産地を断定すること
- 著作権が不明な遺物画像を大量学習・再配布すること
- Vercel上で大規模PyTorch学習を実行すること
- 地図上の推定経路を史実として表示すること
- 発掘調査地点情報を開発行為の法的照会用途に用いること

---

# 3. 公開データ取得仕様

## 3.1 データソース一覧

| ID | データソース | 用途 | 取得方法 | V1.0扱い |
|---|---|---|---|---|
| SRC-NABUNKEN | 全国遺跡報告総覧 | 報告書メタデータ・遺跡概要・文献探索 | OAI-PMH / 公開ページ | 中核 |
| SRC-ITOIGAWA | 糸魚川市 ヒスイ出土情報集成表 | 全国ヒスイ資料 | XLS / PDF | 中核 |
| SRC-GSJ | 20万分の1日本シームレス地質図V2 | 地質背景・地質属性 | Shapefile / Web API | 中核 |
| SRC-GSI | 地理院タイル | ベースマップ | XYZタイル | 中核 |
| SRC-JPSEARCH | ジャパンサーチ | 博物館・文化財メタデータ補完 | Web API | 補完 |
| SRC-MEIJI-COLS | 明治大学黒耀石研究センター | 黒曜石原産地研究参照 | Web参照 | 参照 |
| SRC-MANUAL | 研究者/開発者の確認済み資料 | XRFデータ等 | CSV/Parquet | 学習用 |

---

## 3.2 全国遺跡報告総覧

### 3.2.1 入口

```text
https://sitereports.nabunken.go.jp/ja
```

### 3.2.2 OAI-PMH

COAR/JPCOAR 系の国際リポジトリディレクトリで次の OAI-PMH Base URL が案内されている。

```text
https://sitereports.nabunken.go.jp/api/oai/request
```

実装時は最初に `Identify` を実行し、応答しない場合はCIを fail-closed とする。

例:

```text
?verb=Identify
?verb=ListMetadataFormats
?verb=ListRecords&metadataPrefix=oai_dc
```

> 注意: OAI-PMHは主にメタデータ取得用である。PDF本文の無制限なバルク取得機構として扱わない。

### 3.2.3 取得フィールド

可能な範囲で次を取り込む。

```text
identifier
title
creator
publisher
date
description
subject
coverage
language
rights
relation
source
```

全国遺跡報告総覧の登録項目として「時代」「主な遺構」「主な遺物」「特記事項」「要約」が存在するため、取得可能なメタデータ/公開ページからこれらを優先抽出する。

### 3.2.4 PDF本文利用方針

PDF本文は以下の条件を満たすものだけをNLP対象にする。

- 公開URLが明示されている
- 当該資料の権利・利用条件を確認した
- `source_license.ai_text_mining != "forbidden"`
- 取得頻度制御を実施
- robots.txt / サイトポリシー / 利用条件を遵守

V1.0ではサイト全体を無差別クロールしない。

### 3.2.5 キーワード辞書

```yaml
materials:
  obsidian: [黒曜石, 黒耀石, obsidian]
  jadeite: [ヒスイ, 翡翠, 硬玉, jadeite]
  sanukite: [サヌカイト, 讃岐岩]
  chert: [チャート]
  jasper: [碧玉]
  agate: [瑪瑙, メノウ]
  serpentinite: [蛇紋岩]
  quartz: [水晶, 石英]
methods:
  xrf: [蛍光X線, 蛍光Ｘ線, XRF, EDXRF, WDXRF]
  neutron: [中性子放射化, NAA]
  la_icp_ms: [LA-ICP-MS]
```

---

## 3.3 糸魚川市 ヒスイ出土情報集成表

### 3.3.1 公開ページ

```text
https://www.city.itoigawa.lg.jp/site/koukokan/2181.html
```

### 3.3.2 実データURL

```text
XLS:
https://www.city.itoigawa.lg.jp/uploaded/attachment/5566.xls

PDF:
https://www.city.itoigawa.lg.jp/uploaded/attachment/5567.pdf
```

### 3.3.3 原表の主要列

確認できる原表の列は以下を基本とする。

```text
遺跡名
所在市町村
時代
時期
種別
形状
点数
出土状況
所有者
文献
```

### 3.3.4 取得処理

```bash
python pipeline/acquisition/fetch_itoigawa_jade.py
```

出力:

```text
data/raw/itoigawa/jade_occurrences.xls
data/raw/itoigawa/jade_occurrences.pdf
data/raw/itoigawa/source_manifest.json
```

### 3.3.5 ライセンス制御

公開ダウンロード可能であることとオープンライセンスであることは同義ではない。

初期状態:

```json
{
  "redistribution": "review_required",
  "ai_training": "review_required",
  "derived_facts": "review_required",
  "license_spdx": null
}
```

明示ライセンスが確認できるまでは、原ファイルをリポジトリへコミットしない。CIではユーザー指定キャッシュまたは取得スクリプトで再取得する。

---

## 3.4 産総研 GSJ 20万分の1日本シームレス地質図V2

### 3.4.1 取得ページ

```text
https://gbank.gsj.jp/seamless/use.html
```

### 3.4.2 全国Shapefile

```text
https://gbank.gsj.jp/seamless/download/seamlessV2.zip
```

2026-09-07時点で取得ページには、全国一括ZIP 238MB、地質図更新日 2026-05-10 と表示されている。

### 3.4.3 Web API v1.3.1

ベース:

```text
https://gbank.gsj.jp/seamless/v2/api/1.3.1/
```

タイル:

```text
https://gbank.gsj.jp/seamless/v2/api/1.3.1/tiles/{z}/{y}/{x}.png
```

凡例JSON:

```text
https://gbank.gsj.jp/seamless/v2/api/1.3.1/legend.json
```

地点地質:

```text
https://gbank.gsj.jp/seamless/v2/api/1.3.1/legend.json?point={lat},{lon}
```

地質図画像:

```text
https://gbank.gsj.jp/seamless/v2/api/1.3.1/map.png?box={south},{west},{north},{east}&z={z}
```

### 3.4.4 保存フィールド

```text
symbol
formationAge_ja
formationAge_en
group_ja
group_en
lithology_ja
lithology_en
title
value
```

### 3.4.5 ライセンス

政府標準利用規約2.0準拠。出典表示により改変を含む二次利用が可能。アプリの Attribution パネルに常時表示する。

推奨表記:

```text
20万分の1日本シームレス地質図V2（©産総研地質調査総合センター）
```

---

## 3.5 国土地理院 地理院タイル

### 3.5.1 タイル例

```text
標準地図:
https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png

淡色地図:
https://cyberjapandata.gsi.go.jp/xyz/pale/{z}/{x}/{y}.png
```

### 3.5.2 方針

- Webアプリ上でリアルタイム表示
- 出典「国土地理院」または「地理院タイル」を表示
- タイル種別ごとの追加出典条件を確認
- バルクミラーリングしない

---

## 3.6 ジャパンサーチ

### 3.6.1 検索API

```text
https://jpsearch.go.jp/api/item/search/jps-cross
```

### 3.6.2 検索対象

- `type=archeology`
- `type=mineral`
- キーワード: 黒曜石 / 黒耀石 / ヒスイ / 翡翠 / 硬玉 / サヌカイト

### 3.6.3 権利ファセット

`rights` を必ず保存する。

例:

```text
cc0
pdm
ccby
ccbysa
ccbync
incr
uneval
others
```

### 3.6.4 利用ポリシー

- メタデータはデータベースごとの利用条件を優先
- 紹介ページに条件がなければCC0扱いとなるケースがあるが、レコード単位・DB単位で検証
- サムネイル・画像はメタデータと別に権利確認
- `image_reuse_allowed=false` をデフォルトとする

---

## 3.7 明治大学 黒耀石研究センター

### 3.7.1 参照ページ

```text
原産地推定概要:
https://www.meiji.ac.jp/cols/map01.html

日本の黒曜石産出地:
https://www.meiji.ac.jp/cols/map02.html
```

### 3.7.2 V1.0での使い方

- 原産地推定方法の科学的背景確認
- 原産地名称辞書の作成支援
- 研究文献リンク
- 画面上の説明コンテンツ

Webページの図表・画像・数値データを自動的にオープンデータ扱いしない。

### 3.7.3 XRF特徴量

研究参照として次の系列を扱える構造を用意する。

```text
Rb
Sr
Y
Zr
Mn
Fe
K
Nb
Ti
その他測定値
```

原産地分類モデルを公開するためには、再利用条件の明確なラベル付き実測データセットを別途確保すること。

---

# 4. ライセンス・来歴管理

## 4.1 原則

全レコードに `provenance` と `license` を必須とする。

## 4.2 LicenseManifest

```json
{
  "source_id": "SRC-GSJ",
  "source_title": "20万分の1日本シームレス地質図V2",
  "source_url": "https://gbank.gsj.jp/seamless/",
  "retrieved_at": "2026-09-07T00:00:00Z",
  "license_name": "Government of Japan Standard Terms of Use 2.0",
  "license_url": "https://gbank.gsj.jp/seamless/agreement.html",
  "attribution_required": true,
  "redistribution": true,
  "modification": true,
  "ai_training": "allowed_or_not_restricted",
  "image_reuse": "source_specific",
  "notes": "Attribution required"
}
```

## 4.3 権利状態

```ts
type RightsStatus =
  | "open"
  | "public_domain"
  | "attribution_required"
  | "noncommercial"
  | "restricted"
  | "review_required"
  | "unknown";
```

## 4.4 fail-closed

`unknown` または `review_required` の原データは、公開ビルドへ自動同梱しない。

---

# 5. データモデル

## 5.1 エンティティ

```text
Site                遺跡
Occurrence          出土事例
Artifact            遺物
Material            石材
SourceArea          原産地
ProvenanceAnalysis  原産地分析
Document            文献/報告書
Citation            引用箇所
Geology             地質
ModelPrediction     AI推定
NetworkEdge         ネットワーク辺
LicenseManifest     権利情報
```

## 5.2 Site

```json
{
  "site_id": "JP-SITE-000001",
  "name": "○○遺跡",
  "name_kana": null,
  "prefecture": "長野県",
  "municipality": "長和町",
  "latitude": 36.000000,
  "longitude": 138.000000,
  "coordinate_precision_m": 100,
  "coordinate_source": "published",
  "periods": ["JOMON_MIDDLE"],
  "source_refs": ["DOC-000001"]
}
```

## 5.3 Material

```json
{
  "material_id": "MAT-OBS",
  "canonical_name_ja": "黒曜石",
  "canonical_name_en": "Obsidian",
  "material_class": "volcanic_glass",
  "synonyms": ["黒耀石", "obsidian"]
}
```

## 5.4 Occurrence

```json
{
  "occurrence_id": "OCC-000001",
  "site_id": "JP-SITE-000001",
  "material_id": "MAT-OBS",
  "artifact_type": "ARROWHEAD",
  "artifact_label_original": "石鏃",
  "count": 24,
  "count_min": 24,
  "count_max": 24,
  "period_major": "JOMON",
  "period_phase": "MIDDLE",
  "context": "包含層",
  "source_document_id": "DOC-000001",
  "evidence_status": "published",
  "confidence": 1.0
}
```

## 5.5 ProvenanceAnalysis

```json
{
  "analysis_id": "PA-000001",
  "occurrence_id": "OCC-000001",
  "material_id": "MAT-OBS",
  "source_area_id": "OBS-WADA",
  "method": "XRF",
  "status": "published",
  "reported_probability": null,
  "model_probability": null,
  "citation_id": "CIT-000001"
}
```

`status` は次のいずれか。

```text
published
curated
ai_predicted
unknown
```

## 5.6 ModelPrediction

```json
{
  "prediction_id": "PRED-000001",
  "model_id": "obsidian-provenance-mlp-v1",
  "model_version": "1.0.0",
  "target_type": "source_area",
  "target_id": "OBS-WADA",
  "probability": 0.81,
  "calibrated": true,
  "input_schema_version": "1.0.0",
  "created_at": "2026-09-07T00:00:00Z",
  "label": "AI推定"
}
```

---

# 6. 時代正規化

## 6.1 大区分

```text
PALEOLITHIC
JOMON
YAYOI
KOFUN
ASUKA
NARA
HEIAN
MEDIEVAL
EARLY_MODERN
MODERN
UNKNOWN
```

## 6.2 縄文細期

```text
INCIPIENT
EARLY
EARLY_MIDDLE
MIDDLE
LATE
FINAL
```

原文は必ず `period_original` に保存し、正規化値を上書きしない。

## 6.3 時間スライダー

内部表現は概算年代レンジも保持する。

```json
{
  "period_code": "JOMON_MIDDLE",
  "label_ja": "縄文中期",
  "year_start_bp": 5500,
  "year_end_bp": 4500,
  "certainty": "reference_range"
}
```

年代幅は採用編年を `period_authority.json` で明示し、異なる編年を交換可能とする。

---

# 7. データ取得・ETL

## 7.1 パイプライン

```text
Acquire
  ↓
Raw Archive
  ↓
Parse
  ↓
Normalize
  ↓
Resolve Entities
  ↓
Geocode / Spatial Join
  ↓
Validate
  ↓
Feature Engineering
  ↓
ML/DL
  ↓
Static Export
  ↓
Vercel
```

## 7.2 ディレクトリ

```text
data/
  raw/
    nabunken/
    itoigawa/
    jpsearch/
    gsj/
  staging/
  normalized/
  curated/
  features/
  models/
  public/
```

## 7.3 Python実装

推奨:

```text
Python 3.12+
pandas
polars
pyarrow
requests
httpx
lxml
beautifulsoup4
openpyxl/xlrd（旧XLS読込用の実装に応じて選択）
geopandas
shapely
pyproj
rapidfuzz
pydantic
pandera
duckdb
scikit-learn
xgboost
pytorch
sentence-transformers / transformers
networkx
pyg (PyTorch Geometric)
onnx
onnxruntime
```

## 7.4 ETLコマンド

```bash
python -m pipeline.acquire --source itoigawa
python -m pipeline.acquire --source gsj
python -m pipeline.acquire --source jpsearch
python -m pipeline.acquire --source nabunken

python -m pipeline.normalize
python -m pipeline.geocode
python -m pipeline.validate
python -m pipeline.features
python -m pipeline.export
```

## 7.5 冪等性

各取得物はSHA-256を記録する。

```json
{
  "url": "...",
  "sha256": "...",
  "etag": "...",
  "last_modified": "...",
  "retrieved_at": "..."
}
```

同一hashなら再処理をスキップする。

---

# 8. 地理情報処理

## 8.1 座標系

保存:

```text
EPSG:4326
```

距離・面積分析時:

- JGD2011系の適切な平面直角座標系
- または測地線距離（GeographicLib / pyproj.Geod）

## 8.2 地理コード精度

```text
exact_site
site_centroid
municipality_centroid
prefecture_centroid
unknown
```

`municipality_centroid` 以下の精度しかないものは、地図上で異なる記号を使用する。

## 8.3 地質属性付加

遺跡/原産地の座標に対しGSJ APIを呼び、次を付与。

```text
geology_symbol
formation_age
geology_group
lithology
```

## 8.4 距離

原産地が確定している資料について:

```text
straight_distance_km
```

を計算する。

推定経路距離は別フィールド:

```text
estimated_route_distance_km
route_model_version
```

---

# 9. Layer Manager

## 9.1 レイヤー定義

```json
{
  "id": "obsidian_occurrences",
  "label": "黒曜石出土遺跡",
  "group": "materials",
  "type": "circle",
  "defaultVisible": true,
  "minZoom": 3,
  "maxZoom": 18,
  "evidenceClass": "observed"
}
```

## 9.2 標準レイヤー

```text
Base Map
Geology
Sites
Obsidian
Jade
Sanukite
Other Lithics
Source Areas
Published Provenance
AI Provenance
Heatmap
Clusters
Observed Network
Hypothesis Network
```

## 9.3 事実/推定の見分け

- 実証済み: 実線
- 文献整理/キュレーション: 細実線
- AI推定: 破線
- 仮説経路: 点線

色だけに依存せず、線種・アイコン・ラベルも変える。

---

# 10. フロントエンド

## 10.1 技術

```text
Next.js
TypeScript
React
MapLibre GL JS
deck.gl
Tailwind CSS
ECharts または Plotly
TanStack Query（API利用時）
Zustand（UI state）
Zod（runtime validation）
```

## 10.2 画面

```text
/
/map
/sites
/sites/[siteId]
/materials/[materialId]
/sources/[sourceAreaId]
/network
/timeline
/ai-lab
/data
/about
/methodology
/licenses
```

## 10.3 Map画面

左:

- 検索
- フィルタ
- 時代スライダー
- Layer Manager

中央:

- MapLibre地図

右:

- 選択レコード詳細
- Stone Passport
- 文献
- AI分析

## 10.4 Stone Passport

表示項目:

```text
遺跡
資料
時代
石材
器種
点数
出土状況
公開文献
原産地
分析法
直線距離
根拠の種別
AI推定確率
モデルバージョン
```

必ず以下のバッジを表示:

```text
[文献確認]
[キュレーション]
[AI推定]
[位置概算]
[権利確認済]
```

---

# 11. 静的配信用データ

## 11.1 公開ファイル

```text
public/data/sites.min.json
public/data/occurrences.min.json
public/data/source_areas.geojson
public/data/network_observed.json
public/data/network_predicted.json
public/data/stats.json
public/data/model_cards.json
public/data/licenses.json
```

大規模化したら:

```text
Parquet
PMTiles
FlatGeobuf
```

へ移行する。

## 11.2 目標サイズ

初期ロード:

```text
< 3 MB gzip
```

全国全件データはオンデマンド分割する。

---

# 12. NLP: 発掘報告書からの情報抽出

## 12.1 目的

自由記述から次のエンティティを抽出する。

```text
SITE
PERIOD
MATERIAL
ARTIFACT
COUNT
SOURCE_AREA
ANALYSIS_METHOD
CONTEXT
LOCATION
REFERENCE
```

## 12.2 二段階方式

### Stage A: ルール/辞書抽出

- 高精度キーワード
- 正規表現
- 文脈窓

### Stage B: Transformer

日本語モデルをfine-tuneし、NER/関係抽出を行う。

出力例:

```json
{
  "sentence": "蛍光X線分析の結果、石鏃18点中14点が神津島産黒曜石である可能性が高い。",
  "entities": [
    {"type":"METHOD","text":"蛍光X線分析"},
    {"type":"ARTIFACT","text":"石鏃"},
    {"type":"COUNT","text":"18点"},
    {"type":"SOURCE_AREA","text":"神津島"},
    {"type":"MATERIAL","text":"黒曜石"}
  ]
}
```

## 12.3 Human-in-the-loop

AI抽出結果は `pending_review` に入れる。

```text
pending_review
accepted
corrected
rejected
```

公開データの `evidence_status=published` へ自動昇格させない。

## 12.4 評価

NER:

```text
Precision
Recall
F1
```

関係抽出:

```text
micro-F1
macro-F1
```

V1.0公開基準:

```text
MATERIAL F1 >= 0.90
ARTIFACT F1 >= 0.85
SOURCE_AREA F1 >= 0.80
```

不足時はUIで「実験機能」とする。

---

# 13. 黒曜石原産地推定

## 13.1 入力

定量/半定量の元素組成または研究上利用される比率。

例:

```text
Rb
Sr
Y
Zr
Mn
Fe
K
Nb
Ti
```

## 13.2 モデル

必ず比較ベースラインを持つ。

### Classical

```text
Logistic Regression
SVM
Random Forest
XGBoost
```

### Deep Learning

```text
MLP
1D-CNN（十分なサンプルがある場合）
TabTransformer（十分なサンプルがある場合）
```

V1.0標準は **MLP + RandomForest/XGBoost比較**。

## 13.3 分割

原産地・採取地点由来のリークを避けるため、単純ランダム分割だけを使用しない。

推奨:

```text
GroupKFold(source_subsite)
Leave-One-Collection-Out
```

## 13.4 不均衡対策

- class weights
- stratified/grouped split
- macro-F1重視
- 少数クラスの統合可否を研究者レビュー

## 13.5 出力

```json
{
  "predictions": [
    {"source_area":"和田峠系", "probability":0.72},
    {"source_area":"神津島", "probability":0.15},
    {"source_area":"箱根", "probability":0.07}
  ],
  "uncertainty": 0.31,
  "ood_score": 0.08
}
```

## 13.6 Calibration

確率を表示する場合:

```text
Temperature Scaling
Isotonic Regression
```

等でcalibrationを評価する。

評価指標:

```text
ECE
Brier Score
```

## 13.7 OOD

未知原産地を既知クラスへ無理に割り当てない。

```text
known_source
unknown_or_out_of_distribution
```

を判定する拒否オプションを持つ。

## 13.8 V1.0の公開条件

実測ラベル付きデータが不足する場合、原産地分類器は次のどちらかとする。

1. `experimental` 表示で限定公開
2. UIを無効化し、モデルカードのみ表示

合成データで精度を装わない。

---

# 14. ヒスイ分析

## 14.1 基本分析

糸魚川市集成表から:

- 遺跡分布
- 時代分布
- 器種分布
- 点数分布
- 出土コンテキスト
- 北海道～九州の広域分布

を作成する。

## 14.2 製品形態

正規化例:

```text
MAGATAMA
TAISHU
TARUDAMA
MARUDAMA
KODAMA
PENDANT
RAW_MATERIAL
UNFINISHED
UNKNOWN
```

## 14.3 仮説分析

原石移動/完成品移動を示唆する特徴は表示しても、原表だけでは断定しない。

AI出力:

```text
"完成品流通仮説スコア"
```

のような表現は禁止。

代わりに:

```text
"器種構成類似度"
"時空間クラスタ"
"ネットワーク近接度"
```

のような観測可能指標を提示する。

---

# 15. グラフ分析 / GNN

## 15.1 グラフ

### Nodes

```text
SITE
SOURCE_AREA
MATERIAL
PERIOD_BUCKET
```

### Edges

```text
SOURCE_AREA -> SITE : published provenance
SITE <-> SITE        : shared source/material/period similarity
SITE -> MATERIAL     : occurrence
```

## 15.2 Edge attributes

```text
distance_km
same_period_score
artifact_similarity
material_similarity
published_count
confidence
```

## 15.3 Baseline

GNN前に必ず:

```text
NetworkX
PageRank
Betweenness Centrality
Community Detection
Node2Vec
```

を実装する。

## 15.4 PyTorch Geometric

候補:

```text
GraphSAGE
GAT
Graph AutoEncoder
```

V1.0推奨:

```text
GraphSAGE embedding
```

## 15.5 表示

AIが高いリンクスコアを出した未観測辺は:

```text
AI hypothesis edge
```

とする。

「交易路」「実際の移動経路」と断定しない。

---

# 16. 異常検知

## 16.1 目的

研究者が再確認する価値のある候補を提示する。

## 16.2 特徴量

```text
source_distance
regional_frequency
period_frequency
artifact_type_frequency
geology_similarity
network_degree
source_diversity
```

## 16.3 モデル

```text
Isolation Forest
Local Outlier Factor
AutoEncoder
```

V1.0は Isolation Forest をベースライン、PyTorch AutoEncoderを深層学習比較とする。

## 16.4 UI文言

許可:

```text
AI Interesting Find
周辺地域の同時期資料と比較して特徴が異なる候補です。
```

禁止:

```text
新発見
未知の交易拠点を発見
```

---

# 17. 推定移動ルート

## 17.1 V1.0

V1.0では直線エッジを基本とし、推定経路は実験レイヤーとする。

## 17.2 拡張候補

コストサーフェス:

```text
標高
傾斜
河川
海岸線
峠
既知遺跡
```

を組み合わせる。

アルゴリズム:

```text
Least Cost Path
A*
Dijkstra
```

## 17.3 表示規則

```text
published relationship = solid
inferred network       = dashed
least-cost hypothesis  = dotted
```

---

# 18. モデルカード

各モデルについて `model_cards.json` を公開する。

```json
{
  "model_id": "obsidian-provenance-mlp-v1",
  "task": "provenance classification",
  "framework": "PyTorch",
  "training_data": ["DATASET-ID"],
  "features": ["Rb", "Sr", "Y", "Zr", "Mn", "Fe", "K"],
  "classes": ["..."],
  "metrics": {
    "macro_f1": 0.0,
    "balanced_accuracy": 0.0,
    "ece": 0.0
  },
  "limitations": [
    "結果は研究仮説であり確定的な原産地同定ではない"
  ]
}
```

---

# 19. API / Backend

## 19.1 原則

V1.0は静的配信優先。

- 重い推論をVercel Functionで実行しない
- ETL/学習結果を事前計算
- ブラウザ推論が必要な小型モデルのみONNX Runtime Webを検討

## 19.2 Route Handler

必要最小限:

```text
GET /api/search?q=
GET /api/site/{id}
GET /api/stats
GET /api/model-card/{id}
```

静的JSONで代替可能なら静的JSONを優先する。

---

# 20. Vercel / GitHub 構成

## 20.1 原則

```text
GitHub = source + CI + generated public data
Vercel = frontend + static assets
```

## 20.2 学習処理

Vercelでは行わない。

実行場所:

```text
Local workstation
GitHub Actions（軽量処理）
Google Colab free（手動学習）
Kaggle Notebook free（手動学習）
```

## 20.3 モデル公開

```text
models/*.onnx
models/*.json
```

巨大weightはGitHub通常Gitへ入れない。

---

# 21. リポジトリ構成

```text
archaeostone-atlas-ai/
├─ app/
│  ├─ map/
│  ├─ sites/
│  ├─ materials/
│  ├─ sources/
│  ├─ network/
│  ├─ timeline/
│  ├─ ai-lab/
│  ├─ methodology/
│  └─ licenses/
├─ components/
│  ├─ map/
│  ├─ charts/
│  ├─ filters/
│  └─ evidence/
├─ lib/
│  ├─ data/
│  ├─ map/
│  ├─ model/
│  └─ schema/
├─ public/
│  ├─ data/
│  └─ models/
├─ pipeline/
│  ├─ acquisition/
│  ├─ parsing/
│  ├─ normalization/
│  ├─ geocoding/
│  ├─ validation/
│  ├─ features/
│  └─ export/
├─ ml/
│  ├─ nlp/
│  ├─ provenance/
│  ├─ anomaly/
│  └─ gnn/
├─ schemas/
├─ config/
├─ tests/
├─ docs/
├─ .github/workflows/
├─ package.json
├─ pyproject.toml
└─ README.md
```

---

# 22. 設定ファイル

## 22.1 materials.yaml

```yaml
obsidian:
  label_ja: 黒曜石
  class: volcanic_glass
  synonyms: [黒耀石, obsidian]

jadeite:
  label_ja: ヒスイ
  class: mineral
  synonyms: [翡翠, 硬玉, jadeite]
```

## 22.2 sources.yaml

```yaml
SRC-GSJ:
  enabled: true
  redistribution: true
  attribution: true

SRC-ITOIGAWA:
  enabled: true
  redistribution: review_required
  raw_commit: false
```

## 22.3 layers.json

```json
[
  {
    "id":"obsidian",
    "label":"黒曜石",
    "group":"materials",
    "source":"occurrences",
    "visible":true
  },
  {
    "id":"jade",
    "label":"ヒスイ",
    "group":"materials",
    "source":"occurrences",
    "visible":true
  },
  {
    "id":"gsj-geology",
    "label":"地質",
    "group":"geology",
    "source":"gsj-tile",
    "visible":false
  }
]
```

---

# 23. DuckDB スキーマ

```sql
CREATE TABLE sites (
  site_id VARCHAR PRIMARY KEY,
  name VARCHAR NOT NULL,
  prefecture VARCHAR,
  municipality VARCHAR,
  latitude DOUBLE,
  longitude DOUBLE,
  coordinate_precision_m DOUBLE,
  coordinate_source VARCHAR
);

CREATE TABLE occurrences (
  occurrence_id VARCHAR PRIMARY KEY,
  site_id VARCHAR,
  material_id VARCHAR,
  artifact_type VARCHAR,
  count_min INTEGER,
  count_max INTEGER,
  period_major VARCHAR,
  period_phase VARCHAR,
  evidence_status VARCHAR,
  source_document_id VARCHAR
);

CREATE TABLE source_areas (
  source_area_id VARCHAR PRIMARY KEY,
  material_id VARCHAR,
  name VARCHAR,
  latitude DOUBLE,
  longitude DOUBLE,
  geometry_wkt VARCHAR,
  evidence_status VARCHAR
);

CREATE TABLE provenance_analysis (
  analysis_id VARCHAR PRIMARY KEY,
  occurrence_id VARCHAR,
  source_area_id VARCHAR,
  method VARCHAR,
  status VARCHAR,
  confidence DOUBLE,
  model_id VARCHAR
);
```

---

# 24. データ品質

## 24.1 自動チェック

- lat: -90～90
- lon: -180～180
- 都道府県と座標の概略整合
- `count_min <= count_max`
- material_id が辞書に存在
- source_id がManifestに存在
- AI推定に model_id が存在
- `published` に citation_id が存在
- rights=unknown の原画像が public/ にない

## 24.2 重複統合

キー候補:

```text
normalized_site_name
municipality
period
source_document
```

RapidFuzzで候補を出し、一定閾値以上は人手レビュー。

---

# 25. テスト

## 25.1 Python

```text
pytest
pandera validation
snapshot tests
```

## 25.2 Frontend

```text
Vitest
React Testing Library
Playwright
```

## 25.3 必須E2E

1. `/map` が表示できる
2. 黒曜石レイヤーON/OFF
3. ヒスイレイヤーON/OFF
4. 時代フィルタ
5. 遺跡クリック→Stone Passport
6. 文献リンク表示
7. AI推定が破線/AIバッジ表示
8. ライセンス表示
9. モバイル表示

---

# 26. CI/CD

## 26.1 GitHub Actions

```yaml
name: ci
on:
  push:
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm test
      - run: npm run build
      - run: python -m pytest
```

実際のバージョンは導入時の安定版をlockfileで固定する。

## 26.2 Data refresh

ライセンスと負荷を考慮し、V1.0ではデフォルトを手動実行とする。

```text
workflow_dispatch
```

GSJ・ジャパンサーチ等、利用条件が明確なソースのみ定期更新を許可する。

---

# 27. UX / アクセシビリティ

- 色覚に依存しない線種
- キーボード操作
- WCAG 2.2 AAを目標
- 地図に代替の一覧ビュー
- Tooltipだけに情報を閉じ込めない
- 日本語UIを標準、英語フィールドを準備
- AI推定には常に説明文とモデルカードリンク

---

# 28. セキュリティ

- APIキーをクライアントに置かない
- 外部URLはallowlist
- HTML抽出結果をsanitize
- PDF/ファイル名を直接パス結合しない
- CIでdependency audit
- 任意URL取得APIを実装しない（SSRF防止）

---

# 29. パフォーマンス

## 29.1 Map

- 低ズーム: cluster / heatmap
- 中ズーム: deck.gl aggregation
- 高ズーム: individual points

## 29.2 検索

小規模時:

```text
Fuse.js / client index
```

大規模時:

```text
prebuilt inverted index
DuckDB-WASM
```

## 29.3 目標

```text
LCP < 2.5s（一般的なブロードバンド）
Map first interaction < 3s
フィルタ応答 < 150ms（キャッシュ後）
```

---

# 30. Analytics / Observability

個人情報を収集しない設計を優先。

収集する場合は:

```text
page_view
layer_toggle
filter_usage
```

程度の匿名イベントに限定し、プライバシーポリシーを表示する。

---

# 31. 研究倫理・表示ルール

## 31.1 Evidence Ladder

```text
Level A: Published Measurement
Level B: Published Description
Level C: Curated Interpretation
Level D: AI Prediction
Level E: Exploratory Hypothesis
```

全画面でこの階層を参照可能にする。

## 31.2 禁止表現

AI推定に対し:

- 「確定」
- 「証明」
- 「新発見」
- 「交易路である」

を使用しない。

推奨:

- 「モデル推定」
- 「類似度」
- 「候補」
- 「仮説レイヤー」

---

# 32. V1.0 実装フェーズ

## Phase 0 — 法務・ソース検証

- 利用規約一覧
- OAI-PMH疎通確認
- XLS取得確認
- GSJ取得確認
- GSI Attribution確認
- Japan Search rights確認

## Phase 1 — データ基盤

- Material辞書
- Period辞書
- Site/Occurrenceスキーマ
- DuckDB
- ヒスイETL
- GSJ spatial join

## Phase 2 — Map MVP

- MapLibre
- Layer Manager
- ヒスイ
- 黒曜石シードデータ
- 地質
- Timeline

## Phase 3 — 全国遺跡情報

- OAI-PMH
- 文献メタデータ
- キーワード抽出
- Site entity resolution

## Phase 4 — ML

- anomaly baseline
- provenance baseline
- PyTorch MLP
- model card

## Phase 5 — GNN

- graph export
- Node2Vec
- GraphSAGE
- hypothesis edges

## Phase 6 — 公開品質

- E2E
- accessibility
- attribution
- license page
- performance
- Vercel deploy

---

# 33. MVPデータ量の目安

公開初期目標:

```text
sites:             1,000+
occurrences:       2,000+
jade occurrences: 糸魚川集成表の正規化可能範囲
obsidian records:  公開条件確認済み資料から段階追加
source areas:      20+
documents:         500+
```

数は品質より優先しない。

---

# 34. 原産地分類モデルのGo/No-Go基準

## Go

- 実データ
- 再利用条件確認済み
- 5原産地群以上
- 各主要クラスに十分なサンプル
- Group split評価
- macro-F1公開
- calibration公開
- OOD拒否を実装

## No-Go

- ラベルが文献ごとに不整合
- 測定装置差の補正なし
- 学習/テストに同一原石由来サンプルが混入
- 合成データ中心
- 権利状態不明

No-Goの場合でも、アプリ本体は統計・地図・NLP・グラフ分析で公開できる。

---

# 35. README に必ず書く事項

```text
ArchaeoStone Atlas AI は研究・教育・探索支援ツールです。
AIによる原産地・ネットワーク推定は学術的な確定判定ではありません。
開発・土地取引・文化財行政上の照会には各自治体・所管機関の正式情報を利用してください。
```

---

# 36. Attribution パネル

画面フッターまたは `About data` から常時アクセス可能にする。

最低限:

```text
地理院タイル / 国土地理院
20万分の1日本シームレス地質図V2 / 産総研地質調査総合センター
全国遺跡報告総覧 / 奈良文化財研究所
ヒスイ出土情報集成表 / 糸魚川市
ジャパンサーチ / 各連携機関
```

個別レコードには一次ソースへのリンクを付与する。

---

# 37. 実装開始時のタスク一覧

```text
[ ] repo作成
[ ] Next.js初期化
[ ] Python package初期化
[ ] schemas定義
[ ] materials.yaml
[ ] periods.yaml
[ ] sources.yaml
[ ] license manifest
[ ] Itoigawa fetcher
[ ] Itoigawa parser
[ ] municipality normalizer
[ ] geocoder cache
[ ] GSJ client
[ ] Japan Search client
[ ] Nabunken OAI harvester
[ ] MapLibre basic map
[ ] Layer Manager
[ ] filter store
[ ] Stone Passport
[ ] stats builder
[ ] network builder
[ ] anomaly baseline
[ ] PyTorch MLP skeleton
[ ] model card generator
[ ] E2E tests
[ ] Vercel deploy
```

---

# 38. 受け入れ基準（Acceptance Criteria）

## AC-01 Map

Given アプリを開く  
When 黒曜石レイヤーを選択する  
Then 黒曜石出土地点のみ表示される。

## AC-02 Jade

Given ヒスイレイヤーを選択する  
When 時代を縄文後期に絞る  
Then 対象期間のレコードのみ表示される。

## AC-03 Geology

Given 地質レイヤーをONにする  
Then GSJ地質図が重畳表示され、出典が表示される。

## AC-04 Evidence

Given AI推定原産地が存在する  
Then `AI推定` バッジとモデルバージョンが表示され、publishedと同一表現にならない。

## AC-05 Rights

Given `rights=unknown` の画像が存在する  
Then ビルド成果物に画像本体が含まれない。

## AC-06 Reproducibility

Given 同一raw inputと同一config  
When ETLを2回実行する  
Then normalized output hashが一致する。

---

# 39. V1.1以降の拡張

- サヌカイト専用分析
- チャート産地・地質帯
- 3D地形
- 河川/海岸線ルート
- PMTiles
- DuckDB-WASM
- IIIF対応画像（権利確認済みのみ）
- 文献RAG
- 多言語UI
- 学術DOI連携
- 研究者向けCSV/GeoJSON export
- アノテーションUI
- 研究者レビューの署名付き履歴

---

# 40. 推奨実装順序（最短公開ルート）

最短で価値が出る順序は次の通り。

```text
1. ヒスイ集成表ETL
2. MapLibre全国地図
3. 時間スライダー
4. GSJ地質重畳
5. 全国遺跡報告総覧メタデータ
6. 黒曜石出土地点
7. 原産地辞書
8. 既知原産地ネットワーク
9. NLP抽出
10. 異常検知
11. PyTorch原産地分類
12. GNN仮説レイヤー
```

この順序なら、深層学習用データがまだ不足していても、地図アプリ自体は早期に公開できる。

---

# 41. 参照URL（2026-09-07確認）

## 全国遺跡報告総覧

```text
https://sitereports.nabunken.go.jp/ja
https://sitereports.nabunken.go.jp/api/oai/request
```

## 糸魚川市 ヒスイ文化研究所

```text
https://www.city.itoigawa.lg.jp/site/koukokan/2181.html
https://www.city.itoigawa.lg.jp/uploaded/attachment/5566.xls
https://www.city.itoigawa.lg.jp/uploaded/attachment/5567.pdf
```

## GSJ

```text
https://gbank.gsj.jp/seamless/use.html
https://gbank.gsj.jp/seamless/agreement.html
https://gbank.gsj.jp/seamless/download/seamlessV2.zip
https://gbank.gsj.jp/seamless/v2/api/1.3.1/
https://gbank.gsj.jp/seamless/v2/api/1.3.1/legend.json
```

## 地理院タイル

```text
https://maps.gsi.go.jp/development/
https://www.gsi.go.jp/kikakuchousei/kikakuchousei40182.html
https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png
```

## ジャパンサーチ

```text
https://jpsearch.go.jp/api/item/search/jps-cross
https://jpsearch.go.jp/static/developer/webapi/ch3_search_api.html
https://jpsearch.go.jp/policy
https://jpsearch.go.jp/cooperation/faq
```

## 明治大学 黒耀石研究センター

```text
https://www.meiji.ac.jp/cols/map01.html
https://www.meiji.ac.jp/cols/map02.html
```

---

# 42. 最終アーキテクチャ

```text
┌─────────────────────────────────────────────┐
│             Public Data Sources             │
│ Nabunken / Itoigawa / GSJ / GSI / JPSearch │
└────────────────────┬────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│              Python Acquisition             │
│ fetch / checksum / rights manifest          │
└────────────────────┬────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│                 ETL / GIS                   │
│ normalize / entity resolve / spatial join   │
│ DuckDB / Parquet / GeoJSON                  │
└────────────────────┬────────────────────────┘
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
┌──────────────────┐   ┌──────────────────────┐
│ Classical ML     │   │ PyTorch              │
│ RF/XGB/IF/Node2V │   │ MLP/AE/GraphSAGE/NLP │
└────────┬─────────┘   └──────────┬───────────┘
         │                        │
         └──────────┬─────────────┘
                    ▼
┌─────────────────────────────────────────────┐
│       Precomputed Public Data / ONNX        │
│ JSON / GeoJSON / Parquet / model cards      │
└────────────────────┬────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│            Next.js + MapLibre               │
│ Layer Manager / Timeline / Stone Passport   │
│ Observed vs AI Hypothesis                    │
└────────────────────┬────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│                   Vercel                    │
│         static-first / no heavy ML          │
└─────────────────────────────────────────────┘
```

---

# 43. 結論

ArchaeoStone Atlas AI V1.0 は、**「全国の考古石材の出土・原産地・地質・時代・文献を統合し、AIで探索可能にするアトラス」**として実装する。

V1.0の中核は以下の4本柱とする。

1. **全国分布GIS** — 黒曜石・ヒスイを中心とする出土地点と原産地
2. **時間可視化** — 旧石器～縄文～弥生～古墳の変化
3. **根拠付きAI** — NLP、原産地分類、異常検知、GNN
4. **Evidence First** — 文献事実とAI仮説を完全に分離

実装上最も重要なのは、AIの高度さよりも **データ来歴・権利・出典・確度を失わないこと** である。これを守ることで、一般向けの魅力的な地図アプリでありながら、研究・教育用途にも耐えうる拡張可能な基盤となる。

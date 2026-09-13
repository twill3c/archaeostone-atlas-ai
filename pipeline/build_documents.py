"""収穫した OAI レコードを集計して出荷形にする(F-04)。

出すのは**文献の分布**である。石材の分布ではない ——
報告書の題名は遺跡名と叢書名なので、石材の語をほとんど含まない(SPEC §2.3)。
その「含まない」ことも、全件を走査して数で示す。

    python -m pipeline.build_documents
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib

from archaeostone.dictionaries import load_materials
from archaeostone.oai import RecordShape, SetSpecKind, classify_set_spec, parse_page
from pipeline.paths import display_path

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw" / "nabunken"
OUTPUT = REPO_ROOT / "public" / "data" / "documents.json"

#: 都道府県コード → 名称。setSpec の 2 桁がこれに対応する。
PREFECTURES = {
    "01": "北海道", "02": "青森県", "03": "岩手県", "04": "宮城県", "05": "秋田県",
    "06": "山形県", "07": "福島県", "08": "茨城県", "09": "栃木県", "10": "群馬県",
    "11": "埼玉県", "12": "千葉県", "13": "東京都", "14": "神奈川県", "15": "新潟県",
    "16": "富山県", "17": "石川県", "18": "福井県", "19": "山梨県", "20": "長野県",
    "21": "岐阜県", "22": "静岡県", "23": "愛知県", "24": "三重県", "25": "滋賀県",
    "26": "京都府", "27": "大阪府", "28": "兵庫県", "29": "奈良県", "30": "和歌山県",
    "31": "鳥取県", "32": "島根県", "33": "岡山県", "34": "広島県", "35": "山口県",
    "36": "徳島県", "37": "香川県", "38": "愛媛県", "39": "高知県", "40": "福岡県",
    "41": "佐賀県", "42": "長崎県", "43": "熊本県", "44": "大分県", "45": "宮崎県",
    "46": "鹿児島県", "47": "沖縄県",
}

#: 分析方法をあらわす語。石材の語と同じく、題名にどれだけ出るかを測る。
METHOD_TERMS = ["蛍光X線", "蛍光Ｘ線", "原産地", "産地推定", "中性子放射化", "ICP-MS"]


def material_terms() -> dict[str, list[str]]:
    """材質辞書から検索語を作る。**画面用の加工を経ていない元データから導く**(HC-068)。"""
    out: dict[str, list[str]] = {}
    for key, entry in load_materials().items():
        out[key] = [entry["label_ja"], *entry.get("synonyms", [])]
    return out


def build() -> dict:
    pages = sorted(RAW_DIR.glob("page_*.xml"))
    if not pages:
        raise RuntimeError(
            f"{RAW_DIR} に収穫物が無い。先に "
            "`python -m pipeline.acquisition.nabunken` を実行すること"
        )

    terms = material_terms()
    shapes: collections.Counter[str] = collections.Counter()
    set_kinds: collections.Counter[str] = collections.Counter()
    by_prefecture: collections.Counter[str] = collections.Counter()
    by_municipality: collections.Counter[str] = collections.Counter()
    material_hits: collections.Counter[str] = collections.Counter()
    method_hits: collections.Counter[str] = collections.Counter()
    material_examples: dict[str, list[dict]] = collections.defaultdict(list)
    total = 0
    without_set_spec = 0

    for index, page in enumerate(pages, 1):
        for record in parse_page(page.read_bytes()):
            total += 1
            shapes[record.shape.value] += 1
            if not record.set_specs:
                without_set_spec += 1
            for spec in record.set_specs:
                set_kinds[classify_set_spec(spec).value] += 1
            for code in set(record.prefecture_codes):
                by_prefecture[code] += 1
            for code in set(record.municipality_codes):
                by_municipality[code] += 1

            if record.shape is RecordShape.NO_METADATA:
                continue

            blob = record.title_blob
            for material, words in terms.items():
                if any(word in blob for word in words):
                    material_hits[material] += 1
                    if len(material_examples[material]) < 8:
                        material_examples[material].append(
                            {
                                "title": record.titles[0] if record.titles else "",
                                "url": record.landing_url,
                                "prefecture_codes": list(record.prefecture_codes),
                            }
                        )
            for term in METHOD_TERMS:
                if term in blob:
                    method_hits[term] += 1

        if index % 500 == 0:
            print(f"  {index}/{len(pages)} ページ({total:,} 件)", flush=True)

    with_metadata = total - shapes.get(RecordShape.NO_METADATA.value, 0)

    return {
        "generated_by": "pipeline.build_documents",
        "source_id": "SRC-NABUNKEN",
        "corpus": {
            "pages_parsed": len(pages),
            "records": total,
            "records_with_metadata": with_metadata,
            "record_shapes": dict(shapes),
            "records_without_set_spec": without_set_spec,
            "set_spec_kinds": dict(set_kinds),
        },
        "material_mentions": {
            "scope": "報告書の題名(dc:title / junii2:title / jtitle)のみ。本文は扱わない",
            "denominator": with_metadata,
            "counts": {
                material: {
                    "hits": material_hits.get(material, 0),
                    "rate": material_hits.get(material, 0) / with_metadata
                    if with_metadata
                    else None,
                    "terms": words,
                    "examples": material_examples.get(material, []),
                }
                for material, words in sorted(terms.items())
            },
            "method_terms": {
                term: method_hits.get(term, 0) for term in METHOD_TERMS
            },
            "note": (
                "この数は「石材が出土した遺跡の数」ではない。"
                "**報告書の題名にその語が現れた件数**である。"
                "題名は遺跡名と叢書名が主なので、石材はほとんど現れない。"
            ),
        },
        "by_prefecture": [
            {
                "code": code,
                "name": PREFECTURES.get(code, f"(不明 {code})"),
                "documents": count,
            }
            for code, count in sorted(by_prefecture.items())
        ],
        "municipality_count": len(by_municipality),
        "top_municipalities": [
            {"code": code, "documents": count}
            for code, count in by_municipality.most_common(20)
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="OAI レコードを集計する")
    parser.add_argument("--out", type=pathlib.Path, default=OUTPUT)
    args = parser.parse_args()

    payload = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )

    corpus = payload["corpus"]
    print(f"\n{display_path(args.out)} を書き出した")
    print(f"  レコード {corpus['records']:,} 件 / 形 {corpus['record_shapes']}")
    print(f"  setSpec の種別 {corpus['set_spec_kinds']}")
    print(f"  都道府県 {len(payload['by_prefecture'])} / 市区町村 {payload['municipality_count']}")
    print("\n  題名に現れた石材の語(分母 = メタデータのあるレコード):")
    for material, entry in payload["material_mentions"]["counts"].items():
        rate = entry["rate"]
        print(
            f"    {material:<14} {entry['hits']:>6,} 件"
            + (f" ({rate * 100:.4f}%)" if rate is not None else "")
        )
    print("\n  分析方法の語:")
    for term, hits in payload["material_mentions"]["method_terms"].items():
        print(f"    {term:<14} {hits:>6,} 件")


if __name__ == "__main__":
    main()

"""原産地のある市町村の報告書を出荷形にする(F-07)。

Stone Passport の「当該市町村の文献」。**石材の出土を意味しない** —— 全国遺跡報告総覧の
索引で、原産地の市町村のコードを持つ報告書を数え、題名に黒曜石の語を含むものを添える。

    python -m pipeline.build_area_documents

市町村は原産地の座標を国土地理院の逆ジオコーダに投げて得る(応答は data/raw/gsi/ に残す)。
陸上でない地点(姫島の海岸の露頭)は市町村を推測で埋めず、理由を書いて件数を null にする。
"""

from __future__ import annotations

import argparse
import json
import pathlib
import time
import urllib.request
from typing import Any

from archaeostone.area_documents import AreaTally, tally_area_documents
from archaeostone.dictionaries import load_materials
from archaeostone.municipality import (
    MUNI_JS_URL,
    USER_AGENT,
    Municipality,
    matching_codes,
    municipality_code_from_payload,
    parent_city_code,
    parse_muni_js,
    reverse_geocode,
)
from archaeostone.oai import parse_page
from archaeostone.sources import load_registry, publishable_violations
from pipeline.paths import display_path

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE_AREAS = REPO_ROOT / "public" / "data" / "source_areas.json"
RAW_OAI = REPO_ROOT / "data" / "raw" / "nabunken"
RAW_GSI = REPO_ROOT / "data" / "raw" / "gsi"
OUTPUT = REPO_ROOT / "public" / "data" / "area_documents.json"

#: 出荷レコードは索引(Nabunken)に由来する。市町村名は国土地理院の表(SRC-GSI)から引く。
RECORD_SOURCE_ID = "SRC-NABUNKEN"
POLITE_DELAY_SECONDS = 0.5


def area_record(
    area: dict[str, Any],
    payload: Any,
    table: dict[str, Municipality],
    tally: AreaTally | None,
) -> dict[str, Any]:
    """原産地 1 件の出荷レコード。純関数。"""
    code = municipality_code_from_payload(payload)
    provenance = {
        "method": "gsi_reverse_geocoder",
        "latitude": area["latitude"],
        "longitude": area["longitude"],
        "muniCd": code,
    }
    base = {
        "id": area["id"],
        "source_id": RECORD_SOURCE_ID,
        "municipality_provenance": provenance,
    }
    empty = {"documents": None, "documents_by_code": None, "obsidian_title_count": None, "obsidian_titles": []}

    if code is None:
        return {
            **base,
            "municipality": None,
            "municipality_reason": (
                "国土地理院の逆ジオコーダがこの地点を陸上と判定しない(応答が空)。"
                "市町村を推測で埋めない"
            ),
            **empty,
        }
    municipality = table.get(code)
    if municipality is None:
        return {
            **base,
            "municipality": None,
            "municipality_reason": f"国土地理院の市区町村表にコード {code} が無い",
            **empty,
        }
    return {
        **base,
        "municipality": {
            "code": municipality.code,
            "name": municipality.display_name,
            "prefecture": municipality.prefecture,
            "parent_city_code": parent_city_code(code, table),
            "matched_codes": list(matching_codes(code, table)),
        },
        "municipality_reason": None,
        "documents": tally.documents if tally else 0,
        "documents_by_code": dict(tally.documents_by_code) if tally else {},
        "obsidian_title_count": tally.obsidian_title_count if tally else 0,
        "obsidian_titles": list(tally.obsidian_titles) if tally else [],
    }


def load_muni_table() -> dict[str, Municipality]:
    cache = RAW_GSI / "muni.js"
    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(MUNI_JS_URL, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=60) as response:
            cache.write_bytes(response.read())
    return parse_muni_js(cache.read_text(encoding="utf-8"))


def reverse_payload(area: dict[str, Any], *, sleep=time.sleep) -> Any:
    cache = RAW_GSI / "reverse" / f"{area['id']}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    payload = reverse_geocode(area["latitude"], area["longitude"])
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    sleep(POLITE_DELAY_SECONDS)
    return payload


def obsidian_terms() -> list[str]:
    entry = load_materials()["obsidian"]
    return [entry["label_ja"], *entry.get("synonyms", [])]


def build(*, sleep=time.sleep) -> dict[str, Any]:
    areas = json.loads(SOURCE_AREAS.read_text(encoding="utf-8"))["source_areas"]
    table = load_muni_table()
    payloads = {area["id"]: reverse_payload(area, sleep=sleep) for area in areas}

    targets: dict[str, tuple[str, ...]] = {}
    for area in areas:
        code = municipality_code_from_payload(payloads[area["id"]])
        if code is not None and code in table:
            targets[area["id"]] = matching_codes(code, table)

    pages = sorted(RAW_OAI.glob("page_*.xml"))
    if not pages:
        raise RuntimeError(
            f"{RAW_OAI} に収穫物が無い。先に `python -m pipeline.acquisition.nabunken` を実行すること"
        )

    def records():
        for page in pages:
            yield from parse_page(page.read_bytes())

    terms = obsidian_terms()
    tallies = tally_area_documents(records(), targets, terms)
    shipped = [
        area_record(area, payloads[area["id"]], table, tallies.get(area["id"]))
        for area in areas
    ]

    violations = publishable_violations(shipped, load_registry())
    if violations:
        detail = "\n".join(f"  {v.record_id}: {v.source_id} — {v.reason}" for v in violations)
        raise RuntimeError(f"再配布できない源に由来するレコードがある:\n{detail}")

    with_muni = [a for a in shipped if a["municipality"] is not None]
    return {
        "generated_by": "pipeline.build_area_documents",
        "source_id": RECORD_SOURCE_ID,
        "scope": (
            "原産地の座標がある市町村のコードを setSpec に持つ、全国遺跡報告総覧の報告書。"
            "**石材が出土した遺跡の数ではない。** 題名の例は題名に黒曜石の語を含むものだけを載せる"
        ),
        "terms": terms,
        "municipality_names": "国土地理院 市区町村表(muni.js)",
        "counts": {
            "areas": len(shipped),
            "with_municipality": len(with_muni),
            "without_municipality": len(shipped) - len(with_muni),
            "pages_scanned": len(pages),
        },
        "areas": shipped,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="原産地のある市町村の報告書を数える")
    parser.add_argument("--out", type=pathlib.Path, default=OUTPUT)
    args = parser.parse_args()

    started = time.monotonic()
    payload = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"{display_path(args.out)} を書き出した({time.monotonic() - started:.0f} 秒)")
    for area in payload["areas"]:
        muni = area["municipality"]
        if muni is None:
            print(f"  {area['id']:<20} 市町村なし — {area['municipality_reason']}")
        else:
            print(
                f"  {area['id']:<20} {muni['name']:<12} 報告書 {area['documents']:>5,} 件"
                f" / 題名に黒曜石 {area['obsidian_title_count']:>3} 件 / コード別 {area['documents_by_code']}"
            )


if __name__ == "__main__":
    main()

"""県別ヒスイ集計の札を置く位置を出荷形にする(F-06)。

**札の位置は県庁舎であって、出土地点ではない。** 集成表の個票は再配布できないので、
県より細かい位置は持たない。件数は出荷済みの ``jade_aggregate.json`` から画面が引く ——
このファイルは位置(国土地理院に由来)だけを持ち、糸魚川市の表に由来する値を持たない。

    python -m pipeline.build_jade_prefectures

位置は原産地と同じ規則で地名検索から引き、どの問い合わせの何番目の候補かを残す。
一件でも解決できなければ書き出さずに落ちる(推測で置かない)。
"""

from __future__ import annotations

import argparse
import json
import pathlib
import time
from typing import Any

import yaml

from archaeostone.source_areas import (
    POLITE_DELAY_SECONDS,
    ResolutionOutcome,
    resolve_source_area,
    reverse_prefecture_code,
    search_place,
)
from archaeostone.sources import load_registry, publishable_violations
from pipeline.paths import display_path

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG = REPO_ROOT / "config" / "jade_prefectures.yaml"
JADE = REPO_ROOT / "public" / "data" / "jade_aggregate.json"
OUTPUT = REPO_ROOT / "public" / "data" / "jade_prefectures.json"

RECORD_SOURCE_ID = "SRC-GSI"
POSITION_MEANING = "県庁舎の位置。出土地点ではない(集成表の個票は再配布できないので、県より細かい位置を持たない)"


def build(*, sleep=time.sleep, search=search_place, reverse=reverse_prefecture_code) -> dict[str, Any]:
    entries = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))["prefectures"]
    sheets = {s["sheet"] for s in json.loads(JADE.read_text(encoding="utf-8"))["coverage"]["per_sheet"]}
    configured = {entry["sheet"] for entry in entries.values()}
    if configured != sheets:
        raise RuntimeError(
            f"設定のシート名が集成表と一致しない: 設定のみ {sorted(configured - sheets)} / "
            f"集成表のみ {sorted(sheets - configured)}"
        )

    records = []
    for pref_id, entry in entries.items():
        candidates = [dict(c) for c in search(entry["query"])]
        sleep(POLITE_DELAY_SECONDS)
        for candidate in candidates:
            if candidate.get("title") == entry["title_must_contain"]:
                candidate["pref_code"] = reverse(candidate["lat"], candidate["lon"])
                sleep(POLITE_DELAY_SECONDS)
        resolution = resolve_source_area(pref_id, entry, candidates)
        if resolution.outcome is not ResolutionOutcome.RESOLVED:
            raise RuntimeError(f"{pref_id} の位置が決まらない: {resolution.outcome.value}")
        if resolution.pref_code != entry["expect_pref_code"]:
            raise RuntimeError(
                f"{pref_id} の候補は県コード {resolution.pref_code} で、"
                f"期待した {entry['expect_pref_code']} ではない"
            )
        records.append(
            {
                "id": pref_id,
                "source_id": RECORD_SOURCE_ID,
                "name_ja": entry["name_ja"],
                "sheet": entry["sheet"],
                "prefecture_code": resolution.pref_code,
                "latitude": round(resolution.latitude, 6),
                "longitude": round(resolution.longitude, 6),
                "position_meaning": POSITION_MEANING,
                "position_provenance": resolution.as_provenance(),
                "scope_note": entry.get("scope_note"),
            }
        )

    violations = publishable_violations(records, load_registry())
    if violations:
        detail = "\n".join(f"  {v.record_id}: {v.source_id} — {v.reason}" for v in violations)
        raise RuntimeError(f"再配布できない源に由来するレコードがある:\n{detail}")

    return {
        "generated_by": "pipeline.build_jade_prefectures",
        "note": POSITION_MEANING,
        "prefectures": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="県別ヒスイ集計の札の位置を作る")
    parser.add_argument("--out", type=pathlib.Path, default=OUTPUT)
    args = parser.parse_args()

    payload = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{display_path(args.out)} を書き出した")
    for rec in payload["prefectures"]:
        prov = rec["position_provenance"]
        print(
            f"  {rec['id']:<13} {rec['sheet']:<12} {prov['candidate_count']} 件中 "
            f"{prov['candidate_index'] + 1} 番目「{prov['candidate_title']}」"
        )


if __name__ == "__main__":
    main()

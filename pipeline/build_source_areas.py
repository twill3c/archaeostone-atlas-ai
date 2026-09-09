"""黒曜石原産地の出荷レコードを作る(F-01 / F-02 / G-01 / G-03)。

座標は国土地理院の地名検索から引き、**どの問い合わせの何番目の候補を、
どの規則で選んだか**を全件に載せる。地質は GSJ の点の問い合わせから取る。

公開ファイルへ書く前に、権利の門(G-01)を通す。再配布不可の源に由来する
レコードが 1 件でもあれば**書き出さずに落ちる**(fail-closed)。

    python -m pipeline.build_source_areas
"""

from __future__ import annotations

import argparse
import json
import pathlib
import time

from archaeostone.gsj import GsjOutcome, fetch_point
from archaeostone.source_areas import (
    ResolutionOutcome,
    load_source_area_config,
    resolve_all,
)
from archaeostone.sources import load_registry, publishable_violations

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
OUTPUT = REPO_ROOT / "public" / "data" / "source_areas.json"

#: 原産地レコードそのものは本プロジェクトの編纂物なので SRC-SOURCEAREA に属する。
#: 座標は SRC-GSI、地質は SRC-GSJ に由来し、どちらも再配布可である。
RECORD_SOURCE_ID = "SRC-SOURCEAREA"


def build(*, sleep=time.sleep) -> dict:
    config = load_source_area_config()
    citations = config["citations"]
    resolutions = resolve_all(sleep=sleep)

    records = []
    for source_area_id, entry, resolution in resolutions:
        record: dict = {
            "id": source_area_id,
            "source_id": RECORD_SOURCE_ID,
            "material_id": "MAT-OBS",
            "name_ja": entry["name_ja"],
            "group_ja": entry.get("group_ja"),
            "prefecture_code": resolution.pref_code,
            "latitude": round(resolution.latitude, 6) if resolution.latitude else None,
            "longitude": round(resolution.longitude, 6) if resolution.longitude else None,
            "coordinate_precision": entry.get("coordinate_precision", "point"),
            "coordinate_provenance": resolution.as_provenance(),
            "evidence_status": resolution.evidence_status,
            "note": entry.get("note"),
            "citations": [
                {
                    "citation_id": cid,
                    "title": citations[cid]["title"],
                    "url": citations[cid]["url"],
                    "source_id": citations[cid]["source_id"],
                }
                for cid in entry["citations"]
            ],
        }

        if resolution.outcome is ResolutionOutcome.RESOLVED:
            geology = fetch_point(resolution.latitude, resolution.longitude, sleep=sleep)
            record.update(geology.as_record())
            sleep(0.4)
        else:
            record.update(
                {
                    "geology_outcome": None,
                    "geology_symbol": None,
                    "formation_age_ja": None,
                    "lithology_ja": None,
                }
            )
        records.append(record)

    # ── 権利の門(G-01)。ここを通らないものは書き出さない ──
    registry = load_registry()
    violations = publishable_violations(records, registry)
    if violations:
        detail = "\n".join(f"  {v.record_id}: {v.source_id} — {v.reason}" for v in violations)
        raise RuntimeError(f"再配布できない源に由来するレコードがある:\n{detail}")

    resolved = [r for r in records if r["evidence_status"] == "curated"]
    with_geology = [r for r in records if r.get("geology_outcome") == "ok"]

    return {
        "generated_by": "pipeline.build_source_areas",
        "counts": {
            "total": len(records),
            "resolved": len(resolved),
            "needs_review": len(records) - len(resolved),
            "with_geology": len(with_geology),
            "coordinate_precision_area": sum(
                1 for r in records if r["coordinate_precision"] == "area"
            ),
        },
        "coverage_note": (
            "明治大学 黒耀石研究センターは国内に「80数カ所」の原産地があると述べている"
            "(https://www.meiji.ac.jp/cols/map01.html)。本辞書が典拠を確認できたのは"
            f"{len(records)} 件である。差は「無い」のではなく「本辞書が確認できていない」。"
        ),
        "citations": citations,
        "source_areas": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="黒曜石原産地の出荷レコードを作る")
    parser.add_argument("--out", type=pathlib.Path, default=OUTPUT)
    args = parser.parse_args()

    payload = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    counts = payload["counts"]
    print(
        f"{args.out.relative_to(REPO_ROOT)} を書き出した — 原産地 {counts['total']} 件"
        f"(解決 {counts['resolved']} / 要確認 {counts['needs_review']} / "
        f"地質あり {counts['with_geology']} / 面積精度 {counts['coordinate_precision_area']})"
    )


if __name__ == "__main__":
    main()

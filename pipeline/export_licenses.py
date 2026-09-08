"""`config/sources.yaml` から `public/data/licenses.json` を作る(SPEC §6.1 / §7 G-01)。

権利情報は**画面に出す**。出典と再配布可否を読者が確かめられなければ、
Evidence First は掛け声で終わる(構想書 §36)。

再配布不可の源も**載せる** —— 載せないと「使っていない」と「隠している」が
区別できない。載せるのは権利の記述であって、その源のデータではない。

    python -m pipeline.export_licenses
"""

from __future__ import annotations

import json
import pathlib

from archaeostone.sources import load_registry

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
OUTPUT = REPO_ROOT / "public" / "data" / "licenses.json"


def build() -> dict:
    registry = load_registry()
    sources = []
    for source_id in sorted(registry.ids):
        entry = registry[source_id]
        sources.append(
            {
                "source_id": source_id,
                "title": entry["title"],
                "source_url": entry["source_url"],
                "license_url": entry["license_url"],
                "license_name": entry["license_name"],
                "license_quote": " ".join(str(entry["license_quote"]).split()),
                "redistribution": entry["redistribution"],
                "redistribution_reason": entry.get("redistribution_reason"),
                "modification": entry["modification"],
                "attribution_required": entry["attribution_required"],
                "attribution_text": entry.get("attribution_text"),
                "verified_at": str(entry["verified_at"]),
            }
        )

    redistributable = [s for s in sources if s["redistribution"]]
    return {
        "generated_from": "config/sources.yaml",
        "counts": {
            "total": len(sources),
            "redistributable": len(redistributable),
            "not_redistributable": len(sources) - len(redistributable),
        },
        "attributions": registry.attributions(),
        "sources": sources,
    }


def main() -> None:
    payload = build()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    counts = payload["counts"]
    print(
        f"{OUTPUT.relative_to(REPO_ROOT)} を書き出した — "
        f"源 {counts['total']} 件(再配布可 {counts['redistributable']} / "
        f"不可 {counts['not_redistributable']})"
    )


if __name__ == "__main__":
    main()

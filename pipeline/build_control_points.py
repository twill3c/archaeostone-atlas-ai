"""対照群の作成(F-03 / G-09 の前提)。

原産地の地質が「偏っている」と言うには、比べる相手が要る。相手は
**日本の陸域から面積の重みで無作為に選んだ点**である。

手順は二段に分かれている。理由は計器を揃えるためである(HC-065)。

1. **どこが陸かは、地質図タイルから安く知る。** z=7 のタイル 99 枚で日本を覆い、
   不透明かつ非境界線の画素を陸とみなす。標本抽出の重みは ``cos^2(緯度)``
   (メルカトルの面積の歪みの補正。日本の南北端で 1.727 倍違う)
2. **地質そのものは、点の問い合わせ API から取る。** 原産地とまったく同じ計器で
   測る。タイルの復号で済ませると、原産地(API)と対照群(タイル)で計器が違い、
   差が地質の差なのか計器の差なのか言えなくなる

二段にしたおかげで**経路の突き合わせ**ができる。同じ点についてタイルの色から
引いた凡例と、API が返した凡例を比べ、一致率を出す。一致しなければ、
復号か版のずれのどちらかである(結論だけでなく経路を比べる — HC-065)。

    python -m pipeline.build_control_points --n 400
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import random
import time

from archaeostone.geology_tiles import (
    area_weight,
    fetch_tile,
    land_pixels,
    legend_by_rgb,
    open_tile,
    tile_xy,
)
from archaeostone.gsj import GsjOutcome, fetch_point

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
TILE_CACHE = REPO_ROOT / "data" / "raw" / "gsj" / "tiles"
OUTPUT = REPO_ROOT / "data" / "curated" / "control_points.json"

#: 日本を覆う矩形。タイルの取得範囲を決めるためだけに使う
#: (この矩形の中のどこが陸かは、タイル自身が教える)。
JAPAN_BBOX = {"north": 46.0, "south": 24.0, "west": 122.0, "east": 146.0}
LAND_MASK_ZOOM = 7

#: 抽出の種。固定して再現できるようにする。
DEFAULT_SEED = 20260909


def tile_range(zoom: int) -> tuple[range, range]:
    x0, y0, _, _ = tile_xy(JAPAN_BBOX["north"], JAPAN_BBOX["west"], zoom)
    x1, y1, _, _ = tile_xy(JAPAN_BBOX["south"], JAPAN_BBOX["east"], zoom)
    return range(x0, x1 + 1), range(y0, y1 + 1)


def collect_land_pixels(zoom: int = LAND_MASK_ZOOM) -> list[tuple[float, float, tuple[int, int, int]]]:
    """タイルを走って陸画素を集める。"""
    xs, ys = tile_range(zoom)
    pixels: list[tuple[float, float, tuple[int, int, int]]] = []
    fetched = missing = 0

    for tile_x in xs:
        for tile_y in ys:
            raw = fetch_tile(zoom, tile_x, tile_y, cache_dir=TILE_CACHE)
            if raw is None:
                missing += 1
                continue
            fetched += 1
            pixels.extend(land_pixels(open_tile(raw), zoom, tile_x, tile_y))

    print(
        f"タイル z{zoom}: 取得 {fetched} 枚 / 無し {missing} 枚 → 陸画素 {len(pixels):,} 個"
    )
    return pixels


def sample_area_weighted(
    pixels: list[tuple[float, float, tuple[int, int, int]]],
    count: int,
    *,
    seed: int = DEFAULT_SEED,
) -> list[tuple[float, float, tuple[int, int, int]]]:
    """面積の重みで非復元抽出する。

    メルカトル図法では同じ画素が表す地表面積が緯度で変わるので、重み無しだと
    北を過大に数える。重みは ``cos^2(緯度)``(図法の定義から出る閉形式)。
    """
    if count >= len(pixels):
        return list(pixels)
    rng = random.Random(seed)
    weights = [area_weight(lat) for lat, _lon, _rgb in pixels]

    # 非復元の重みつき抽出。Efraimidis-Spirakis の指数ジャンプ法
    # (u^(1/w) の大きい順に取る)。重みが 0 の画素は取れない。
    keys = [(rng.random() ** (1.0 / w) if w > 0 else -1.0, i) for i, w in enumerate(weights)]
    keys.sort(reverse=True)
    return [pixels[i] for _key, i in keys[:count]]


def build(count: int, *, seed: int = DEFAULT_SEED, sleep=time.sleep) -> dict:
    legend = legend_by_rgb()
    pixels = collect_land_pixels()
    if not pixels:
        raise RuntimeError("陸画素が 0 個。タイルの取得か復号が壊れている")

    chosen = sample_area_weighted(pixels, count, seed=seed)
    print(f"対照点 {len(chosen)} 個を抽出(seed={seed})。点の問い合わせで地質を取る")

    records = []
    agree = disagree = 0
    outcomes: dict[str, int] = {}

    for index, (latitude, longitude, rgb) in enumerate(chosen, 1):
        result = fetch_point(latitude, longitude, sleep=sleep)
        outcomes[result.outcome.value] = outcomes.get(result.outcome.value, 0) + 1

        tile_symbol = legend[rgb]["symbol"]
        api_symbol = result.symbol
        if result.outcome is GsjOutcome.OK:
            if api_symbol == tile_symbol:
                agree += 1
            else:
                disagree += 1

        records.append(
            {
                "control_id": f"CTL-{index:04d}",
                "source_id": "SRC-GSJ",
                "latitude": round(latitude, 6),
                "longitude": round(longitude, 6),
                "tile_symbol": tile_symbol,
                **result.as_record(),
            }
        )
        if index % 50 == 0:
            print(f"  {index}/{len(chosen)} 点", flush=True)
        sleep(0.4)

    checked = agree + disagree
    return {
        "generated_by": "pipeline.build_control_points",
        "sampling": {
            "land_mask": f"GSJ シームレス地質図タイル z{LAND_MASK_ZOOM}",
            "weight": "cos^2(latitude) — ウェブメルカトルの面積の歪みの補正",
            "seed": seed,
            "land_pixels_available": len(pixels),
            "requested": count,
            "sampled": len(chosen),
        },
        "two_path_check": {
            "description": (
                "同じ点について、タイルの色から引いた凡例(ラスタ・z7 = 約 1 km/画素)と、"
                "点の問い合わせ API が返した凡例(ベクタ)を比べる。"
                "**これは正しさの門ではなく解像度の比較である。**"
            ),
            "compared": checked,
            "agree": agree,
            "disagree": disagree,
            "agreement_rate": (agree / checked) if checked else None,
            "interpretation": (
                "不一致はラスタの一般化による(実測 2026-09-09: 不一致の行き先は"
                "谷底平野・山間盆地などの幅の狭い線状の単位に偏り、大分類では 70% が一致する)。"
                "**出荷レコードの地質は API 側を採っている** —— タイルは「どこが陸か」を"
                "決めるためだけに使う。原産地も同じ API で測るので、両群の計器は揃っている。"
            ),
            "used_for_geology": "point_api",
            "used_for_land_mask": "tile",
        },
        "outcomes": outcomes,
        "control_points": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="対照群(無作為陸地点)を作る")
    parser.add_argument("--n", type=int, default=400)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()

    payload = build(args.n, seed=args.seed)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    check = payload["two_path_check"]
    rate = check["agreement_rate"]
    print(
        f"\n{OUTPUT.relative_to(REPO_ROOT)} を書き出した — 対照点 "
        f"{len(payload['control_points'])} 個 / 結末 {payload['outcomes']}"
    )
    print(
        "二経路の一致: "
        + (f"{check['agree']}/{check['compared']} ({rate:.1%})" if rate is not None else "比較なし")
    )


if __name__ == "__main__":
    main()

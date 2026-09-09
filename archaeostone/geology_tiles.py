"""GSJ シームレス地質図タイルの復号と、面積を歪めない標本抽出(F-03 / G-09 の前提)。

タイルの画素は凡例の RGB をそのまま持っている。実測(2026-09-08)では凡例
2,416 件すべてが RGB を持ち、**重複は 0 件** —— 色から凡例への対応は一対一である。
だから点の問い合わせを何千回も投げなくても、タイル数枚で陸域の標本が取れる。

ただし三つ歪みの原因がある。

* **境界線**。タイルには純黒 ``(0, 0, 0)`` の図郭の輪郭が引かれている。
  実測では和田峠の z10 タイクで 65,536 画素中 8,061 画素(12.3%)。地質ではない
* **メルカトルの面積**。同じ画素が表す地表面積は ``cos^2(緯度)`` に比例する。
  日本の南北端で 1.727 倍違うので、無補正だと北を過大に数える
* **凡例に無い色**。黙って捨てると、凡例が更新された日に静かに陸を取りこぼす。
  ここでは**例外にする**(HC-075)

なお対照群の地質そのものは、この復号ではなく**点の問い合わせ API** から取る。
原産地と対照群を同じ計器で測るためである。タイルは「どこが陸か」を安く知るために
だけ使い、両者の一致は突き合わせて確かめる(HC-065)。
"""

from __future__ import annotations

import functools
import io
import json
import math
import pathlib
import urllib.request
from collections.abc import Iterator
from typing import Any

LEGEND_URL = "https://gbank.gsj.jp/seamless/v2/api/1.3.1/legend.json"
TILE_URL = "https://gbank.gsj.jp/seamless/v2/api/1.3.1/tiles/{z}/{y}/{x}.png"
USER_AGENT = "Mozilla/5.0 (compatible; ArchaeoStoneAtlas/0.1; research)"

TILE_SIZE = 256

#: 図郭の輪郭線。地質ではないので陸として数えない。
BOUNDARY_RGB: tuple[int, int, int] = (0, 0, 0)

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
LEGEND_CACHE = REPO_ROOT / "data" / "raw" / "gsj" / "legend.json"


# ── 凡例 ────────────────────────────────────────────────


def fetch_legend(*, cache: pathlib.Path | None = None) -> list[dict[str, Any]]:
    path = cache if cache is not None else LEGEND_CACHE
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    request = urllib.request.Request(LEGEND_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=90) as response:
        payload = response.read().decode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
    return json.loads(payload)


@functools.cache
def legend_by_rgb() -> dict[tuple[int, int, int], dict[str, Any]]:
    """RGB → 凡例エントリ。

    重複する RGB があれば**例外にする**。返り値で示すと、呼ぶ側が黙って
    上書きした辞書を使ってしまい、復号が当て推量になる。
    """
    index: dict[tuple[int, int, int], dict[str, Any]] = {}
    for entry in fetch_legend():
        if entry.get("r") is None:
            continue
        rgb = (int(entry["r"]), int(entry["g"]), int(entry["b"]))
        if rgb in index and index[rgb]["symbol"] != entry.get("symbol"):
            raise ValueError(
                f"凡例の RGB {rgb} が {index[rgb]['symbol']} と {entry.get('symbol')} "
                "の 2 つに対応している。色からの復号ができない"
            )
        index[rgb] = entry
    if BOUNDARY_RGB in index:
        raise ValueError(
            f"境界線の色 {BOUNDARY_RGB} が凡例に現れた。境界線を地質として数えてしまう"
        )
    return index


# ── メルカトルの座標変換 ────────────────────────────────


def tile_xy(latitude: float, longitude: float, zoom: int) -> tuple[int, int, int, int]:
    """座標 → (タイル x, タイル y, 画素 x, 画素 y)。"""
    n = 2**zoom
    fx = (longitude + 180.0) / 360.0 * n
    fy = (1.0 - math.asinh(math.tan(math.radians(latitude))) / math.pi) / 2.0 * n
    tile_x, tile_y = int(fx), int(fy)
    px = int((fx - tile_x) * TILE_SIZE)
    py = int((fy - tile_y) * TILE_SIZE)
    return tile_x, tile_y, min(px, TILE_SIZE - 1), min(py, TILE_SIZE - 1)


def pixel_center_latlon(
    zoom: int, tile_x: int, tile_y: int, pixel_x: int, pixel_y: int
) -> tuple[float, float]:
    """タイル画素の中心の座標。"""
    n = 2**zoom
    fx = tile_x + (pixel_x + 0.5) / TILE_SIZE
    fy = tile_y + (pixel_y + 0.5) / TILE_SIZE
    longitude = fx / n * 360.0 - 180.0
    latitude = math.degrees(math.atan(math.sinh(math.pi * (1.0 - 2.0 * fy / n))))
    return latitude, longitude


def area_weight(latitude: float) -> float:
    """画素が表す地表面積の相対値。

    ウェブメルカトルの縮尺係数は ``1/cos(緯度)`` なので、投影面上で等しい面積が
    表す地表面積は ``cos^2(緯度)`` に比例する。図法の定義から出る閉形式である。
    """
    return math.cos(math.radians(latitude)) ** 2


# ── 陸画素の取り出し ────────────────────────────────────


def land_pixels(
    image: Any, zoom: int, tile_x: int, tile_y: int
) -> Iterator[tuple[float, float, tuple[int, int, int]]]:
    """タイルから (緯度, 経度, RGB) を陸画素だけ取り出す。

    透明(海・被覆外)と純黒(境界線)を除く。凡例に無い不透明な色は例外にする。
    """
    rgba = image.convert("RGBA")
    size = rgba.size[0]
    data = rgba.get_flattened_data()
    known = legend_by_rgb()

    for index, pixel in enumerate(data):
        red, green, blue, alpha = pixel
        if alpha == 0:
            continue
        rgb = (red, green, blue)
        if rgb == BOUNDARY_RGB:
            continue
        if rgb not in known:
            raise ValueError(
                f"凡例に無い不透明な色 {rgb} が z{zoom}/{tile_y}/{tile_x} に現れた。"
                "凡例が更新された可能性がある。黙って捨てない"
            )
        pixel_y, pixel_x = divmod(index, size)
        latitude, longitude = pixel_center_latlon(zoom, tile_x, tile_y, pixel_x, pixel_y)
        yield latitude, longitude, rgb


def fetch_tile(zoom: int, tile_x: int, tile_y: int, *, cache_dir: pathlib.Path) -> bytes | None:
    """タイルを取る。無い(404)なら None —— **障害ではなく「そこに図が無い」という答え**。"""
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"{zoom}_{tile_y}_{tile_x}.png"
    if path.exists():
        raw = path.read_bytes()
        return raw or None

    url = TILE_URL.format(z=zoom, y=tile_y, x=tile_x)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        if exc.code in (404, 500):
            path.write_bytes(b"")  # 「無い」もキャッシュする(繰り返し訊かない)
            return None
        raise
    path.write_bytes(raw)
    return raw


def open_tile(raw: bytes) -> Any:
    from PIL import Image

    return Image.open(io.BytesIO(raw))

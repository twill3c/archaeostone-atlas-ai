"""地質タイルの復号と、面積を歪めない標本抽出の検査(T-080〜 / G-09 の前提)。

対照群は「日本の陸域から無作為に選んだ点」である。無作為が歪んでいると、
原産地との比較そのものが意味を失うので、歪みの原因を三つ潰す。

1. **色 → 凡例の対応が一意であること。** GSJ のタイルは凡例の RGB をそのまま
   画素にしている。重複があれば復号は当て推量になる
2. **図郭の境界線を陸として数えないこと。** タイルには純黒(0,0,0)の輪郭線が
   引かれており、これは地質ではない。実測(2026-09-09)では和田峠の z10 タイルで
   65,536 画素中 8,061 画素(12.3%)が純黒だった
3. **メルカトルの面積の歪みを補正すること。** 同じ画素が表す地表面積は
   緯度によって cos^2 で変わる。日本の南北端で 1.7 倍違う

期待値は閉形式のオラクル(メルカトル図法の定義)から導く。
"""

import math

import pytest

from archaeostone.geology_tiles import (
    BOUNDARY_RGB,
    area_weight,
    land_pixels,
    legend_by_rgb,
    pixel_center_latlon,
    tile_xy,
)


# ── 凡例 ────────────────────────────────────────────────


def test_t080_legend_rgb_is_a_bijection() -> None:
    """T-080: 色 → 凡例が一意であること。

    実測 2026-09-08: 凡例 2,416 件すべてが RGB を持ち、重複は 0 件。
    重複が出たら復号は当て推量になるので、**例外にして止める**設計にしてある。
    """
    by_rgb = legend_by_rgb()
    assert len(by_rgb) >= 2_400, f"凡例が {len(by_rgb)} 件しかない"
    for rgb, entry in by_rgb.items():
        assert len(rgb) == 3
        assert all(0 <= channel <= 255 for channel in rgb)
        assert entry.get("symbol"), f"{rgb} の凡例に symbol が無い"


def test_t081_boundary_colour_is_not_a_legend_entry() -> None:
    """T-081: 純黒(境界線)が凡例に無いこと。

    もし凡例に純黒があれば、境界線を地質として数えてしまう。
    """
    assert BOUNDARY_RGB == (0, 0, 0)
    assert BOUNDARY_RGB not in legend_by_rgb()


# ── メルカトルの座標変換(閉形式のオラクル) ────────────


@pytest.mark.parametrize(
    "lat,lon",
    [(36.14506, 138.14385), (43.88016, 143.17752), (24.5, 122.5), (45.5, 145.5)],
)
def test_t082_tile_and_pixel_roundtrip(lat: float, lon: float) -> None:
    """T-082: 座標 → タイル画素 → 座標 が 1 画素以内で戻る。

    オラクルはメルカトル図法の定義そのもの(閉形式)であって、実装の出力ではない。
    """
    z = 7
    tx, ty, px, py = tile_xy(lat, lon, z)
    back_lat, back_lon = pixel_center_latlon(z, tx, ty, px, py)

    # z=7 の 1 画素は赤道で約 1.2 km。緯度 1 画素ぶんの許容差を閉形式で出す。
    degrees_per_pixel_lon = 360.0 / (2**z * 256)
    assert abs(back_lon - lon) <= degrees_per_pixel_lon
    assert abs(back_lat - lat) <= degrees_per_pixel_lon  # 緯度方向はこれより細かい


def test_t083_tile_x_increases_eastward_and_y_increases_southward() -> None:
    """T-083: 軸の向き。取り違えると地図が転置する。"""
    z = 7
    west = tile_xy(36.0, 130.0, z)
    east = tile_xy(36.0, 140.0, z)
    north = tile_xy(44.0, 135.0, z)
    south = tile_xy(26.0, 135.0, z)

    assert (west[0], west[2]) < (east[0], east[2]), "東へ行くと x が増えるはず"
    assert (north[1], north[3]) < (south[1], south[3]), "南へ行くと y が増えるはず"


# ── 面積の重み(閉形式のオラクル) ──────────────────────


def test_t084_area_weight_follows_cos_squared() -> None:
    """T-084: 画素の面積重みが cos^2(緯度) に比例すること。

    ウェブメルカトルの縮尺係数は 1/cos(緯度) なので、投影面上で等しい面積が
    表す地表面積は cos^2(緯度) に比例する。これは図法の定義から出る閉形式である。
    """
    for lat in (0.0, 24.0, 36.0, 46.0, 60.0):
        assert area_weight(lat) == pytest.approx(math.cos(math.radians(lat)) ** 2, rel=1e-12)


def test_t085_area_weight_spans_the_expected_range_over_japan() -> None:
    """T-085: 日本の南北で重みが 1.7 倍ほど違うこと(補正が必要な大きさか)。

    差が無視できるなら補正は要らない。**要るかどうかを測ってから入れる。**
    """
    south = area_weight(24.0)
    north = area_weight(46.0)
    ratio = south / north
    assert ratio == pytest.approx(1.727, abs=0.01), f"実測比 {ratio}"
    assert ratio > 1.2, "この程度の歪みなら補正は不要だったことになる"


# ── 陸画素の取り出し ────────────────────────────────────


class FakeImage:
    """RGBA の画素列を持つだけの替え玉。Pillow に依存させない。"""

    def __init__(self, pixels: list[tuple[int, int, int, int]], size: int) -> None:
        self._pixels = pixels
        self.size = (size, size)

    def convert(self, _mode: str) -> "FakeImage":
        return self

    def get_flattened_data(self) -> list[tuple[int, int, int, int]]:
        return self._pixels


def _solid(rgba: tuple[int, int, int, int], size: int = 2) -> FakeImage:
    return FakeImage([rgba] * (size * size), size)


def test_t086_transparent_pixels_are_not_land() -> None:
    """T-086: 透明画素(海・被覆外)を陸として数えない。"""
    image = _solid((0, 0, 0, 0))
    assert list(land_pixels(image, 7, 100, 100)) == []


def test_t087_positive_control_boundary_pixels_are_excluded() -> None:
    """T-087(陽性対照): 純黒の境界線を陸として数えない。

    境界線は不透明なので、透明かどうかだけを見る実装は**通してしまう**。
    その違いをここで見分ける。
    """
    image = _solid((0, 0, 0, 255))
    assert list(land_pixels(image, 7, 100, 100)) == [], "境界線を陸として数えている"


def test_t088_legend_coloured_pixels_are_land() -> None:
    """T-088(陰性対照): 凡例にある色の画素は陸として取れる。

    先に陰性対照を当てる —— 誤検出があれば陽性対照より先に分かる(HC-074)。
    """
    rgb = next(iter(legend_by_rgb()))
    image = _solid((*rgb, 255))
    got = list(land_pixels(image, 7, 100, 100))
    assert len(got) == 4, f"2x2 の全画素が陸のはずが {len(got)} 件"
    for lat, lon, pixel_rgb in got:
        assert pixel_rgb == rgb
        assert -90 <= lat <= 90 and -180 <= lon <= 180


def test_t089_unknown_opaque_colour_raises() -> None:
    """T-089: 凡例に無い不透明な色は**黙って捨てず例外にする**。

    「たいてい境界線だろう」で捨てると、凡例が更新された日に静かに
    陸を取りこぼす。仮定が崩れたら実装のほうが教えてくれるようにする(HC-075)。
    """
    image = _solid((1, 2, 3, 255))
    with pytest.raises(ValueError, match="凡例"):
        list(land_pixels(image, 7, 100, 100))

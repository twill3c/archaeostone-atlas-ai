"""市区町村コードと名前(F-07)。

原産地の座標を国土地理院の逆ジオコーダに投げ、市区町村コードを得る。
名前は国土地理院の市区町村表 ``muni.js`` から引く。

実測(2026-09-14)で分かっている癖:

* **二つの源でコードの桁数が違う。** 逆ジオコーダは ``01555``(5 桁)を返すが、
  ``muni.js`` は先頭の 0 を落として ``1555`` と書く(1,919 行のうち 497 行が 4 桁)。
  そのまま引くと北海道〜群馬(コード 01〜09)の市町村だけが**黙って見つからない**
* **政令市は区のコードで返る。** 仙台 秋保は ``04104``(太白区)。一方、報告書の
  索引が区と市のどちらで持つかは源による。区の名前は ``仙台市　太白区`` と
  全角空白で市名を前に持つので、市のコードは名前から辿れる
* **陸上でない地点は ``{}`` が返る**(姫島の海岸の露頭)。答えであって障害ではない。
  市区町村を推測で埋めない
"""

from __future__ import annotations

import dataclasses
import json
import re
import urllib.request
from typing import Any, Callable

MUNI_JS_URL = "https://maps.gsi.go.jp/js/muni.js"
REVERSE_GEOCODER_URL = (
    "https://mreversegeocoder.gsi.go.jp/reverse-geocoder/LonLatToAddress"
)
USER_AGENT = "Mozilla/5.0 (compatible; ArchaeoStoneAtlas/0.1; research)"

_ROW = re.compile(r"GSI\.MUNI_ARRAY\[\"(\d+)\"\]\s*=\s*'([^']*)';")

#: 区の名前で市名と区名を分ける全角空白。
WARD_SEPARATOR = "　"


@dataclasses.dataclass(frozen=True)
class Municipality:
    code: str
    """5 桁に揃えた全国地方公共団体コード。"""
    prefecture_code: str
    prefecture: str
    name: str
    """``muni.js`` の表記そのまま(区は ``仙台市　太白区``)。"""

    @property
    def display_name(self) -> str:
        return self.name.replace(WARD_SEPARATOR, " ")


def normalize_code(code: str | int) -> str:
    """市区町村コードを 5 桁に揃える。4 桁・5 桁以外は受けない(黙って直さない)。"""
    text = str(code).strip()
    if not text.isdigit() or len(text) not in (4, 5):
        raise ValueError(f"市区町村コードではない: {code!r}")
    return text.zfill(5)


def parse_muni_js(text: str) -> dict[str, Municipality]:
    """``muni.js`` を読み、5 桁コード → 市区町村 の表にする。

    行の鍵と値の中のコードが食い違えば落ちる —— 取り違えた表で名前を引くと、
    違う市町村の名前が静かに画面に出る。
    """
    table: dict[str, Municipality] = {}
    for key, value in _ROW.findall(text):
        parts = value.split(",")
        if len(parts) != 4:
            raise ValueError(f"muni.js の行が 4 項目でない: {value!r}")
        pref_num, prefecture, code_in_value, name = parts
        code = normalize_code(key)
        if normalize_code(code_in_value) != code:
            raise ValueError(f"muni.js の鍵 {key} と値のコード {code_in_value} が食い違う")
        table[code] = Municipality(
            code=code,
            prefecture_code=pref_num.strip().zfill(2),
            prefecture=prefecture.strip(),
            name=name.strip(),
        )
    if not table:
        raise ValueError("muni.js から 1 行も読めなかった")
    return table


def parent_city_code(code: str, table: dict[str, Municipality]) -> str | None:
    """政令市の区なら、その市のコード。区でなければ None。

    コードの算術では決めない —— 大阪市は ``27100`` に対して区が ``27102〜27128`` まで
    あるので、「下 1 桁を 0 にする」は ``27128 → 27120`` という実在しない市を作る。
    名前の前半(全角空白の前)と同じ県で完全一致する市を、ちょうど 1 件のときだけ採る。
    """
    municipality = table.get(normalize_code(code))
    if municipality is None or WARD_SEPARATOR not in municipality.name:
        return None
    city_name = municipality.name.split(WARD_SEPARATOR, 1)[0]
    matches = [
        candidate.code
        for candidate in table.values()
        if candidate.prefecture_code == municipality.prefecture_code
        and candidate.name == city_name
    ]
    return matches[0] if len(matches) == 1 else None


def matching_codes(code: str, table: dict[str, Municipality]) -> tuple[str, ...]:
    """報告書の索引と突き合わせるコードの組(区なら区と市の両方)。"""
    normalized = normalize_code(code)
    parent = parent_city_code(normalized, table)
    return (normalized,) if parent is None else (normalized, parent)


def _get_json(url: str, *, timeout: float = 60.0) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def municipality_code_from_payload(payload: Any) -> str | None:
    """逆ジオコーダの応答からコード。陸上でなければ(``{}``)None。純関数。"""
    if not isinstance(payload, dict):
        raise ValueError(f"逆ジオコーダの応答が辞書でない: {payload!r}")
    results = payload.get("results")
    if not results:
        return None
    return normalize_code(results["muniCd"])


def reverse_geocode(
    latitude: float,
    longitude: float,
    *,
    get_json: Callable[[str], Any] = _get_json,
) -> Any:
    """逆ジオコーダの**生の応答**を返す(キャッシュと出所の記録に使う)。"""
    return get_json(f"{REVERSE_GEOCODER_URL}?lat={latitude}&lon={longitude}")

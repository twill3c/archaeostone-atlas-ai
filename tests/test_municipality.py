"""市区町村コードと名前の検査(T-500〜T-505 / F-07)。

ネットワークには触らない。``muni.js`` は実物(2026-09-14)から検査に要る行だけを写した。
"""

import pathlib
import re

import pytest

from archaeostone.municipality import (
    matching_codes,
    municipality_code_from_payload,
    normalize_code,
    parent_city_code,
    parse_muni_js,
)

MUNI_EXCERPT = pathlib.Path(__file__).parent / "fixtures" / "gsi_muni_excerpt.js"


@pytest.fixture(scope="module")
def table() -> dict:
    return parse_muni_js(MUNI_EXCERPT.read_text(encoding="utf-8"))


def test_t500_codes_are_normalised_to_five_digits(table: dict) -> None:
    """T-500: 表の鍵は 5 桁。北海道の遠軽町は 01555 で引ける。"""
    assert len(table) == 15
    assert all(len(code) == 5 for code in table)
    assert table["01555"].name == "遠軽町"
    assert table["01555"].prefecture == "北海道"
    assert table["09213"].name == "那須塩原市"


def test_t501_positive_control_raw_keys_miss_the_reverse_geocoder_code() -> None:
    """T-501(陽性対照): 素朴に鍵をそのまま使うと、逆ジオコーダのコードで引けない。

    逆ジオコーダは ``01555`` を返し、``muni.js`` は ``1555`` と書く。
    この対照が無いと、T-500 の 5 桁化は理由の無い整形に見える。
    """
    text = MUNI_EXCERPT.read_text(encoding="utf-8")
    raw = dict(re.findall(r"GSI\.MUNI_ARRAY\[\"(\d+)\"\]\s*=\s*'([^']*)';", text))
    assert "01555" not in raw
    assert "1555" in raw


def test_t502_ward_resolves_to_its_city_by_name(table: dict) -> None:
    """T-502: 政令市の区は、名前の前半から市のコードへ辿る。区でなければ None。"""
    assert parent_city_code("04104", table) == "04100"
    assert parent_city_code("14131", table) == "14130"
    assert parent_city_code("20361", table) is None
    assert parent_city_code("04100", table) is None
    assert matching_codes("04104", table) == ("04104", "04100")
    assert matching_codes("20361", table) == ("20361",)
    assert table["04104"].display_name == "仙台市 太白区"


def test_t503_off_land_payload_is_an_answer_not_a_failure() -> None:
    """T-503: 陸上でない地点の ``{}`` は None(姫島の実測)。コードは 5 桁に揃える。"""
    assert municipality_code_from_payload({}) is None
    assert municipality_code_from_payload({"results": {"muniCd": "04104", "lv01Nm": "秋保町湯元"}}) == "04104"
    assert municipality_code_from_payload({"results": {"muniCd": "1555", "lv01Nm": "白滝"}}) == "01555"
    with pytest.raises(ValueError):
        municipality_code_from_payload([])


@pytest.mark.parametrize("bad", ["123", "abcde", "123456", ""])
def test_t504_normalize_code_does_not_silently_repair(bad: str) -> None:
    """T-504: 4 桁・5 桁の数字以外は受けない。"""
    with pytest.raises(ValueError):
        normalize_code(bad)


def test_t505_parse_rejects_mismatched_or_empty_tables() -> None:
    """T-505: 鍵と値のコードが食い違う表・1 行も読めない表で落ちる。"""
    with pytest.raises(ValueError):
        parse_muni_js("GSI.MUNI_ARRAY[\"1555\"] = '1,北海道,1550,置戸町';")
    with pytest.raises(ValueError):
        parse_muni_js("GSI.MUNI_ARRAY = {};")

"""原産地のある市町村の報告書の検査(T-510〜T-516 / F-07)。"""

import json
import pathlib

import pytest

from archaeostone.area_documents import tally_area_documents
from archaeostone.municipality import parse_muni_js
from archaeostone.oai import OaiRecord, RecordShape
from archaeostone.sources import publishable_violations
from pipeline.build_area_documents import area_record

ROOT = pathlib.Path(__file__).resolve().parent.parent
MUNI_EXCERPT = ROOT / "tests" / "fixtures" / "gsi_muni_excerpt.js"
SHIPPED = ROOT / "public" / "data" / "area_documents.json"
TERMS = ["黒曜石", "黒耀石", "黒曜岩"]


def record(codes, title, shape=RecordShape.OAI_DC, url="https://example.test/1") -> OaiRecord:
    return OaiRecord(
        identifier=f"oai:{title}",
        datestamp=None,
        shape=shape,
        set_specs=tuple(codes),
        titles=(title,) if title else (),
        publishers=(),
        landing_url=url,
        doi=None,
        issued=None,
    )


@pytest.fixture(scope="module")
def table() -> dict:
    return parse_muni_js(MUNI_EXCERPT.read_text(encoding="utf-8"))


def test_t510_a_record_with_ward_and_city_codes_counts_once(table: dict) -> None:
    """T-510: 区と市の両方を持つレコードは、一原産地につき 1 回だけ数える。"""
    records = [
        record(["04", "04104", "04100"], "秋保の遺跡"),
        record(["04", "04100"], "仙台市の遺跡"),
        record(["04", "04101"], "青葉区の遺跡"),
    ]
    tallies = tally_area_documents(records, {"OBS-AKIU": ("04104", "04100")}, TERMS)
    assert tallies["OBS-AKIU"].documents == 2
    assert tallies["OBS-AKIU"].documents_by_code == {"04104": 1, "04100": 2}


def test_t511_withdrawn_records_are_not_counted() -> None:
    """T-511: メタデータの無いレコード(取り下げ)は数えない。"""
    records = [
        record(["20361"], "", shape=RecordShape.NO_METADATA),
        record(["20361"], "星ヶ塔遺跡"),
    ]
    tallies = tally_area_documents(records, {"OBS-HOSHIGATO": ("20361",)}, TERMS)
    assert tallies["OBS-HOSHIGATO"].documents == 1


def test_t512_titles_are_capped_but_the_count_is_not() -> None:
    """T-512: 題名の例は上限で止め、件数は数え続ける。題名に語が無いものは例に入れない。"""
    records = [record(["20350"], f"黒耀石原産地遺跡 第{i}次") for i in range(15)]
    records.append(record(["20350"], "大門遺跡"))
    tallies = tally_area_documents(records, {"OBS-HOSHIKUSO": ("20350",)}, TERMS, example_limit=12)
    tally = tallies["OBS-HOSHIKUSO"]
    assert tally.documents == 16
    assert tally.obsidian_title_count == 15
    assert len(tally.obsidian_titles) == 12
    assert all("黒耀石" in t["title"] for t in tally.obsidian_titles)


AREA = {"id": "OBS-X", "latitude": 34.0, "longitude": 131.0}


def test_t513_off_land_area_has_a_reason_and_no_zero(table: dict) -> None:
    """T-513: 市町村が決まらない原産地は理由を持ち、件数は 0 でなく null(姫島の実測)。"""
    out = area_record(AREA, {}, table, None)
    assert out["municipality"] is None
    assert "陸上" in out["municipality_reason"]
    assert out["documents"] is None
    assert out["obsidian_title_count"] is None
    assert out["municipality_provenance"]["muniCd"] is None


def test_t514_code_missing_from_the_name_table_is_reported(table: dict) -> None:
    """T-514: 名前の表に無いコードは、推測で名前を付けずに理由を書く。"""
    out = area_record(AREA, {"results": {"muniCd": "99999", "lv01Nm": "−"}}, table, None)
    assert out["municipality"] is None
    assert "99999" in out["municipality_reason"]


def test_t515_ward_record_keeps_both_codes_and_the_display_name(table: dict) -> None:
    """T-515: 区の原産地は区と市の両方のコードで引き、表示名は全角空白を半角にする。"""
    tallies = tally_area_documents(
        [record(["04100"], "黒曜石の研究")], {"OBS-X": ("04104", "04100")}, TERMS
    )
    out = area_record(AREA, {"results": {"muniCd": "04104", "lv01Nm": "秋保町湯元"}}, table, tallies["OBS-X"])
    assert out["municipality"]["name"] == "仙台市 太白区"
    assert out["municipality"]["matched_codes"] == ["04104", "04100"]
    assert out["documents"] == 1
    assert out["obsidian_titles"][0]["title"] == "黒曜石の研究"
    assert out["municipality_reason"] is None


def test_t516_shipped_file_covers_every_area_and_passes_the_gate() -> None:
    """T-516: 出荷ファイルは原産地 14 件すべてを持ち、市町村か理由のどちらか一方を持つ。"""
    payload = json.loads(SHIPPED.read_text(encoding="utf-8"))
    areas = payload["areas"]
    source_ids = {a["id"] for a in json.loads((ROOT / "public" / "data" / "source_areas.json").read_text(encoding="utf-8"))["source_areas"]}
    assert {a["id"] for a in areas} == source_ids
    for area in areas:
        assert (area["municipality"] is None) != (area["municipality_reason"] is None), area["id"]
        assert (area["documents"] is None) == (area["municipality"] is None), area["id"]
    assert publishable_violations(areas) == []
    himeshima = next(a for a in areas if a["id"] == "OBS-HIMESHIMA")
    assert himeshima["municipality"] is None

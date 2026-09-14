"""県別ヒスイ集計の札の位置の検査(T-520〜T-524 / F-06)。

**札の位置は県庁舎であって、出土地点ではない。** 個票は再配布できないので、
県より細かい位置は持たない。ネットワークには触らない(応答は実測のフィクスチャ)。
"""

import json
import pathlib

import pytest
import yaml

from archaeostone.source_areas import ResolutionOutcome, ResolutionRule, resolve_source_area
from archaeostone.sources import publishable_violations
from pipeline.build_jade_prefectures import build

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "jade_prefectures.yaml"
FIXTURE = ROOT / "tests" / "fixtures" / "gsi_prefecture_offices.json"
JADE = ROOT / "public" / "data" / "jade_aggregate.json"
SHIPPED = ROOT / "public" / "data" / "jade_prefectures.json"


@pytest.fixture(scope="module")
def entries() -> dict:
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))["prefectures"]


@pytest.fixture(scope="module")
def searches() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_t520_office_is_chosen_by_exact_title_not_the_top_hit(entries: dict, searches: dict) -> None:
    """T-520: 上位 1 件は県そのもの。完全一致がちょうど 1 件の「…庁舎」を選ぶ。"""
    for pref_id, entry in entries.items():
        candidates = searches[entry["query"]]["results"]
        assert candidates[0]["title"] != entry["title_must_contain"], "上位 1 件が既に庁舎なら対照にならない"
        result = resolve_source_area(pref_id, entry, candidates)
        assert result.outcome is ResolutionOutcome.RESOLVED, pref_id
        assert result.rule_kind is ResolutionRule.EXACT_AND_UNIQUE
        assert result.candidate_title == entry["title_must_contain"]
        assert result.candidate_index != 0


def test_t521_config_sheets_match_the_aggregate_exactly(entries: dict) -> None:
    """T-521: 設定のシート名は集成表のシート名と一字一句同じで、過不足が無い。"""
    sheets = {s["sheet"] for s in json.loads(JADE.read_text(encoding="utf-8"))["coverage"]["per_sheet"]}
    assert {e["sheet"] for e in entries.values()} == sheets


def test_t522_positive_control_prefecture_name_alone_does_not_match_the_niigata_sheet(entries: dict) -> None:
    """T-522(陽性対照): 県名で突き合わせると新潟のシートを落とす(シート名は「新潟県（上・中越）」)。"""
    sheets = {s["sheet"] for s in json.loads(JADE.read_text(encoding="utf-8"))["coverage"]["per_sheet"]}
    by_name = {e["name_ja"] for e in entries.values()}
    assert by_name != sheets
    assert "新潟県" not in sheets
    niigata = next(e for e in entries.values() if e["name_ja"] == "新潟県")
    assert "上越" in niigata["scope_note"] and "下越" in niigata["scope_note"]


def test_t523_build_from_fixtures_places_all_nine_and_passes_the_gate(searches: dict, entries: dict) -> None:
    """T-523: フィクスチャから作ると 9 県すべてに位置が付き、権利の門を通る。"""
    expect = {e["query"]: e["expect_pref_code"] for e in entries.values()}
    title_to_pref = {e["title_must_contain"]: e["expect_pref_code"] for e in entries.values()}
    payload = build(
        sleep=lambda _: None,
        search=lambda q: searches[q]["results"],
        reverse=lambda lat, lon: next(
            code for query, code in expect.items()
            for c in searches[query]["results"]
            if c["lat"] == lat and c["lon"] == lon
        ),
    )
    records = payload["prefectures"]
    assert len(records) == 9
    assert publishable_violations(records) == []
    for rec in records:
        assert rec["position_provenance"]["candidate_title"] in title_to_pref
        assert "出土地点ではない" in rec["position_meaning"]


def test_t524_shipped_positions_are_offices_inside_japan() -> None:
    """T-524: 出荷ファイルの位置は 9 県すべて県庁舎の候補から採られ、日本の範囲にある。"""
    records = json.loads(SHIPPED.read_text(encoding="utf-8"))["prefectures"]
    assert len(records) == 9
    for rec in records:
        assert rec["position_provenance"]["candidate_title"].endswith("庁舎")
        assert 24 < rec["latitude"] < 46 and 122 < rec["longitude"] < 154

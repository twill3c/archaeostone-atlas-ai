"""OAI レコードの解析の検査(T-050〜 / G-08)。

眼目は **三つの形を取り違えずに数え分けること**。実測(2026-09-08)では
1 応答に `oai_dc` 2,227 / `junii2` 150 / メタデータ無し 273(10.3%)が混在した。
一つの形だけを見る解析器は、残りを黙って落とす —— しかも出力は正常に見える。
"""

import pathlib

import pytest

from archaeostone.oai import (
    RecordShape,
    SetSpecKind,
    classify_set_spec,
    parse_page,
)

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "oai" / "page_real.xml"


@pytest.fixture(scope="module")
def records():
    return parse_page(FIXTURE.read_bytes())


def test_fixture_contains_all_three_shapes(records) -> None:
    """前提の固定(HC-070)。三形が揃っていなければ以下は空振りする。"""
    shapes = {r.shape for r in records}
    assert shapes == {
        RecordShape.OAI_DC,
        RecordShape.JUNII2,
        RecordShape.NO_METADATA,
    }, f"三形が揃っていない: {shapes}"


def test_t050_every_record_is_classified(records) -> None:
    """T-050: 全レコードがどれかの形に分類され、取りこぼしが無い。"""
    assert len(records) > 50
    counts = {shape: 0 for shape in RecordShape}
    for record in records:
        counts[record.shape] += 1
    assert sum(counts.values()) == len(records)
    # メタデータ無しが 0 だと、その経路が検査されていない。
    assert counts[RecordShape.NO_METADATA] > 0


def test_t051_no_metadata_records_still_carry_header(records) -> None:
    """T-051: メタデータ無しでも identifier と setSpec は読める。

    **取り下げられたレコードも「無かったこと」にしない。** 件数の分母に入る。
    """
    absent = [r for r in records if r.shape is RecordShape.NO_METADATA]
    assert absent
    for record in absent:
        assert record.identifier, "identifier が無い"
        assert record.titles == ()


def test_t052_oai_dc_records_have_titles_and_landing_url(records) -> None:
    dc = [r for r in records if r.shape is RecordShape.OAI_DC]
    assert dc
    with_title = [r for r in dc if r.titles]
    assert len(with_title) == len(dc), "題名が無い oai_dc レコードがある"
    with_url = [r for r in dc if r.landing_url]
    assert len(with_url) > len(dc) * 0.9, "着地 URL の取り出しが弱い"


def test_t053_identifier_overloading_is_untangled(records) -> None:
    """T-053: 無型で多値の `dc:identifier` から、種別ごとに正しく取り出す。

    実測: 1 レコードあたり平均 6.0 個の identifier に、URL・DOI・NCID・
    叢書名・巻号・日付が混在する。**1 個目を「識別子」として採ると叢書名を掴む。**
    """
    dc = [r for r in records if r.shape is RecordShape.OAI_DC]
    dois = [r.doi for r in dc if r.doi]
    assert dois, "DOI が 1 件も取れていない"
    for doi in dois:
        assert doi.startswith("10."), f"DOI らしくない: {doi}"
        assert "info:doi" not in doi, "接頭辞を外していない"

    for record in dc:
        if record.landing_url:
            assert record.landing_url.startswith("https://sitereports.nabunken.go.jp/")
            assert not record.landing_url.endswith(".pdf"), (
                "本文 PDF を着地 URL として採っている"
            )
        if record.issued:
            assert len(record.issued) == 10, f"日付らしくない: {record.issued}"


def test_t054_junii2_records_are_read_with_their_own_field_names(records) -> None:
    """T-054: junii2 は独自のフィールド名を持つ(`jtitle` / `dateofissued` / `URI`)。"""
    junii2 = [r for r in records if r.shape is RecordShape.JUNII2]
    assert junii2
    assert all(r.titles for r in junii2), "junii2 の題名が取れていない"
    assert any(r.landing_url for r in junii2), "junii2 の URI が取れていない"


# ── setSpec の分類 ──────────────────────────────────────


@pytest.mark.parametrize(
    "value,kind",
    [
        ("20", SetSpecKind.PREFECTURE),
        ("01", SetSpecKind.PREFECTURE),
        ("01363", SetSpecKind.MUNICIPALITY),
        ("20361", SetSpecKind.MUNICIPALITY),
        ("040000", SetSpecKind.OTHER_NUMERIC),
        ("1234567", SetSpecKind.OTHER_NUMERIC),
        ("J84604", SetSpecKind.NON_NUMERIC),
    ],
)
def test_t055_set_spec_is_classified_by_shape(value: str, kind: SetSpecKind) -> None:
    """T-055: setSpec を桁で分類する。**知らない形を黙って捨てない。**"""
    assert classify_set_spec(value) is kind


def test_t056_every_record_has_at_least_one_set_spec(records) -> None:
    """T-056: 実測 2026-09-08 では 2,650/2,650 件が最低 1 個を持っていた。

    地理コード化がここから無料で得られるという前提なので、崩れたら気づきたい。
    """
    without = [r for r in records if not r.set_specs]
    assert not without, f"setSpec の無いレコードが {len(without)} 件"


def test_t057_prefecture_codes_are_in_range(records) -> None:
    """T-057: 都道府県コードが 01〜47 の範囲にあること。"""
    seen = set()
    for record in records:
        for code in record.prefecture_codes:
            assert 1 <= int(code) <= 47, f"県コードが範囲外: {code}"
            seen.add(code)
    # 走査が空でないことの確認。1 ページに何県ぶん入るかは源の並び順しだいで、
    # このフィクスチャ(2026-09-08 取得の先頭ページ)では 3 県だった。
    # **観測する前に「5 県以上」と書いて落とした** —— 件数を定数で書かない(HC-016)。
    assert seen, "県コードを一つも取れていない"


def test_t058_municipality_codes_start_with_their_prefecture(records) -> None:
    """T-058: 市区町村コードの先頭 2 桁が、同じレコードの県コードと整合すること。

    整合しないレコードがあれば、setSpec を県と市区町村の両方に使う前提が崩れる。
    片方だけを信じる設計にしていると、黙ってずれる(kofun-atlas の HC 参照)。
    """
    mismatched = []
    checked = 0
    for record in records:
        prefectures = set(record.prefecture_codes)
        if not prefectures:
            continue
        for municipality in record.municipality_codes:
            checked += 1
            if municipality[:2] not in prefectures:
                mismatched.append((record.identifier, municipality, sorted(prefectures)))
    assert checked > 0, "市区町村コードを一つも検査していない"
    assert not mismatched, f"県と市区町村が食い違うレコード {len(mismatched)} 件: {mismatched[:3]}"


def test_t059_positive_control_unknown_metadata_shape_raises() -> None:
    """T-059(陽性対照): 知らないメタデータ形式は例外にする。

    黙って捨てる実装だと、源が新しい形式を足した日に静かに取りこぼす。
    """
    payload = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">'
        "<ListRecords><record><header>"
        "<identifier>oai:example/1</identifier><setSpec>20</setSpec>"
        "</header><metadata>"
        '<mods xmlns="http://www.loc.gov/mods/v3"><title>x</title></mods>'
        "</metadata></record></ListRecords></OAI-PMH>"
    ).encode()
    with pytest.raises(ValueError, match="未知のメタデータ形式"):
        parse_page(payload)


def test_t059_negative_control_known_shapes_do_not_raise(records) -> None:
    """T-059(陰性対照): 既知の三形は例外にならない。

    陽性対照だけを置くと、「何でも例外にする」実装でも緑になる(HC-074)。
    """
    assert len(records) > 50  # 実データを通して例外が出なかったこと自体が対照である

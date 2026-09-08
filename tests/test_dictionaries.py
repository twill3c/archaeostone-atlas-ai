"""材質辞書・時代辞書の検査(T-013 / T-014)。

辞書は抽出器と正規化器の両方が使う。**同じ語が二つの概念へ属していると、
抽出器はどちらとも取れる場面で黙って一方に倒れる** —— 検査は緑のままになる。
"""

import pytest

from archaeostone.dictionaries import (
    load_materials,
    load_periods,
    material_lookup,
)


def test_t013_material_ids_are_unique() -> None:
    materials = load_materials()
    assert materials, "材質辞書が空である"
    ids = [m["material_id"] for m in materials.values()]
    assert len(ids) == len(set(ids)), f"material_id が重複している: {ids}"


def test_t013_no_synonym_belongs_to_two_materials() -> None:
    """T-013: どの語も 2 つの材質へ同時に属さない。

    見るのは**材質をまたぐ**衝突である。同じ材質の中での重複は別の検査
    (`test_t013_no_material_repeats_its_own_label`)が見る —— 一つの assert に
    二つの主張を混ぜると、落ちたときにどちらが壊れたか言えなくなる。
    """
    materials = load_materials()
    owner: dict[str, str] = {}
    for key, entry in materials.items():
        terms = {
            term.strip().lower()
            for term in [entry["label_ja"], entry["label_en"], *entry.get("synonyms", [])]
        }
        for term in terms:
            assert term, f"{key} に空の同義語がある"
            assert owner.get(term, key) == key, (
                f"語 {term!r} が {owner.get(term)} と {key} の両方に属している"
            )
            owner[term] = key
    assert len(owner) > len(materials), "語が材質の数以下しかない(索引が空同然)"


def test_t013_no_material_repeats_its_own_label() -> None:
    """同義語が自分の見出し語をそのまま繰り返していないこと。

    冗長なだけに見えるが、放っておくと「同義語の件数」を数える検査が
    水増しされ、辞書がどれだけ表記ゆれを吸収できるかを測れなくなる。
    """
    for key, entry in load_materials().items():
        labels = {entry["label_ja"].strip().lower(), entry["label_en"].strip().lower()}
        for term in entry.get("synonyms", []):
            assert term.strip().lower() not in labels, (
                f"{key}: 同義語 {term!r} が見出し語の繰り返しになっている"
            )


def test_t013_lookup_resolves_every_declared_term() -> None:
    """辞書から作った索引が、宣言した全語を引けること。

    走査対象が空でないことも同時に確かめる(HC-041)。
    """
    materials = load_materials()
    lookup = material_lookup()
    assert len(lookup) >= len(materials), "索引が辞書より小さい"
    for key, entry in materials.items():
        for term in [entry["label_ja"], *entry.get("synonyms", [])]:
            assert lookup[term] == entry["material_id"], f"{term} を引けない"


def test_t013_positive_control_lookup_rejects_unrelated_terms() -> None:
    """陽性対照: 石材でない語を索引が拾わないこと。

    索引が「何でも引ける」形に壊れたら、上の検査は緑のまま通ってしまう。
    """
    lookup = material_lookup()
    for term in ["土器", "石器", "住居跡", "obsidianite", ""]:
        assert term not in lookup, f"{term!r} を石材として引いてしまう"


def test_t013_v1_scope_is_declared_for_every_material() -> None:
    """V1.0 の対象かどうかを全材質が明示すること(SPEC §9 の裏付け)。"""
    materials = load_materials()
    for key, entry in materials.items():
        assert isinstance(entry.get("v1_scope"), bool), f"{key} に v1_scope が無い"
    in_scope = {k for k, v in materials.items() if v["v1_scope"]}
    assert in_scope == {"obsidian", "jadeite"}, f"V1.0 対象が想定と違う: {in_scope}"


def _walk_periods(periods: dict):
    """時代とその細分を (経路, エントリ) で列挙する。"""
    for code, entry in periods.items():
        yield code, entry
        for phase_code, phase in (entry.get("phases") or {}).items():
            yield f"{code}_{phase_code}", phase


def test_t014_period_ranges_are_ordered() -> None:
    """T-014: 各コードが年代域を持ち、古い方(start)が大きいこと。"""
    doc = load_periods()
    periods = doc["periods"]
    assert periods, "時代辞書が空である"
    checked = 0
    for code, entry in _walk_periods(periods):
        start, end = entry.get("year_start_bp"), entry.get("year_end_bp")
        if start is None or end is None:
            # UNKNOWN だけが年代域を持たないことを確かめる。
            assert code == "UNKNOWN", f"{code} に年代域が無い"
            continue
        assert start > end, f"{code}: start_bp {start} は end_bp {end} より大きいはず"
        checked += 1
    assert checked >= 10, f"検査した時代が {checked} 件しかない(走査が空でないことの確認)"


def test_t014_phases_stay_inside_their_period() -> None:
    """細分の年代域が親の時代からはみ出さないこと。"""
    periods = load_periods()["periods"]
    seen_phases = 0
    for code, entry in periods.items():
        phases = entry.get("phases") or {}
        for phase_code, phase in phases.items():
            seen_phases += 1
            assert phase["year_start_bp"] <= entry["year_start_bp"], (
                f"{code}/{phase_code} の開始が親より古い"
            )
            assert phase["year_end_bp"] >= entry["year_end_bp"], (
                f"{code}/{phase_code} の終了が親より新しい"
            )
    assert seen_phases > 0, "細分を一つも検査していない"


def test_t014_authority_is_declared() -> None:
    """採用編年を明示していること(構想書 §6.3 の period_authority に相当)。

    年代は編年に依存するので、「誰の編年か」が書かれていない年代を出さない。
    """
    doc = load_periods()
    assert doc["authority"]["name"], "採用編年の名前が無い"
    assert doc["authority"]["note"], "採用編年の但し書きが無い"


@pytest.mark.parametrize("code", ["PALEOLITHIC", "JOMON", "YAYOI", "KOFUN", "UNKNOWN"])
def test_t014_required_period_codes_exist(code: str) -> None:
    """構想書 §6.1 の大区分のうち、V1.0 で必ず使うものが揃っていること。"""
    assert code in load_periods()["periods"]

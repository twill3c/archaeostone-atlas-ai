"""原産地の座標解決の検査(T-060〜 / G-03)。

**この検査の芯は「上位 1 件を正解にしない」ことである。**
実測(2026-09-08)では、和田峠の地名検索は 69 件を返し、上位 3 件は
青森県七戸町和田・山形県南陽市和田・福島県会津若松市和田だった。
長野県の和田峠は 66 番目である。同名の峠は全国に 5 か所ある。

ネットワークには触らない。応答は実測を落としたフィクスチャを使う。
"""

import json
import pathlib

import pytest

from archaeostone.source_areas import (
    ResolutionOutcome,
    ResolutionRule,
    load_source_area_config,
    resolve_source_area,
)

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "gsi_searches.json"


@pytest.fixture(scope="module")
def searches() -> dict:
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def config() -> dict:
    return load_source_area_config()


# ── 前提の固定 ──────────────────────────────────────────


def test_fixture_reproduces_the_ambiguity_we_are_defending_against(searches: dict) -> None:
    """前提の固定(HC-070/HC-079)。

    「上位 1 件を採らない」対照が意味を持つのは、上位 1 件が実際に**誤り**の
    ときだけである。それをここで表明する。表明が崩れたらフィクスチャを取り直す。
    """
    wada = searches["和田峠"]["results"]
    assert len(wada) >= 60, f"候補が {len(wada)} 件では曖昧さを再現していない"

    # 上位 1 件は「和田峠」ではなく別の「和田」である。
    assert "和田峠" not in wada[0]["title"], "上位 1 件が既に和田峠なら対照にならない"

    # 探している長野の和田峠は候補列の後方にある。
    # (県コードは名前の制約を満たす候補にだけ付けてある — 逆ジオの呼び出しを抑えるため)
    nagano = [i for i, r in enumerate(wada) if r.get("pref_code") == "20"]
    assert nagano, "長野県の候補が含まれていない"
    assert min(nagano) > 3, f"長野の候補が {min(nagano)} 番目では曖昧さが弱い"

    # 同名の峠が複数県にあることも押さえる(これが曖昧さの正体である)。
    with_code = {r["pref_code"] for r in wada if r.get("pref_code")}
    assert len(with_code) > 1, f"「和田峠」が 1 県にしか無いなら対照にならない: {with_code}"


# ── 解決の正常系 ────────────────────────────────────────


def test_t060_resolves_the_nagano_wada_pass_not_the_top_hit(
    config: dict, searches: dict
) -> None:
    """T-060: 県コードで絞って、長野の和田峠を選ぶ。"""
    entry = config["source_areas"]["OBS-WADATOGE"]
    result = resolve_source_area("OBS-WADATOGE", entry, searches["和田峠"]["results"])

    assert result.outcome is ResolutionOutcome.RESOLVED
    assert result.pref_code == "20"
    assert "和田峠" in result.candidate_title
    # 上位 1 件ではないことを明示的に押さえる。
    assert result.candidate_index > 0
    assert result.candidate_title != searches["和田峠"]["results"][0]["title"]


def test_t061_gazetteer_attested_names_resolve_on_the_first_candidate(
    config: dict, searches: dict
) -> None:
    """T-061: 地名情報に「黒曜石原産地」として載っている名は素直に解決する。"""
    entry = config["source_areas"]["OBS-HOSHIGATO"]
    result = resolve_source_area("OBS-HOSHIGATO", entry, searches["星ヶ塔"]["results"])
    assert result.outcome is ResolutionOutcome.RESOLVED
    assert result.candidate_title == "星ヶ塔黒曜石原産地遺跡"


def test_t062_every_resolution_records_its_provenance(config: dict, searches: dict) -> None:
    """T-062: 解決したものは必ず「どう選んだか」を持つ(G-03)。"""
    entry = config["source_areas"]["OBS-KASHIWATOGE"]
    result = resolve_source_area("OBS-KASHIWATOGE", entry, searches["柏峠"]["results"])
    assert result.outcome is ResolutionOutcome.RESOLVED

    prov = result.as_provenance()
    for key in ("method", "query", "candidate_index", "candidate_title", "rule"):
        assert prov.get(key), f"{key} が出所に無い"
    assert prov["method"] == "gsi_address_search"
    assert prov["query"] == "柏峠"


# ── 解決できない場合 ────────────────────────────────────


def test_t063_no_matching_prefecture_becomes_needs_review(config: dict) -> None:
    """T-063: 県が合う候補が無ければ needs_review。**推測で埋めない。**"""
    entry = config["source_areas"]["OBS-KASHIWATOGE"]  # 静岡県を期待する
    only_wakayama = [
        {"title": "柏峠", "lat": 33.94016, "lon": 135.09844, "pref_code": "30"}
    ]
    result = resolve_source_area("OBS-KASHIWATOGE", entry, only_wakayama)
    assert result.outcome is ResolutionOutcome.NO_MATCH
    assert result.latitude is None and result.longitude is None


def test_t064_empty_result_becomes_needs_review(config: dict) -> None:
    """T-064: 候補 0 件も needs_review。

    地名検索は不明な語にも 200 + `[]` を返す。空は**答え**なので、
    通信の失敗と混ぜない(HC-235 と同型)。
    """
    entry = config["source_areas"]["OBS-TSUMETAYAMA"]
    result = resolve_source_area("OBS-TSUMETAYAMA", entry, [])
    assert result.outcome is ResolutionOutcome.NO_CANDIDATES


def test_t065_title_constraint_rejects_same_prefecture_wrong_place(config: dict) -> None:
    """T-065(陽性対照): 県は合っていても名前が違う候補を採らない。

    県だけで絞ると、同じ県の無関係な地名を掴む。二条件の**両方**が必要である。
    """
    entry = config["source_areas"]["OBS-WADATOGE"]
    same_pref_wrong_name = [
        {"title": "長野県長野市松代", "lat": 36.5657, "lon": 138.1948, "pref_code": "20"}
    ]
    result = resolve_source_area("OBS-WADATOGE", entry, same_pref_wrong_name)
    assert result.outcome is ResolutionOutcome.NO_MATCH


def test_t066_positive_control_top_hit_policy_would_pick_the_wrong_place(
    config: dict, searches: dict
) -> None:
    """T-066(陽性対照): 上位 1 件を採る方針だと、実際に別地を掴む。

    方針の違いを検査が見分けられていることを示す。見分けられないなら、
    T-060 は「たまたま 1 位が正しかった」だけかもしれない。
    """
    entry = config["source_areas"]["OBS-WADATOGE"]
    naive = searches["和田峠"]["results"][0]

    # 上位 1 件は名前の制約すら満たさない —— つまり方針の違いは実在する。
    assert entry["title_must_contain"] not in naive["title"], (
        f"陽性対照が発火していない: 1 位 {naive['title']!r} が既に制約を満たす"
    )

    ours = resolve_source_area("OBS-WADATOGE", entry, searches["和田峠"]["results"])
    assert ours.outcome is ResolutionOutcome.RESOLVED
    assert ours.pref_code == "20"
    # 上位 1 件(青森県七戸町和田)と、選んだ点(長野の和田峠)は 4 度以上離れている。
    assert abs(ours.latitude - naive["lat"]) > 1.0, "1 位と同じ場所を選んでしまっている"


# ── 辞書そのものの検査 ──────────────────────────────────


def test_t067_every_source_area_declares_query_and_constraints(config: dict) -> None:
    """T-067: 全エントリが問い合わせ語と二つの制約を持つ。"""
    areas = config["source_areas"]
    assert len(areas) >= 10, f"原産地が {len(areas)} 件しかない"
    for area_id, entry in areas.items():
        for key in ("name_ja", "query", "title_must_contain", "expect_pref_code", "citations"):
            assert entry.get(key), f"{area_id} に {key} が無い"
        assert len(entry["expect_pref_code"]) == 2, f"{area_id} の県コードが 2 桁でない"


def test_t068_no_source_area_hardcodes_coordinates(config: dict) -> None:
    """T-068(陽性対照): 辞書に座標を書いていないこと。

    座標を書けるようにすると、いつか誰かが記憶から書く。**書く場所を作らない。**
    """
    for area_id, entry in config["source_areas"].items():
        for forbidden in ("latitude", "longitude", "lat", "lon"):
            assert forbidden not in entry, (
                f"{area_id} に {forbidden} がある。座標は地名検索から引くこと"
            )


def test_t069_every_citation_reference_exists(config: dict) -> None:
    """T-069: 参照している典拠が実在すること(G-03)。"""
    defined = set(config["citations"])
    assert defined, "典拠が定義されていない"
    used: set[str] = set()
    for area_id, entry in config["source_areas"].items():
        for cid in entry["citations"]:
            assert cid in defined, f"{area_id} が未定義の典拠 {cid} を参照している"
            used.add(cid)
    # 使われていない典拠は、消し忘れか参照漏れのどちらかなので報告する。
    unused = defined - used
    assert unused <= {"CIT-COLS-MAP01"}, f"参照されていない典拠がある: {sorted(unused)}"


def test_t070_every_citation_names_its_source_registry_entry(config: dict) -> None:
    """T-070: 典拠が源の登録簿の識別子を持つこと。

    これが無いと、公開ビルドの門(G-01)がその典拠の再配布可否を判定できない。
    """
    from archaeostone.sources import load_registry

    registry = load_registry()
    for cid, citation in config["citations"].items():
        source_id = citation.get("source_id")
        assert source_id, f"{cid} に source_id が無い"
        assert source_id in registry, f"{cid} が登録簿に無い源 {source_id} を指している"


# ── title_is_exact: 一意性で県の照合を代替する経路 ──────


def test_t071_exact_mode_resolves_without_a_prefecture(config: dict, searches: dict) -> None:
    """T-071: 名称が対象を一意に指す場合、県が確認できなくても確定する。

    実測(2026-09-09): 「姫島の黒曜石産地」(33.73194, 131.64276)を逆ジオコード
    すると None が返る。小島の海岸の露頭で、逆ジオコーダの陸域マスクが届かない。
    県コードの照合は**同名別地を切り分けるため**の規則なので、切り分ける必要が
    無いところでは要求しない。
    """
    entry = config["source_areas"]["OBS-HIMESHIMA"]
    assert entry.get("title_is_exact") is True, "この検査は exact 経路のものである"

    candidates = searches["姫島の黒曜石産地"]["results"]
    result = resolve_source_area("OBS-HIMESHIMA", entry, candidates)

    assert result.outcome is ResolutionOutcome.RESOLVED
    assert result.candidate_title == "姫島の黒曜石産地"
    # 県は確認できていない。分かっていないことを「分かった」と書かない。
    assert result.pref_code is None
    # 採った規則は**構造化された種別**で確かめる。表示用の文は言い換えられるので
    # 検査の根拠にしない(HC-068)。
    assert result.rule_kind is ResolutionRule.EXACT_AND_UNIQUE
    assert result.as_provenance()["rule_kind"] == "exact_and_unique"


def test_t072_exact_mode_prerequisite_the_prefecture_check_really_fails(
    config: dict, searches: dict
) -> None:
    """T-072: この経路が必要である前提を固定する。

    exact 経路は「県で確認できない」ときの逃げ道である。もし県で確認できるなら、
    逃げ道は不要であり、置いてあること自体が緩みになる。だから
    **本当に確認できないこと**をここで表明する(HC-070/HC-079)。
    """
    candidates = searches["姫島の黒曜石産地"]["results"]
    exact = [c for c in candidates if c["title"] == "姫島の黒曜石産地"]
    assert len(exact) == 1, "完全一致が 1 件でなければ前提が崩れている"
    assert exact[0].get("pref_code") is None, (
        "逆ジオコードで県が取れるなら exact 経路は不要である。"
        "フィクスチャを取り直し、通常経路へ戻すこと"
    )


def test_t073_positive_control_exact_mode_is_not_a_loophole(
    config: dict, searches: dict
) -> None:
    """T-073(陽性対照): exact 経路を開けても、和田峠は上位 1 件を掴まない。

    これが本検査の芯である。逃げ道を作るときは、**その逃げ道が通ってはならない
    ものを通さないこと**を対で示す。和田峠は完全一致が複数あるので一意性を満たさず、
    exact 経路には入れない。
    """
    entry = dict(config["source_areas"]["OBS-WADATOGE"])
    entry["title_is_exact"] = True  # 意図的に開ける

    candidates = searches["和田峠"]["results"]
    exact_matches = [c for c in candidates if c["title"] == "和田峠"]
    assert len(exact_matches) > 1, (
        f"「和田峠」の完全一致が {len(exact_matches)} 件では対照にならない"
    )

    result = resolve_source_area("OBS-WADATOGE", entry, candidates)
    assert result.outcome is ResolutionOutcome.NO_MATCH, (
        "一意でない完全一致が exact 経路を通ってしまった"
    )


def test_t074_exact_mode_requires_full_equality_not_containment(config: dict) -> None:
    """T-074(陽性対照): exact 経路は部分一致では通らない。

    含む/等しいを取り違えると、「姫島の黒曜石産地の駐車場」のような
    別の地物が一意に見えて通ってしまう。
    """
    entry = config["source_areas"]["OBS-HIMESHIMA"]
    near_miss = [
        {"title": "姫島の黒曜石産地入口", "lat": 33.73, "lon": 131.64, "pref_code": "44"}
    ]
    result = resolve_source_area("OBS-HIMESHIMA", entry, near_miss)
    assert result.outcome is ResolutionOutcome.NO_MATCH


def test_t075_only_declared_entries_use_the_exact_path(config: dict) -> None:
    """T-075: exact 経路を使うエントリが、意図した 1 件だけであること。

    逃げ道が黙って増えていないかを見る。増やすなら、増やした理由が
    `note` に書かれているはずである。
    """
    using = {
        area_id
        for area_id, entry in config["source_areas"].items()
        if entry.get("title_is_exact")
    }
    assert using == {"OBS-HIMESHIMA"}, f"exact 経路を使うエントリが変わった: {using}"
    for area_id in using:
        assert config["source_areas"][area_id].get("note"), f"{area_id} に理由が無い"

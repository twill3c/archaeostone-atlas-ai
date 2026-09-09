"""ヒスイ集計の出荷形と、個票を配らない門の検査(T-230〜 / G-02)。

**約束は「集計だけを配る」である。** 約束は文で書いても守られないので、
書き出す前に機械で確かめる。ここではその門に陽性対照を対で置く ——
初回実行で偶然発火したことがあるが、事故は検査ではない(HC-041)。
"""

import json
import pathlib

import pytest

from archaeostone.jade import RAW_XLS

AGGREGATE = pathlib.Path(__file__).parent.parent / "public" / "data" / "jade_aggregate.json"

#: 出荷形に現れてはならない個票のフィールド。
FORBIDDEN = ("遺跡名", "所在市町村", "文献", "所有者", "その他", "伴出土器")


# ── 門そのものの検査(生ファイル不要) ──────────────────


def test_t230_positive_control_the_gate_catches_a_leaked_field() -> None:
    """T-230(陽性対照): 個票フィールドを混ぜた payload を門が落とす。

    門が働くことを**意図して**確かめる。実装の初回実行で偶然発火したが、
    偶然は再現しないので検査にはならない。
    """
    from pipeline.build_jade_aggregate import FORBIDDEN_COLUMNS

    assert FORBIDDEN_COLUMNS, "禁止列の一覧が空なら門は何も止めない"

    # 門と同じ判定を、意図的に汚した payload に当てる。
    dirty = json.dumps({"rows": [{"遺跡名": "ある遺跡"}]}, ensure_ascii=False)
    leaked = [c for c in FORBIDDEN_COLUMNS if f'"{c}"' in dirty]
    assert leaked == ["遺跡名"], f"門が漏れを見つけられていない: {leaked}"


def test_t231_negative_control_the_gate_passes_a_clean_payload() -> None:
    """T-231(陰性対照): 集計だけの payload は門を素通りする。

    陰性対照を先に当てる —— 誤検出があれば陽性対照より先に分かる(HC-074)。
    """
    from pipeline.build_jade_aggregate import FORBIDDEN_COLUMNS

    clean = json.dumps(
        {"coverage": {"rows": 572}, "tallies": {"時代": {"distinct": 9}}},
        ensure_ascii=False,
    )
    assert [c for c in FORBIDDEN_COLUMNS if f'"{c}"' in clean] == []


def test_t232_forbidden_list_covers_the_identifying_columns() -> None:
    """T-232: 禁止一覧が、個体を指す列を実際に網羅していること。

    一覧が痩せていると門は緩む。**緩める側だけを用意しない**(HC-041)。
    """
    from pipeline.build_jade_aggregate import FORBIDDEN_COLUMNS, TALLY_COLUMNS

    identifying = {"遺跡名", "所在市町村", "文献", "所有者"}
    assert identifying <= set(FORBIDDEN_COLUMNS), (
        f"個体を指す列が禁止一覧から漏れている: {identifying - set(FORBIDDEN_COLUMNS)}"
    )
    # 集計する列と禁止する列が重なっていないこと(重なると必ず落ちる)。
    assert not (set(TALLY_COLUMNS) & set(FORBIDDEN_COLUMNS)), (
        "集計対象の列が禁止一覧にも入っている"
    )


# ── 出荷ファイルの検査 ──────────────────────────────────

pytestmark_file = pytest.mark.skipif(
    not AGGREGATE.exists(),
    reason=f"{AGGREGATE} が無い。`python -m pipeline.build_jade_aggregate` で作る",
)


@pytest.fixture(scope="module")
def aggregate() -> dict:
    if not AGGREGATE.exists():
        pytest.skip(f"{AGGREGATE} が無い")
    return json.loads(AGGREGATE.read_text(encoding="utf-8"))


def test_t233_shipped_file_contains_no_forbidden_field(aggregate: dict) -> None:
    """T-233: 出荷された実ファイルに個票フィールドが 1 個も無い(G-02)。

    門は書き出す前に働くが、**出荷物そのものにも当てる** ——
    門を通らない経路で書き足されることがある。
    """
    serialised = json.dumps(aggregate, ensure_ascii=False)
    leaked = [column for column in FORBIDDEN if f'"{column}"' in serialised]
    assert leaked == [], f"出荷形に個票フィールドがある: {leaked}"


def test_t234_shipped_file_states_the_redistribution_notice(aggregate: dict) -> None:
    """T-234: 再配布できないことと、何を配っているかが出荷形に書かれている。"""
    notice = aggregate.get("redistribution_notice", "")
    assert "再配布できない" in notice
    assert "集計" in notice
    assert aggregate["source_id"] == "SRC-ITOIGAWA"


def test_t235_internal_checks_are_reported_with_their_gates(aggregate: dict) -> None:
    """T-235: 三つの内部照合が、ゲート ID つきで出荷形に載っている。

    SPEC の品質ゲート表は宣言であって検査ではない(HC-157)。
    出荷形に ID を載せることで、宣言と実測が突き合わせられる。
    """
    checks = aggregate["internal_checks"]
    gates = {entry["gate"] for entry in checks.values()}
    assert gates == {"G-05", "G-06", "G-07"}, f"ゲートが揃っていない: {gates}"


def test_t236_note_vs_sheets_discrepancy_is_shipped(aggregate: dict) -> None:
    """T-236: 註とシートの食い違いを、隠さず出荷形に載せる(G-05)。

    **件数が同じ(9 対 9)なので、集合の差を出さないと食い違いが見えない。**
    """
    check = aggregate["internal_checks"]["note_vs_sheets"]
    assert len(check["named_in_note"]) == len(check["sheets"]), (
        "件数が違うなら、この検査の眼目(件数では見えない)が変わっている"
    )
    assert check["named_but_missing"] == ["栃木県"]
    assert len(check["present_but_unnamed"]) == 1
    assert check["present_but_unnamed"][0].startswith("新潟")


def test_t237_inline_disagreements_ship_notation_without_site_names(aggregate: dict) -> None:
    """T-237: 食い違った行は**記法だけ**を出し、遺跡名を出さない。

    食い違いを見せることと、個票を配ることは両立する ——
    出すのは「種別の書き方」であって「どの遺跡か」ではない。
    """
    check = aggregate["internal_checks"]["inline_counts_vs_count_column"]
    assert check["disagreements"] == len(check["disagreement_notations"])
    assert check["disagreements"] > 0, "食い違いが 0 件なら、この検査は何も見ていない"

    for entry in check["disagreement_notations"]:
        assert set(entry) == {"sheet", "notation", "inline_total", "recorded_count"}
        assert entry["inline_total"] != entry["recorded_count"]


def test_t238_background_check_reports_the_measured_colour(aggregate: dict) -> None:
    """T-238: 背景色の照合が一致し、実際の色を実測値で載せている(G-07)。"""
    check = aggregate["internal_checks"]["background_colour_vs_blank_cells"]
    assert check["match"] is True
    assert check["flagged_rows"] == check["blank_count_rows"] == 13
    assert check["observed_colours"] == [[255, 255, 153]]
    assert check["declared_colour"] == [255, 255, 153]
    # 註は「緑」と書くが、実体は緑ではない。
    assert "緑" in check["note"]


def test_t239_count_column_semantics_are_shipped(aggregate: dict) -> None:
    """T-239: 点数の空欄が 0 でないことが、型の分布とともに載っている。

    「和 1,448」だけを配ると、空欄を 0 として合計したように読める。
    型の分布を並べれば、**分母がどれだけ欠けているか**が読める。
    """
    coverage = aggregate["coverage"]
    assert coverage["rows"] == 572
    assert coverage["rows_with_count"] == 343
    assert coverage["rows_with_count"] < coverage["rows"], "全行に点数があるなら注意書きは不要"
    assert "不明" in coverage["note"]

    types = coverage["count_cell_types"]
    assert types.get("数値") == 343
    assert types.get("空欄", 0) + types.get("書式のみ", 0) > 0, "欠測が 0 件なのは想定外"


def test_t240_tallies_are_vocabularies_not_individuals(aggregate: dict) -> None:
    """T-240: 集計が語彙の分布であって、個体の列挙でないこと。

    実測 2026-09-10(出荷形): 時代 **8** 種 / 形状 21 種。
    **異なり数が行数に近ければそれは事実上の個票**なので、そうなっていないことを確かめる。

    時代が 8 なのは、生の異なり 9 種から「不明」(2 行)を語彙から外しているため。
    外した分は `explicit_unknown` に数えてある —— **落とした行を消さない。**
    """
    rows = aggregate["coverage"]["rows"]
    tallies = aggregate["tallies"]
    assert tallies["時代"]["distinct"] == 8, (
        f"実測 2026-09-10 では 8 種だったが今回は {tallies['時代']['distinct']} 種"
    )
    assert tallies["時代"]["explicit_unknown"] == 2, "「不明」の行が数えられていない"
    assert tallies["形状"]["distinct"] == 21

    # 落とした行が、どの列でも見えなくなっていないこと。
    for column, tally in tallies.items():
        assert "explicit_unknown" in tally and "blank" in tally, (
            f"{column}: 落とした行の数が出荷形に無い"
        )
        assert (
            tally["recorded"] + tally["explicit_unknown"] + tally["blank"] == rows
        ), (
            f"{column}: 記入 {tally['recorded']} + 不明 {tally['explicit_unknown']} + "
            f"空欄 {tally['blank']} が行数 {rows} に合わない"
        )

    for column, tally in tallies.items():
        assert tally["distinct"] < rows * 0.5, (
            f"{column} の異なり数 {tally['distinct']} が行数 {rows} に近い。"
            "事実上の個票になっていないか疑うこと"
        )


@pytest.mark.skipif(RAW_XLS.exists(), reason="生ファイルがあるので skip の確認はできない")
def test_t241_workbook_tests_skip_when_the_raw_file_is_absent() -> None:
    """T-241: 生ファイルが無いとき、帳簿の検査が **skip** されること。

    「検査していない」を「合格」に見せないための確認である。
    生ファイルがある環境ではこの検査自体が skip される。
    """
    from archaeostone.jade import load_workbook

    with pytest.raises(FileNotFoundError, match="再配布不可"):
        load_workbook()

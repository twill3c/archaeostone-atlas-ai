"""ヒスイ集成表の構造と、源の内部にある非循環照合(T-210〜 / G-05 / G-07)。

**生ファイルはリポジトリに無い**(再配布不可 — SPEC §2.1)。だから
`python -m pipeline.acquisition.itoigawa` で手元に取得したときだけ走る。
無いときは skip し、**「検査していない」ことを「合格」に見せない**。

ここで使う照合は三つとも**源の内部にある**ので循環しない(HC-045)。

1. **註が挙げる県 と 実データシート** の集合が一致するか。
   注意: どちらも 9 件なので**件数だけでは食い違いが見えない**。集合で比べる
2. **種別に埋まった内訳の和 と 点数** が一致するか
3. **背景色つきの行 と 点数セルが BLANK の行** が一致するか。
   註は「緑の欄」と書くが実体は RGB(255,255,153) —— 註と書式も食い違っている
"""

import pathlib

import pytest

from archaeostone.jade import (
    RAW_XLS,
    BackgroundFlag,
    load_workbook,
    note_prefectures,
    data_sheet_names,
    header_row_index,
    read_sheet,
    inline_count_disagreements,
    background_flagged_rows,
    blank_count_rows,
)

pytestmark = pytest.mark.skipif(
    not RAW_XLS.exists(),
    reason=(
        f"{RAW_XLS} が無い。再配布不可なのでリポジトリに含めていない。"
        "`python -m pipeline.acquisition.itoigawa` で取得すると走る"
    ),
)


@pytest.fixture(scope="module")
def workbook():
    return load_workbook()


# ── 構造 ────────────────────────────────────────────────


def test_t210_workbook_shape(workbook) -> None:
    """T-210: 14 シート = 9 データ + 4 文献 + 註。実測 2026-09-08。"""
    assert workbook.nsheets == 14
    assert len(data_sheet_names(workbook)) == 9
    assert len([n for n in workbook.sheet_names() if n.endswith("文献")]) == 4
    assert "註" in workbook.sheet_names()


def test_t211_header_row_is_not_uniform(workbook) -> None:
    """T-211: 見出し行の位置が一様でない。新潟だけ 1 行目、他は 0 行目。

    **0 行目を決め打ちすると新潟のシートだけ注記を見出しとして読む** ——
    しかも例外にならず、列が全部ずれた表として通る。
    """
    rows = {name: header_row_index(workbook.sheet_by_name(name)) for name in data_sheet_names(workbook)}
    niigata = [n for n in rows if n.startswith("新潟")]
    assert len(niigata) == 1, f"新潟のシートが {len(niigata)} 枚"
    assert rows[niigata[0]] == 1, "新潟の見出しは 1 行目のはず"
    for name, row in rows.items():
        if name != niigata[0]:
            assert row == 0, f"{name} の見出しが {row} 行目"


def test_t212_column_sets_differ_between_sheets(workbook) -> None:
    """T-212: 列構成が 3 通りあり、**同じ列数でも中身が違う**。

    北海道・青森の 12 列目は `伴出土器`、埼玉・東京・千葉の 12 列目は `石材`。
    **位置で読むと黙って混ざる。** だから見出し名で対応づける。
    """
    twelve_column: dict[str, str] = {}
    for name in data_sheet_names(workbook):
        sheet = workbook.sheet_by_name(name)
        header = [str(c.value).strip() for c in sheet.row(header_row_index(sheet))]
        if len(header) == 12:
            twelve_column[name] = header[11]

    assert len(twelve_column) >= 5, f"12 列のシートが {len(twelve_column)} 枚"
    assert len(set(twelve_column.values())) > 1, (
        f"12 列目が全部同じなら、位置で読んでも混ざらない: {twelve_column}"
    )
    assert set(twelve_column.values()) == {"伴出土器", "石材"}, twelve_column


def test_t213_every_sheet_has_the_common_columns(workbook) -> None:
    """T-213: 全シートに共通する 11 列が揃っている。"""
    common = {
        "遺跡名", "所在市町村", "時代", "時期", "種別",
        "形状", "点数", "出土状況", "所有者", "文献", "その他",
    }
    for name in data_sheet_names(workbook):
        sheet = workbook.sheet_by_name(name)
        header = {str(c.value).strip() for c in sheet.row(header_row_index(sheet))}
        missing = common - header
        assert not missing, f"{name} に {sorted(missing)} が無い"


def test_t214_total_data_rows(workbook) -> None:
    """T-214: データ行の総数。実測 2026-09-08 で 572 行。

    源が更新されれば変わるので、**一致ではなく下限**で押さえ、
    実測値はここに日付つきで残す。
    """
    total = sum(len(read_sheet(workbook, name)) for name in data_sheet_names(workbook))
    assert total >= 500, f"データ行が {total} 行しかない"
    assert total == 572, (
        f"実測 2026-09-08 では 572 行だったが今回は {total} 行。"
        "源が更新された可能性がある(SPEC §2.7 を測り直すこと)"
    )


# ── 照合 1: 註と実シート(G-05) ─────────────────────────


def test_t215_note_and_sheets_disagree_in_a_known_way(workbook) -> None:
    """T-215: 註が挙げる県と実シートの差が、既知の 2 件であること(G-05)。

    **件数だけでは食い違いが見えない** —— 註 9 件・シート 9 件で同数である。
    集合で比べて初めて、栃木が欠け新潟が余ることが分かる。
    """
    named = note_prefectures(workbook)
    sheets = data_sheet_names(workbook)

    # まず「同数だから一致」と読めてしまうことを表明する。
    assert len(named) == len(sheets) == 9, (
        f"註 {len(named)} 件 / シート {len(sheets)} 件 —— "
        "同数でなくなったら、この検査の眼目(件数では見えない)が変わっている"
    )

    named_only = [n for n in named if n not in sheets]
    sheets_only = [n for n in sheets if n not in named]

    assert named_only == ["栃木県"], f"註にあってシートが無い県: {named_only}"
    assert len(sheets_only) == 1 and sheets_only[0].startswith("新潟"), (
        f"シートにあって註に無い県: {sheets_only}"
    )


# ── 照合 2: 内訳の和と点数(G-06) ───────────────────────


def test_t216_inline_counts_mostly_agree_with_the_count_column(workbook) -> None:
    """T-216: 種別の内訳の和が点数と一致する(G-06)。

    実測 2026-09-10(実装後): 内訳が読めて点数もある **34 行**のうち、
    一致 29 / 不一致 5。

    **探索時の数(照合 31 / 一致 26 / 解析不能 5)とは違う。** 探索の規則を
    そのまま写さず、二点直して昇格させたためである(HC-069):

    * 形 A(``勾玉(2),小玉(1)``)に対応した → 北海道の 3 行が解析不能から
      照合へ移り、3 行とも点数と一致した
    * 全角数字を個数と見ないようにした → ``樽型大珠・３孔`` が走査対象外へ
      (``fullwidth_only`` で数える)

    **不一致の 5 行は両方で同一**である。規則を直しても食い違いが動かないことが、
    それが**源の中の食い違い**であって解析器の誤りでないことを示している。
    """
    report = inline_count_disagreements(workbook)

    assert report.compared == 34, (
        f"実測 2026-09-10 では照合 34 行だったが今回は {report.compared} 行"
    )
    assert report.agreements == 29, (
        f"実測 2026-09-10 では一致 29 行だったが今回は {report.agreements} 行"
    )

    # 不一致は少数にとどまるはず。多ければ解析器を疑う。
    rate = report.disagreements_count / report.compared
    assert rate < 0.25, (
        f"不一致率 {rate:.1%} は高すぎる({report.disagreements_count}/{report.compared})。"
        "源の食い違いではなく解析器の誤りを疑うこと"
    )

    # 実測との突き合わせ。ずれたら源が動いたか解析器が変わった。
    assert report.disagreements_count == 5, (
        f"実測 2026-09-10 では不一致 5 件だったが今回は {report.disagreements_count} 件: "
        f"{[(d.sheet, d.row) for d in report.disagreements]}"
    )


def test_t217_disagreements_are_reported_not_silently_dropped(workbook) -> None:
    """T-217: 不一致を黙って捨てず、行ごとに報告すること。

    捨てると「照合した」と「食い違いが無かった」が区別できなくなる。
    """
    report = inline_count_disagreements(workbook)
    for disagreement in report.disagreements:
        assert disagreement.sheet
        assert disagreement.row >= 0
        assert disagreement.inline_total != disagreement.recorded_count
        assert disagreement.raw_kind


def test_t218_unparsed_and_skipped_rows_are_counted(workbook) -> None:
    """T-218: 読めなかった行・読まなかった行を、どちらも数えること。

    0 件にしておくと「全部読めた」と読めてしまう。実測 2026-09-10:

    * ``unparsed`` = 1 …… ``大珠(3穿孔を含む)``(括弧の中の数字が個数でない)
    * ``fullwidth_only`` = 1 …… ``樽型大珠・３孔``(「３孔」は穿孔の数)

    **後者は「失敗」ではなく「個数の記法ではない」**ので分けて数える。
    一緒にすると、解析器の弱点と源の書き方の違いが区別できなくなる。
    """
    report = inline_count_disagreements(workbook)
    assert report.unparsed == 1, (
        f"実測 2026-09-10 では解析不能 1 件だったが今回は {report.unparsed} 件"
    )
    assert report.fullwidth_only == 1, (
        f"実測 2026-09-10 では全角数字のみ 1 件だったが今回は {report.fullwidth_only} 件"
    )
    # 内訳が読めたのに点数が無い行は、実測では 0 件。
    assert report.without_count == 0, (
        f"内訳は読めたが点数が無い行が {report.without_count} 件ある"
    )


# ── 照合 3: 背景色と BLANK(G-07) ───────────────────────


def test_t219_background_colour_matches_blank_count_cells(workbook) -> None:
    """T-219: 背景色つきの行 と 点数が BLANK の行 が完全に一致する(G-07)。

    これは**源の内部にある非循環の照合**である。書式(背景色)と
    セルの型(BLANK = 書式あり・値なし)は別の経路で決まるのに、
    同じ 13 行を指す —— 行全体に色を塗ったので、空の点数セルにも書式が付いた。

    註は「緑の欄」と書くが実体は RGB(255,255,153) の淡い黄色である。
    **註と書式も食い違っている**ので、色の名前で探してはならない。
    """
    flagged = background_flagged_rows(workbook)
    blanks = blank_count_rows(workbook)

    assert flagged, "背景色つきの行が 1 行も無い"
    assert flagged == blanks, (
        "背景色つきの行と点数が BLANK の行が一致しない\n"
        f"  色つきのみ: {sorted(set(flagged) - set(blanks))}\n"
        f"  BLANK のみ: {sorted(set(blanks) - set(flagged))}"
    )

    # 実測 2026-09-08: 新潟のシートだけに 13 行。
    assert len(flagged) == 13, f"実測では 13 行だったが今回は {len(flagged)} 行"
    assert {sheet for sheet, _row in flagged} == {
        n for n in data_sheet_names(workbook) if n.startswith("新潟")
    }


def test_t220_flagged_rows_are_production_sites(workbook) -> None:
    """T-220: 色つきの行が、註の言う「製作を確認できている遺跡」の性質を持つこと。

    註の主張(製作遺跡)を、**別のフィールド**(種別)で裏づける。
    実測では 13 行すべての種別に「未成品」「原石」「敲石」のいずれかが現れる ——
    書式だけを信じずに、意味の側からも確かめる。
    """
    flagged = background_flagged_rows(workbook)
    assert flagged

    production_words = ("未成品", "原石", "敲石", "角礫")
    for sheet_name, row_index in flagged:
        rows = read_sheet(workbook, sheet_name)
        record = next(r for r in rows if r["row_index"] == row_index)
        kind = record.get("種別") or ""
        assert any(word in kind for word in production_words), (
            f"{sheet_name} r{row_index}: 種別 {kind!r} に製作を示す語が無い"
        )


def test_t221_background_flag_is_declared_not_guessed(workbook) -> None:
    """T-221: 旗の値が、色の名前ではなく**実測した RGB** で決まっていること。"""
    assert BackgroundFlag.PRODUCTION_SITE.rgb == (255, 255, 153)
    # 註は「緑」と書いているが、実体は緑ではない。
    red, green, blue = BackgroundFlag.PRODUCTION_SITE.rgb
    assert not (green > red + 40 and green > blue + 40), (
        "この色は緑ではない。註の記述(緑の欄)と書式が食い違っている"
    )

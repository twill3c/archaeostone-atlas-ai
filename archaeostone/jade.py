"""糸魚川市ヒスイ出土情報集成表の解析(F-05 / G-05 / G-06 / G-07)。

**この表は再配布できない**(SPEC §2.1)。生ファイルも個票もリポジトリに入れない。
公開するのは集計統計だけである(SPEC §6.3)。ここにあるのは解析器と検査だけで、
生ファイルは ``python -m pipeline.acquisition.itoigawa`` で手元に作る。

実測(2026-09-08 / 2026-09-10)で分かった癖を、取り違えないように書いてある。

* **見出し行の位置が一様でない。** 新潟のシートだけ 0 行目が注記で見出しは 1 行目。
  0 行目を決め打ちすると、そのシートだけ列が全部ずれた表として**例外にならずに通る**
* **列構成が 3 通り(11 / 12 / 13 列)あり、同じ列数でも中身が違う。**
  北海道・青森の 12 列目は ``伴出土器``、埼玉・東京・千葉の 12 列目は ``石材``。
  位置で読むと黙って混ざるので、**見出し名で対応づける**
* **個数の記法がセルごとに二形ある**(:func:`parse_inline_counts`)
* **13 行が背景色でのみ「製作遺跡」を示す。** 註は「緑の欄」と書くが実体は
  RGB(255,255,153) の淡い黄色である。色の名前で探してはならない
* ``点数`` の空欄は 0 ではなく**不明**(註 2「不明な箇所は空欄とした」)
"""

from __future__ import annotations

import dataclasses
import enum
import pathlib
import re
from typing import Any

import xlrd

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW_XLS = REPO_ROOT / "data" / "raw" / "itoigawa" / "jade_occurrences.xls"

NOTE_SHEET = "註"
BIBLIOGRAPHY_SUFFIX = "文献"
SITE_NAME_COLUMN = "遺跡名"
COUNT_COLUMN = "点数"
KIND_COLUMN = "種別"

#: xlrd がセルに付ける型。BLANK は「書式はあるが値が無い」。
CELL_EMPTY = 0
CELL_TEXT = 1
CELL_NUMBER = 2
CELL_BLANK = 6

#: 背景色が無いことを表す索引(xlrd の既定)。
NO_FILL_COLOUR_INDEX = 64


class BackgroundFlag(enum.Enum):
    """背景色が担っている意味。

    **書式にしか存在しない情報**なので、値は実測した RGB で持つ。
    註は「緑の欄」と書いているが実体は淡い黄色で、註と書式が食い違っている。
    """

    PRODUCTION_SITE = (255, 255, 153)
    """新潟のシートで「翡翠製玉類の製作を確認できている遺跡」を示す。"""

    @property
    def rgb(self) -> tuple[int, int, int]:
        return self.value


# ── 記法の解析 ──────────────────────────────────────────

#: 内訳の区切り。源は同じ意味に全角読点・半角読点・中黒の三つを使う。
_SEPARATORS = re.compile(r"[、,・]")

#: 括弧とその中身。
_PARENTHETICAL = re.compile(r"[(（][^)）]*[)）]")

#: 形 A ―― 品目名のあと、括弧の中が個数(``勾玉(2)``)。
#: 名前に数字も括弧も含まないことを要求する。
_FORM_A = re.compile(r"^(?P<name>[^()（）0-9]+)[(（](?P<count>[0-9]+)[)）]$")

#: 形 B ―― 裸の数字が個数(``大珠1``)。括弧を落としてから当てる。
_FORM_B = re.compile(r"^(?P<name>[^0-9]+?)(?P<count>[0-9]+)$")

#: 半角数字だけを数える。**Python の ``\d`` は全角数字にも当たる**ので使わない ——
#: ``樽型大珠・３孔`` の「３」は個数ではない(「孔」は穿孔の数で品目の個数ではない)。
_ASCII_DIGIT = re.compile(r"[0-9]")

#: 全角数字。個数としては読まないが、**黙って無視せず数える** ——
#: 数えないと「読み落とした行」と「そういう行が無い」が区別できなくなる。
_FULLWIDTH_DIGIT = re.compile(r"[０-９]")


def _split_parts(text: str) -> list[str]:
    return [part.strip() for part in _SEPARATORS.split(text) if part.strip()]


def parse_inline_counts(kind: str) -> list[tuple[str, int]] | None:
    """``種別`` に埋まった内訳を (品目, 個数) の列にする。読めなければ ``None``。

    記法は**セルごとに二形**ある。実測 2026-09-10:

    * 形 A ―― ``勾玉(2),小玉(1)``  括弧の中が個数(北海道のシート)
    * 形 B ―― ``大珠1、垂玉2``      裸の数字が個数、括弧は注記(青森のシート)

    どちらの形かは**セルの全部分が同じ形に当たるか**で決める。一部だけなら、
    括弧が個数か注記かを決められないので ``None`` を返す。

    ``None`` は「読めなかった」であって「0 件」ではない。**推測して数を作らない** ——
    ここで無理に読むと、内訳と点数を突き合わせる検査(G-06)が当て推量で汚れる。
    """
    if not kind or not _ASCII_DIGIT.search(kind):
        return None

    parts = _split_parts(kind)
    if not parts:
        return None

    # 形 A ―― すべての部分が `品目(数字)` のとき。
    form_a: list[tuple[str, int]] = []
    for part in parts:
        match = _FORM_A.match(part)
        if match is None:
            form_a = []
            break
        form_a.append((match.group("name").strip(), int(match.group("count"))))
    if form_a:
        return form_a

    # 形 B ―― 括弧を注記として落としてから、裸の数字を個数と読む。
    stripped_parts = _split_parts(_PARENTHETICAL.sub("", kind))
    if not stripped_parts:
        return None

    form_b: list[tuple[str, int]] = []
    for part in stripped_parts:
        match = _FORM_B.match(part)
        if match is None:
            # 一部でも個数を持たなければ、そのセル全体を諦める。
            # 読めた分だけ足すと、実際より小さい和が出て偽の不一致になる。
            return None
        name = match.group("name").strip()
        if not name:
            return None
        form_b.append((name, int(match.group("count"))))

    return form_b or None


# ── 帳簿の読み取り ──────────────────────────────────────


def load_workbook(path: pathlib.Path | None = None) -> Any:
    """書式つきで開く。背景色を読むために ``formatting_info`` が要る。"""
    target = path or RAW_XLS
    if not target.exists():
        raise FileNotFoundError(
            f"{target} が無い。再配布不可なのでリポジトリに含めていない。"
            "`python -m pipeline.acquisition.itoigawa` で取得すること"
        )
    return xlrd.open_workbook(str(target), formatting_info=True)


def data_sheet_names(workbook: Any) -> list[str]:
    """データシートの名前(註と文献シートを除く)。"""
    return [
        name
        for name in workbook.sheet_names()
        if name != NOTE_SHEET and not name.endswith(BIBLIOGRAPHY_SUFFIX)
    ]


def header_row_index(sheet: Any) -> int:
    """見出し行の位置。**シートによって違う**ので探す。

    決め打ちすると、新潟のシートだけ注記を見出しとして読み、列が全部ずれる。
    しかも例外にならないので、静かに間違った表ができる。
    """
    for row in range(min(5, sheet.nrows)):
        if str(sheet.cell(row, 0).value).strip() == SITE_NAME_COLUMN:
            return row
    raise ValueError(f"{sheet.name}: 見出し行({SITE_NAME_COLUMN})が見つからない")


def sheet_header(sheet: Any) -> list[str]:
    return [str(cell.value).strip() for cell in sheet.row(header_row_index(sheet))]


def read_sheet(workbook: Any, name: str) -> list[dict[str, Any]]:
    """1 シートを、**見出し名を鍵にした**辞書の列として読む。

    位置で読まない —— 同じ列数でも 12 列目の意味がシートで違う。
    """
    sheet = workbook.sheet_by_name(name)
    header_row = header_row_index(sheet)
    header = sheet_header(sheet)

    records: list[dict[str, Any]] = []
    for row in range(header_row + 1, sheet.nrows):
        record: dict[str, Any] = {"sheet": name, "row_index": row}
        for column, column_name in enumerate(header):
            if not column_name:
                continue
            cell = sheet.cell(row, column)
            record[column_name] = str(cell.value).strip() if cell.ctype != CELL_EMPTY else ""
            if column_name == COUNT_COLUMN:
                # 点数だけは型を保つ。**空欄は 0 ではなく不明**(註 2)。
                record["点数_値"] = cell.value if cell.ctype == CELL_NUMBER else None
                record["点数_型"] = cell.ctype
        records.append(record)
    return records


def note_prefectures(workbook: Any) -> list[str]:
    """註が調査担当者を挙げている県の一覧。

    註は「県名 / 担当者名」の二列で並ぶ。番号つきの箇条(「１．」など)や
    字下げの行は県名ではないので落とす。
    """
    sheet = workbook.sheet_by_name(NOTE_SHEET)
    names: list[str] = []
    for row in range(sheet.nrows):
        left = str(sheet.cell(row, 0).value).strip()
        right = str(sheet.cell(row, 1).value).strip() if sheet.ncols > 1 else ""
        if not left or not right:
            continue
        # 箇条書きの番号(全角数字)や字下げで始まる行は本文であって県名ではない。
        if left[0] in "１２３４５６７８９０　":
            continue
        names.append(left)
    return names


# ── 照合 ────────────────────────────────────────────────


@dataclasses.dataclass(frozen=True)
class InlineDisagreement:
    """内訳の和と点数が食い違った行。**源の中の食い違い**である。"""

    sheet: str
    row: int
    raw_kind: str
    items: tuple[tuple[str, int], ...]
    inline_total: int
    recorded_count: float


@dataclasses.dataclass(frozen=True)
class InlineCountReport:
    compared: int
    """内訳が読めて点数も数値だった行の数。"""

    agreements: int
    unparsed: int
    """内訳が読めなかった行の数。**0 件だと「全部読めた」と読めるので必ず持つ。**"""

    without_count: int
    """内訳は読めたが点数が無かった行の数。"""

    fullwidth_only: int
    """半角数字が無く全角数字だけを持つ行の数。

    個数としては読まないが、**黙って無視せず数える**。実測 2026-09-10 では
    ``樽型大珠・３孔`` の 1 行。「３孔」は穿孔の数で品目の個数ではない。
    """

    disagreements: tuple[InlineDisagreement, ...]

    @property
    def disagreements_count(self) -> int:
        return len(self.disagreements)


def inline_count_disagreements(workbook: Any) -> InlineCountReport:
    """``種別`` の内訳の和と ``点数`` を突き合わせる(G-06)。

    これは**源の内部にある照合**なので循環しない —— 内訳と点数は別の欄で、
    どちらも人が書いたものである。食い違いは黙って捨てず、行ごとに報告する。
    """
    compared = agreements = unparsed = without_count = fullwidth_only = 0
    disagreements: list[InlineDisagreement] = []

    for name in data_sheet_names(workbook):
        for record in read_sheet(workbook, name):
            kind = record.get(KIND_COLUMN) or ""
            if not _ASCII_DIGIT.search(kind):
                if _FULLWIDTH_DIGIT.search(kind):
                    fullwidth_only += 1
                continue
            items = parse_inline_counts(kind)
            if items is None:
                unparsed += 1
                continue
            count = record.get("点数_値")
            if count is None:
                without_count += 1
                continue
            compared += 1
            total = sum(n for _name, n in items)
            if abs(total - count) < 1e-9:
                agreements += 1
            else:
                disagreements.append(
                    InlineDisagreement(
                        sheet=name,
                        row=record["row_index"],
                        raw_kind=kind,
                        items=tuple(items),
                        inline_total=total,
                        recorded_count=count,
                    )
                )

    return InlineCountReport(
        compared=compared,
        agreements=agreements,
        unparsed=unparsed,
        without_count=without_count,
        fullwidth_only=fullwidth_only,
        disagreements=tuple(disagreements),
    )


def _row_background_indices(workbook: Any, sheet: Any, row: int) -> set[int]:
    return {
        workbook.xf_list[sheet.cell_xf_index(row, column)].background.pattern_colour_index
        for column in range(sheet.ncols)
    }


def background_flagged_rows(workbook: Any) -> list[tuple[str, int]]:
    """背景色が付いている行(シート名, 行番号)。

    色の名前ではなく**塗りがあるかどうか**で拾い、色そのものは
    :func:`background_flag_colours` で確かめる。
    """
    flagged: list[tuple[str, int]] = []
    for name in data_sheet_names(workbook):
        sheet = workbook.sheet_by_name(name)
        for row in range(header_row_index(sheet) + 1, sheet.nrows):
            if _row_background_indices(workbook, sheet, row) != {NO_FILL_COLOUR_INDEX}:
                flagged.append((name, row))
    return flagged


def background_flag_colours(workbook: Any) -> set[tuple[int, int, int]]:
    """実際に使われている背景色の RGB。註の記述と突き合わせるために測る。"""
    colours: set[tuple[int, int, int]] = set()
    for name, row in background_flagged_rows(workbook):
        sheet = workbook.sheet_by_name(name)
        for index in _row_background_indices(workbook, sheet, row):
            if index == NO_FILL_COLOUR_INDEX:
                continue
            rgb = workbook.colour_map.get(index)
            if rgb is not None:
                colours.add(tuple(rgb))
    return colours


def blank_count_rows(workbook: Any) -> list[tuple[str, int]]:
    """``点数`` セルの型が BLANK(書式あり・値なし)の行。

    背景色つきの行と一致するはずである —— 行全体に色を塗ったので、
    空の点数セルにも書式が付いた。**書式とセルの型は別の経路で決まる**ので、
    この一致は非循環の照合になる(G-07)。
    """
    rows: list[tuple[str, int]] = []
    for name in data_sheet_names(workbook):
        sheet = workbook.sheet_by_name(name)
        header = sheet_header(sheet)
        if COUNT_COLUMN not in header:
            continue
        column = header.index(COUNT_COLUMN)
        for row in range(header_row_index(sheet) + 1, sheet.nrows):
            if sheet.cell(row, column).ctype == CELL_BLANK:
                rows.append((name, row))
    return rows

"""ヒスイ集成表の集計統計だけを出荷形へ書く(F-05 / G-02 / G-05 / G-06 / G-07)。

**個票は書き出さない。** 出すのは件数の集計と、源の内部照合の結果だけである
(SPEC §6.3)。遺跡名・所在市町村・文献・所有者は一つも出荷ファイルに現れない ——
それを書き出す前に機械で確かめる(G-02)。

    python -m pipeline.build_jade_aggregate
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re

from archaeostone.jade import (
    BackgroundFlag,
    background_flag_colours,
    background_flagged_rows,
    blank_count_rows,
    data_sheet_names,
    inline_count_disagreements,
    load_workbook,
    note_prefectures,
    read_sheet,
    sheet_header,
)
from pipeline.paths import display_path

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
OUTPUT = REPO_ROOT / "public" / "data" / "jade_aggregate.json"

#: **出荷形に現れてはならない**個票のフィールド(G-02)。
#: 集計だけを配るという約束を、書き出す前に機械で確かめる。
FORBIDDEN_COLUMNS = ("遺跡名", "所在市町村", "文献", "所有者", "その他", "伴出土器")

#: 集計する列。いずれも語彙であって個体を指さない。
TALLY_COLUMNS = ("時代", "時期", "種別", "形状", "出土状況", "石材")

#: 「不明」を意味する表記。空欄と同じ扱いにする(註 2)。
_UNKNOWN = re.compile(r"^(不明|\?|？)$")


def _sheet_label(name: str) -> str:
    """シート名をそのまま県のラベルとして使う(新潟は括弧つきなのでそのまま)。"""
    return name


def build() -> dict:
    workbook = load_workbook()
    sheets = data_sheet_names(workbook)

    per_sheet = []
    tallies: dict[str, collections.Counter[str]] = {
        column: collections.Counter() for column in TALLY_COLUMNS
    }
    # 「不明」と空欄は語彙に数えないが、**何件あったかは数える** ——
    # 落とした数を出さないと「そういう行が無かった」と読めてしまう。
    unknown_counts: dict[str, int] = {column: 0 for column in TALLY_COLUMNS}
    blank_counts: dict[str, int] = {column: 0 for column in TALLY_COLUMNS}
    count_cell_types: collections.Counter[str] = collections.Counter()
    total_rows = 0
    total_recorded_pieces = 0.0
    rows_with_count = 0

    for name in sheets:
        records = read_sheet(workbook, name)
        total_rows += len(records)
        header = sheet_header(workbook.sheet_by_name(name))

        pieces = 0.0
        with_count = 0
        for record in records:
            value = record.get("点数_値")
            if value is not None:
                pieces += value
                with_count += 1
            # 点数セルの型の分布(空欄は 0 ではなく不明なので、型ごとに数える)
            cell_type = record.get("点数_型")
            count_cell_types[
                {0: "空欄", 1: "文字列", 2: "数値", 6: "書式のみ"}.get(cell_type, str(cell_type))
            ] += 1

            for column in TALLY_COLUMNS:
                raw = (record.get(column) or "").strip()
                if not raw:
                    blank_counts[column] += 1
                    continue
                if _UNKNOWN.match(raw):
                    unknown_counts[column] += 1
                    continue
                tallies[column][raw] += 1

        total_recorded_pieces += pieces
        rows_with_count += with_count
        per_sheet.append(
            {
                "sheet": _sheet_label(name),
                "rows": len(records),
                "rows_with_count": with_count,
                "recorded_pieces": pieces,
                "columns": len(header),
                # 追加列の**数**だけを出す。列名は出さない ——
                # 出荷形の門(G-02)は禁止列の名前を探すので、構造のラベルとして
                # 載せると発火する。列名そのものは SPEC §2.7 に書いてある。
                "extra_column_count": len(
                    [
                        c
                        for c in header
                        if c
                        not in (
                            "遺跡名", "所在市町村", "時代", "時期", "種別",
                            "形状", "点数", "出土状況", "所有者", "文献", "その他",
                        )
                    ]
                ),
            }
        )

    # ── 源の内部照合 ────────────────────────────────────
    named = note_prefectures(workbook)
    flagged = background_flagged_rows(workbook)
    blanks = blank_count_rows(workbook)
    inline = inline_count_disagreements(workbook)

    payload = {
        "generated_by": "pipeline.build_jade_aggregate",
        "source_id": "SRC-ITOIGAWA",
        "redistribution_notice": (
            "この集成表は糸魚川市の著作物で再配布できない。本アトラスが公開するのは"
            "**件数の集計だけ**であり、遺跡名・所在市町村・文献・所有者といった"
            "個票フィールドは一つも含まれていない。個票を見るには"
            "`python -m pipeline.acquisition.itoigawa` で手元に取得すること。"
        ),
        "coverage": {
            "sheets": len(sheets),
            "rows": total_rows,
            "rows_with_count": rows_with_count,
            "recorded_pieces": total_recorded_pieces,
            "note": (
                "収録は 9 県のみ。構想書 §14.1 の「北海道〜九州の出土分布」は"
                "この表からは作れない。点数の空欄は 0 ではなく**不明**である"
                "(註 2「不明な箇所は空欄とした」)。"
            ),
            "per_sheet": per_sheet,
            "count_cell_types": dict(count_cell_types),
        },
        "internal_checks": {
            "note_vs_sheets": {
                "gate": "G-05",
                "description": (
                    "註が調査担当者を挙げる県と、実際のデータシートを比べる。"
                    "**どちらも 9 件なので件数だけでは食い違いが見えない。**"
                ),
                "named_in_note": named,
                "sheets": sheets,
                "named_but_missing": [n for n in named if n not in sheets],
                "present_but_unnamed": [n for n in sheets if n not in named],
            },
            "inline_counts_vs_count_column": {
                "gate": "G-06",
                "description": (
                    "種別に埋まった内訳の和と、点数の欄を突き合わせる。"
                    "どちらも人が書いた別の欄なので、この照合は循環しない。"
                ),
                "compared": inline.compared,
                "agreements": inline.agreements,
                "disagreements": inline.disagreements_count,
                "unparsed": inline.unparsed,
                "fullwidth_only": inline.fullwidth_only,
                "without_count": inline.without_count,
                # 食い違った行の**記法だけ**を出す。遺跡名は出さない。
                "disagreement_notations": [
                    {
                        "sheet": d.sheet,
                        "notation": d.raw_kind,
                        "inline_total": d.inline_total,
                        "recorded_count": d.recorded_count,
                    }
                    for d in inline.disagreements
                ],
            },
            "background_colour_vs_blank_cells": {
                "gate": "G-07",
                "description": (
                    "背景色つきの行と、点数セルの型が BLANK(書式あり・値なし)の行が"
                    "一致するかを見る。書式とセルの型は別の経路で決まるので非循環。"
                ),
                "flagged_rows": len(flagged),
                "blank_count_rows": len(blanks),
                "match": sorted(flagged) == sorted(blanks),
                "sheets_with_flags": sorted({sheet for sheet, _row in flagged}),
                "observed_colours": [list(c) for c in sorted(background_flag_colours(workbook))],
                "declared_colour": list(BackgroundFlag.PRODUCTION_SITE.rgb),
                "note": (
                    "註は「緑の欄」と書くが、実体は RGB(255,255,153) の淡い黄色である。"
                    "**註と書式も食い違っている**ので、色の名前で探してはならない。"
                ),
            },
        },
        "tallies": {
            column: {
                "distinct": len(counter),
                "recorded": sum(counter.values()),
                # 落とした行も数える。「不明」は 0 ではなく**不明**であり、
                # 空欄も同じ(註 2「不明な箇所は空欄とした」)。
                "explicit_unknown": unknown_counts[column],
                "blank": blank_counts[column],
                "top": counter.most_common(20),
            }
            for column, counter in tallies.items()
        },
    }

    # ── G-02: 個票フィールドが漏れていないか、書き出す前に確かめる ──
    serialised = json.dumps(payload, ensure_ascii=False)
    leaked = [column for column in FORBIDDEN_COLUMNS if f'"{column}"' in serialised]
    if leaked:
        raise RuntimeError(
            f"出荷形に個票フィールドが現れた: {leaked}。"
            "集計だけを配る約束が破れている(G-02)"
        )

    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="ヒスイ集計統計を書き出す")
    parser.add_argument("--out", type=pathlib.Path, default=OUTPUT)
    args = parser.parse_args()

    payload = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )

    coverage = payload["coverage"]
    checks = payload["internal_checks"]
    print(f"{display_path(args.out)} を書き出した")
    print(
        f"  {coverage['sheets']} シート / {coverage['rows']} 行 / "
        f"点数のある行 {coverage['rows_with_count']} / 記録された点数の和 "
        f"{coverage['recorded_pieces']:g}"
    )
    note = checks["note_vs_sheets"]
    print(
        f"  G-05 註 {len(note['named_in_note'])} 件 vs シート {len(note['sheets'])} 件 — "
        f"註のみ {note['named_but_missing']} / シートのみ {note['present_but_unnamed']}"
    )
    inline = checks["inline_counts_vs_count_column"]
    print(
        f"  G-06 照合 {inline['compared']} / 一致 {inline['agreements']} / "
        f"不一致 {inline['disagreements']} / 解析不能 {inline['unparsed']} / "
        f"全角のみ {inline['fullwidth_only']}"
    )
    colour = checks["background_colour_vs_blank_cells"]
    print(
        f"  G-07 色つき {colour['flagged_rows']} 行 vs BLANK {colour['blank_count_rows']} 行 — "
        f"一致 {colour['match']} / 実際の色 {colour['observed_colours']}"
    )


if __name__ == "__main__":
    main()

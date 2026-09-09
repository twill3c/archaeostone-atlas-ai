"""ヒスイ集成表の記法の解析(T-200〜 / G-06)。

この検査は**生ファイルを必要としない純関数**に当てる。生ファイルは再配布不可なので
リポジトリに無い(SPEC §2.1)。だから記法の規則そのものをここで固定する。

例文はいずれも実物から写した**記法の見本**であって、遺跡名・所在地は含まない。
値は 2026-09-10 に全 572 行を走査して観測したものである(HC-068: 自作物ではなく
実物の性質を先に測ってから期待値を書く)。

**記法はセルごとに二形ある。** これが芯である。
* 形 A ―― ``勾玉(2),小玉(1)``  括弧の中が個数(北海道のシートで使われる)
* 形 B ―― ``大珠1、垂玉2``      裸の数字が個数、括弧は注記(青森のシートで使われる)

括弧は個数のことも注記のこともあるので、**どちらでもないものは推測せず None を返す**。
"""

import pytest

from archaeostone.jade import parse_inline_counts


# ── 形 B: 裸の数字が個数 ────────────────────────────────


@pytest.mark.parametrize(
    "text,expected",
    [
        ("大珠1、垂玉2", [("大珠", 1), ("垂玉", 2)]),
        ("勾玉1、垂玉2", [("勾玉", 1), ("垂玉", 2)]),
        ("丸玉11、垂玉1", [("丸玉", 11), ("垂玉", 1)]),
        ("勾玉2,丸玉42,垂玉5", [("勾玉", 2), ("丸玉", 42), ("垂玉", 5)]),
        ("丸玉17", [("丸玉", 17)]),
    ],
)
def test_t200_bare_digits_are_counts(text: str, expected) -> None:
    """T-200: 裸の数字を個数として読む。実測 2026-09-10 の記法。"""
    assert parse_inline_counts(text) == expected


def test_t201_parenthetical_qualifier_is_not_a_count() -> None:
    """T-201: 括弧の中の注記を個数に足さない。

    ``勾玉3(未成品2)`` は勾玉 3 点(うち 2 点が未成品)であって 5 点ではない。
    足すと**もっともらしく間違った数**が出るので、内部照合が壊れているように見える。
    """
    assert parse_inline_counts("勾玉3(未成品2)") == [("勾玉", 3)]


def test_t202_qualifier_inside_the_item_name_survives() -> None:
    """T-202: 品目名の一部としての括弧は残す。"""
    assert parse_inline_counts("勾玉1、丸玉(未成品)1") == [("勾玉", 1), ("丸玉", 1)]


# ── 形 A: 括弧の中が個数 ────────────────────────────────


@pytest.mark.parametrize(
    "text,expected",
    [
        ("勾玉(2),小玉(1)", [("勾玉", 2), ("小玉", 1)]),
        ("大珠(2),小玉(2)", [("大珠", 2), ("小玉", 2)]),
        ("勾玉(3),丸玉(6)", [("勾玉", 3), ("丸玉", 6)]),
    ],
)
def test_t203_parenthesised_digits_are_counts_when_every_part_matches(
    text: str, expected
) -> None:
    """T-203: **すべての部分が** `品目(数字)` の形なら、括弧の中を個数と読む。

    「すべての部分が」が要である。一部だけなら、括弧が個数か注記か決められない。
    実測ではこの三行の和が点数と一致しており、読み方が正しいことを源が裏づけている。
    """
    assert parse_inline_counts(text) == expected


# ── どちらでもないものは推測しない ──────────────────────


@pytest.mark.parametrize(
    "text",
    [
        "大珠(3穿孔を含む)",  # 括弧の中の数字が個数ではない
        "樽型大珠・３孔",  # 全角数字で、しかも「孔」は個数ではない
        "原石ほか",  # 数字が無い
        "大珠",
        "",
        "大珠・鰹節型",
    ],
)
def test_t204_ambiguous_or_countless_notation_returns_none(text: str) -> None:
    """T-204: 読み方が決まらない・個数が無い記法は **None**。

    **推測して数を作らない。** ここで無理に読むと、源の中の食い違いを
    数える検査(G-06)が、解析器の当て推量で汚染される。
    """
    assert parse_inline_counts(text) is None


def test_t205_positive_control_a_greedy_parser_would_be_wrong() -> None:
    """T-205(陽性対照): 素朴に「数字を全部拾って足す」実装が実際に間違うことを示す。

    この対照が無いと、T-201 と T-204 は「たまたま合っていた」だけかもしれない。
    """
    import re

    def greedy(text: str) -> int:
        return sum(int(n) for n in re.findall(r"\d+", text))

    # 括弧の注記まで足してしまう。
    assert greedy("勾玉3(未成品2)") == 5
    assert parse_inline_counts("勾玉3(未成品2)") == [("勾玉", 3)]

    # 個数でない数字まで足してしまう。
    assert greedy("大珠(3穿孔を含む)") == 3
    assert parse_inline_counts("大珠(3穿孔を含む)") is None


def test_t206_separators_cover_the_forms_seen_in_the_source() -> None:
    """T-206: 区切りは全角読点・半角読点・中黒の三つ。実測 2026-09-10。

    源は同じ意味に三つの記号を使っている。どれかを落とすと、
    その行だけ 1 品目として読んで**大きすぎる個数**を作る。
    """
    assert parse_inline_counts("大珠1、垂玉2") == [("大珠", 1), ("垂玉", 2)]
    assert parse_inline_counts("大珠1,垂玉2") == [("大珠", 1), ("垂玉", 2)]
    assert parse_inline_counts("大珠1・垂玉2") == [("大珠", 1), ("垂玉", 2)]


def test_t207_a_part_without_a_count_invalidates_the_whole_cell() -> None:
    """T-207: 一部の品目に個数が無ければ、そのセル全体を None にする。

    読めた分だけ足すと、**実際より小さい和**になって内部照合が偽の不一致を出す。
    """
    assert parse_inline_counts("大珠1、原石ほか") is None
    assert parse_inline_counts("原石ほか、大珠1") is None

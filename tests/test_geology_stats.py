"""地質分布の比較と順列検定の検査(T-090〜 / G-09)。

順列検定の実装は、**厳密列挙**と突き合わせて確かめる。小さな標本では
ラベルの割り当てを全部数え上げられるので、そこに閉形式のオラクルがある。

対照も対で置く。
* 同じ分布どうしなら有意にならない(陰性対照)
* 明らかに違う分布なら有意になる(陽性対照)
* 片方が空・全件同一など、退化した入力で黙って 0 を返さない
"""

import math

import pytest

from archaeostone.geology_stats import (
    PermutationResult,
    category_counts,
    exact_permutation_p_value,
    permutation_test,
    proportion,
)


# ── 集計 ────────────────────────────────────────────────


def test_t090_category_counts_and_proportion() -> None:
    values = ["火成岩", "火成岩", "堆積岩", None, "火成岩"]
    counts = category_counts(values)
    # None は「測れていない」であって category ではない。数に混ぜない。
    assert counts == {"火成岩": 3, "堆積岩": 1}
    assert proportion(values, "火成岩") == pytest.approx(3 / 4)


def test_t091_proportion_of_empty_is_none_not_zero() -> None:
    """T-091: 空集合の比率は 0 ではなく「無い」。

    0 を返すと「測ったら 0% だった」と読める。**測っていないことを
    測ったように見せない。**
    """
    assert proportion([], "火成岩") is None
    assert proportion([None, None], "火成岩") is None


# ── 順列検定: 厳密列挙との突き合わせ ────────────────────


@pytest.mark.parametrize(
    "source,control",
    [
        (["A"], ["B", "B"]),
        (["A", "A"], ["B", "B"]),
        (["A", "B"], ["A", "B", "B"]),
        (["A", "A", "A"], ["A", "B", "B", "B"]),
    ],
)
def test_t092_sampled_matches_exact_enumeration(source: list[str], control: list[str]) -> None:
    """T-092: 抽出による p 値が、厳密列挙の p 値に一致する。

    小さな標本ではラベルの割り当てを全部数え上げられる。これは実装の出力ではなく
    順列検定の定義そのものなので、**閉形式のオラクル**である。
    """
    exact = exact_permutation_p_value(source, control, target="A")
    sampled = permutation_test(source, control, target="A", iterations=20000, seed=20260909)

    # 抽出誤差の許容幅。二項の標準偏差の 4 倍で押さえる。
    tolerance = 4 * math.sqrt(max(exact, 1e-9) * (1 - exact) / 20000) + 1e-9
    assert sampled.p_value == pytest.approx(exact, abs=max(tolerance, 0.01)), (
        f"抽出 {sampled.p_value} と厳密 {exact} が離れすぎている"
    )


def test_t093_exact_enumeration_is_not_the_same_code_path() -> None:
    """T-093: 二つの経路が実際に別物であること。

    同じ関数を二度呼んで「一致した」と言っても何も検査していない(HC-045)。
    厳密側は組み合わせの列挙、抽出側は乱数の並べ替えで、**中間量が違う**
    (列挙数 vs 反復数)ことを表明する。
    """
    source, control = ["A", "A"], ["A", "B", "B"]
    exact = exact_permutation_p_value(source, control, target="A")
    sampled = permutation_test(source, control, target="A", iterations=5000, seed=1)

    assert sampled.iterations == 5000
    assert sampled.enumerated is False
    # 厳密側は C(5,2) = 10 通りの列挙なので、p は 10 分の 1 刻みになる。
    assert (exact * 10) == pytest.approx(round(exact * 10)), f"厳密 p {exact} が 1/10 刻みでない"


# ── 対照 ────────────────────────────────────────────────


def test_t094_negative_control_same_distribution_is_not_significant() -> None:
    """T-094(陰性対照): 同じ分布どうしは有意にならない。

    先に陰性対照を当てる(HC-074)。ここで有意が出るなら実装が壊れている。
    """
    rng_like = ["A", "B", "B", "A", "B"] * 20
    result = permutation_test(rng_like[:15], rng_like[15:], target="A", iterations=5000, seed=7)
    assert result.p_value > 0.2, f"同じ分布で p={result.p_value}"


def test_t095_positive_control_clear_difference_is_significant() -> None:
    """T-095(陽性対照): 明らかに違う分布は有意になる。

    これが無いと、検定が常に「有意でない」を返す実装でも T-094 は緑になる。
    """
    source = ["A"] * 13
    control = ["A"] * 150 + ["B"] * 250
    result = permutation_test(source, control, target="A", iterations=5000, seed=7)
    assert result.p_value < 0.01, f"明らかな差で p={result.p_value}"
    assert result.source_proportion == pytest.approx(1.0)
    assert result.control_proportion == pytest.approx(150 / 400)


def test_t096_degenerate_all_same_category_returns_no_p_value() -> None:
    """T-096: 全件が同じ category なら、並べ替えても統計量が動かない。

    このとき p 値は 1 ではなく **「検定できない」** である。1 を返すと
    「検定して有意でなかった」と読める。
    """
    result = permutation_test(["A"] * 5, ["A"] * 10, target="A", iterations=1000, seed=3)
    assert result.p_value is None
    assert result.reason is not None


def test_t097_empty_source_returns_no_p_value() -> None:
    result = permutation_test([], ["A", "B"], target="A", iterations=100, seed=3)
    assert result.p_value is None
    assert result.reason is not None


def test_t098_result_is_reproducible_with_the_same_seed() -> None:
    """T-098: 同じ種なら同じ p 値。報告する数が実行ごとに動かないこと。"""
    kwargs = dict(target="A", iterations=3000, seed=42)
    source, control = ["A", "A", "B"], ["A", "B", "B", "B"]
    first = permutation_test(source, control, **kwargs)
    second = permutation_test(source, control, **kwargs)
    assert first.p_value == second.p_value


def test_t099_result_records_what_was_measured(monkeypatch) -> None:
    """T-099: 結果が「何を・いくつ・どの種で」測ったかを持つ(HC-152)。

    母集団の分からない数を実測と呼ばない。
    """
    result = permutation_test(["A", "B"], ["A", "B", "B"], target="A", iterations=1000, seed=5)
    assert isinstance(result, PermutationResult)
    for field in ("target", "source_n", "control_n", "iterations", "seed"):
        assert getattr(result, field) is not None, f"{field} が結果に無い"
    assert result.source_n == 2
    assert result.control_n == 3

"""地質分布の比較と順列検定(F-08 / G-09)。

主張したいのは「原産地の足もとの地質は、無作為な陸地点と比べて偏っている」である。
検定はラベルの置換で行う —— 原産地と対照点をまとめて、どちらのラベルかを
無作為に振り直し、観測した差より大きい差がどれだけの割合で出るかを数える。

実装は**厳密列挙と突き合わせて**確かめてある。標本が小さいときは
ラベルの割り当てを全部数え上げられるので、そこに閉形式のオラクルがある
(``tests/test_geology_stats.py`` T-092)。

**測れなかったことを 0 や 1 で表さない。** 空集合の比率は 0 ではなく None、
統計量が動かない退化した入力の p 値は 1 ではなく None(理由つき)である。
0 は「測ったら 0 だった」と読め、1 は「検定して有意でなかった」と読めてしまう。
"""

from __future__ import annotations

import dataclasses
import itertools
import random
from collections.abc import Sequence


def category_counts(values: Sequence[str | None]) -> dict[str, int]:
    """category ごとの件数。``None``(測れていない)は数に混ぜない。"""
    counts: dict[str, int] = {}
    for value in values:
        if value is None:
            continue
        counts[value] = counts.get(value, 0) + 1
    return counts


def proportion(values: Sequence[str | None], target: str) -> float | None:
    """``target`` の占める割合。測れた件数が 0 なら **None**(0 ではない)。"""
    measured = [value for value in values if value is not None]
    if not measured:
        return None
    return sum(1 for value in measured if value == target) / len(measured)


@dataclasses.dataclass(frozen=True)
class PermutationResult:
    """何を・いくつ・どの種で測ったかを、値と一緒に持つ(HC-152)。"""

    target: str
    source_n: int
    control_n: int
    source_proportion: float | None
    control_proportion: float | None
    observed_difference: float | None
    p_value: float | None
    iterations: int
    seed: int
    enumerated: bool = False
    reason: str | None = None
    """p 値が出せなかった理由。出せたときは None。"""


def _difference(labels: Sequence[str], source_n: int, target: str) -> float:
    source = labels[:source_n]
    control = labels[source_n:]
    source_rate = sum(1 for value in source if value == target) / len(source)
    control_rate = sum(1 for value in control if value == target) / len(control)
    return source_rate - control_rate


def _prepare(
    source: Sequence[str | None], control: Sequence[str | None], target: str
) -> tuple[list[str], list[str], str | None]:
    """測れた値だけを取り出し、検定できない理由があれば返す。"""
    measured_source = [value for value in source if value is not None]
    measured_control = [value for value in control if value is not None]

    if not measured_source:
        return measured_source, measured_control, "原産地側に測れた地質が 1 件も無い"
    if not measured_control:
        return measured_source, measured_control, "対照群側に測れた地質が 1 件も無い"

    pooled = set(measured_source) | set(measured_control)
    if len(pooled) < 2:
        return (
            measured_source,
            measured_control,
            f"両群の地質がすべて {pooled.pop()!r} なので、ラベルを振り直しても統計量が動かない",
        )
    if target not in pooled:
        return (
            measured_source,
            measured_control,
            f"{target!r} が両群のどこにも現れないので比率が常に 0 になる",
        )
    return measured_source, measured_control, None


def exact_permutation_p_value(
    source: Sequence[str | None],
    control: Sequence[str | None],
    *,
    target: str,
) -> float | None:
    """ラベルの割り当てを全部数え上げた p 値(小さな標本用のオラクル)。

    抽出による ``permutation_test`` と突き合わせるために置いてある。
    組み合わせ数が大きいときは使えないので、呼ぶ側が標本の大きさを見て選ぶ。
    """
    measured_source, measured_control, reason = _prepare(source, control, target)
    if reason is not None:
        return None

    pooled = measured_source + measured_control
    source_n = len(measured_source)
    observed = abs(_difference(pooled, source_n, target))

    total = extreme = 0
    indices = range(len(pooled))
    for chosen in itertools.combinations(indices, source_n):
        chosen_set = set(chosen)
        permuted = [pooled[i] for i in chosen] + [
            pooled[i] for i in indices if i not in chosen_set
        ]
        total += 1
        if abs(_difference(permuted, source_n, target)) >= observed - 1e-12:
            extreme += 1
    return extreme / total


def permutation_test(
    source: Sequence[str | None],
    control: Sequence[str | None],
    *,
    target: str,
    iterations: int = 20_000,
    seed: int = 20260909,
) -> PermutationResult:
    """ラベル置換検定。両側。

    ``p_value`` が None のときは ``reason`` を読むこと。**None は「有意でない」
    ではなく「検定できなかった」である。**
    """
    measured_source, measured_control, reason = _prepare(source, control, target)
    source_rate = proportion(measured_source, target)
    control_rate = proportion(measured_control, target)

    if reason is not None:
        return PermutationResult(
            target=target,
            source_n=len(measured_source),
            control_n=len(measured_control),
            source_proportion=source_rate,
            control_proportion=control_rate,
            observed_difference=(
                source_rate - control_rate
                if source_rate is not None and control_rate is not None
                else None
            ),
            p_value=None,
            iterations=iterations,
            seed=seed,
            reason=reason,
        )

    pooled = measured_source + measured_control
    source_n = len(measured_source)
    observed = _difference(pooled, source_n, target)

    rng = random.Random(seed)
    shuffled = list(pooled)
    extreme = 0
    for _ in range(iterations):
        rng.shuffle(shuffled)
        if abs(_difference(shuffled, source_n, target)) >= abs(observed) - 1e-12:
            extreme += 1

    return PermutationResult(
        target=target,
        source_n=source_n,
        control_n=len(measured_control),
        source_proportion=source_rate,
        control_proportion=control_rate,
        observed_difference=observed,
        p_value=extreme / iterations,
        iterations=iterations,
        seed=seed,
        enumerated=False,
    )

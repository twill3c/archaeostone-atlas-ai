"""地質から「原産地らしさ」を当てる分類器の検査(T-300〜 / G-10)。

**この分類器は H-01〜H-03 の確認にはならない。** 同じデータ・同じ計器から
作った特徴なので、当たるのは当然である(HC-045)。問うのは一つだけ ——
**学習した組み合わせが、訓練側で選んだ単一規則を超えるか。**

漏れを作らないための三点を、実装より先に固定する。

1. **空間で分ける。** 同じ火山体の原産地と対照点が訓練と試験に割れると、
   位置の近さを覚えるだけで当たる。1.5 度格子の一群抜きで分ける
2. **規則の選択も訓練側だけで行う。** 全データで選んだ規則を試験に当てると、
   規則の側だけが試験データを見たことになり、学習モデルに不公平になる
3. **ラベル置換の陽性対照。** ラベルを並べ替えても当たるなら、どこかで漏れている
"""

import math

import numpy as np
import pytest

from archaeostone.likeness import (
    FEATURE_NAMES,
    balanced_accuracy,
    best_single_rule,
    featurize,
    leave_one_group_out,
    spatial_group,
    evaluate_grouped,
)


# ── 特徴量 ──────────────────────────────────────────────


def _record(group=None, age=None, lithology=None, outcome="ok"):
    return {
        "geology_outcome": outcome,
        "geology_group_ja": group,
        "formation_age_ja": age,
        "lithology_ja": lithology,
    }


def test_t300_featurize_quaternary_felsic_volcanic() -> None:
    """T-300: 実物の記法(2026-09-09 の API 応答)から二値特徴を立てる。"""
    features = featurize(
        _record("火成岩", "新生代 第四紀 完新世", "デイサイト・流紋岩 溶岩・火砕岩")
    )
    assert features["group_火成岩"] == 1
    assert features["era_第四紀"] == 1
    assert features["felsic"] == 1
    assert features["volcanic"] == 1
    assert features["plutonic"] == 0
    assert set(features) == set(FEATURE_NAMES)


def test_t301_featurize_cretaceous_plutonic() -> None:
    features = featurize(
        _record("火成岩", "中生代 後期白亜紀 セノマニアン期〜サントニアン期",
                "花崗閃緑岩・トーナル岩 片麻状 島弧・大陸")
    )
    assert features["era_白亜紀"] == 1
    assert features["era_第四紀"] == 0
    assert features["plutonic"] == 1
    assert features["volcanic"] == 0


def test_t302_records_without_geology_are_not_featurized() -> None:
    """T-302: 地質が取れなかった点は特徴にしない(0 で埋めない)。

    0 で埋めると「堆積岩でも火成岩でもない地質」という存在しない値を作る。
    """
    assert featurize(_record(outcome="no_polygon")) is None
    assert featurize(_record(outcome=None)) is None


def test_t303_every_feature_is_binary() -> None:
    features = featurize(_record("堆積岩", "新生代 新第三紀 中新世", "海成層 泥岩"))
    assert all(value in (0, 1) for value in features.values())


# ── 空間の群(閉形式) ──────────────────────────────────


def test_t304_spatial_group_is_the_grid_cell() -> None:
    """T-304: 1.5 度格子のセル番号。定義から出る閉形式。"""
    assert spatial_group(24.0, 122.0, cell_deg=1.5) == (0, 0)
    assert spatial_group(25.49, 123.49, cell_deg=1.5) == (0, 0)
    assert spatial_group(25.5, 123.5, cell_deg=1.5) == (1, 1)
    # 和田峠と星ヶ塔(直線で約 2 km)は同じセルに入る。
    assert spatial_group(36.14506, 138.14385, 1.5) == spatial_group(36.12848, 138.14043, 1.5)


def test_t305_leave_one_group_out_never_leaks_a_group() -> None:
    """T-305: 試験側の群が訓練側に一つも現れない。**漏れの検査そのもの。**"""
    groups = ["a", "a", "b", "c", "c", "c", "d"]
    splits = list(leave_one_group_out(groups))
    assert len(splits) == 4
    covered = []
    for train, test in splits:
        test_groups = {groups[i] for i in test}
        train_groups = {groups[i] for i in train}
        assert len(test_groups) == 1
        assert not (test_groups & train_groups), "試験側の群が訓練側に漏れている"
        assert set(train) | set(test) == set(range(len(groups)))
        covered.extend(test)
    assert sorted(covered) == list(range(len(groups))), "全点がちょうど一度だけ試験される"


# ── 指標(二経路) ──────────────────────────────────────


@pytest.mark.parametrize(
    "y,pred",
    [
        ([1, 1, 0, 0, 0, 0], [1, 0, 0, 0, 1, 0]),
        ([1, 0, 0, 0], [1, 1, 1, 1]),
        ([1, 1, 1, 0], [0, 0, 0, 0]),
        ([0, 1, 0, 1, 0, 0, 1], [0, 1, 1, 1, 0, 0, 0]),
    ],
)
def test_t306_balanced_accuracy_matches_sklearn(y, pred) -> None:
    """T-306: 自前の平衡正解率が scikit-learn と一致する(二経路)。

    自前で持つのは、画面へ出す数と検査の数を同じ関数から出すため。
    一致を外部実装で確かめる。
    """
    from sklearn.metrics import balanced_accuracy_score

    assert balanced_accuracy(y, pred) == pytest.approx(balanced_accuracy_score(y, pred))


def test_t307_majority_class_scores_half() -> None:
    """T-307: 多数派だけを答える分類器の平衡正解率は 0.5(閉形式)。

    正例 13 / 負例 397 で「全部負例」と答えると正解率は 96.8% になる。
    **正解率では何も言えない**ことを、ここで固定する。
    """
    y = [1] * 13 + [0] * 397
    pred = [0] * 410
    plain_accuracy = sum(a == b for a, b in zip(y, pred)) / len(y)
    assert plain_accuracy == pytest.approx(397 / 410)
    assert balanced_accuracy(y, pred) == pytest.approx(0.5)


# ── 単一規則の選択 ──────────────────────────────────────


def test_t308_best_single_rule_finds_the_planted_feature() -> None:
    """T-308: ラベルを完全に決める特徴を植えると、それを選ぶ。"""
    rng = np.random.default_rng(0)
    X = rng.integers(0, 2, size=(200, 5))
    y = X[:, 3].copy()
    name, score = best_single_rule(X, y, ["f0", "f1", "f2", "f3", "f4"])
    assert name == "f3"
    assert score == pytest.approx(1.0)


def test_t309_rule_selection_sees_only_the_training_rows(monkeypatch) -> None:
    """T-309: 規則の選択に**訓練側の行だけ**が渡る。

    全データで選んだ規則を試験に当てると、規則の側だけが試験データを見る。
    選択関数を差し替えて、渡された行が試験の行と重ならないことを数える。
    """
    import archaeostone.likeness as likeness

    seen_sizes: list[int] = []
    original = likeness.best_single_rule

    def spy(X, y, names):
        seen_sizes.append(len(y))
        return original(X, y, names)

    monkeypatch.setattr(likeness, "best_single_rule", spy)

    rng = np.random.default_rng(1)
    X = rng.integers(0, 2, size=(60, len(FEATURE_NAMES)))
    y = np.array([1] * 12 + [0] * 48)
    groups = [f"g{i % 6}" for i in range(60)]

    likeness.evaluate_grouped(X, y, groups, permutations=0, seed=0)

    assert seen_sizes, "規則の選択が一度も呼ばれていない"
    assert max(seen_sizes) < 60, "全データで規則を選んでいる(試験の行が混ざっている)"
    assert all(size == 50 for size in seen_sizes), seen_sizes


# ── 評価全体の対照 ──────────────────────────────────────


def _planted(n_pos=13, n_neg=397, seed=0, strength=1.0):
    """正例ほど特徴 0 が立ちやすい合成データ。strength=0 で無関係。"""
    rng = np.random.default_rng(seed)
    y = np.array([1] * n_pos + [0] * n_neg)
    X = rng.integers(0, 2, size=(len(y), len(FEATURE_NAMES)))
    if strength > 0:
        X[:, 0] = np.where(y == 1, 1, (rng.random(len(y)) < 0.1).astype(int))
    groups = [f"g{i % 7}" for i in range(len(y))]
    return X, y, groups


def test_t310_positive_control_planted_signal_is_found() -> None:
    """T-310(陽性対照): 強い信号を植えると、規則もモデルも高く当たる。"""
    X, y, groups = _planted(strength=1.0)
    result = evaluate_grouped(X, y, groups, permutations=0, seed=0)
    assert result["rule"]["balanced_accuracy"] > 0.85
    assert result["logistic"]["balanced_accuracy"] > 0.85
    assert result["majority"]["balanced_accuracy"] == pytest.approx(0.5)


def test_t311_negative_control_label_permutation_destroys_the_signal() -> None:
    """T-311(陰性対照): ラベルを並べ替えると、置換分布の中心が 0.5 付近に落ちる。

    ここで高く当たるなら、分割か特徴のどこかで漏れている。
    """
    X, y, groups = _planted(strength=1.0)
    result = evaluate_grouped(X, y, groups, permutations=60, seed=3)
    null = result["logistic"]["permutation_null"]
    assert len(null) == 60
    assert abs(float(np.mean(null)) - 0.5) < 0.08, f"置換の平均 {np.mean(null):.3f}"
    assert result["logistic"]["permutation_p"] < 0.05


def test_t312_no_signal_is_not_reported_as_signal() -> None:
    """T-312: 信号が無いデータでは、置換 p 値が小さくならない。"""
    X, y, groups = _planted(strength=0.0, seed=5)
    result = evaluate_grouped(X, y, groups, permutations=60, seed=5)
    assert result["logistic"]["permutation_p"] > 0.05


def test_t313_result_reports_counts_not_only_rates() -> None:
    """T-313: 率だけでなく件数を返す(HC-152)。

    正例 13 件の平衡正解率は 1 件で 3.8 ポイント動く。**率だけを見せると
    粒度を読み違える。**
    """
    X, y, groups = _planted()
    result = evaluate_grouped(X, y, groups, permutations=0, seed=0)
    for model in ("majority", "rule", "logistic"):
        counts = result[model]
        for key in ("tp", "fn", "fp", "tn"):
            assert key in counts
        assert counts["tp"] + counts["fn"] == 13
        assert counts["fp"] + counts["tn"] == 397
    assert math.isclose(1 / 13, 0.0769, abs_tol=1e-3)


# ── G-10 の判定(SPEC §12.3 を機械で当てる) ────────────


from archaeostone.likeness import g10_verdict  # noqa: E402


def test_t314_verdict_passes_only_with_the_declared_margin() -> None:
    """T-314: ロジスティックが単一規則を 0.05 以上上回ったときだけ成立。

    判定は SPEC §12.3 に**モデルを走らせる前に**書いた。ここで閾値を固定し、
    結果を見て動かせないようにする。
    """
    assert g10_verdict(logistic_ba=0.90, rule_ba=0.84, permutation_p=0.01)["verdict"] == "成立"
    assert g10_verdict(logistic_ba=0.88, rule_ba=0.84, permutation_p=0.01)["verdict"] == "不成立"


def test_t315_boundary_is_inclusive_and_not_fooled_by_float_error() -> None:
    """T-315: ちょうど 0.05 上回るときは成立(浮動小数の丸めで落とさない)。"""
    assert g10_verdict(logistic_ba=0.85 + 0.05, rule_ba=0.85, permutation_p=0.01)["verdict"] == "成立"


def test_t316_no_signal_is_stated_separately_from_the_comparison() -> None:
    """T-316: 置換 p が 0.05 以上なら「見分けられない」を別に立てる。

    比較の成否と、信号の有無は別の問いである。混ぜると「規則に負けた」と
    「そもそも何も当たっていない」が区別できない。
    """
    result = g10_verdict(logistic_ba=0.55, rule_ba=0.52, permutation_p=0.30)
    assert result["verdict"] == "不成立"
    assert result["distinguishable"] is False
    signal = g10_verdict(logistic_ba=0.80, rule_ba=0.84, permutation_p=0.005)
    assert signal["distinguishable"] is True


def test_t317_verdict_records_the_declared_rule_and_resolution() -> None:
    """T-317: 判定が、宣言した規則と粒度(正例 1 件あたりの動き)を持つ。"""
    result = g10_verdict(logistic_ba=0.80, rule_ba=0.84, permutation_p=0.01, n_positive=13)
    assert result["margin"] == 0.05
    assert result["resolution_per_positive"] == pytest.approx(0.5 / 13)
    assert "SPEC §12" in result["rule"]

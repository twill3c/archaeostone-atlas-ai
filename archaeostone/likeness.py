"""地質から「原産地らしさ」を当てる分類器と、その評価(F-09 / G-10)。

**この分類器は H-01〜H-03 の確認にはならない。** 同じデータ・同じ計器から作った
特徴なので、当たるのは当然である(HC-045)。問いは一つだけ ——
**学習した組み合わせが、訓練側で選んだ単一規則を超えるか**(SPEC §12)。

漏れを作らないための約束:

* **空間で分ける。** 1.5 度格子の一群抜き。同じ火山体の原産地と対照点を
  訓練と試験に割ると、位置の近さを覚えるだけで当たる
* **規則の選択も訓練側だけで行う。** 全データで選んだ規則を試験に当てると、
  規則の側だけが試験データを見たことになる
* **率だけでなく件数を返す。** 正例 13 件の平衡正解率は 1 件で約 3.8 ポイント動く
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from typing import Any

import numpy as np

GROUPS = ("火成岩", "堆積岩", "付加体", "変成岩", "その他")
ERAS = ("第四紀", "新第三紀", "古第三紀", "白亜紀", "それ以前")

#: 白亜紀より古い時代を示す語。
_OLDER_WORDS = ("ジュラ", "三畳", "ペルム", "石炭", "デボン", "シルル", "オルドビス", "カンブリア", "古生代")
_FELSIC_WORDS = ("流紋岩", "デイサイト")
_VOLCANIC_WORDS = ("溶岩", "火砕")
_PLUTONIC_WORDS = ("花崗", "閃緑", "トーナル", "斑れい", "はんれい")
_UNCONSOLIDATED_WORDS = ("堆積物",)

FEATURE_NAMES: tuple[str, ...] = (
    *(f"group_{g}" for g in GROUPS),
    *(f"era_{e}" for e in ERAS),
    "felsic",
    "volcanic",
    "plutonic",
    "unconsolidated",
)

#: 空間の群を作る格子の大きさ(度)と原点。
CELL_DEG = 1.5
ORIGIN = (24.0, 122.0)


def featurize(record: dict[str, Any]) -> dict[str, int] | None:
    """地質の二値特徴。**地質が取れなかった点は None**(0 で埋めない)。

    0 で埋めると「どの大分類にも属さない地質」という存在しない値を作る。
    """
    if record.get("geology_outcome") != "ok":
        return None

    group = record.get("geology_group_ja") or ""
    age = record.get("formation_age_ja") or ""
    lithology = record.get("lithology_ja") or ""

    features = {name: 0 for name in FEATURE_NAMES}
    for g in GROUPS:
        if group == g:
            features[f"group_{g}"] = 1
    for era in ("第四紀", "新第三紀", "古第三紀", "白亜紀"):
        if era in age:
            features[f"era_{era}"] = 1
    if any(word in age for word in _OLDER_WORDS):
        features["era_それ以前"] = 1
    features["felsic"] = int(any(w in lithology for w in _FELSIC_WORDS))
    features["volcanic"] = int(any(w in lithology for w in _VOLCANIC_WORDS))
    features["plutonic"] = int(any(w in lithology for w in _PLUTONIC_WORDS))
    features["unconsolidated"] = int(any(w in lithology for w in _UNCONSOLIDATED_WORDS))
    return features


def spatial_group(latitude: float, longitude: float, cell_deg: float = CELL_DEG) -> tuple[int, int]:
    """格子のセル番号。定義から出る閉形式。"""
    return (
        int((latitude - ORIGIN[0]) // cell_deg),
        int((longitude - ORIGIN[1]) // cell_deg),
    )


def leave_one_group_out(groups: Sequence[Any]) -> Iterator[tuple[list[int], list[int]]]:
    """一群抜きの分割。群は初出順に並べる(再現できる順序にする)。"""
    order: list[Any] = []
    for g in groups:
        if g not in order:
            order.append(g)
    for held_out in order:
        test = [i for i, g in enumerate(groups) if g == held_out]
        train = [i for i, g in enumerate(groups) if g != held_out]
        yield train, test


def balanced_accuracy(y: Sequence[int], pred: Sequence[int]) -> float:
    """平衡正解率 = 真のクラスごとの再現率の平均。"""
    y_arr = np.asarray(y)
    p_arr = np.asarray(pred)
    recalls = []
    for cls in np.unique(y_arr):
        mask = y_arr == cls
        recalls.append(float(np.mean(p_arr[mask] == cls)))
    return float(np.mean(recalls))


def best_single_rule(X: np.ndarray, y: np.ndarray, names: Sequence[str]) -> tuple[str, float]:
    """「その特徴が立っていれば正例」という規則のうち、平衡正解率が最大のもの。

    同点は列の順で先のものを採る(決定的にする)。**渡された行だけで選ぶ** ——
    呼ぶ側が訓練側の行だけを渡す責任を持つ(T-309 で数えて確かめる)。
    """
    best_name, best_score = names[0], -1.0
    for j, name in enumerate(names):
        score = balanced_accuracy(y, X[:, j])
        if score > best_score:
            best_name, best_score = name, score
    return best_name, best_score


def _counts(y: np.ndarray, pred: np.ndarray) -> dict[str, int]:
    return {
        "tp": int(np.sum((y == 1) & (pred == 1))),
        "fn": int(np.sum((y == 1) & (pred == 0))),
        "fp": int(np.sum((y == 0) & (pred == 1))),
        "tn": int(np.sum((y == 0) & (pred == 0))),
    }


def _logistic_oof(X: np.ndarray, y: np.ndarray, groups: Sequence[Any]) -> tuple[np.ndarray, np.ndarray]:
    """一群抜きで、束ねた折り外の予測と確率を返す。"""
    from sklearn.linear_model import LogisticRegression

    pred = np.zeros(len(y), dtype=int)
    proba = np.zeros(len(y), dtype=float)
    for train, test in leave_one_group_out(groups):
        y_train = y[train]
        if len(np.unique(y_train)) < 2:
            # 訓練側に片方のクラスしか無ければ学習できない。多数派を答える。
            majority = int(np.bincount(y_train).argmax())
            pred[test] = majority
            proba[test] = float(majority)
            continue
        model = LogisticRegression(class_weight="balanced", max_iter=2000)
        model.fit(X[train], y_train)
        pred[test] = model.predict(X[test])
        proba[test] = model.predict_proba(X[test])[:, 1]
    return pred, proba


def evaluate_grouped(
    X: np.ndarray,
    y: np.ndarray,
    groups: Sequence[Any],
    *,
    permutations: int = 200,
    seed: int = 20260914,
) -> dict[str, Any]:
    """多数決 / 訓練側で選ぶ単一規則 / ロジスティック回帰 を一群抜きで比べる。"""
    X = np.asarray(X)
    y = np.asarray(y).astype(int)

    majority_pred = np.zeros(len(y), dtype=int)
    rule_pred = np.zeros(len(y), dtype=int)
    selected_rules: list[str] = []

    for train, test in leave_one_group_out(groups):
        majority = int(np.bincount(y[train], minlength=2).argmax())
        majority_pred[test] = majority

        # 規則の選択は訓練側の行だけで行う。
        name, _score = best_single_rule(X[train], y[train], FEATURE_NAMES)
        selected_rules.append(name)
        rule_pred[test] = X[test, FEATURE_NAMES.index(name)]

    logistic_pred, logistic_proba = _logistic_oof(X, y, groups)

    result: dict[str, Any] = {
        "n_positive": int(np.sum(y == 1)),
        "n_negative": int(np.sum(y == 0)),
        "n_groups": len({g for g in groups}),
        "majority": {"balanced_accuracy": balanced_accuracy(y, majority_pred), **_counts(y, majority_pred)},
        "rule": {
            "balanced_accuracy": balanced_accuracy(y, rule_pred),
            **_counts(y, rule_pred),
            "selected_per_fold": selected_rules,
        },
        "logistic": {
            "balanced_accuracy": balanced_accuracy(y, logistic_pred),
            **_counts(y, logistic_pred),
        },
    }

    if len(np.unique(y)) == 2:
        from sklearn.metrics import roc_auc_score

        result["logistic"]["pooled_auc"] = float(roc_auc_score(y, logistic_proba))

    if permutations > 0:
        rng = np.random.default_rng(seed)
        observed = result["logistic"]["balanced_accuracy"]
        null = []
        for _ in range(permutations):
            y_perm = rng.permutation(y)
            perm_pred, _ = _logistic_oof(X, y_perm, groups)
            null.append(balanced_accuracy(y_perm, perm_pred))
        exceed = sum(1 for value in null if value >= observed - 1e-12)
        result["logistic"]["permutation_null"] = null
        result["logistic"]["permutation_p"] = (1 + exceed) / (1 + permutations)
        result["logistic"]["permutations"] = permutations
        result["logistic"]["seed"] = seed

    return result


#: SPEC §12.3 で**モデルを走らせる前に**宣言した差。結果を見て動かさない。
G10_MARGIN = 0.05
#: 置換 p 値がこれ未満なら「この特徴で見分けられる」と言う。
G10_ALPHA = 0.05


def g10_verdict(
    *,
    logistic_ba: float,
    rule_ba: float,
    permutation_p: float,
    n_positive: int = 13,
) -> dict[str, Any]:
    """G-10 の判定を機械で当てる(SPEC §12.3)。

    比較の成否(学習モデルが単一規則を超えたか)と、信号の有無(置換で消えるか)は
    **別の問い**として分けて返す。混ぜると「規則に負けた」と「そもそも何も
    当たっていない」が区別できない。
    """
    difference = logistic_ba - rule_ba
    # ちょうど宣言した差を上回るときは成立。浮動小数の丸めで落とさない。
    passed = difference >= G10_MARGIN - 1e-9
    return {
        "verdict": "成立" if passed else "不成立",
        "difference": difference,
        "margin": G10_MARGIN,
        "distinguishable": permutation_p < G10_ALPHA,
        "permutation_p": permutation_p,
        # 正例 1 件が平衡正解率を動かす幅(正例側の再現率は重み 1/2)。
        "resolution_per_positive": 0.5 / n_positive,
        "rule": (
            "SPEC §12.3: ロジスティック回帰の平衡正解率が、訓練側で選んだ単一規則を "
            f"{G10_MARGIN} 以上上回るときだけ成立。置換 p 値が {G10_ALPHA} 以上なら"
            "「この特徴では原産地を見分けられない」と別に書く"
        ),
    }

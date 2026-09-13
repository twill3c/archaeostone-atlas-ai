"""モデルカード(構想書 §18 / F-09 / F-10 / F-11)。

モデルカードは**モデルが何を言ってよいか**の宣言である。

* 主張の欄に構想書 §31.2 の禁止表現を置かない
* ただし限界の欄の「確定的な判定ではない」は**否定の中の引用**なので違反ではない(HC-074)
* 限界の欄が肯定の主張の逃げ場にならないよう、禁止表現を含む限界の文には
  否定の語を要求する(HC-041: 除外の仕掛けには緩みすぎを止める仕掛けを対で置く)
"""

from __future__ import annotations

import collections
from typing import Any

#: 構想書 §31.2 が AI 推定に対して禁じる表現。
FORBIDDEN_CLAIM_PHRASES: tuple[str, ...] = ("確定", "証明", "新発見", "交易路である")

#: 否定であることを示す語。限界の欄の文は、禁止表現を含むならこれを含まねばならない。
NEGATION_MARKERS: tuple[str, ...] = ("ではない", "ない", "しない", "ません")

LIMITATIONS_KEY = "limitations"


def _strings(value: Any, path: str = "") -> list[tuple[str, str]]:
    """カードの中の文字列を (経路, 文字列) で全部拾う。限界の欄は除く。"""
    out: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key == LIMITATIONS_KEY:
                continue
            out.extend(_strings(child, f"{path}.{key}" if path else key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            out.extend(_strings(child, f"{path}[{index}]"))
    elif isinstance(value, str):
        out.append((path, value))
    return out


def claim_violations(card: dict[str, Any]) -> list[str]:
    """禁止表現の違反を列挙する。無ければ空リスト。"""
    violations: list[str] = []
    for path, text in _strings(card):
        for phrase in FORBIDDEN_CLAIM_PHRASES:
            if phrase in text:
                violations.append(f"{path}: 主張の欄に「{phrase}」がある — {text[:60]}")
    for index, text in enumerate(card.get(LIMITATIONS_KEY, []) or []):
        hits = [p for p in FORBIDDEN_CLAIM_PHRASES if p in text]
        if hits and not any(marker in text for marker in NEGATION_MARKERS):
            violations.append(
                f"limitations[{index}]: 「{'・'.join(hits)}」を否定なしで含む — {text[:60]}"
            )
    return violations


# ── F-10 蛍光X線による原産地推定: No-Go ─────────────────

#: 明治大 COLS の分析リストの機器欄に現れた分析機器(実測 2026-09-08)。
#: 2025 年版の表記 ``JSX-3100Ⅱ`` は 2020 年版の ``JSX3100Ⅱ`` と同一機種とみなした。
COLS_INSTRUMENTS_SEEN: tuple[str, ...] = ("JSX3100Ⅱ", "SEA2110", "SEA2110L", "DELTA")

_NO_DATA = "学習に使える元素の測定値を 1 件も持っていないので、この基準は満たせない"


def xrf_no_go_card() -> dict[str, Any]:
    """構想書 §34 の Go / No-Go 基準を、項目ごとに根拠つきで判定したカード。"""
    go_criteria = [
        {
            "name": "実データ",
            "met": False,
            "evidence": (
                "元素の測定値(Rb・Sr・Y・Zr・Mn・Fe・K 等)を 1 件も入手していない。"
                "明治大 COLS の分析リストに載るのは遺跡ごとの判定結果(原産地名と点数)で、測定値ではない"
            ),
        },
        {
            "name": "再利用条件確認済み",
            "met": False,
            "evidence": (
                "唯一の候補である明治大 COLS の資料には明示ライセンスが無い"
                "(SRC-MEIJI-COLS の redistribution は false・2026-09-08 に確認)"
            ),
        },
        {
            "name": "5原産地群以上",
            "met": False,
            "evidence": (
                "原産地の名称は辞書に 14 件あるが、学習ラベルつきの測定値としては 0 件。"
                "群の数を数える対象が無い"
            ),
        },
        {"name": "各主要クラスに十分なサンプル", "met": False, "evidence": _NO_DATA},
        {"name": "Group split評価", "met": False, "evidence": _NO_DATA},
        {"name": "macro-F1公開", "met": False, "evidence": _NO_DATA},
        {"name": "calibration公開", "met": False, "evidence": _NO_DATA},
        {"name": "OOD拒否を実装", "met": False, "evidence": _NO_DATA},
    ]

    no_go_triggers = [
        {
            "name": "ラベルが文献ごとに不整合",
            "triggered": None,
            "evidence": "ラベルつきの測定値を持たないので、整合を調べられない(判定不能)",
        },
        {
            "name": "測定装置差の補正なし",
            "triggered": True,
            "instruments_seen": list(COLS_INSTRUMENTS_SEEN),
            "evidence": (
                f"明治大 COLS の分析リスト(2020・2025 年版)の機器欄に {len(COLS_INSTRUMENTS_SEEN)} 種の"
                "分析機器が記されている。同センター自身が「測定値が個別の分析機器に依存するという"
                "問題を抱えている」と書いており(map01.html)、機器間の補正値は公開されていない"
            ),
        },
        {
            "name": "学習/テストに同一原石由来サンプルが混入",
            "triggered": None,
            "evidence": "サンプルを持たないので調べられない(判定不能)",
        },
        {
            "name": "合成データ中心",
            "triggered": False,
            "evidence": "合成データで精度を補わない(構想書 §13.8)。合成データは作っていない",
        },
        {
            "name": "権利状態不明",
            "triggered": True,
            "evidence": (
                "明治大 COLS の分析リストに明示ライセンスが無い。構想書 §3.7.2 自身が"
                "「自動的にオープンデータ扱いしない」と定めている"
            ),
        },
    ]

    return {
        "model_id": "obsidian-provenance-xrf",
        "task": "蛍光X線の元素組成から黒曜石の原産地を推定する(構想書 §13)",
        "status": "no_go",
        "trained": False,
        "ui_enabled": False,
        "framework": None,
        "summary": (
            "構想書 §34 の Go 基準 8 項目のうち満たすものは 0 項目。"
            "No-Go の引き金のうち「測定装置差の補正なし」と「権利状態不明」が立つ。"
            "構想書 §13.8 の出口に従い、UI を無効にしてモデルカードだけを出す"
        ),
        "go_criteria": go_criteria,
        "no_go_triggers": no_go_triggers,
        "method_reference": (
            "明治大 COLS の判別図は Rb 分率・Sr 分率・Mn×100/Fe・Log(Fe/K) の 4 指標による"
            "(望月・池谷 1994)。本アトラスはこの方法を再実装していない"
        ),
        "limitations": [
            "このカードはモデルの性能を示すものではない。モデルは存在しない",
            "判定の根拠は 2026-09-08 時点で入手できた公開資料に限られ、他の資料が無いことを意味しない",
        ],
    }


# ── F-09 原産地らしさ ───────────────────────────────────


def _model_metrics(result_entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "balanced_accuracy": result_entry["balanced_accuracy"],
        "tp": result_entry["tp"],
        "fn": result_entry["fn"],
        "fp": result_entry["fp"],
        "tn": result_entry["tn"],
    }


def likeness_card(result: dict[str, Any], verdict: dict[str, Any], features: list[str]) -> dict[str, Any]:
    """G-10 の評価結果からカードを作る。置換分布は要約だけを載せる。"""
    logistic = result["logistic"]
    null = logistic.get("permutation_null", [])
    selected = collections.Counter(result["rule"]["selected_per_fold"])

    metrics = {
        "n_positive": result["n_positive"],
        "n_negative": result["n_negative"],
        "n_groups": result["n_groups"],
        "majority": _model_metrics(result["majority"]),
        "rule": {
            **_model_metrics(result["rule"]),
            "selected_rule_counts": dict(selected),
        },
        "logistic": {
            **_model_metrics(logistic),
            "pooled_auc": logistic.get("pooled_auc"),
            "permutation": {
                "n": len(null),
                "mean": (sum(null) / len(null)) if null else None,
                "max": max(null) if null else None,
                "p": logistic.get("permutation_p"),
                "seed": logistic.get("seed"),
            },
        },
    }

    difference = verdict["difference"]
    return {
        "model_id": "provenance-likeness-logistic",
        "task": "足もとの地質(二値特徴 14 個)から、その地点が黒曜石原産地らしいかを推定する",
        "status": "experimental",
        "trained": True,
        "ui_enabled": True,
        "framework": "scikit-learn LogisticRegression(class_weight=balanced)",
        "features": features,
        "training_data": [
            "public/data/source_areas.json(正例: 地質が取れた原産地)",
            "data/curated/control_points.json(負例: 面積の重みで抽出した陸地点)",
        ],
        "split": "1.5 度格子の一群抜き交差検証(原産地と対照点を同じ格子で束ねる)",
        "summary": (
            f"ロジスティック回帰の平衡正解率は {logistic['balanced_accuracy']:.4f}、"
            f"訓練側で選んだ単一規則は {result['rule']['balanced_accuracy']:.4f}。"
            f"差 {difference:+.4f} は事前に宣言した {verdict['margin']} に届かず、G-10 は{verdict['verdict']}。"
            "学習した組み合わせは、単一規則を宣言した幅では超えなかった"
        ),
        "metrics": metrics,
        "g10": verdict,
        "limitations": [
            "この分類器は H-01〜H-03 の確認にはならない。同じデータ・同じ計器から作った特徴で当てているため",
            "結果は研究仮説であり、確定的な原産地判定ではない",
            f"正例は {result['n_positive']} 件しかない。平衡正解率は正例 1 件で約 {verdict['resolution_per_positive']:.3f} 動く",
            "原産地辞書は網羅ではない。明治大 COLS は国内に 80 数カ所の原産地があると述べるが、辞書は 14 件",
            "20 万分の 1 の図郭は黒曜石の岩体より粗く、個々の岩相の label は黒曜石そのものの岩相ではない",
            "空間で分けたが、1.5 度格子より広い範囲の相関は取り除けていない",
        ],
    }

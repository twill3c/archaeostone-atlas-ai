"""モデルカードを作る(F-09 / F-10 / G-10)。

* F-09 原産地らしさ ―― 地質の二値特徴で一群抜き交差検証を回し、SPEC §12.3 の
  規則で G-10 を判定する。**判定規則は走らせる前に宣言してある**ので、ここでは当てるだけ
* F-10 蛍光X線 ―― 構想書 §34 の Go / No-Go を項目ごとに判定した No-Go カード

出荷前に禁止表現の門(F-11)を通す。違反があれば書き出さずに落ちる。

**出荷物に実行ごとに変わる値を載せない**(構想書 AC-06)。所要時間は標準出力にだけ出す。
実測(2026-09-14): 所要時間を出荷形に載せていたため、数がすべて一致しているのに
出荷物のバイト列が毎回変わっていた(158.1 秒 / 142.6 秒)。

    python -m pipeline.build_model_cards
"""

from __future__ import annotations

import argparse
import json
import pathlib
import time

import numpy as np

from archaeostone.likeness import (
    FEATURE_NAMES,
    evaluate_grouped,
    featurize,
    g10_verdict,
    spatial_group,
)
from archaeostone.model_cards import claim_violations, likeness_card, xrf_no_go_card
from pipeline.paths import display_path

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE_AREAS = REPO_ROOT / "public" / "data" / "source_areas.json"
CONTROL_POINTS = REPO_ROOT / "data" / "curated" / "control_points.json"
OUTPUT = REPO_ROOT / "public" / "data" / "model_cards.json"

PERMUTATIONS = 200
SEED = 20260914


def build_matrix() -> tuple[np.ndarray, np.ndarray, list[tuple[int, int]]]:
    sources = json.loads(SOURCE_AREAS.read_text(encoding="utf-8"))["source_areas"]
    controls = json.loads(CONTROL_POINTS.read_text(encoding="utf-8"))["control_points"]

    rows: list[list[int]] = []
    labels: list[int] = []
    groups: list[tuple[int, int]] = []
    for label, records in ((1, sources), (0, controls)):
        for record in records:
            features = featurize(record)
            if features is None:
                continue  # 地質が取れなかった点は 0 で埋めずに外す
            rows.append([features[name] for name in FEATURE_NAMES])
            labels.append(label)
            groups.append(spatial_group(record["latitude"], record["longitude"]))
    return np.array(rows), np.array(labels), groups


def build() -> dict:
    """出荷形を作る。**実行ごとに変わる値は入れない。**"""
    X, y, groups = build_matrix()
    result = evaluate_grouped(X, y, groups, permutations=PERMUTATIONS, seed=SEED)

    verdict = g10_verdict(
        logistic_ba=result["logistic"]["balanced_accuracy"],
        rule_ba=result["rule"]["balanced_accuracy"],
        permutation_p=result["logistic"]["permutation_p"],
        n_positive=result["n_positive"],
    )

    cards = [likeness_card(result, verdict, list(FEATURE_NAMES)), xrf_no_go_card()]

    # ── 禁止表現の門(F-11)。ここを通らないカードは書き出さない ──
    problems = {card["model_id"]: claim_violations(card) for card in cards}
    problems = {k: v for k, v in problems.items() if v}
    if problems:
        raise RuntimeError(f"モデルカードに禁止表現がある: {problems}")

    return {
        "generated_by": "pipeline.build_model_cards",
        "cards": cards,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="モデルカードを作る")
    parser.add_argument("--out", type=pathlib.Path, default=OUTPUT)
    args = parser.parse_args()

    started = time.time()
    payload = build()
    elapsed = time.time() - started

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    likeness = payload["cards"][0]
    metrics = likeness["metrics"]
    # 所要時間は標準出力にだけ出す(出荷形に載せると実行ごとにバイト列が変わる)。
    print(f"{display_path(args.out)} を書き出した(評価 {elapsed:.1f} 秒)")
    for model in ("majority", "rule", "logistic"):
        m = metrics[model]
        print(
            f"  {model:<9} BA {m['balanced_accuracy']:.4f}  TP {m['tp']}/{metrics['n_positive']}"
            f"  FP {m['fp']}/{metrics['n_negative']}"
        )
    g10 = likeness["g10"]
    print(
        f"  G-10 {g10['verdict']}(差 {g10['difference']:+.4f} / 宣言 {g10['margin']})"
        f"  見分けられる={g10['distinguishable']}(置換 p {g10['permutation_p']:.4f})"
    )
    xrf = payload["cards"][1]
    met = sum(1 for c in xrf["go_criteria"] if c["met"])
    print(f"  XRF: {xrf['status']} / Go 基準 {met}/{len(xrf['go_criteria'])} / UI {xrf['ui_enabled']}")


if __name__ == "__main__":
    main()

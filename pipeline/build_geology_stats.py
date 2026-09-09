"""原産地と対照群の地質分布を比べる(F-08 / G-09)。

**判定の規則を先に決めてある。** ある主張が「成立」と言えるのは、
宣言した感度分析の**すべての条件で** p < 0.05 を保つときだけである。
一つの切り方で有意になり別の切り方で有意でなくなる主張は、
「有意だった」ではなく **「成立しなかった」** と書く。

有意でなかった主張も消さずに載せる(SPEC §7 G-09)。外れた予測を残すのは、
後から読む人の判断材料になるからである。

    python -m pipeline.build_geology_stats
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
from typing import Any

from archaeostone.geology_stats import PermutationResult, category_counts, permutation_test

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE_AREAS = REPO_ROOT / "public" / "data" / "source_areas.json"
CONTROL_POINTS = REPO_ROOT / "data" / "curated" / "control_points.json"
OUTPUT = REPO_ROOT / "public" / "data" / "geology_stats.json"

ITERATIONS = 20_000
SEED = 20260909

#: 「成立」の判定に使う有意水準。感度分析の**すべて**で下回ることを要求する。
ALPHA = 0.05


def _felsic(lithology: str | None) -> str | None:
    """珪長質火山岩(デイサイト・流紋岩)かどうか。

    黒曜石は流紋岩質のガラスなので、本来この区分に入るはずである。
    「溶岩・火砕岩」と「大規模火砕流」は凡例では別項目なので、
    **細分と、まとめた場合の両方**を測る(切り方に結論が依存しないかを見る)。
    """
    if lithology is None:
        return None
    return "FELSIC" if "デイサイト・流紋岩" in lithology or "流紋岩" in lithology else "OTHER"


def _quaternary_igneous(record: dict) -> str | None:
    group = record.get("geology_group_ja")
    if group is None:
        return None
    age = record.get("formation_age_ja") or ""
    return "YES" if (group == "火成岩" and "第四紀" in age) else "NO"


def _result_dict(result: PermutationResult) -> dict[str, Any]:
    return {
        "target": result.target,
        "source_n": result.source_n,
        "control_n": result.control_n,
        "source_proportion": result.source_proportion,
        "control_proportion": result.control_proportion,
        "observed_difference": result.observed_difference,
        "p_value": result.p_value,
        "iterations": result.iterations,
        "seed": result.seed,
        "reason": result.reason,
    }


def build() -> dict:
    source_payload = json.loads(SOURCE_AREAS.read_text(encoding="utf-8"))
    control_payload = json.loads(CONTROL_POINTS.read_text(encoding="utf-8"))
    sources = source_payload["source_areas"]
    controls = control_payload["control_points"]

    precise = [r for r in sources if r.get("coordinate_precision") != "area"]

    def test(src: list[dict], extract, target: str) -> PermutationResult:
        return permutation_test(
            [extract(r) for r in src],
            [extract(r) for r in controls],
            target=target,
            iterations=ITERATIONS,
            seed=SEED,
        )

    group = lambda r: r.get("geology_group_ja")  # noqa: E731
    lith = lambda r: r.get("lithology_ja")  # noqa: E731
    felsic = lambda r: _felsic(r.get("lithology_ja"))  # noqa: E731

    claims = [
        {
            "claim_id": "H-01",
            "statement": "黒曜石原産地の足もとの地質は、無作為な陸地点と比べて火成岩に偏る",
            "variants": {
                "全件": test(sources, group, "火成岩"),
                "面積精度の点を除く": test(precise, group, "火成岩"),
            },
        },
        {
            "claim_id": "H-02",
            "statement": "同じ偏りは、第四紀の火成岩に絞るとさらに強く出る",
            "variants": {
                "全件": test(sources, _quaternary_igneous, "YES"),
                "面積精度の点を除く": test(precise, _quaternary_igneous, "YES"),
            },
        },
        {
            "claim_id": "H-03",
            "statement": (
                "黒曜石は流紋岩質のガラスなので、原産地は珪長質火山岩"
                "(デイサイト・流紋岩)に偏る"
            ),
            "variants": {
                "細分(溶岩・火砕岩のみ)": test(sources, lith, "デイサイト・流紋岩 溶岩・火砕岩"),
                "まとめる(大規模火砕流も含む)": test(sources, felsic, "FELSIC"),
                "まとめる・面積精度の点を除く": test(precise, felsic, "FELSIC"),
            },
        },
    ]

    out_claims = []
    for claim in claims:
        variants = claim["variants"]
        p_values = [r.p_value for r in variants.values()]
        testable = [p for p in p_values if p is not None]

        if not testable or len(testable) != len(p_values):
            verdict, note = "検定不可", "一部の条件で検定できなかった"
        elif all(p < ALPHA for p in testable):
            verdict = "成立"
            note = f"宣言した {len(testable)} 通りの条件すべてで p < {ALPHA}"
        elif any(p < ALPHA for p in testable):
            verdict = "不成立"
            note = (
                f"条件によって有意性が入れ替わる(p = "
                + " / ".join(f"{p:.5f}" for p in testable)
                + f")。一つの切り方で有意でも、別の切り方で {ALPHA} を超えるなら成立とは書かない"
            )
        else:
            verdict = "不成立"
            note = f"どの条件でも p >= {ALPHA}"

        out_claims.append(
            {
                "claim_id": claim["claim_id"],
                "statement": claim["statement"],
                "verdict": verdict,
                "verdict_note": note,
                "variants": {name: _result_dict(r) for name, r in variants.items()},
            }
        )

    return {
        "generated_by": "pipeline.build_geology_stats",
        "method": {
            "test": "ラベル置換検定(両側)",
            "iterations": ITERATIONS,
            "seed": SEED,
            "alpha": ALPHA,
            "verdict_rule": (
                f"宣言した感度分析のすべての条件で p < {ALPHA} のときだけ「成立」とする。"
                "一つの切り方で有意になり別の切り方で有意でなくなる主張は「不成立」と書く。"
            ),
            "control_group": (
                "GSJ シームレス地質図タイル z7 を陸マスクとして、"
                "cos^2(緯度) の重みで無作為抽出した陸地点。"
                "地質は原産地と同じ点の問い合わせ API から取る(計器を揃える)。"
            ),
            "non_circularity": (
                "原産地の一覧は考古・岩石学の文献から編み、地質図は産総研が独立に作っている。"
                "両者は互いを前提にしていないので、突き合わせても恒等式にならない。"
            ),
            "limitation": (
                "20 万分の 1 の図郭は黒曜石の岩体より粗い。実測(2026-09-09)では、"
                "原産地 13 件のうち珪長質火山岩の label を持つのは 5 件で、"
                "6 件は安山岩・玄武岩質安山岩と出る。**個々の label は黒曜石そのものの"
                "岩相ではない**。だから H-03 のような細分の主張は弱い。"
            ),
        },
        "distributions": {
            "source_areas": {
                "group_ja": category_counts([r.get("geology_group_ja") for r in sources]),
                "lithology_ja": dict(
                    collections.Counter(
                        v for v in (r.get("lithology_ja") for r in sources) if v
                    ).most_common()
                ),
                "n": len(sources),
                "n_measured": sum(1 for r in sources if r.get("geology_group_ja")),
            },
            "control_points": {
                "group_ja": category_counts([r.get("geology_group_ja") for r in controls]),
                "lithology_ja": dict(
                    collections.Counter(
                        v for v in (r.get("lithology_ja") for r in controls) if v
                    ).most_common(15)
                ),
                "n": len(controls),
                "n_measured": sum(1 for r in controls if r.get("geology_group_ja")),
            },
        },
        "claims": out_claims,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="地質分布の比較と検定")
    parser.add_argument("--out", type=pathlib.Path, default=OUTPUT)
    args = parser.parse_args()

    payload = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )

    print(f"{args.out.relative_to(REPO_ROOT)} を書き出した\n")
    for claim in payload["claims"]:
        print(f"[{claim['claim_id']}] {claim['verdict']} — {claim['statement']}")
        for name, variant in claim["variants"].items():
            p = variant["p_value"]
            src, ctl = variant["source_proportion"], variant["control_proportion"]
            shown = f"p={p:.5f}" if p is not None else f"検定不可({variant['reason']})"
            print(
                f"    {name:<28} 原産地 {src:6.1%} (n={variant['source_n']:>2})"
                f" vs 対照 {ctl:6.1%} (n={variant['control_n']})  {shown}"
            )
        print(f"    → {claim['verdict_note']}\n")


if __name__ == "__main__":
    main()

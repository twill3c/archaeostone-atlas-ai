"""モデルカードの検査(T-320〜 / F-09 / F-10 / F-11)。

モデルカードは**モデルが何を言ってよいか**の宣言である。だから二つを固定する。

1. **判定は保存された数から再計算しても同じになる。** カードに書いた「不成立」が、
   カードに書いた平衡正解率から SPEC §12.3 の規則で導けること(二経路)
2. **主張の欄に禁止表現が無い。** ただし「確定的な判定ではない」のような
   **否定の中の引用**は違反ではない(HC-074)。主張の欄と限界の欄を分け、
   限界の欄が否定でない文の逃げ場にならないことも対で確かめる
"""

import json
import pathlib

import pytest

from archaeostone.model_cards import (
    FORBIDDEN_CLAIM_PHRASES,
    claim_violations,
    xrf_no_go_card,
)

CARDS = pathlib.Path(__file__).parent.parent / "public" / "data" / "model_cards.json"


# ── 禁止表現の検査器そのもの(生成物不要) ──────────────


def test_t320_positive_control_a_claim_with_a_forbidden_phrase_is_caught() -> None:
    """T-320(陽性対照): 主張の欄に禁止表現があれば捕まえる。"""
    card = {"summary": "このモデルは原産地を確定した", "limitations": []}
    violations = claim_violations(card)
    assert violations, "禁止表現を見逃している"
    assert any("確定" in v for v in violations)


def test_t321_negative_control_negated_quote_in_limitations_is_allowed() -> None:
    """T-321(陰性対照): 限界の欄の「確定的な判定ではない」は違反ではない。

    構想書 §18 の雛形そのものが「確定的な原産地判定ではない」と書く。
    否定の中の引用まで撃つ検査は、正しいカードを落とす。
    """
    card = {
        "summary": "地質の二値特徴から原産地らしさを推定するモデル推定",
        "limitations": ["結果は研究仮説であり、確定的な原産地判定ではない"],
    }
    assert claim_violations(card) == []


def test_t322_limitations_cannot_hide_an_affirmative_claim() -> None:
    """T-322: 限界の欄は、否定でない文の逃げ場にならない。

    除外の仕掛けには緩みすぎを止める仕掛けを対で置く(HC-041)。
    限界の欄に否定の語を持たない文があれば、それも違反にする。
    """
    card = {"summary": "モデル推定", "limitations": ["このモデルは新発見を証明した"]}
    violations = claim_violations(card)
    assert violations, "限界の欄に肯定の主張を隠せてしまう"


def test_t323_forbidden_list_matches_the_spec() -> None:
    """T-323: 禁止表現が構想書 §31.2 の四語を含む。"""
    assert {"確定", "証明", "新発見", "交易路である"} <= set(FORBIDDEN_CLAIM_PHRASES)


# ── F-10 XRF の No-Go カード(生成物不要) ──────────────


def test_t324_xrf_card_is_no_go_with_ui_disabled() -> None:
    """T-324: 蛍光X線による原産地推定は No-Go で、UI を無効にする(構想書 §13.8)。"""
    card = xrf_no_go_card()
    assert card["status"] == "no_go"
    assert card["ui_enabled"] is False
    assert card["trained"] is False


def test_t325_every_go_criterion_is_judged_with_evidence() -> None:
    """T-325: 構想書 §34 の Go 基準 8 項目を、項目ごとに根拠つきで判定する。

    「No-Go」と一言で済ませると、どの基準で落ちたのか後から辿れない。
    """
    card = xrf_no_go_card()
    criteria = card["go_criteria"]
    assert len(criteria) == 8
    for criterion in criteria:
        assert set(criterion) >= {"name", "met", "evidence"}
        assert isinstance(criterion["met"], bool)
        assert criterion["evidence"], f"{criterion['name']} に根拠が無い"
    assert not all(c["met"] for c in criteria), "全部満たすなら No-Go ではない"


def test_t326_no_go_triggers_cite_measured_facts() -> None:
    """T-326: No-Go の引き金が、実測した事実を根拠にしている。

    実測 2026-09-08: 明治大 COLS の分析リストには分析機器が 3 種以上記されている
    (JSX3100Ⅱ・SEA2110・SEA2110L・DELTA)。機器間の補正は公開されていない。
    権利表示は存在しない(SRC-MEIJI-COLS の redistribution は false)。
    """
    card = xrf_no_go_card()
    triggered = {t["name"]: t for t in card["no_go_triggers"] if t["triggered"]}
    assert "権利状態不明" in triggered
    assert "測定装置差の補正なし" in triggered
    instruments = triggered["測定装置差の補正なし"]["instruments_seen"]
    assert len(set(instruments)) >= 3, instruments


# ── 出荷されたカード ────────────────────────────────────


@pytest.fixture(scope="module")
def cards() -> dict:
    if not CARDS.exists():
        pytest.skip(f"{CARDS} が無い。`python -m pipeline.build_model_cards` で作る")
    return json.loads(CARDS.read_text(encoding="utf-8"))


def test_t327_shipped_cards_have_no_forbidden_claims(cards: dict) -> None:
    """T-327: 出荷された全カードの主張の欄に禁止表現が無い(F-11)。"""
    for card in cards["cards"]:
        assert claim_violations(card) == [], card["model_id"]


def test_t328_likeness_verdict_is_reproducible_from_stored_metrics(cards: dict) -> None:
    """T-328: カードの判定を、カードの数から SPEC §12.3 で再計算しても同じ(二経路)。

    判定の文字列だけを保存すると、数と判定が食い違っても気づけない。
    """
    from archaeostone.likeness import g10_verdict

    card = next(c for c in cards["cards"] if c["model_id"] == "provenance-likeness-logistic")
    metrics = card["metrics"]
    recomputed = g10_verdict(
        logistic_ba=metrics["logistic"]["balanced_accuracy"],
        rule_ba=metrics["rule"]["balanced_accuracy"],
        permutation_p=metrics["logistic"]["permutation"]["p"],
        n_positive=metrics["n_positive"],
    )
    assert card["g10"]["verdict"] == recomputed["verdict"]
    assert card["g10"]["distinguishable"] == recomputed["distinguishable"]


def test_t329_likeness_card_counts_are_consistent(cards: dict) -> None:
    """T-329: 件数が正例数・負例数と整合する(HC-152)。"""
    card = next(c for c in cards["cards"] if c["model_id"] == "provenance-likeness-logistic")
    metrics = card["metrics"]
    for model in ("majority", "rule", "logistic"):
        m = metrics[model]
        assert m["tp"] + m["fn"] == metrics["n_positive"]
        assert m["fp"] + m["tn"] == metrics["n_negative"]


def test_t330_likeness_card_says_it_does_not_confirm_the_geology_claims(cards: dict) -> None:
    """T-330: 分類器が H-01〜H-03 の確認にならないことを限界に書いている(HC-045)。"""
    card = next(c for c in cards["cards"] if c["model_id"] == "provenance-likeness-logistic")
    joined = "".join(card["limitations"])
    assert "H-01" in joined
    assert "確認にはならない" in joined


def test_t331_permutation_is_summarised_not_dumped(cards: dict) -> None:
    """T-331: 置換分布は要約で出す(回数・平均・最大・p)。200 個の生値は配らない。"""
    card = next(c for c in cards["cards"] if c["model_id"] == "provenance-likeness-logistic")
    permutation = card["metrics"]["logistic"]["permutation"]
    assert set(permutation) >= {"n", "mean", "max", "p", "seed"}
    assert "permutation_null" not in card["metrics"]["logistic"]


def test_t332_shipped_xrf_card_is_the_no_go_card(cards: dict) -> None:
    card = next(c for c in cards["cards"] if c["model_id"] == "obsidian-provenance-xrf")
    assert card["status"] == "no_go"
    assert card["ui_enabled"] is False

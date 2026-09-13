"""出荷器が、リポジトリ外の出力先でも落ちないこと(T-341〜)。

実測(2026-09-14): 再現性の確認で ``python -m pipeline.build_model_cards --out <スクラッチパッド>``
を走らせたところ、**ファイルを書き終えた後の print** で
``args.out.relative_to(REPO_ROOT)`` が ``ValueError`` を投げて異常終了した。
同じ書き方が出荷器・取得器の 8 箇所にあった。

しかもその Traceback は、確認コマンドの ``| head -1`` に隠れていた(HC-080)。
だから個々の出荷器を走らせる検査ではなく、**表示用の経路を作る関数を一つにまとめ**、
その関数と「直接 relative_to(REPO_ROOT) を呼んでいないこと」を確かめる。
"""

import pathlib
import re

import pytest

from pipeline.paths import REPO_ROOT, display_path

PIPELINE_DIR = REPO_ROOT / "pipeline"

#: 表示のためにリポジトリ基準の相対経路を直接作る書き方。
DIRECT_RELATIVE = re.compile(r"\.relative_to\(\s*REPO_ROOT\s*\)")


def direct_relative_calls(text: str) -> int:
    return len(DIRECT_RELATIVE.findall(text))


# ── display_path ────────────────────────────────────────


def test_t341_path_inside_the_repo_is_shown_relative() -> None:
    """T-341: リポジトリの中なら相対経路で見せる。"""
    inside = REPO_ROOT / "public" / "data" / "model_cards.json"
    assert display_path(inside) == str(pathlib.Path("public") / "data" / "model_cards.json")


def test_t342_path_outside_the_repo_does_not_raise(tmp_path: pathlib.Path) -> None:
    """T-342: リポジトリの外なら例外を投げず、そのままの経路で見せる。

    **実際に踏んだ欠陥の再現。** 書き終えた後に落ちると、ファイルはできているのに
    終了コードは失敗になり、成否の読み方が反転する。
    """
    outside = tmp_path / "model_cards_second.json"
    with pytest.raises(ValueError):
        outside.relative_to(REPO_ROOT)  # 前提の固定: 素朴な書き方は本当に落ちる
    assert display_path(outside) == str(outside)


def test_t343_relative_input_is_resolved_against_the_current_directory(
    tmp_path: pathlib.Path, monkeypatch
) -> None:
    """T-343: 相対経路で渡されても落ちない(--out に相対経路を書く人はいる)。"""
    monkeypatch.chdir(tmp_path)
    shown = display_path(pathlib.Path("out.json"))
    assert shown.endswith("out.json")


# ── 直接の relative_to を残さない ───────────────────────


def test_t344_positive_control_the_scanner_finds_the_old_idiom() -> None:
    """T-344(陽性対照): 実際に 8 箇所にあった書き方を検出する。"""
    old = 'print(f"{args.out.relative_to(REPO_ROOT)} を書き出した")'
    assert direct_relative_calls(old) == 1


def test_t345_negative_control_the_helper_itself_is_not_flagged() -> None:
    """T-345(陰性対照): 表示用の関数を呼ぶ書き方は撃たない。"""
    new = 'print(f"{display_path(args.out)} を書き出した")'
    assert direct_relative_calls(new) == 0


def test_t346_scan_targets_are_not_empty() -> None:
    """T-346: 走査対象に出荷器が実際に含まれる(HC-041)。"""
    files = sorted(PIPELINE_DIR.rglob("*.py"))
    names = {p.name for p in files}
    assert {"build_model_cards.py", "build_source_areas.py", "export_licenses.py"} <= names


@pytest.mark.parametrize(
    "path",
    [p for p in sorted(PIPELINE_DIR.rglob("*.py")) if p.name != "paths.py"],
    ids=lambda p: str(p.relative_to(PIPELINE_DIR)),
)
def test_t347_no_pipeline_builds_display_paths_with_relative_to(path: pathlib.Path) -> None:
    """T-347: 出荷器・取得器が relative_to(REPO_ROOT) を直接呼んでいない。

    ``paths.py`` だけは、例外を捕まえる前提でその呼び出しを持つので除く。
    """
    count = direct_relative_calls(path.read_text(encoding="utf-8"))
    assert count == 0, f"{path.name} に relative_to(REPO_ROOT) が {count} 箇所ある"

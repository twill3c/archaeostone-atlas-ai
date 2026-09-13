"""出荷ファイルが実行ごとに変わる値を持たないこと(T-337〜 / 構想書 AC-06)。

**同じ入力と同じ種から作った出荷物は、バイト列まで同じでなければならない。**
実測(2026-09-14): ``model_cards.json`` に所要時間 ``evaluation_seconds`` を載せていて、
一度目 158.1 秒・二度目 142.6 秒と、数がすべて一致しているのに出荷物だけが毎回変わった。
値は画面に出ておらず、どの検査もバイト列の再現性を見ていなかったので、全部緑のまま通っていた。
"""

import json
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
PUBLIC_DATA = ROOT / "public" / "data"

#: 実行ごとに変わる値を示す鍵の名前。
RUN_DEPENDENT_KEY = re.compile(
    r"(seconds|elapsed|duration|timestamp|generated_at|retrieved_at|run_at|_time$)",
    re.IGNORECASE,
)


def run_dependent_keys(value, path: str = "") -> list[str]:
    """入れ子の中の、実行依存の鍵を経路つきで列挙する。"""
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            if RUN_DEPENDENT_KEY.search(key):
                found.append(child_path)
            found.extend(run_dependent_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(run_dependent_keys(child, f"{path}[{index}]"))
    return found


def shipped_files() -> list[pathlib.Path]:
    return sorted(PUBLIC_DATA.glob("*.json"))


def test_t337_positive_control_run_dependent_keys_are_caught() -> None:
    """T-337(陽性対照): 実際に載せていた鍵と、よくある実行依存の鍵を捕まえる。"""
    payload = {
        "evaluation_seconds": 142.6,
        "cards": [{"meta": {"generated_at": "2026-09-14T10:00:00"}}],
    }
    assert run_dependent_keys(payload) == ["evaluation_seconds", "cards[0].meta.generated_at"]


def test_t338_negative_control_stable_keys_pass() -> None:
    """T-338(陰性対照): 種・件数・検証日のような固定の値は撃たない。

    ``seed`` や ``verified_at``(権利表示を読んだ日 — 入力の一部)は実行ごとに変わらない。
    """
    payload = {"seed": 20260914, "n": 200, "verified_at": "2026-09-08", "iterations": 20000}
    assert run_dependent_keys(payload) == []


def test_t339_there_are_shipped_files_to_scan() -> None:
    """T-339: 走査対象が空でない(HC-041)。"""
    names = {p.name for p in shipped_files()}
    assert {"model_cards.json", "source_areas.json", "geology_stats.json"} <= names, names


@pytest.mark.parametrize("path", shipped_files(), ids=lambda p: p.name)
def test_t340_shipped_file_has_no_run_dependent_keys(path: pathlib.Path) -> None:
    """T-340: 出荷ファイルに実行ごとに変わる鍵が無い(構想書 AC-06)。"""
    keys = run_dependent_keys(json.loads(path.read_text(encoding="utf-8")))
    assert keys == [], f"{path.name} に実行依存の鍵: {keys}"

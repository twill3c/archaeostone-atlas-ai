"""材質辞書・時代辞書の読み込み(SPEC §4)。

辞書は抽出・正規化・表示の三箇所から使われる。**同じ語が二つの概念へ属していないこと**
だけは、どこで使うにせよ壊れてはならない不変量なので、索引を作る側で例外にする
(黙って一方に倒れる道を残さない — HC-075)。
"""

from __future__ import annotations

import functools
import pathlib
from typing import Any

import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG_DIR = REPO_ROOT / "config"


def _load_yaml(path: pathlib.Path) -> dict[str, Any]:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or not doc:
        raise ValueError(f"{path.name} が空、または辞書ではない")
    return doc


@functools.cache
def load_materials() -> dict[str, dict[str, Any]]:
    """`config/materials.yaml`。"""
    return _load_yaml(CONFIG_DIR / "materials.yaml")


@functools.cache
def load_periods() -> dict[str, Any]:
    """`config/periods.yaml`(`authority` と `periods` を持つ)。"""
    doc = _load_yaml(CONFIG_DIR / "periods.yaml")
    for key in ("authority", "periods"):
        if key not in doc:
            raise ValueError(f"periods.yaml に {key} が無い")
    return doc


@functools.cache
def material_lookup() -> dict[str, str]:
    """表記 → material_id の索引。

    衝突は返り値で示さず**例外にする**。呼ぶ側が索引を作り直すたびに黙って
    上書きされる形にすると、辞書に語を足した日に壊れて誰も気づかない。
    """
    index: dict[str, str] = {}
    owner: dict[str, str] = {}
    for key, entry in load_materials().items():
        material_id = entry["material_id"]
        terms = [entry["label_ja"], entry["label_en"], *entry.get("synonyms", [])]
        for term in terms:
            term = term.strip()
            if not term:
                raise ValueError(f"{key} に空の表記がある")
            if term in index and index[term] != material_id:
                raise ValueError(
                    f"表記 {term!r} が {owner[term]} と {key} の両方に属している"
                )
            index[term] = material_id
            owner[term] = key
    return index


def normalize_material(text: str) -> str | None:
    """表記を material_id へ。引けなければ None(推測しない)。"""
    return material_lookup().get(text.strip())


def period_codes() -> list[str]:
    return list(load_periods()["periods"])

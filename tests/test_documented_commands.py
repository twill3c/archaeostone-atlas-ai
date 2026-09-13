"""文書に書いた再現コマンドが実在するか(T-333〜 / HC-152)。

**文書に書いたコマンドはテストに守られない。** 実測(2026-09-14): README と方法の頁に
L0 から ``python -m pipeline.acquire --source itoigawa`` と ``python -m pipeline.export`` が
載っていたが、そのモジュールは一度も作っていない。構想書 §7.4 の形を写して書き、
実装が別の形に育っても文書は黙って古いまま残った。

だから文書と画面から ``python -m <モジュール>`` を拾い、そのモジュールのファイルが
リポジトリに実在することを確かめる。
"""

import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent

#: 本リポジトリの外のモジュール(標準ライブラリ・導入物)。実在の検査から外す。
EXTERNAL_MODULES = frozenset({"venv", "pip", "pytest"})

COMMAND = re.compile(r"python\s+-m\s+([A-Za-z_][\w.]*)")


def documents() -> list[pathlib.Path]:
    """コマンドを書きうる文書と画面。"""
    paths = [ROOT / "README.md"]
    paths.extend(sorted((ROOT / "app").rglob("*.tsx")))
    paths.extend(sorted((ROOT / "components").rglob("*.tsx")))
    return [p for p in paths if p.exists()]


def module_exists(module: str) -> bool:
    """モジュール名に対応するファイル(``a/b.py`` か ``a/b/__init__.py``)があるか。"""
    base = ROOT.joinpath(*module.split("."))
    return base.with_suffix(".py").exists() or (base / "__init__.py").exists()


def missing_commands(text: str) -> list[str]:
    """文章の中の、実在しないモジュールを指すコマンドを列挙する。"""
    missing = []
    for module in COMMAND.findall(text):
        if module.split(".")[0] in EXTERNAL_MODULES:
            continue
        if not module_exists(module):
            missing.append(module)
    return missing


# ── 検査器そのものの対照 ────────────────────────────────


def test_t333_positive_control_a_nonexistent_module_is_caught() -> None:
    """T-333(陽性対照): 実際に古いまま残っていたコマンドを捕まえる。"""
    text = "python -m pipeline.acquire --source itoigawa\npython -m pipeline.export"
    assert missing_commands(text) == ["pipeline.acquire", "pipeline.export"]


def test_t334_negative_control_real_modules_and_external_ones_pass() -> None:
    """T-334(陰性対照): 実在するモジュールと外部モジュールは素通りする。

    陰性対照を先に確かめる —— 誤検出があれば、画面の検査より先に分かる(HC-074)。
    """
    text = (
        "python -m pipeline.build_model_cards\n"
        "python -m pipeline.acquisition.itoigawa\n"
        "python -m venv .venv\n"
        "python -m pytest"
    )
    assert missing_commands(text) == []


def test_t335_scan_targets_are_not_empty() -> None:
    """T-335: 走査対象が空でなく、README にコマンドが実際に書かれていること。

    走査対象が空だと、次の検査は何も見ないまま緑になる(HC-041)。
    """
    targets = documents()
    assert any(p.name == "README.md" for p in targets)
    assert any(p.parent.name == "methodology" for p in targets), "方法の頁を走査していない"
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert len(COMMAND.findall(readme)) >= 5, "README に拾えるコマンドが少なすぎる"


# ── 本検査 ──────────────────────────────────────────────


@pytest.mark.parametrize("path", documents(), ids=lambda p: str(p.relative_to(ROOT)))
def test_t336_every_documented_command_points_to_a_real_module(path: pathlib.Path) -> None:
    """T-336: 文書と画面に書いた ``python -m`` のモジュールが全て実在する。"""
    missing = missing_commands(path.read_text(encoding="utf-8"))
    assert missing == [], f"{path.relative_to(ROOT)} に実在しないモジュールのコマンド: {missing}"

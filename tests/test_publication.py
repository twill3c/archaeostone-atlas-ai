"""公開の直前に確かめること(T-400〜T-405 / G-13)。

実測(2026-09-14)で公開前に見つかった二つの誤りを、検査で固定する。

1. **フッタのリンクが押しても届かない先を指していた。** App Menu は
   ``app-menu-tau.vercel.app``(404)で、本物は ``app-menu-amber.vercel.app``。
   GitHub は存在しないアカウントを指していた。どちらもビルドも検品も緑のまま通っていた
2. **``.vercelignore`` の無印パターンは深い階層にも当たる。** ``data/`` と書くと
   画面が読む ``public/data/`` まで消える(folksound-atlas で実際に踏まれた)
"""

import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
FOOTER = ROOT / "components" / "Footer.tsx"
VERCELIGNORE = ROOT / ".vercelignore"

APP_MENU_PRODUCTION = "https://app-menu-amber.vercel.app/"
GITHUB_REPO = "https://github.com/twill3c/archaeostone-atlas-ai"

#: どの階層にあっても要らないと分かっている生成物だけは、無印を許す。
UNANCHORED_ALLOWED = {"__pycache__/", "*.pyc", ".pytest_cache/"}

#: Vercel のビルドに要るもの。どれも除外されてはならない。
REQUIRED_FOR_BUILD = [
    "app/page.tsx",
    "components/Footer.tsx",
    "lib/evidence.ts",
    "public/data/source_areas.json",
    "public/data/model_cards.json",
    "scripts/build_stamp.mjs",
    "package.json",
    "package-lock.json",
    "next.config.mjs",
    "tsconfig.json",
]

#: 送ってはならないもの(容量・権利・秘密)。
MUST_EXCLUDE = [
    "data/raw/itoigawa/jade_occurrences.xls",
    "data/raw/nabunken/page_00000.xml",
    "node_modules/next/package.json",
    ".venv/pyvenv.cfg",
    ".next/BUILD_ID",
    "out/index.html",
    ".env.local",
    ".vercel/project.json",
]


def patterns(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip() and not line.startswith("#")]


def matches(pattern: str, path: str) -> bool:
    """gitignore の意味で、パターンが経路に当たるか(この検査に要る範囲で)。

    * ``/x/`` …… 直下の x ディレクトリの中身
    * ``/x`` …… 直下の x(ファイルでもディレクトリでも)。``*`` は 1 階層の中の任意文字列
    * 無印 ``x/`` …… **どの階層の** x ディレクトリの中身にも当たる
    * 無印 ``*.ext`` …… どの階層の同じ拡張子にも当たる
    """
    parts = path.split("/")
    if pattern.startswith("/"):
        body = pattern[1:]
        if body.endswith("/"):
            return path.startswith(body)
        regex = "^" + re.escape(body).replace(r"\*", "[^/]*") + "(/.*)?$"
        return re.match(regex, path) is not None
    if pattern.endswith("/"):
        name = pattern[:-1]
        return name in parts[:-1]
    regex = "^" + re.escape(pattern).replace(r"\*", "[^/]*") + "$"
    return any(re.match(regex, part) for part in parts)


# ── フッタ ──────────────────────────────────────────────


def test_t400_footer_app_menu_points_to_the_real_production() -> None:
    """T-400: App Menu は本物の本番を指し、404 の別名や他者のサービスを指さない。"""
    text = FOOTER.read_text(encoding="utf-8")
    assert APP_MENU_PRODUCTION in text
    assert "app-menu-tau" not in text, "404 の別名(kofun-atlas から写したもの)が残っている"
    assert "app-menu.vercel.app" not in text, "app-menu.vercel.app は他者のサービス"


def test_t401_footer_github_is_the_real_repo_or_hidden() -> None:
    """T-401: GitHub は実在するリポジトリを指すか、項目を出さない(null)かのどちらか。

    存在しないアカウントを指すリンクは、押すまで壊れていることが分からない。
    """
    text = FOOTER.read_text(encoding="utf-8")
    match = re.search(r"const GITHUB_URL[^=]*=\s*(null|\"([^\"]*)\")", text)
    assert match, "GITHUB_URL の定義が見つからない"
    value = match.group(2)
    assert value in (None, GITHUB_REPO), f"GitHub が想定外の先を指している: {value}"
    assert "tetsuro-sakata" not in text


# ── .vercelignore ───────────────────────────────────────


def test_t405_positive_control_unanchored_pattern_would_remove_public_data() -> None:
    """T-405(陽性対照): 無印の ``data/`` は ``public/data`` まで消す。

    この対照が無いと、T-402 の「先頭 / で固定」は理由の無い形式の検査に見える。
    """
    assert matches("data/", "public/data/source_areas.json") is True
    assert matches("/data/", "public/data/source_areas.json") is False
    assert matches("/data/", "data/raw/nabunken/page_00000.xml") is True


def test_t402_vercelignore_patterns_are_anchored() -> None:
    """T-402: パターンは先頭 / で固定する(許した生成物を除く)。"""
    assert VERCELIGNORE.exists(), ".vercelignore が無い"
    found = patterns(VERCELIGNORE.read_text(encoding="utf-8"))
    assert found, ".vercelignore にパターンが無い"
    loose = [p for p in found if not p.startswith("/") and p not in UNANCHORED_ALLOWED]
    assert loose == [], f"先頭 / で固定されていないパターン: {loose}"


@pytest.mark.parametrize("path", REQUIRED_FOR_BUILD)
def test_t403_vercelignore_keeps_what_the_build_needs(path: str) -> None:
    """T-403: ビルドに要るものを除外していない。"""
    hits = [p for p in patterns(VERCELIGNORE.read_text(encoding="utf-8")) if matches(p, path)]
    assert hits == [], f"{path} が {hits} に除外される"


@pytest.mark.parametrize("path", MUST_EXCLUDE)
def test_t404_vercelignore_excludes_raw_data_dependencies_and_secrets(path: str) -> None:
    """T-404: 生データ(再配布不可を含む)・依存・生成物・秘密情報を送らない。"""
    hits = [p for p in patterns(VERCELIGNORE.read_text(encoding="utf-8")) if matches(p, path)]
    assert hits, f"{path} が除外されていない"

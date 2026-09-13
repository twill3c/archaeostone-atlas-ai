"""出荷器・取得器が「書き出した先」を表示するための経路(T-341〜T-347)。

実測(2026-09-14): 出荷器の終わりの print で ``args.out.relative_to(REPO_ROOT)`` と
書いていたため、``--out`` にリポジトリ外の経路を渡すと、**ファイルを書き終えた後で**
``ValueError`` が出て異常終了した。ファイルはできているのに終了コードは失敗になり、
成否の読み方が反転する。同じ書き方が 8 箇所にあったので、ここへ一つにまとめる。
"""

from __future__ import annotations

import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


def display_path(path: pathlib.Path | str) -> str:
    """表示用の経路。リポジトリの中なら相対、外ならそのままの絶対経路。**例外を投げない。**

    外側の経路は ``resolve()`` しない —— Windows の 8.3 形式の短い名前
    (``TETRUR~1`` など)が展開され、渡した経路と違う文字列を見せてしまう。
    """
    candidate = pathlib.Path(path)
    for form in (candidate.absolute(), candidate.resolve()):
        try:
            return str(form.relative_to(REPO_ROOT))
        except ValueError:
            continue
    return str(candidate.absolute())

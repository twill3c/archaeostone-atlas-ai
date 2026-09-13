"""糸魚川市ヒスイ出土情報集成表を手元に取得する(SPEC §2.1 / §6.2)。

**この表は再配布できない。** 同市の権利表示は「私的利用」または「引用」を除き
無断での転載・複製・改変を禁じている。だから取得器だけをリポジトリに置き、
落としたファイルは ``.gitignore`` で除外してある。

    python -m pipeline.acquisition.itoigawa

取得した内容の要約(集計統計)だけが ``public/data/jade_aggregate.json`` へ出る。
個票フィールド(遺跡名・所在市町村・文献・所有者)は出荷形に書き出さない。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import time
import urllib.error
import urllib.request
from pipeline.paths import display_path

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
OUT_DIR = REPO_ROOT / "data" / "raw" / "itoigawa"

LANDING_PAGE = "https://www.city.itoigawa.lg.jp/site/koukokan/2181.html"
RIGHTS_PAGE = "https://www.city.itoigawa.lg.jp/site/userguide/8571.html"

DOWNLOADS = {
    "jade_occurrences.xls": "https://www.city.itoigawa.lg.jp/uploaded/attachment/5566.xls",
    "jade_occurrences.pdf": "https://www.city.itoigawa.lg.jp/uploaded/attachment/5567.pdf",
}

USER_AGENT = "Mozilla/5.0 (compatible; ArchaeoStoneAtlas/0.1; research)"

#: 実測 2026-09-08 に落としたファイルの sha256。中身が変わったら気づけるように残す。
#: **一致を要求はしない** —— 源が更新されることは正常なので、違いを報告するだけにする。
OBSERVED_SHA256 = {
    "jade_occurrences.xls": (
        "77a48b13077637f8e16c4e6e5b7394434fce053d251bb329d36aa7ad3eec1884"
    ),
}

NOTICE = """
このデータは糸魚川市の著作物であり、再配布できません。

  権利表示: {rights}
  「私的利用」または「引用」など著作権法上認められた行為として適切な方法で
  利用する場合を除き、無断で転載、複製、改変など利用をすることはできません。

本アトラスは取得器・解析器・検査だけを配り、公開するのは集計統計のみです。
落としたファイルは .gitignore で除外されており、コミットされません。
""".strip()


def fetch(
    name: str,
    url: str,
    *,
    out_dir: pathlib.Path,
    max_attempts: int = 4,
    backoff_seconds: float = 3.0,
    sleep=time.sleep,
) -> pathlib.Path:
    """1 ファイル落とす。通信の失敗だけを再試行する(HC-221)。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / name

    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last: Exception | None = None
    for attempt in range(max_attempts):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                target.write_bytes(response.read())
            return target
        except urllib.error.HTTPError as exc:
            # 4xx は URL の問題なので再試行しない。
            if exc.code < 500:
                raise
            last = exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = exc
        if attempt < max_attempts - 1:
            sleep(backoff_seconds * (attempt + 1))
    raise RuntimeError(f"{name} を {max_attempts} 回試みて取得できなかった: {last}") from last


def main() -> None:
    parser = argparse.ArgumentParser(
        description="糸魚川市ヒスイ集成表を手元に取得する(再配布不可)"
    )
    parser.add_argument("--out", type=pathlib.Path, default=OUT_DIR)
    args = parser.parse_args()

    print(NOTICE.format(rights=RIGHTS_PAGE))
    print()

    manifest = {
        "source_id": "SRC-ITOIGAWA",
        "landing_page": LANDING_PAGE,
        "rights_page": RIGHTS_PAGE,
        "redistribution": False,
        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "files": [],
    }

    for name, url in DOWNLOADS.items():
        path = fetch(name, url, out_dir=args.out)
        payload = path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        expected = OBSERVED_SHA256.get(name)
        note = None
        if expected and digest != expected:
            note = (
                f"2026-09-08 に観測した sha256 と違う(観測 {expected[:12]}… / "
                f"今回 {digest[:12]}…)。源が更新された可能性がある —— "
                "SPEC §2.7 の実測値を測り直すこと"
            )
        manifest["files"].append(
            {"name": name, "url": url, "bytes": len(payload), "sha256": digest, "note": note}
        )
        print(f"  {name}: {len(payload):,} バイト / sha256 {digest[:16]}…")
        if note:
            print(f"    ! {note}")

    manifest_path = args.out / "source_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\n{display_path(manifest_path)} を書いた")
    print("次: python -m pipeline.build_jade_aggregate")


if __name__ == "__main__":
    main()

"""全国遺跡報告総覧 OAI-PMH の収穫(SPEC §3.3 / F-04)。

実測(2026-09-08)で分かっている癖を、最初から織り込んである:

* ``completeListSize`` は **312,794**。1 ページ 106 件前後なので約 2,950 ページ
* **1 応答に三形が混在する。** ``oai_dc`` / ``junii2`` / **メタデータ無し**
  (``Identify`` の ``deletedRecord: transient`` に対応。実測 10.3%)。
  一つの形だけを見る解析器は、残りを黙って落とす
* ``setSpec`` は全国地方公共団体コード(2 桁 = 都道府県 / 5 桁 = 市区町村)
* ``dc:identifier`` は**無型で多値**。URL・DOI・NCID・叢書名・巻号・日付が同じ要素に入る

長い取得なので、(a) ページ単位でキャッシュし、(b) 間を空けた再試行を入れ、
(c) **「もう無い」は再試行しない**(HC-221 / HC-235)。

    python -m pipeline.acquisition.nabunken --out data/raw/nabunken
"""

from __future__ import annotations

import argparse
import json
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request

from lxml import etree

OAI_BASE = "https://sitereports.nabunken.go.jp/api/oai/request"
USER_AGENT = "Mozilla/5.0 (compatible; ArchaeoStoneAtlas/0.1; research)"
OAI_NS = {"o": "http://www.openarchives.org/OAI/2.0/"}

#: 取得の間隔。相手は公共の索引なので、速さより礼儀を採る。
POLITE_DELAY_SECONDS = 1.0


class HarvestStopped(Exception):
    """resumptionToken が尽きた(= 正常終了)。"""


def _request(params: dict[str, str], *, timeout: float = 120.0) -> bytes:
    url = f"{OAI_BASE}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def fetch_page(
    params: dict[str, str],
    *,
    max_attempts: int = 5,
    backoff_seconds: float = 5.0,
    sleep=time.sleep,
) -> bytes:
    """1 ページ取る。通信の失敗だけを再試行する。

    OAI のプロトコル上のエラー(badResumptionToken 等)は本文が返ってくるので、
    ここでは再試行しない —— 呼ぶ側が中身を見て判断する。
    """
    last: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return _request(params)
        except urllib.error.HTTPError as exc:
            # 4xx は引数の問題なので再試行しない。5xx は相手側の一時障害とみなす。
            if exc.code < 500:
                raise
            last = exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = exc
        if attempt < max_attempts - 1:
            sleep(backoff_seconds * (attempt + 1))
    raise RuntimeError(f"{max_attempts} 回試みて取得できなかった: {last}") from last


def resumption_token(page: bytes) -> str | None:
    """次ページの合図。無ければ None(= 打ち切りではなく完了)。"""
    root = etree.fromstring(page)
    node = root.find(".//o:resumptionToken", OAI_NS)
    if node is None or not (node.text or "").strip():
        return None
    return node.text.strip()


def complete_list_size(page: bytes) -> int | None:
    root = etree.fromstring(page)
    node = root.find(".//o:resumptionToken", OAI_NS)
    if node is None:
        return None
    value = node.get("completeListSize")
    return int(value) if value else None


def oai_errors(page: bytes) -> list[tuple[str, str]]:
    """OAI のプロトコルエラー。空なら正常。"""
    root = etree.fromstring(page)
    return [
        (node.get("code", "?"), (node.text or "").strip())
        for node in root.findall("o:error", OAI_NS)
    ]


def harvest(
    out_dir: pathlib.Path,
    *,
    metadata_prefix: str = "oai_dc",
    max_pages: int | None = None,
    sleep=time.sleep,
) -> dict:
    """全ページを取り、ページごとに XML を落とす。

    既に落ちているページは読み飛ばす(``--out`` を同じにすれば続きから進む)。
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    state_path = out_dir / "harvest_state.json"
    state: dict = (
        json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    )

    token: str | None = state.get("next_token")
    page_index: int = state.get("pages_written", 0)
    total: int | None = state.get("complete_list_size")
    started_fresh = token is None and page_index == 0

    # ループ内で `state` を作り直すので、開始時のページ数はここで退避しておく。
    # `state["pages_written"]` と比べると差が常に 0 になり、上限が黙って外れる。
    pages_at_start = page_index

    while True:
        if max_pages is not None and page_index - pages_at_start >= max_pages:
            break

        params = (
            {"verb": "ListRecords", "metadataPrefix": metadata_prefix}
            if token is None and started_fresh and page_index == 0
            else {"verb": "ListRecords", "resumptionToken": token or ""}
        )
        if params.get("resumptionToken") == "" and page_index > 0:
            break  # token が無いのに続きから始めようとした → 完了扱い

        page = fetch_page(params, sleep=sleep)

        errors = oai_errors(page)
        if errors:
            codes = [c for c, _ in errors]
            if "noRecordsMatch" in codes:
                break
            raise RuntimeError(f"OAI エラー: {errors}")

        path = out_dir / f"page_{page_index:05d}.xml"
        path.write_bytes(page)
        if total is None:
            total = complete_list_size(page)
        page_index += 1

        token = resumption_token(page)
        state = {
            "next_token": token,
            "pages_written": page_index,
            "complete_list_size": total,
            "metadata_prefix": metadata_prefix,
            "oai_base_url": OAI_BASE,
        }
        state_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

        if page_index % 25 == 0:
            print(f"  {page_index} ページ取得(全 {total} 件のうち)", flush=True)

        if token is None:
            break
        sleep(POLITE_DELAY_SECONDS)

    return state


def main() -> None:
    parser = argparse.ArgumentParser(description="全国遺跡報告総覧 OAI-PMH を収穫する")
    parser.add_argument("--out", default="data/raw/nabunken", type=pathlib.Path)
    parser.add_argument("--max-pages", type=int, default=None)
    args = parser.parse_args()

    state = harvest(args.out, max_pages=args.max_pages)
    print(
        f"収穫 {state['pages_written']} ページ / 全 {state.get('complete_list_size')} 件"
        f" / 次の token: {'(完了)' if state['next_token'] is None else '継続あり'}"
    )


if __name__ == "__main__":
    main()

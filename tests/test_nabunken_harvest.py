"""OAI 収穫器の検査(T-040〜 / G-08)。

ネットワークには触らない。実際の応答から切り出したページを使う。

眼目は二つ。
1. **礼儀の安全弁が実際に効くこと。** `--max-pages` が効かなくても、
   正常時とまったく同じ出力(ページが増える)になる。実行してみるまで
   気づけない型なので、テストで固定する
2. **三形のレコードを取り違えずに数えること。** 一つの形だけを見る解析器は
   残りを黙って落とす
"""

import json
import pathlib

import pytest

from pipeline.acquisition.nabunken import (
    complete_list_size,
    harvest,
    oai_errors,
    resumption_token,
)

FIXTURE_DIR = pathlib.Path(__file__).parent / "fixtures" / "oai"


@pytest.fixture(scope="module")
def real_page() -> bytes:
    """実際の応答 1 ページ(2026-09-08 取得)。"""
    return (FIXTURE_DIR / "page_real.xml").read_bytes()


def test_fixture_is_a_real_multi_shape_page(real_page: bytes) -> None:
    """前提の固定: このページが本当に三形を含んでいること。

    含んでいなければ、以下の「取り違えない」検査はすべて空振りする(HC-070)。
    """
    text = real_page.decode("utf-8")
    assert "oai_dc:dc" in text, "oai_dc のレコードが無い"
    assert "junii2" in text, "junii2 のレコードが無い"
    assert text.count("<record>") > 50, "レコードが少なすぎる"


def test_t040_complete_list_size_is_read(real_page: bytes) -> None:
    """T-040: 全件数を読める。実測 2026-09-08 で 312,794 件。"""
    size = complete_list_size(real_page)
    assert size is not None
    # 索引は増えるので下限で押さえる。定数一致にすると source が動くたび壊れる。
    assert size >= 312_794


def test_t041_resumption_token_is_read(real_page: bytes) -> None:
    """T-041: 次ページの合図を読める。"""
    assert resumption_token(real_page)


def test_t042_no_errors_on_a_good_page(real_page: bytes) -> None:
    """T-042(陰性対照): 正常なページにプロトコルエラーは無い。"""
    assert oai_errors(real_page) == []


def test_t043_positive_control_protocol_error_is_detected() -> None:
    """T-043(陽性対照): OAI のエラー応答を検出する。

    エラーは HTTP 200 で本文に入って返るので、状態コードでは分からない。
    """
    bad = (FIXTURE_DIR / "page_error.xml").read_bytes()
    errors = oai_errors(bad)
    assert [code for code, _ in errors] == ["badResumptionToken"]


def test_t044_absent_resumption_token_means_done() -> None:
    """T-044: token が無いのは「打ち切り」ではなく「完了」。

    ここを取り違えると、最後のページで失敗したように見える。
    """
    last = (FIXTURE_DIR / "page_last.xml").read_bytes()
    assert resumption_token(last) is None


def test_t045_max_pages_actually_stops(tmp_path: pathlib.Path, monkeypatch) -> None:
    """T-045: `max_pages` が指定した数で本当に止まる。

    相手は公共の索引なので、上限が効かないことはバグでは済まない。
    しかも**上限が外れても正常時と同じ出力になる**ので、実行しても気づけない。
    """
    page = (FIXTURE_DIR / "page_real.xml").read_bytes()
    calls: list[dict] = []

    def fake_fetch(params, **_kwargs):
        calls.append(dict(params))
        return page

    monkeypatch.setattr("pipeline.acquisition.nabunken.fetch_page", fake_fetch)

    state = harvest(tmp_path, max_pages=3, sleep=lambda _s: None)

    assert len(calls) == 3, f"3 ページで止まるはずが {len(calls)} 回叩いた"
    assert state["pages_written"] == 3
    assert sorted(p.name for p in tmp_path.glob("page_*.xml")) == [
        "page_00000.xml",
        "page_00001.xml",
        "page_00002.xml",
    ]


def test_t046_resume_continues_and_respects_the_cap(
    tmp_path: pathlib.Path, monkeypatch
) -> None:
    """T-046: 続きから再開しても、上限はその回の取得数に掛かる。

    退避を忘れると、再開時に「既に書いた数」と比べてしまって上限が外れる ——
    これが実際に踏んだ欠陥である。
    """
    page = (FIXTURE_DIR / "page_real.xml").read_bytes()
    calls: list[dict] = []
    monkeypatch.setattr(
        "pipeline.acquisition.nabunken.fetch_page",
        lambda params, **_k: (calls.append(dict(params)), page)[1],
    )

    harvest(tmp_path, max_pages=2, sleep=lambda _s: None)
    assert len(calls) == 2

    calls.clear()
    state = harvest(tmp_path, max_pages=2, sleep=lambda _s: None)
    assert len(calls) == 2, f"再開後も 2 ページで止まるはずが {len(calls)} 回叩いた"
    assert state["pages_written"] == 4

    # 再開時は resumptionToken を使っており、最初から取り直していないこと。
    assert all("resumptionToken" in c for c in calls)


def test_t047_state_file_records_where_to_continue(
    tmp_path: pathlib.Path, monkeypatch
) -> None:
    """T-047: 途中で落ちても続きから進めるだけの情報が残っていること。"""
    page = (FIXTURE_DIR / "page_real.xml").read_bytes()
    monkeypatch.setattr("pipeline.acquisition.nabunken.fetch_page", lambda *_a, **_k: page)

    harvest(tmp_path, max_pages=1, sleep=lambda _s: None)
    state = json.loads((tmp_path / "harvest_state.json").read_text(encoding="utf-8"))

    for key in ("next_token", "pages_written", "complete_list_size", "oai_base_url"):
        assert key in state, f"{key} が状態ファイルに無い"
    assert state["next_token"], "次の token が残っていない"

"""GSJ シームレス地質図 地点 API の応答分類(T-006〜T-012 / G-04)。

固定した 4 地点の応答は 2026-09-08 に実際に叩いて記録したものである
(`tests/fixtures/gsj_responses.json`)。ネットワークには触らない。

この検査の眼目は **「無い」が三通りの形で返ること**(SPEC §2.5 / HC-235)。
うち一つは HTTP 500 で、階級だけで再試行を決める実装は被覆外の地点ごとに
最大回数まで待つ。そこを陽性対照(T-010)で押さえる。
"""

import json
import pathlib

import pytest

from archaeostone.gsj import (
    GsjOutcome,
    classify_response,
    is_retryable,
)

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "gsj_responses.json"


@pytest.fixture(scope="module")
def observed() -> dict:
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


def test_fixture_actually_holds_the_four_shapes(observed: dict) -> None:
    """前提の固定(HC-070/HC-079)。

    この対照が意味を持つのは、フィクスチャが本当に 4 通りの応答を
    含んでいるときだけである。含んでいなければ以後の検査は空振りする。
    """
    assert set(observed) == {"land", "lake_suwa", "lake_biwa", "offshore", "thailand", "swapped"}
    assert observed["land"]["http_status"] == 200
    assert observed["lake_suwa"]["http_status"] == 200
    for key in ("lake_biwa", "offshore", "thailand"):
        assert observed[key]["http_status"] == 500
        assert observed[key]["body"] == ""


def test_t006_land_point_is_ok(observed: dict) -> None:
    """T-006: 陸域の完全な応答。実測 2026-09-08 富士山 35.3606,138.7274。"""
    result = classify_response(**observed["land"])
    assert result.outcome is GsjOutcome.OK
    assert result.symbol == "H_vbs_al"
    assert result.lithology_ja == "玄武岩 溶岩・火砕岩"
    assert result.formation_age_ja == "新生代 第四紀 完新世"


def test_t007_lake_suwa_is_no_polygon(observed: dict) -> None:
    """T-007: 図郭内だがポリゴンが無い。実測 2026-09-08 諏訪湖 36.0450,138.0830。"""
    result = classify_response(**observed["lake_suwa"])
    assert result.outcome is GsjOutcome.NO_POLYGON
    assert result.symbol is None


@pytest.mark.parametrize("key", ["lake_biwa", "offshore", "thailand"])
def test_t008_http_500_is_no_coverage(observed: dict, key: str) -> None:
    """T-008: HTTP 500 + 本文 0 バイトは「被覆外」という答えである。

    実測 2026-09-08: 琵琶湖 35.25,136.08 / 太平洋沖 34.5,140.0 / タイ 12.0,100.0。
    """
    result = classify_response(**observed[key])
    assert result.outcome is GsjOutcome.NO_COVERAGE
    assert result.symbol is None


@pytest.mark.parametrize(
    "outcome,retryable",
    [
        (GsjOutcome.OK, False),
        (GsjOutcome.NO_POLYGON, False),
        (GsjOutcome.NO_COVERAGE, False),
        (GsjOutcome.PARAMETER_ERROR, False),
        (GsjOutcome.TRANSPORT_ERROR, True),
    ],
)
def test_t009_only_transport_failures_are_retryable(
    outcome: GsjOutcome, retryable: bool
) -> None:
    """T-009: 再試行するのは接続断・タイムアウトだけ。

    `NO_COVERAGE` は HTTP 500 で来るが**答え**なので再試行しない(HC-235)。
    """
    assert is_retryable(outcome) is retryable


def test_t010_positive_control_status_class_policy_would_fail(observed: dict) -> None:
    """T-010(陽性対照): 状態コードの階級で再試行を決める実装は落ちる。

    「5xx なら再試行」という広く使われる方針を、そのままここへ当ててみる。
    被覆外の 3 地点すべてを再試行対象にしてしまうことを示す ——
    つまり本検査は、方針の違いを実際に見分けられている。
    """

    def retry_by_status_class(http_status: int | None) -> bool:
        return http_status is not None and http_status >= 500

    naive = [k for k in ("lake_biwa", "offshore", "thailand")
             if retry_by_status_class(observed[k]["http_status"])]
    assert naive == ["lake_biwa", "offshore", "thailand"], "陽性対照が発火していない"

    ours = [k for k in ("lake_biwa", "offshore", "thailand")
            if is_retryable(classify_response(**observed[k]).outcome)]
    assert ours == []


def test_t011_title_is_not_used_for_parsing(observed: dict) -> None:
    """T-011: `title` を解析に使わない。

    `title` は `formationAge_ja + "," + lithology_ja` の連結なので、
    両方 null のとき `","` という**文字列**になる。真偽値として扱うと真になる。
    """
    body = json.loads(observed["lake_suwa"]["body"])
    assert body["title"] == ",", "前提が変わった。フィクスチャを取り直すこと"
    assert bool(body["title"]) is True, "空文字ではないので truthy 判定では通ってしまう"

    result = classify_response(**observed["lake_suwa"])
    assert result.outcome is GsjOutcome.NO_POLYGON
    # 分類は symbol を見て決まっており、title には触れていない。
    assert result.title_raw == ","


def test_t012_swapped_coordinates_are_detected(observed: dict) -> None:
    """T-012: 座標順の取り違えは `code: 102` として検出できる。

    実測 2026-09-08: `point=138.11,36.05`(lng,lat の順)。
    黙って別の地点の地質を返すのではなく、エラーになることを確かめる。
    """
    result = classify_response(**observed["swapped"])
    assert result.outcome is GsjOutcome.PARAMETER_ERROR
    assert result.symbol is None

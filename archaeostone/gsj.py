"""GSJ シームレス地質図 V2 の地点問い合わせ(SPEC §2.5・§3.1 / G-04)。

この API は「地質が無い」を**三通りの形**で返す(2026-09-08 実測):

===================  ==========================================  ================
地点                 応答                                        意味
===================  ==========================================  ================
陸域のポリゴン上     200 + 全項目                                地質あり
諏訪湖上             200 + ``symbol: null`` / ``title: ","``     図郭内・ポリゴン無し
琵琶湖上・外洋・国外 **HTTP 500 + 本文 0 バイト**                被覆外
===================  ==========================================  ================

したがって **状態コードの階級で再試行を決めてはならない**。5xx は再試行の階級として
広く実装されているが、ここでの 500 は障害ではなく「被覆外」という答えである。
数千地点に掛ければ、正常に動いていても終わらない(HC-235)。

``title`` は ``formationAge_ja + "," + lithology_ja`` の連結にすぎず、両方 null の
とき文字列 ``","`` になる。**空文字ではないので真偽判定では通ってしまう**。解析に使わない。
"""

from __future__ import annotations

import dataclasses
import enum
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

API_BASE = "https://gbank.gsj.jp/seamless/v2/api/1.3.1/legend.json"
USER_AGENT = "Mozilla/5.0 (compatible; ArchaeoStoneAtlas/0.1; research)"


class GsjOutcome(enum.Enum):
    """地点問い合わせの結末。"""

    OK = "ok"
    """地質ポリゴンがあった。"""

    NO_POLYGON = "no_polygon"
    """図郭内だがポリゴンが無い(内水面など)。**答えであって障害ではない。**"""

    NO_COVERAGE = "no_coverage"
    """被覆外。HTTP 500 で来る。**答えであって障害ではない。**"""

    PARAMETER_ERROR = "parameter_error"
    """引数が不正(座標順の取り違えなど)。直さないかぎり再試行しても同じ。"""

    TRANSPORT_ERROR = "transport_error"
    """接続断・タイムアウト。**これだけが再試行に値する。**"""


@dataclasses.dataclass(frozen=True)
class GsjResult:
    outcome: GsjOutcome
    symbol: str | None = None
    formation_age_ja: str | None = None
    formation_age_en: str | None = None
    group_ja: str | None = None
    group_en: str | None = None
    lithology_ja: str | None = None
    lithology_en: str | None = None
    title_raw: str | None = None
    """API が返した ``title`` をそのまま持つ。**解析には使わない**(表示・監査用)。"""

    error_code: str | None = None

    def as_record(self) -> dict[str, Any]:
        """出荷レコードへ載せる形。"""
        return {
            "geology_outcome": self.outcome.value,
            "geology_symbol": self.symbol,
            "formation_age_ja": self.formation_age_ja,
            "formation_age_en": self.formation_age_en,
            "geology_group_ja": self.group_ja,
            "geology_group_en": self.group_en,
            "lithology_ja": self.lithology_ja,
            "lithology_en": self.lithology_en,
        }


def is_retryable(outcome: GsjOutcome) -> bool:
    """再試行してよいか。

    「無い」は再試行しない —— 障害と区別できないと、存在しないものを待ち続ける
    (HC-221 / HC-235)。
    """
    return outcome is GsjOutcome.TRANSPORT_ERROR


def classify_response(
    http_status: int | None,
    body: str,
    **_ignored: Any,
) -> GsjResult:
    """生の応答を結末へ分類する。ネットワークには触らない(テスト可能な純関数)。

    ``http_status`` が None のときは transport 層で失敗したことを表す。
    """
    if http_status is None:
        return GsjResult(GsjOutcome.TRANSPORT_ERROR)

    # 被覆外。本文が空の 500 がその形である(2026-09-08 実測)。
    if http_status >= 500:
        return GsjResult(GsjOutcome.NO_COVERAGE)

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        # 200 でも壊れた本文なら、黙って通さず transport の失敗として扱う。
        return GsjResult(GsjOutcome.TRANSPORT_ERROR)

    if not isinstance(payload, dict):
        return GsjResult(GsjOutcome.TRANSPORT_ERROR)

    if "code" in payload:
        return GsjResult(GsjOutcome.PARAMETER_ERROR, error_code=str(payload["code"]))

    if http_status >= 400:
        return GsjResult(GsjOutcome.PARAMETER_ERROR)

    title_raw = payload.get("title")
    symbol = payload.get("symbol")

    # 分類は symbol の有無だけで決める。title は連結文字列なので使わない(T-011)。
    if symbol is None:
        return GsjResult(GsjOutcome.NO_POLYGON, title_raw=title_raw)

    return GsjResult(
        GsjOutcome.OK,
        symbol=symbol,
        formation_age_ja=payload.get("formationAge_ja"),
        formation_age_en=payload.get("formationAge_en"),
        group_ja=payload.get("group_ja"),
        group_en=payload.get("group_en"),
        lithology_ja=payload.get("lithology_ja"),
        lithology_en=payload.get("lithology_en"),
        title_raw=title_raw,
    )


def fetch_point(
    latitude: float,
    longitude: float,
    *,
    max_attempts: int = 4,
    backoff_seconds: float = 2.0,
    timeout: float = 60.0,
    sleep=time.sleep,
) -> GsjResult:
    """1 地点の地質を引く。

    座標順は ``point=lat,lng``。逆順は ``code: 102`` のパラメータエラーになるので、
    黙って別地点の地質が返ることはない(T-012)。

    再試行するのは transport の失敗だけである。``NO_COVERAGE`` / ``NO_POLYGON`` は
    答えなので、そこで確定させて返す。
    """
    url = f"{API_BASE}?{urllib.parse.urlencode({'point': f'{latitude},{longitude}'})}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    result = GsjResult(GsjOutcome.TRANSPORT_ERROR)
    for attempt in range(max_attempts):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                result = classify_response(response.status, response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            result = classify_response(exc.code, exc.read().decode("utf-8", "replace"))
        except (urllib.error.URLError, TimeoutError, OSError):
            result = GsjResult(GsjOutcome.TRANSPORT_ERROR)

        if not is_retryable(result.outcome):
            return result
        if attempt < max_attempts - 1:
            sleep(backoff_seconds * (attempt + 1))

    return result

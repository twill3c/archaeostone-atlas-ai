"""黒曜石原産地の座標解決(SPEC §4.1・§4.2 / F-01 / G-03)。

**上位 1 件を正解にしない。** 国土地理院の地名検索は候補を順位つきで返すが、
順位は地名の一致度であって「探しているものか」ではない。実測(2026-09-08):

* ``和田峠`` は 69 件を返し、上位 3 件は青森県七戸町和田・山形県南陽市和田・
  福島県会津若松市和田。長野県の和田峠は **66 番目**。同名の峠が全国に 5 か所ある
* ``柏峠`` は和歌山県にもある
* ``蓼科冷山`` は 0 件。局所名 ``冷山`` でしか引けない

だから選択は二条件の**両方**で行う ——(a) 表示名に必ず含まれる文字列、
(b) 逆ジオコードした都道府県コード。どちらも満たす候補が無ければ、
**推測で埋めずに needs_review で返す**。

外部への問い合わせは Python 内で完結させる。Git Bash 経由の ``curl`` に
日本語を渡すと CP932 のバイトが送られ、実在する地名でも空が返る(HC-236)。
"""

from __future__ import annotations

import dataclasses
import enum
import functools
import json
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "source_areas.yaml"

GEOCODER_URL = "https://msearch.gsi.go.jp/address-search/AddressSearch"
REVERSE_GEOCODER_URL = (
    "https://mreversegeocoder.gsi.go.jp/reverse-geocoder/LonLatToAddress"
)
USER_AGENT = "Mozilla/5.0 (compatible; ArchaeoStoneAtlas/0.1; research)"
POLITE_DELAY_SECONDS = 0.5


class ResolutionRule(enum.Enum):
    """どの規則で候補を選んだか。

    表示用の文(``Resolution.rule``)ではなく**こちら**を検査の根拠にする。
    文は言い換えられるが、種別は言い換えられない(HC-068)。
    """

    CONTAINS_AND_PREFECTURE = "contains_and_prefecture"
    """表示名に部分一致し、かつ逆ジオコードした県コードが一致する。既定。"""

    EXACT_AND_UNIQUE = "exact_and_unique"
    """表示名が完全一致し、その一致が候補中ちょうど 1 件である。

    名称そのものが対象を一意に指す場合にだけ使う。県で確認できない地物
    (海岸の露頭など)のための経路であり、一意性が緩みを止めている。
    """


class ResolutionOutcome(enum.Enum):
    RESOLVED = "resolved"
    """二条件を満たす候補が見つかった。"""

    NO_CANDIDATES = "no_candidates"
    """地名検索が 0 件を返した。**答えであって障害ではない。**"""

    NO_MATCH = "no_match"
    """候補はあったが、名前と県の両方を満たすものが無かった。"""


@dataclasses.dataclass(frozen=True)
class Resolution:
    source_area_id: str
    outcome: ResolutionOutcome
    query: str
    candidate_count: int
    candidate_index: int | None = None
    candidate_title: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    pref_code: str | None = None
    rule: str | None = None
    rule_kind: ResolutionRule = ResolutionRule.CONTAINS_AND_PREFECTURE

    @property
    def evidence_status(self) -> str:
        return "curated" if self.outcome is ResolutionOutcome.RESOLVED else "needs_review"

    def as_provenance(self) -> dict[str, Any]:
        """出荷レコードの ``coordinate_provenance``。

        「どの問い合わせの、何番目の候補を、どの規則で選んだか」が全部残る。
        後から見て、誰かの記憶か観測かが区別できるようにする。
        """
        return {
            "method": "gsi_address_search",
            "query": self.query,
            "candidate_count": self.candidate_count,
            "candidate_index": self.candidate_index,
            "candidate_title": self.candidate_title,
            "rule": self.rule,
            "rule_kind": self.rule_kind.value,
            "outcome": self.outcome.value,
        }


@functools.cache
def load_source_area_config(path: pathlib.Path | None = None) -> dict[str, Any]:
    doc = yaml.safe_load((path or CONFIG_PATH).read_text(encoding="utf-8"))
    for key in ("citations", "source_areas"):
        if key not in doc:
            raise ValueError(f"source_areas.yaml に {key} が無い")
    return doc


def resolve_source_area(
    source_area_id: str,
    entry: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> Resolution:
    """候補列から 1 件を選ぶ。純関数(ネットワークに触らない)。

    ``candidates`` の各要素は ``title`` / ``lat`` / ``lon`` を持ち、
    名前の制約を満たすものには ``pref_code`` が付いている想定。
    """
    query = entry["query"]
    needle = entry["title_must_contain"]
    want_pref = entry["expect_pref_code"]
    exact_mode = bool(entry.get("title_is_exact"))

    if not candidates:
        rule = f"title に {needle!r} を含み、逆ジオコードした県コードが {want_pref} であること"
        return Resolution(
            source_area_id, ResolutionOutcome.NO_CANDIDATES, query, 0, rule=rule
        )

    if exact_mode:
        # 名称そのものが対象を一意に指す場合(「姫島の黒曜石産地」など)。
        #
        # 県コードの照合は**同名別地を切り分けるための**規則であって、
        # 切り分ける必要が無いところでは要求しない —— 実測では、海岸の露頭は
        # 逆ジオコーダが「陸上でない」を返すので、県では確認できない。
        #
        # 代わりに**一意性**を要求する。これは抜け道にならない: 「和田峠」は
        # 完全一致が 5 件あるので一意性を満たさず、この経路には入れない。
        rule = f"title が {needle!r} と完全一致し、その一致が候補中ちょうど 1 件であること"
        matches = [
            (index, candidate)
            for index, candidate in enumerate(candidates)
            if (candidate.get("title") or "") == needle
        ]
        if len(matches) != 1:
            return Resolution(
                source_area_id,
                ResolutionOutcome.NO_MATCH,
                query,
                len(candidates),
                rule=rule,
                rule_kind=ResolutionRule.EXACT_AND_UNIQUE,
            )
        index, candidate = matches[0]
        return Resolution(
            source_area_id=source_area_id,
            outcome=ResolutionOutcome.RESOLVED,
            query=query,
            candidate_count=len(candidates),
            candidate_index=index,
            candidate_title=candidate["title"],
            latitude=float(candidate["lat"]),
            longitude=float(candidate["lon"]),
            # 県は確認できていない。分かっていないことを「分かった」と書かない。
            pref_code=candidate.get("pref_code"),
            rule=rule,
            rule_kind=ResolutionRule.EXACT_AND_UNIQUE,
        )

    rule = f"title に {needle!r} を含み、逆ジオコードした県コードが {want_pref} であること"
    for index, candidate in enumerate(candidates):
        title = candidate.get("title") or ""
        if needle not in title:
            continue
        if candidate.get("pref_code") != want_pref:
            continue
        return Resolution(
            source_area_id=source_area_id,
            outcome=ResolutionOutcome.RESOLVED,
            query=query,
            candidate_count=len(candidates),
            candidate_index=index,
            candidate_title=title,
            latitude=float(candidate["lat"]),
            longitude=float(candidate["lon"]),
            pref_code=want_pref,
            rule=rule,
        )

    return Resolution(
        source_area_id,
        ResolutionOutcome.NO_MATCH,
        query,
        len(candidates),
        rule=rule,
    )


# ── 外部への問い合わせ ──────────────────────────────────


def _get_json(url: str, *, timeout: float = 60.0) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def search_place(name: str) -> list[dict[str, Any]]:
    """地名検索。候補を**全部**返す(選ぶのは呼ぶ側)。

    不明な語には 200 + ``[]`` が返る。空は「無い」という答えなので再試行しない。
    """
    url = f"{GEOCODER_URL}?{urllib.parse.urlencode({'q': name})}"
    features = _get_json(url)
    rows = []
    for feature in features:
        lon, lat = feature["geometry"]["coordinates"]
        rows.append(
            {
                "title": feature["properties"].get("title"),
                "lat": lat,
                "lon": lon,
                "dataSource": feature["properties"].get("dataSource"),
            }
        )
    return rows


def reverse_prefecture_code(latitude: float, longitude: float) -> str | None:
    """座標から都道府県コード(2 桁)。陸でなければ None。

    海上・国外では ``{}`` が返る。これは**エラーではなく「陸上でない」という答え**
    なので再試行しない(HC-221)。
    """
    url = f"{REVERSE_GEOCODER_URL}?lat={latitude}&lon={longitude}"
    payload = _get_json(url)
    results = payload.get("results")
    if not results:
        return None
    return str(results["muniCd"]).zfill(5)[:2]


def resolve_all(
    *,
    sleep=time.sleep,
    search=search_place,
    reverse=reverse_prefecture_code,
) -> list[tuple[str, dict[str, Any], Resolution]]:
    """辞書の全エントリを解決する。

    逆ジオコードは**名前の制約を満たす候補にだけ**掛ける。全候補に掛けると
    「白滝」だけで 117 回の問い合わせになり、相手に無用な負荷をかける。
    """
    config = load_source_area_config()
    out: list[tuple[str, dict[str, Any], Resolution]] = []

    cache: dict[str, list[dict[str, Any]]] = {}
    for source_area_id, entry in config["source_areas"].items():
        query = entry["query"]
        if query not in cache:
            cache[query] = search(query)
            sleep(POLITE_DELAY_SECONDS)
        candidates = [dict(c) for c in cache[query]]

        needle = entry["title_must_contain"]
        for candidate in candidates:
            if needle in (candidate.get("title") or "") and "pref_code" not in candidate:
                candidate["pref_code"] = reverse(candidate["lat"], candidate["lon"])
                sleep(POLITE_DELAY_SECONDS)

        out.append((source_area_id, entry, resolve_source_area(source_area_id, entry, candidates)))
    return out

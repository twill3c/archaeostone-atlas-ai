"""原産地のある市町村の報告書を数える(F-07)。

Stone Passport に「当該市町村の文献」を出すための集計。**これは石材の出土を意味しない** ——
全国遺跡報告総覧の索引で、その市町村のコードを ``setSpec`` に持つ報告書を数えるだけである。
題名に黒曜石の語を含むものは別に数え、題名とリンクを添える(索引メタデータは自由利用)。

純関数だけを置く。収穫物の読み出しとネットワークは ``pipeline.build_area_documents`` が持つ。
"""

from __future__ import annotations

import dataclasses
from typing import Iterable, Mapping, Sequence

from archaeostone.oai import OaiRecord, RecordShape

#: 題名の例をいくつまで出荷形に載せるか。件数はこれを超えても数え続ける。
EXAMPLE_LIMIT = 12


@dataclasses.dataclass
class AreaTally:
    codes: tuple[str, ...]
    documents: int = 0
    """メタデータのある報告書の件数(取り下げられたレコードは数えない)。"""
    documents_by_code: dict[str, int] = dataclasses.field(default_factory=dict)
    """コードごとの件数。区と市の両方で持つレコードは両方に数える(合計は documents と一致しない)。"""
    obsidian_title_count: int = 0
    obsidian_titles: list[dict[str, str | None]] = dataclasses.field(default_factory=list)


def tally_area_documents(
    records: Iterable[OaiRecord],
    targets: Mapping[str, Sequence[str]],
    terms: Sequence[str],
    *,
    example_limit: int = EXAMPLE_LIMIT,
) -> dict[str, AreaTally]:
    """原産地 ID → その市町村のコード組 を受け、報告書を数える。

    * 一つのレコードは、区と市の両方のコードを持っていても**一原産地につき 1 回**だけ数える
    * メタデータの無いレコード(取り下げ)は数えない。題名が無いので中身を言えない
    """
    tallies = {
        area_id: AreaTally(
            codes=tuple(codes), documents_by_code={code: 0 for code in codes}
        )
        for area_id, codes in targets.items()
    }
    by_code: dict[str, list[str]] = {}
    for area_id, codes in targets.items():
        for code in codes:
            by_code.setdefault(code, []).append(area_id)

    for record in records:
        if record.shape is RecordShape.NO_METADATA:
            continue
        codes = set(record.municipality_codes) & by_code.keys()
        if not codes:
            continue
        areas = {area_id for code in codes for area_id in by_code[code]}
        mentions = any(term in record.title_blob for term in terms)
        for area_id in areas:
            tally = tallies[area_id]
            tally.documents += 1
            for code in codes & set(tally.codes):
                tally.documents_by_code[code] += 1
            if mentions:
                tally.obsidian_title_count += 1
                if len(tally.obsidian_titles) < example_limit:
                    tally.obsidian_titles.append(
                        {
                            "title": record.titles[0] if record.titles else "",
                            "url": record.landing_url,
                        }
                    )
    return tallies

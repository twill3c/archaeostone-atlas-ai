"""収穫した OAI レコードの解析(F-04)。

実測(2026-09-08)で分かっている癖を、取り違えないように書いてある。

* **1 応答に三形が混在する。** ``oai_dc`` / ``junii2`` / **メタデータ無し**。
  一つの形だけを見る解析器は残りを黙って落とす。だから
  :func:`parse_record` は形を**返り値で報告**し、呼ぶ側が数え分けられるようにする
* ``setSpec`` は全国地方公共団体コード。**2 桁 = 都道府県 / 5 桁 = 市区町村**。
  それ以外の桁(6 桁・7 桁・英字始まり)も実在するので、桁で分類して
  **知らない形を黙って捨てない**
* ``dc:identifier`` は**無型で多値**。URL・DOI・NCID・叢書名・巻号・日付が
  同じ要素に入る。「識別子」として 1 個目を採ると叢書名を掴むことがある
"""

from __future__ import annotations

import dataclasses
import enum
import re
from typing import Any

from lxml import etree

OAI_NS = "http://www.openarchives.org/OAI/2.0/"
DC_NS = "http://purl.org/dc/elements/1.1/"
DCTERMS_NS = "http://purl.org/dc/terms/"
JUNII2_NS = "http://irdb.nii.ac.jp/oai"

NS = {"o": OAI_NS, "dc": DC_NS, "dcterms": DCTERMS_NS, "j": JUNII2_NS}

_DOI = re.compile(r"^info:doi/(.+)$")
_NCID = re.compile(r"^[A-Z]{2}\d{6,}$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class RecordShape(enum.Enum):
    """レコードの形。**三つある。**"""

    OAI_DC = "oai_dc"
    JUNII2 = "junii2"
    NO_METADATA = "no_metadata"
    """メタデータ要素が無い。``Identify`` の ``deletedRecord: transient`` に対応。
    実測では約 10% がこれ。**障害ではなく「取り下げられた」という状態である。**"""


class SetSpecKind(enum.Enum):
    PREFECTURE = "prefecture"
    """2 桁の全国地方公共団体コード。"""

    MUNICIPALITY = "municipality"
    """5 桁の全国地方公共団体コード。"""

    OTHER_NUMERIC = "other_numeric"
    """6 桁・7 桁など。意味を決めつけずに分けて数える。"""

    NON_NUMERIC = "non_numeric"
    """``J84604`` のような英字始まり。"""


def classify_set_spec(value: str) -> SetSpecKind:
    if not value.isdigit():
        return SetSpecKind.NON_NUMERIC
    if len(value) == 2:
        return SetSpecKind.PREFECTURE
    if len(value) == 5:
        return SetSpecKind.MUNICIPALITY
    return SetSpecKind.OTHER_NUMERIC


@dataclasses.dataclass(frozen=True)
class OaiRecord:
    identifier: str
    datestamp: str | None
    shape: RecordShape
    set_specs: tuple[str, ...]
    titles: tuple[str, ...]
    publishers: tuple[str, ...]
    landing_url: str | None
    doi: str | None
    issued: str | None

    @property
    def prefecture_codes(self) -> tuple[str, ...]:
        return tuple(
            s for s in self.set_specs if classify_set_spec(s) is SetSpecKind.PREFECTURE
        )

    @property
    def municipality_codes(self) -> tuple[str, ...]:
        return tuple(
            s for s in self.set_specs if classify_set_spec(s) is SetSpecKind.MUNICIPALITY
        )

    @property
    def title_blob(self) -> str:
        """語の検索に使う一続きの文字列。"""
        return " ".join(self.titles)


def _texts(element: Any, tag: str, namespace: str) -> tuple[str, ...]:
    return tuple(
        (child.text or "").strip()
        for child in element
        if etree.QName(child).localname == tag
        and etree.QName(child).namespace == namespace
        and (child.text or "").strip()
    )


def parse_record(record: Any) -> OaiRecord:
    """1 レコードを読む。三つの形すべてを受ける。"""
    header = record.find(f"{{{OAI_NS}}}header")
    identifier_el = header.find(f"{{{OAI_NS}}}identifier") if header is not None else None
    datestamp_el = header.find(f"{{{OAI_NS}}}datestamp") if header is not None else None
    set_specs = tuple(
        (el.text or "").strip()
        for el in (header.findall(f"{{{OAI_NS}}}setSpec") if header is not None else [])
        if (el.text or "").strip()
    )

    metadata = record.find(f"{{{OAI_NS}}}metadata")
    if metadata is None or len(metadata) == 0:
        return OaiRecord(
            identifier=(identifier_el.text or "").strip() if identifier_el is not None else "",
            datestamp=(datestamp_el.text or "").strip() if datestamp_el is not None else None,
            shape=RecordShape.NO_METADATA,
            set_specs=set_specs,
            titles=(),
            publishers=(),
            landing_url=None,
            doi=None,
            issued=None,
        )

    root = metadata[0]
    localname = etree.QName(root).localname

    if localname == "dc":
        shape = RecordShape.OAI_DC
        titles = _texts(root, "title", DC_NS)
        publishers = _texts(root, "publisher", DC_NS)
        identifiers = _texts(root, "identifier", DC_NS)
        landing_url = next(
            (
                v
                for v in identifiers
                if v.startswith("https://sitereports.nabunken.go.jp/")
                and not v.endswith(".pdf")
            ),
            None,
        )
        doi = next((m.group(1) for v in identifiers if (m := _DOI.match(v))), None)
        issued = next((v for v in identifiers if _DATE.match(v)), None)
    elif localname == "junii2":
        shape = RecordShape.JUNII2
        titles = _texts(root, "title", JUNII2_NS) + _texts(root, "jtitle", JUNII2_NS)
        publishers = _texts(root, "publisher", JUNII2_NS)
        landing_url = next(iter(_texts(root, "URI", JUNII2_NS)), None)
        doi = None
        issued = next(iter(_texts(root, "dateofissued", JUNII2_NS)), None)
    else:
        # 知らない形を黙って捨てない。仮定が崩れたら実装が教えるようにする(HC-075)。
        raise ValueError(f"未知のメタデータ形式: {localname}")

    return OaiRecord(
        identifier=(identifier_el.text or "").strip() if identifier_el is not None else "",
        datestamp=(datestamp_el.text or "").strip() if datestamp_el is not None else None,
        shape=shape,
        set_specs=set_specs,
        titles=titles,
        publishers=publishers,
        landing_url=landing_url,
        doi=doi,
        issued=issued,
    )


def parse_page(xml: bytes) -> list[OaiRecord]:
    root = etree.fromstring(xml)
    return [parse_record(r) for r in root.findall(f".//{{{OAI_NS}}}record")]

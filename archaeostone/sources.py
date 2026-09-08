"""源の登録簿と、公開ビルドの門(SPEC §3・§7 G-01)。

この module の役目はひとつだけである: **配ってよい源から来たレコードだけを
public/ へ通す**。判定は fail-closed —— 知らない源・出所の書かれていない
レコードは、疑わしいのではなく違反として扱う(SPEC §4.4)。
"""

from __future__ import annotations

import dataclasses
import pathlib
from collections.abc import Iterable, Iterator, Mapping
from typing import Any

import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_REGISTRY_PATH = REPO_ROOT / "config" / "sources.yaml"

#: 全エントリが必ず持つキー(T-001)。
REQUIRED_KEYS: frozenset[str] = frozenset(
    {
        "title",
        "source_url",
        "license_url",
        "license_name",
        "license_quote",
        "redistribution",
        "modification",
        "attribution_required",
        "verified_at",
    }
)


class SourceRegistry(Mapping[str, dict[str, Any]]):
    """`config/sources.yaml` を読んだもの。"""

    def __init__(self, entries: Mapping[str, dict[str, Any]]) -> None:
        self._entries = dict(entries)

    def __getitem__(self, source_id: str) -> dict[str, Any]:
        return self._entries[source_id]

    def __iter__(self) -> Iterator[str]:
        return iter(self._entries)

    def __len__(self) -> int:
        return len(self._entries)

    @property
    def ids(self) -> list[str]:
        return list(self._entries)

    def is_redistributable(self, source_id: str | None) -> bool:
        """配ってよい源か。未登録・None は False(fail-closed)。"""
        if source_id is None:
            return False
        entry = self._entries.get(source_id)
        if entry is None:
            return False
        return entry.get("redistribution") is True

    def attributions(self) -> list[dict[str, str]]:
        """出典表示が要る源の一覧(Attribution パネル用・SPEC §36)。"""
        out = []
        for source_id, entry in self._entries.items():
            if entry.get("attribution_required") and entry.get("attribution_text"):
                out.append(
                    {
                        "source_id": source_id,
                        "text": entry["attribution_text"],
                        "url": entry["source_url"],
                    }
                )
        return out


@dataclasses.dataclass(frozen=True)
class Violation:
    """公開してはならないレコード。"""

    record_id: str
    source_id: str | None
    reason: str


def load_registry(path: pathlib.Path | None = None) -> SourceRegistry:
    raw = yaml.safe_load((path or DEFAULT_REGISTRY_PATH).read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not raw:
        raise ValueError("源の登録簿が空、または辞書ではない")
    return SourceRegistry(raw)


def publishable_violations(
    records: Iterable[Mapping[str, Any]],
    registry: SourceRegistry | None = None,
    *,
    id_key: str = "id",
    source_key: str = "source_id",
) -> list[Violation]:
    """公開ファイルへ書き出す前の門(G-01)。

    違反を**返す**のであって、無ければ空リストになる。呼ぶ側が中身を見ずに
    真偽だけ取ると「違反 0 件」と「検査していない」が区別できなくなるので、
    書き出し器は必ず件数と内訳を出力する。
    """
    reg = registry if registry is not None else load_registry()
    violations: list[Violation] = []
    for record in records:
        record_id = str(record.get(id_key, "(id 無し)"))
        source_id = record.get(source_key)
        if source_id is None:
            violations.append(Violation(record_id, None, "出所(source_id)が書かれていない"))
        elif source_id not in reg:
            violations.append(Violation(record_id, source_id, "登録簿に無い源"))
        elif not reg.is_redistributable(source_id):
            reason = reg[source_id].get("redistribution_reason", "再配布不可")
            violations.append(Violation(record_id, source_id, reason))
    return violations

"""源の登録簿の検査(T-001〜T-005 / G-01)。

期待値の出所は SPEC.md §2・§3 の実測表。再配布可否は 2026-09-08 に
各サイトの権利ページを読んで決めたものであり、推測ではない。
"""

import pytest

from archaeostone.sources import (
    REQUIRED_KEYS,
    SourceRegistry,
    load_registry,
    publishable_violations,
)


@pytest.fixture(scope="module")
def registry() -> SourceRegistry:
    return load_registry()


def test_t001_every_source_has_required_keys(registry: SourceRegistry) -> None:
    """T-001: 全エントリが必須キーを持つ。"""
    assert registry.ids, "登録簿が空である(走査対象が空でないことの確認)"
    for source_id, entry in registry.items():
        missing = REQUIRED_KEYS - entry.keys()
        assert not missing, f"{source_id} に必須キーが無い: {sorted(missing)}"


# SPEC §2.1/§2.2 — 2026-09-08 に権利ページ・robots.txt を読んで確定した。
NOT_REDISTRIBUTABLE = {"SRC-ITOIGAWA", "SRC-MEIJI-COLS", "SRC-JPSEARCH"}
REDISTRIBUTABLE = {"SRC-GSJ", "SRC-GSI", "SRC-NABUNKEN", "SRC-SOURCEAREA"}


def test_t002_non_redistributable_sources_are_marked(registry: SourceRegistry) -> None:
    """T-002: 実測で再配布不可と判明した源が false になっている。"""
    for source_id in NOT_REDISTRIBUTABLE:
        entry = registry[source_id]
        assert entry["redistribution"] is False, f"{source_id} は再配布不可のはず"
        # 「なぜ不可か」を必ず残す。理由の無い禁止は後から緩められてしまう。
        assert entry.get("redistribution_reason"), f"{source_id} に理由が無い"


def test_t003_redistributable_sources_carry_attribution(registry: SourceRegistry) -> None:
    """T-003: 再配布可の源は出典表記を持つ。"""
    for source_id in REDISTRIBUTABLE:
        entry = registry[source_id]
        assert entry["redistribution"] is True, f"{source_id} は再配布可のはず"
        if entry["attribution_required"]:
            assert entry.get("attribution_text"), f"{source_id} に出典表記が無い"


def test_t002_t003_partition_is_exhaustive(registry: SourceRegistry) -> None:
    """登録簿に、上の二群のどちらでもない源が紛れていないこと。

    これが無いと、新しい源を足したときに T-002/T-003 が黙って素通りする。
    """
    assert set(registry.ids) == NOT_REDISTRIBUTABLE | REDISTRIBUTABLE


def test_t005_negative_control_real_records_pass(registry: SourceRegistry) -> None:
    """T-005(陰性対照): 正当なレコードは公開可否の検査を素通りする。

    先に陰性対照を当てる(HC-074)。誤検出があれば陽性対照より先に分かる。
    """
    records = [
        {"id": "OBS-A", "source_id": "SRC-SOURCEAREA"},
        {"id": "OBS-B", "source_id": "SRC-GSJ"},
        {"id": "DOC-1", "source_id": "SRC-NABUNKEN"},
    ]
    assert publishable_violations(records, registry) == []


def test_t004_positive_control_forbidden_source_is_caught(registry: SourceRegistry) -> None:
    """T-004(陽性対照): 再配布不可の源に由来するレコードを検査が落とす。"""
    records = [
        {"id": "OBS-A", "source_id": "SRC-SOURCEAREA"},
        {"id": "JADE-1", "source_id": "SRC-ITOIGAWA"},  # 落ちるべき
    ]
    violations = publishable_violations(records, registry)
    assert [v.record_id for v in violations] == ["JADE-1"]
    assert violations[0].source_id == "SRC-ITOIGAWA"


def test_t004_positive_control_unknown_source_is_caught(registry: SourceRegistry) -> None:
    """T-004(陽性対照その 2): 登録簿に無い源も落とす。

    fail-closed(SPEC §4.4)。知らない源は「たぶん大丈夫」ではなく違反とする。
    """
    records = [{"id": "X-1", "source_id": "SRC-DOES-NOT-EXIST"}]
    violations = publishable_violations(records, registry)
    assert [v.record_id for v in violations] == ["X-1"]


def test_t004_positive_control_missing_source_id_is_caught(registry: SourceRegistry) -> None:
    """T-004(陽性対照その 3): 出所が書かれていないレコードも落とす。"""
    violations = publishable_violations([{"id": "X-2"}], registry)
    assert [v.record_id for v in violations] == ["X-2"]

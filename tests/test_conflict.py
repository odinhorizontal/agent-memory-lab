from datetime import UTC, datetime

import pytest

from agent_memory_lab.memory.manager import MemoryManager
from agent_memory_lab.models import Candidate, MemoryType, Status, Strategy
from agent_memory_lab.storage.sqlite_store import SQLiteStore

JAN = datetime(2025, 1, 1, tzinfo=UTC)
MAR = datetime(2025, 3, 1, tzinfo=UTC)
JUN = datetime(2025, 6, 1, tzinfo=UTC)


@pytest.mark.parametrize("strategy", list(Strategy))
def test_temporal_replacement(tmp_path, strategy):
    manager = MemoryManager(SQLiteStore(tmp_path / "db.sqlite3"), "u", "a", strategy)
    old, = manager.import_turn("项目使用 SQLite 数据库。", effective_at=JAN, recorded_at=MAR)
    new, = manager.import_turn("项目数据库已经从 SQLite 改成 PostgreSQL。",
                               effective_at=JUN, recorded_at=MAR)
    assert old.value == "SQLite"
    assert new.created_at == MAR and new.valid_from == JUN
    assert [item.id for item in manager.list_memories(as_of=MAR)] == [old.id]
    if strategy == Strategy.VERSIONED:
        assert [item.id for item in manager.list_memories(as_of=JUN)] == [new.id]
        assert manager.get_memory(old.id).status == Status.SUPERSEDED
        assert manager.get_memory_activity(new.id)[1][0].target_id == old.id
    else:
        assert {item.id for item in manager.list_memories(as_of=JUN)} == {old.id, new.id}
        assert new.pending_conflict


@pytest.mark.parametrize(("entity", "attribute", "scope"), [
    ("other", "database", "global"), ("project", "cache", "global"), ("project", "database", "other"),
])
def test_unrelated_slots_do_not_conflict(tmp_path, entity, attribute, scope):
    manager = MemoryManager(SQLiteStore(tmp_path / "db.sqlite3"), "u", "a")
    manager.import_turn("项目使用 SQLite 数据库。", effective_at=JAN)
    new = manager.add_memory(Candidate("PostgreSQL", MemoryType.SEMANTIC, entity, attribute,
                                       "PostgreSQL", scope=scope, valid_from=JUN, replaces=True))
    assert len(manager.list_memories(as_of=JUN)) == 2
    assert not new.pending_conflict


@pytest.mark.parametrize(("effective", "explicit", "previous"), [
    (None, True, "SQLite"), (JAN, True, "SQLite"), (JUN, False, None), (JUN, True, "Other"),
])
def test_uncertain_conflict_is_preserved(tmp_path, effective, explicit, previous):
    manager = MemoryManager(SQLiteStore(tmp_path / "db.sqlite3"), "u", "a")
    old, = manager.import_turn("项目使用 SQLite 数据库。", effective_at=JAN)
    new = manager.add_memory(Candidate("Project database PostgreSQL", MemoryType.SEMANTIC,
                                       "project", "database", "PostgreSQL", valid_from=effective,
                                       replaces=explicit, previous_value=previous))
    assert manager.get_memory(old.id).status == Status.ACTIVE
    assert new.pending_conflict
    assert manager.get_memory_activity(new.id)[0][-1].operation == "CONFLICT"

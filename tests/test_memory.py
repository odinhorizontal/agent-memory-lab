from datetime import UTC, datetime, timedelta

import pytest

from agent_memory_lab.memory.manager import MemoryManager
from agent_memory_lab.models import Candidate, MemoryType, Status, now
from agent_memory_lab.storage.sqlite_store import SQLiteStore


def test_dedup_edit_delete_restore_and_audit(tmp_path):
    manager = MemoryManager(SQLiteStore(tmp_path / "memory.sqlite3"), "user", "agent")
    before = datetime(2025, 1, 1, tzinfo=UTC)
    edit = before + timedelta(days=1)
    first = manager.add_memory(Candidate("SQLite notes", MemoryType.SEMANTIC, valid_from=before))
    assert manager.add_memory(Candidate("  sqlite NOTES ", MemoryType.SEMANTIC,
                                        valid_from=before)).id == first.id
    edited = manager.update_memory(first.id, content="PostgreSQL notes", effective_at=edit,
                                   expected_version=first.version)
    assert manager.list_memories(as_of=before)[0].content == "SQLite notes"
    assert manager.list_memories(as_of=edit) == [edited]
    with pytest.raises(ValueError, match="edited"):
        manager.delete_memory(first.id, expected_version=first.version)
    deleted = manager.delete_memory(first.id)
    assert deleted.status == Status.DELETED and manager.list_memories() == []
    assert manager.list_memories(as_of=edit)[0].content == edited.content
    restored = manager.restore_memory(first.id, version=1)
    assert restored.content == first.content and restored.status == Status.ACTIVE
    assert manager.list_memories(as_of=now()) == [restored]
    history = manager.get_memory_history(first.id)
    assert [item.memory.version for item in history] == list(range(1, restored.version + 1))
    events, links = manager.get_memory_activity(first.id)
    assert [event.operation for event in events] == ["ADD", "DEDUPLICATE", "UPDATE", "DELETE", "RESTORE"]
    assert links[0].kind == "supersedes"
    other = MemoryManager(manager.store, "user", "other")
    with pytest.raises(KeyError):
        other.get_memory_history(first.id)


def test_consolidation_keeps_sources_and_provenance(tmp_path):
    manager = MemoryManager(SQLiteStore(tmp_path / "memory.sqlite3"), "user", "agent")
    ids = [manager.add_memory(Candidate(text, MemoryType.EPISODIC)).id
           for text in ("Trace A", "Trace B")]
    summary = manager.consolidate_memories(ids)
    assert summary.content == "Trace A\nTrace B"
    assert len(manager.list_memories()) == 3
    _, links = manager.get_memory_activity(summary.id)
    assert {link.target_id for link in links} == set(ids)
    assert all(link.kind == "consolidates" for link in links)

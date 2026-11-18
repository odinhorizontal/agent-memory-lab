import sqlite3
from datetime import UTC, datetime

import pytest

from agent_memory_lab.models import Memory, MemoryType, Status
from agent_memory_lab.storage.sqlite_store import SQLiteStore


def test_snapshot_fts_and_rollback(tmp_path):
    store = SQLiteStore(tmp_path / "store.sqlite3")
    when = datetime(2025, 1, 1, tzinfo=UTC)
    fact = Memory("id", "user", "agent", "session", "SQLite 数据库",
                  MemoryType.SEMANTIC, "project", "database", "SQLite",
                  "source", when, when, when, None, Status.ACTIVE, 1.0, 1)
    with pytest.raises(sqlite3.IntegrityError), store.transaction(write=True) as db:
        store.insert(db, fact)
        store.event(db, fact, "ADD", when)
        store.insert(db, fact)
    with store.transaction() as db:
        assert db.execute("SELECT COUNT(*) FROM memory_keys").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM memory_events").fetchone()[0] == 0
        assert not db.execute("SELECT rowid FROM memory_fts WHERE memory_fts MATCH 'sqlite'").fetchall()
    with store.transaction(write=True) as db:
        store.insert(db, fact)
        store.event(db, fact, "ADD", when)
    with store.transaction() as db:
        assert store.head(db, "id", "user", "agent") == fact
        assert store.history(db, "id")[0].memory == fact
        assert store.activity(db, "id")[0][0].operation == "ADD"
        assert db.execute("SELECT rowid FROM memory_fts WHERE memory_fts MATCH '数据库'").fetchall()
        with pytest.raises(KeyError):
            store.head(db, "id", "other", "agent")

"""SQLite transaction and persistence primitives."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, fields
from datetime import datetime
import json
from pathlib import Path
import sqlite3

from ..models import Memory, MemoryEvent, MemoryRelation, MemoryType, MemoryVersion, Status, now, utc
from ..tokenization import tokenize
from .migrations import migrate

FROM = "memory_versions AS v JOIN memory_keys AS k ON k.id=v.id"
SELECT = "v.*, k.user_id, k.agent_id"
_RECORD_FIELDS = tuple(f.name for f in fields(Memory))
_DATES = ("created_at", "updated_at", "valid_from", "valid_to")
_COLUMNS = tuple(name for name in _RECORD_FIELDS if name not in ("user_id", "agent_id"))


def stamp(value: datetime) -> str:
    return utc(value).isoformat(timespec="microseconds")


def read_memory(row: sqlite3.Row) -> Memory:
    data = {name: row[name] for name in _RECORD_FIELDS}
    for name in _DATES:
        if data[name] is not None:
            data[name] = datetime.fromisoformat(data[name])
    data["memory_type"] = MemoryType(data["memory_type"])
    data["status"] = Status(data["status"])
    data["pending_conflict"] = bool(data["pending_conflict"])
    return Memory(**data)


def filters(user_id=None, agent_id=None, memory_type=None, as_of=None, include_history=False):
    clauses, values = ["1=1"], []
    for column, value in (("k.user_id", user_id), ("k.agent_id", agent_id),
                          ("v.memory_type", memory_type)):
        if value is not None:
            clauses.append(f"{column} = ?")
            values.append(value)
    if as_of is not None or not include_history:
        point = stamp(as_of if as_of is not None else now())
        clauses.extend(("v.visible = 1", "v.status IN ('active','superseded')",
                        "(v.valid_from IS NULL OR v.valid_from <= ?)",
                        "(v.valid_to IS NULL OR ? < v.valid_to)"))
        values.extend((point, point))
    return " AND ".join(clauses), values


class SQLiteStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            migrate(db)

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=5)
        try:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("PRAGMA busy_timeout=5000")
            yield db
        finally:
            db.close()

    @contextmanager
    def transaction(self, *, write: bool = False) -> Iterator[sqlite3.Connection]:
        with self._connection() as db, db:
            db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield db

    def head(self, db, memory_id: str, user_id: str, agent_id: str) -> Memory:
        row = db.execute(
            f"SELECT {SELECT} FROM {FROM} WHERE v.id=? AND k.user_id=? AND k.agent_id=? "
            "ORDER BY v.version DESC LIMIT 1", (memory_id, user_id, agent_id)
        ).fetchone()
        if row is None:
            raise KeyError(memory_id)
        return read_memory(row)

    def insert(self, db, memory: Memory, *, visible: bool = True) -> None:
        if memory.version == 1:
            db.execute("INSERT INTO memory_keys VALUES (?,?,?)",
                       (memory.id, memory.user_id, memory.agent_id))
        data = asdict(memory)
        for name in _DATES:
            if data[name] is not None:
                data[name] = stamp(data[name])
        columns = ", ".join((*_COLUMNS, "visible", "terms"))
        marks = ", ".join("?" for _ in range(len(_COLUMNS) + 2))
        terms = " ".join(tokenize(memory.content))
        db.execute(f"INSERT INTO memory_versions ({columns}) VALUES ({marks})",
                   (*[data[name] for name in _COLUMNS], visible, terms))

    def hide(self, db, memory: Memory) -> None:
        db.execute("UPDATE memory_versions SET visible=0 WHERE id=? AND version=?",
                   (memory.id, memory.version))

    def event(self, db, memory: Memory, operation: str, recorded_at: datetime, **details) -> None:
        db.execute(
            "INSERT INTO memory_events(memory_id,version,operation,recorded_at,details) "
            "VALUES (?,?,?,?,?)",
            (memory.id, memory.version, operation, stamp(recorded_at), json.dumps(details))
        )

    def relate(self, db, source: Memory, target: Memory, kind: str) -> None:
        db.execute("INSERT INTO memory_relations VALUES (?,?,?,?,?)",
                   (source.id, source.version, target.id, target.version, kind))

    def history(self, db, memory_id: str) -> list[MemoryVersion]:
        rows = db.execute(f"SELECT {SELECT} FROM {FROM} WHERE v.id=? ORDER BY v.version",
                          (memory_id,))
        return [MemoryVersion(read_memory(row), bool(row["visible"])) for row in rows]

    def activity(self, db, memory_id: str) -> tuple[list[MemoryEvent], list[MemoryRelation]]:
        events = db.execute("SELECT * FROM memory_events WHERE memory_id=? ORDER BY id",
                            (memory_id,))
        relations = db.execute(
            "SELECT * FROM memory_relations WHERE source_id=? OR target_id=? "
            "ORDER BY source_id, source_version, target_id, target_version", (memory_id, memory_id)
        )
        return (
            [MemoryEvent(e["id"], e["memory_id"], e["version"], e["operation"],
                         datetime.fromisoformat(e["recorded_at"]), json.loads(e["details"]))
             for e in events],
            [MemoryRelation(**dict(row)) for row in relations],
        )

    def heads(self, db, user_id: str, agent_id: str, memory_type=None) -> list[Memory]:
        rows = db.execute(
            f"SELECT {SELECT} FROM {FROM} WHERE k.user_id=? AND k.agent_id=? "
            "AND (? IS NULL OR v.memory_type=?) AND v.version=("
            "SELECT MAX(h.version) FROM memory_versions h WHERE h.id=v.id) "
            "ORDER BY v.updated_at DESC, v.id", (user_id, agent_id, memory_type, memory_type)
        )
        return [read_memory(row) for row in rows]

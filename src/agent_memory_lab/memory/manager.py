"""Tenant-bound lifecycle and audit API."""

from dataclasses import asdict, replace
from datetime import datetime
from uuid import uuid4

from ..extraction.base import MemoryExtractor
from ..extraction.rule_extractor import RuleExtractor
from ..models import Candidate, Memory, MemoryEvent, MemoryRelation, MemoryType, MemoryVersion
from ..models import Status, Strategy, now, utc
from ..storage.sqlite_store import FROM, SELECT, SQLiteStore, filters, read_memory
from .conflict import conflicts, duplicate, replacement
from .consolidation import MemoryCompressionProvider, MockCompression
from .versioning import close_fact, revise


class MemoryManager:
    def __init__(self, store: SQLiteStore, user_id: str, agent_id: str,
                 strategy: Strategy = Strategy.VERSIONED):
        if not user_id.strip() or not agent_id.strip():
            raise ValueError("User and agent are required")
        self.store = store
        self.user_id = user_id
        self.agent_id = agent_id
        self.strategy = Strategy(strategy)

    def _head(self, db, memory_id: str) -> Memory:
        return self.store.head(db, memory_id, self.user_id, self.agent_id)

    def _projected(self, db, candidate: Candidate) -> list[Memory]:
        rows = db.execute(
            f"SELECT {SELECT} FROM {FROM} WHERE k.user_id=? AND k.agent_id=? "
            "AND v.visible=1 AND v.status IN ('active','superseded') "
            "AND v.scope=? AND v.memory_type=? ORDER BY v.version DESC,v.id",
            (self.user_id, self.agent_id, candidate.scope, candidate.memory_type)
        )
        return [read_memory(row) for row in rows]

    def _add(self, db, candidate, session_id, source_id, memory_id, recorded_at) -> Memory:
        if not session_id.strip() or (memory_id is not None and not memory_id.strip()):
            raise ValueError("Session and memory identifiers must be nonblank")
        visible = self._projected(db, candidate)
        for existing in visible:
            if duplicate(existing, candidate):
                self.store.event(db, existing, "DEDUPLICATE", recorded_at, source_id=source_id)
                return existing
        competing = [old for old in visible if conflicts(old, candidate)]
        old = replacement(competing, candidate) if self.strategy == Strategy.VERSIONED else None
        data = asdict(candidate)
        del data["replaces"], data["previous_value"]
        memory = Memory(
            id=memory_id or uuid4().hex, user_id=self.user_id, agent_id=self.agent_id,
            session_id=session_id, source_id=source_id, created_at=recorded_at,
            updated_at=recorded_at, status=Status.ACTIVE, version=1,
            pending_conflict=bool(competing and old is None), **data,
        )
        if old is not None:
            closed = close_fact(self.store, db, old, candidate.valid_from, recorded_at)
            self.store.insert(db, memory)
            self.store.relate(db, memory, closed, "supersedes")
            self.store.event(db, closed, "UPDATE", recorded_at, superseded_by=memory.id)
            self.store.event(db, memory, "ADD", recorded_at, supersedes=old.id)
        else:
            self.store.insert(db, memory)
            self.store.event(db, memory, "ADD", recorded_at)
            if competing:
                self.store.event(db, memory, "CONFLICT", recorded_at,
                                 competing_ids=[item.id for item in competing])
        return memory

    def add_memory(self, candidate: Candidate, *, session_id: str = "default",
                   source_id: str | None = None, memory_id: str | None = None,
                   recorded_at: datetime | None = None) -> Memory:
        with self.store.transaction(write=True) as db:
            return self._add(db, candidate, session_id, source_id, memory_id,
                             now() if recorded_at is None else utc(recorded_at))

    def import_turn(self, text: str, *, session_id: str = "default", source_id: str | None = None,
                    effective_at: datetime | None = None, recorded_at: datetime | None = None,
                    extractor: MemoryExtractor | None = None) -> list[Memory]:
        candidates = (extractor or RuleExtractor()).extract(text, effective_at=effective_at)
        timestamp = now() if recorded_at is None else utc(recorded_at)
        with self.store.transaction(write=True) as db:
            return [self._add(db, item, session_id, source_id, None, timestamp)
                    for item in candidates]

    def get_memory(self, memory_id: str) -> Memory:
        with self.store.transaction() as db:
            return self._head(db, memory_id)

    def list_memories(self, *, memory_type: MemoryType | None = None,
                      as_of: datetime | None = None, include_history: bool = False) -> list[Memory]:
        with self.store.transaction() as db:
            if include_history and as_of is None:
                return self.store.heads(db, self.user_id, self.agent_id, memory_type)
            where, args = filters(self.user_id, self.agent_id, memory_type, as_of)
            return [read_memory(row) for row in db.execute(
                f"SELECT {SELECT} FROM {FROM} WHERE {where} ORDER BY v.updated_at DESC,v.id", args
            )]

    def get_memory_history(self, memory_id: str) -> list[MemoryVersion]:
        with self.store.transaction() as db:
            self._head(db, memory_id)
            return self.store.history(db, memory_id)

    def get_memory_activity(self, memory_id: str) -> tuple[list[MemoryEvent], list[MemoryRelation]]:
        with self.store.transaction() as db:
            self._head(db, memory_id)
            return self.store.activity(db, memory_id)

    def update_memory(self, memory_id: str, *, content: str, value: str | None = None,
                      effective_at: datetime | None = None,
                      expected_version: int | None = None) -> Memory:
        recorded_at = now()
        effective = recorded_at if effective_at is None else utc(effective_at)
        with self.store.transaction(write=True) as db:
            old = self._head(db, memory_id)
            self._require_active(old, expected_version)
            candidate = Candidate(content, old.memory_type, old.entity, old.attribute,
                                  old.value if value is None else value, old.scope,
                                  effective, old.valid_to, old.confidence)
            if old.content == candidate.content and old.value == candidate.value:
                return old
            if old.valid_from is not None and effective < old.valid_from:
                raise ValueError("An edit cannot predate the current version")
            if old.valid_from == effective:
                self.store.hide(db, old)
                previous = old
            else:
                previous = close_fact(self.store, db, old, effective, recorded_at)
            updated = replace(old, version=previous.version + 1, content=candidate.content,
                              value=candidate.value, valid_from=effective, updated_at=recorded_at,
                              pending_conflict=self._has_conflict(db, candidate, old.id))
            self.store.insert(db, updated)
            self.store.relate(db, updated, previous, "supersedes")
            self.store.event(db, updated, "UPDATE", recorded_at, previous_version=old.version)
            return updated

    def delete_memory(self, memory_id: str, *, expected_version: int | None = None) -> Memory:
        with self.store.transaction(write=True) as db:
            old = self._head(db, memory_id)
            if old.status == Status.DELETED and expected_version is None:
                return old
            self._require_active(old, expected_version)
            recorded_at = now()
            self.store.hide(db, old)
            if old.valid_from is None or old.valid_from < recorded_at:
                end = min(recorded_at, old.valid_to) if old.valid_to else recorded_at
                closed = replace(old, version=old.version + 1, updated_at=recorded_at,
                                 status=Status.SUPERSEDED, valid_to=end)
                self.store.insert(db, closed)
                previous = closed
            else:
                previous = old
            deleted = replace(old, version=previous.version + 1,
                              status=Status.DELETED, updated_at=recorded_at)
            self.store.insert(db, deleted, visible=False)
            self.store.event(db, deleted, "DELETE", recorded_at)
            return deleted

    def restore_memory(self, memory_id: str, version: int | None = None) -> Memory:
        with self.store.transaction(write=True) as db:
            head = self._head(db, memory_id)
            history = self.store.history(db, memory_id)
            target = next((row.memory for row in reversed(history)
                           if row.memory.status != Status.DELETED
                           and (version is None or row.memory.version == version)), None)
            if target is None:
                raise KeyError((memory_id, version))
            recorded_at = now()
            previous = head
            if head.status == Status.ACTIVE:
                if head.valid_from is None or head.valid_from < recorded_at:
                    end = min(recorded_at, head.valid_to) if head.valid_to else recorded_at
                    previous = close_fact(self.store, db, head, end, recorded_at)
                else:
                    self.store.hide(db, head)
            candidate = Candidate(target.content, target.memory_type, target.entity, target.attribute,
                                  target.value, target.scope, recorded_at, confidence=target.confidence)
            restored = replace(target, version=previous.version + 1, status=Status.ACTIVE,
                               valid_from=recorded_at, valid_to=None, updated_at=recorded_at,
                               pending_conflict=self._has_conflict(db, candidate, memory_id))
            self.store.insert(db, restored)
            self.store.event(db, restored, "RESTORE", recorded_at, restored_from=target.version)
            return restored

    def _has_conflict(self, db, candidate: Candidate, own_id: str) -> bool:
        return any(old.id != own_id and conflicts(old, candidate)
                   for old in self._projected(db, candidate))

    @staticmethod
    def _require_active(memory: Memory, expected_version: int | None) -> None:
        if expected_version is not None and memory.version != expected_version:
            raise ValueError("Memory was edited. Reload its current version")
        if memory.status != Status.ACTIVE:
            raise ValueError("Only active memories can be edited or deleted")

    def consolidate_memories(self, ids: list[str],
                             provider: MemoryCompressionProvider | None = None) -> Memory:
        if len(set(ids)) < 2:
            raise ValueError("Consolidation requires at least two distinct memories")
        with self.store.transaction() as db:
            sources = [self._head(db, item) for item in dict.fromkeys(ids)]
        if len({item.scope for item in sources}) != 1:
            raise ValueError("Consolidation requires a common scope")
        text = (provider or MockCompression()).compress(sources)
        recorded_at = now()
        candidate = Candidate(text, MemoryType.SEMANTIC, scope=sources[0].scope,
                              valid_from=recorded_at)
        with self.store.transaction(write=True) as db:
            for item in sources:
                self._require_active(self._head(db, item.id), item.version)
                if ((item.valid_from and item.valid_from > recorded_at)
                        or (item.valid_to and item.valid_to <= recorded_at)):
                    raise ValueError("Consolidation requires currently valid sources")
            summary = self._add(db, candidate, "consolidation", None, None, recorded_at)
            for item in sources:
                db.execute("INSERT OR IGNORE INTO memory_relations VALUES (?,?,?,?,?)",
                           (summary.id, summary.version, item.id, item.version, "consolidates"))
            self.store.event(db, summary, "CONSOLIDATE", recorded_at, sources=ids)
            return summary

    def search_memories(self, query: str, *, method: str = "Hybrid", top_k: int = 5,
                        memory_type: MemoryType | None = None, as_of: datetime | None = None,
                        include_history: bool = False):
        from ..retrieval import RETRIEVERS

        if method not in RETRIEVERS:
            raise ValueError(f"Unknown retrieval method: {method}")
        return RETRIEVERS[method](self.store).search(
            query, top_k, self.user_id, self.agent_id, memory_type, as_of, include_history
        )

"""Shared ranking API with a consistent SQLite read snapshot."""

from abc import ABC, abstractmethod
from datetime import datetime

from ..models import Memory, MemoryType, RetrievalResult, now
from ..storage.sqlite_store import SQLiteStore, filters
from ..tokenization import tokenize

Ranked = list[tuple[Memory, float]]


class Retriever(ABC):
    def __init__(self, store: SQLiteStore):
        self.store = store

    def search(self, query: str, top_k: int = 5, user_id: str | None = None,
               agent_id: str | None = None, memory_type: MemoryType | None = None,
               as_of: datetime | None = None, include_history: bool = False
               ) -> list[RetrievalResult]:
        if type(top_k) is not int or not 0 <= top_k <= 1000:
            raise ValueError("top_k must be an integer in [0, 1000]")
        if top_k == 0 or not tokenize(query):
            return []
        if as_of is None and not include_history:
            as_of = now()
        where, args = filters(user_id, agent_id, memory_type, as_of, include_history)
        with self.store.transaction() as db:
            ranked = self._rank(db, query, where, args, top_k)
        return [RetrievalResult(memory, rank, float(score))
                for rank, (memory, score) in enumerate(ranked, start=1)]

    @abstractmethod
    def _rank(self, db, query: str, where: str, args: list, limit: int) -> Ranked:
        """Rank only the revisions admitted by the shared filter."""

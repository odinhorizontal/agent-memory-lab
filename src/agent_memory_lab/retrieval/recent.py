"""Recency baseline."""

from ..storage.sqlite_store import FROM, SELECT, read_memory
from .base import Ranked, Retriever


class RecentRetriever(Retriever):
    def _rank(self, db, query: str, where: str, args: list, limit: int) -> Ranked:
        rows = db.execute(
            f"SELECT {SELECT} FROM {FROM} WHERE {where} "
            "ORDER BY v.created_at DESC, v.updated_at DESC, v.id, v.version DESC LIMIT ?",
            (*args, limit)
        )
        return [(read_memory(row), 1 / rank) for rank, row in enumerate(rows, 1)]

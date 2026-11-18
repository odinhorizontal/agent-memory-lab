"""Keyword retrieval with SQLite FTS5 BM25."""

from ..storage.sqlite_store import FROM, SELECT, read_memory
from .base import Ranked, Retriever
from ..tokenization import tokenize


class BM25Retriever(Retriever):
    def _rank(self, db, query: str, where: str, args: list, limit: int) -> Ranked:
        terms = list(dict.fromkeys(tokenize(query)))[:96]
        if not terms:
            return []
        expression = " OR ".join('"' + term.replace('"', '""') + '"' for term in terms)
        rows = db.execute(
            f"SELECT {SELECT}, -bm25(memory_fts) AS score FROM memory_fts "
            f"JOIN ({FROM}) ON memory_fts.rowid=v.row_id "
            f"WHERE memory_fts MATCH ? AND {where} "
            "ORDER BY score DESC, v.id, v.version DESC LIMIT ?", (expression, *args, limit)
        )
        return [(read_memory(row), row["score"]) for row in rows]

"""BM25 and cosine fusion via reciprocal rank fusion."""

from ..providers.embedding import EmbeddingProvider
from ..storage.sqlite_store import SQLiteStore
from .base import Ranked, Retriever
from .bm25 import BM25Retriever
from .vector import VectorRetriever


def reciprocal_rank_fusion(*rankings: Ranked) -> Ranked:
    merged = {}
    for ranked in rankings:
        for rank, (memory, _) in enumerate(ranked, start=1):
            key = (memory.id, memory.version)
            _, score = merged.get(key, (memory, 0.0))
            merged[key] = memory, score + 1 / (60 + rank)
    return sorted(merged.values(), key=lambda item: (-item[1], item[0].id, -item[0].version))


class HybridRetriever(Retriever):
    def __init__(self, store: SQLiteStore, provider: EmbeddingProvider | None = None):
        super().__init__(store)
        self.bm25 = BM25Retriever(store)
        self.vector = VectorRetriever(store, provider)

    def _rank(self, db, query: str, where: str, args: list, limit: int) -> Ranked:
        depth = max(20, limit)
        return reciprocal_rank_fusion(
            self.bm25._rank(db, query, where, args, depth),
            self.vector._rank(db, query, where, args, depth),
        )[:limit]

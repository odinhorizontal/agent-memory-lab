"""Exhaustive cosine ranking for small CPU workloads."""

import numpy as np

from ..providers.embedding import EmbeddingProvider, MockEmbedding
from ..storage.sqlite_store import FROM, SELECT, SQLiteStore, read_memory
from .base import Ranked, Retriever


def normalize(vectors: np.ndarray) -> np.ndarray:
    data = np.asarray(vectors, dtype=np.float64)
    if data.ndim != 2 or not np.isfinite(data).all():
        raise ValueError("Embeddings must be a finite two-dimensional array")
    norms = np.linalg.norm(data, axis=1, keepdims=True)
    return np.divide(data, norms, out=np.zeros_like(data), where=norms != 0)


class VectorRetriever(Retriever):
    def __init__(self, store: SQLiteStore, provider: EmbeddingProvider | None = None):
        super().__init__(store)
        self.provider = provider or MockEmbedding()

    def _rank(self, db, query: str, where: str, args: list, limit: int) -> Ranked:
        rows = db.execute(
            f"SELECT {SELECT} FROM {FROM} WHERE {where} ORDER BY v.id,v.version DESC", args
        ).fetchall()
        if not rows:
            return []
        vectors = normalize(self.provider.embed([query, *(row["content"] for row in rows)]))
        if vectors.shape[0] != len(rows) + 1:
            raise ValueError("Embedding provider returned the wrong number of vectors")
        scores = vectors[1:] @ vectors[0]
        order = np.argsort(-scores, kind="stable")[:limit]
        return [(read_memory(rows[i]), scores[i]) for i in order if scores[i] > 0]

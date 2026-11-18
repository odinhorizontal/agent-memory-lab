"""Retriever factory."""

from .bm25 import BM25Retriever
from .hybrid import HybridRetriever
from .recent import RecentRetriever
from .vector import VectorRetriever

RETRIEVERS = {
    "Recent": RecentRetriever,
    "BM25": BM25Retriever,
    "Vector": VectorRetriever,
    "Hybrid": HybridRetriever,
}

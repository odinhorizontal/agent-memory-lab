"""Embedding provider API and deterministic, lexical mock vectors."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from functools import lru_cache
from hashlib import blake2b

import numpy as np

from ..tokenization import tokenize


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, texts: Sequence[str]) -> np.ndarray:
        """Return one fixed-size vector per text in the same order."""


class LocalEmbeddingProvider(EmbeddingProvider):
    """Extension point for local embedding models."""


class MockEmbedding(LocalEmbeddingProvider):
    def __init__(self, dimensions: int = 1024):
        if dimensions <= 0:
            raise ValueError("Embedding dimensions must be positive")
        self.dimensions = dimensions

    @lru_cache(maxsize=2048)
    def _vector(self, text: str) -> np.ndarray:
        vector = np.zeros(self.dimensions, dtype=np.float32)
        for token in tokenize(text):
            digest = blake2b(token.encode(), digest_size=8).digest()
            index = int.from_bytes(digest, "little") % self.dimensions
            vector[index] += 1 if digest[0] & 1 else -1
        vector.flags.writeable = False
        return vector

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        if len(texts) == 0:
            return np.empty((0, self.dimensions), dtype=np.float32)
        return np.stack([self._vector(text) for text in texts])

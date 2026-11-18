"""An offline compression extension point and deterministic mock."""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from ..models import Memory


class MemoryCompressionProvider(ABC):
    @abstractmethod
    def compress(self, memories: Sequence[Memory]) -> str:
        """Produce a text summary from the given evidence."""


class MockCompression(MemoryCompressionProvider):
    def compress(self, memories: Sequence[Memory]) -> str:
        return "\n".join(dict.fromkeys(memory.content for memory in memories))

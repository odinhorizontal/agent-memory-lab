"""Conversation-to-candidate interface."""

from abc import ABC, abstractmethod
from datetime import datetime

from ..models import Candidate


class MemoryExtractor(ABC):
    @abstractmethod
    def extract(self, text: str, *, effective_at: datetime | None = None) -> list[Candidate]:
        """Extract zero or more candidates from one dialogue turn."""

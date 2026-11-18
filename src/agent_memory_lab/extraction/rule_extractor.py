"""Deterministic patterns for supported Chinese and English synthetic dialogue."""

from datetime import datetime
import re

from ..models import Candidate, MemoryType
from .base import MemoryExtractor

_FLAGS = re.IGNORECASE
_CHANGES = (
    ("database", r"项目(?:的)?数据库(?:已经|已)?从\s*(.+?)\s*(?:改成|改为|迁移到)\s*(.+)"),
    ("database", r"(?:the )?project(?: database)? (?:migrated|switched) from\s+(.+?)\s+to\s+(.+)"),
    ("status", r"项目(?:当前)?状态(?:已经|已)?从\s*(.+?)\s*(?:变成|变为|改成|改为)\s*(.+)"),
    ("status", r"(?:the )?project status changed from\s+(.+?)\s+to\s+(.+)"),
)
_FACTS = (
    ("database", r"项目(?:的)?数据库(?:是|使用|采用)\s*(.+)"),
    ("database", r"项目(?:使用|采用)\s*(.+?)\s*数据库"),
    ("database", r"(?:the )?project (?:uses|runs on)\s+(.+?) as (?:its|the) database"),
    ("status", r"项目(?:当前)?状态(?:是|为)\s*(.+)"),
    ("status", r"(?:the )?project status is\s+(.+)"),
)
_TYPES = (
    (MemoryType.PREFERENCE, r"(?:用户|我)(?:更)?(?:偏好|喜欢)\s*(.+)|(?:the user|i) prefer[s]?\s+(.+)"),
    (MemoryType.PROCEDURAL, r"遇到.+?[，,]\s*可以.+|(?:solution|workaround):\s*.+"),
    (MemoryType.EPISODIC, r"(?:Agent|代理)(?:\s*在.+?)?\s*(?:遇到|成功|失败)\s*.+"
                          r"|(?:the )?agent (?:encountered|succeeded at|failed to)\s+.+"),
    (MemoryType.SEMANTIC, r"项目(?:使用|采用|包含|支持)\s*.+"
                          r"|(?:the )?project (?:uses|includes|supports|runs on)\s+.+"),
)


class RuleExtractor(MemoryExtractor):
    def extract(self, text: str, *, effective_at: datetime | None = None) -> list[Candidate]:
        facts = []
        for raw in re.split(r"[。！？!?\r\n]+", text):
            sentence = raw.strip().rstrip(".")
            fact = self._classify(sentence, effective_at)
            if fact is not None:
                facts.append(fact)
        return facts

    @staticmethod
    def _classify(sentence: str, effective_at: datetime | None) -> Candidate | None:
        for attribute, pattern in _CHANGES:
            if match := re.fullmatch(pattern, sentence, _FLAGS):
                old, new = match.groups()
                return Candidate(sentence, MemoryType.SEMANTIC, "project", attribute, new,
                                 valid_from=effective_at, replaces=True, previous_value=old)
        for attribute, pattern in _FACTS:
            if match := re.fullmatch(pattern, sentence, _FLAGS):
                return Candidate(sentence, MemoryType.SEMANTIC, "project", attribute, match[1],
                                 valid_from=effective_at)
        for kind, pattern in _TYPES:
            if re.fullmatch(pattern, sentence, _FLAGS):
                return Candidate(sentence, kind, valid_from=effective_at)
        return None

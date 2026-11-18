"""Deterministic patterns for supported Chinese and English synthetic dialogue."""

from datetime import datetime
import re

from ..models import Candidate, MemoryType
from .base import MemoryExtractor

_FLAGS = re.IGNORECASE
_DB_CHANGE = re.compile(
    r"(?:项目(?:的)?数据库(?:已经|已)?从\s*(.+?)\s*(?:改成|改为|迁移到)\s*(.+)"
    r"|(?:the )?project(?: database)? (?:migrated|switched) from\s+(.+?)\s+to\s+(.+))", _FLAGS
)
_DB_FACT = re.compile(
    r"(?:项目(?:的)?(?:数据库(?:是|使用|采用)|(?:使用|采用))\s*(.+?)"
    r"(?:数据库)?|(?:the )?project (?:uses|runs on)\s+(.+?)(?: as (?:its|the) database)?)", _FLAGS
)
_RULES = (
    (MemoryType.PREFERENCE, r"(?:用户|我)(?:更)?(?:偏好|喜欢)\s*(.+)|(?:the user|i) prefer[s]?\s+(.+)"),
    (MemoryType.PROCEDURAL, r"遇到(.+?[，,]\s*可以.+)|(?:solution|workaround):\s*(.+)"),
    (MemoryType.EPISODIC, r"(?:Agent|代理)(?:\s*在.+?)?\s*(?:遇到|成功|失败)\s*(.+)"
                          r"|(?:the )?agent (?:encountered|succeeded at|failed to)\s+(.+)"),
)


class RuleExtractor(MemoryExtractor):
    def extract(self, text: str, *, effective_at: datetime | None = None) -> list[Candidate]:
        facts = []
        for raw in re.split(r"[。！？!?\r\n]+", text):
            sentence = raw.strip().rstrip(".")
            if match := _DB_CHANGE.fullmatch(sentence):
                old, new = match.groups()[:2] if match[1] is not None else match.groups()[2:]
                facts.append(Candidate(sentence, MemoryType.SEMANTIC, "project", "database",
                                       new, valid_from=effective_at, replaces=True,
                                       previous_value=old))
                continue
            if match := _DB_FACT.fullmatch(sentence):
                value = match[1] or match[2]
                facts.append(Candidate(sentence, MemoryType.SEMANTIC, "project", "database",
                                       value, valid_from=effective_at))
                continue
            for kind, pattern in _RULES:
                if re.fullmatch(pattern, sentence, _FLAGS):
                    facts.append(Candidate(sentence, kind, valid_from=effective_at))
                    break
        return facts

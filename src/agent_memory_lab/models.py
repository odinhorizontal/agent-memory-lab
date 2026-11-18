"""Typed records for storage, lifecycle, and evaluation."""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


def utc(value: datetime) -> datetime:
    if value.utcoffset() is None:
        raise ValueError("Use an offset-aware timestamp")
    return value.astimezone(UTC)


def now() -> datetime:
    return datetime.now(UTC)


class MemoryType(StrEnum):
    SEMANTIC = "semantic"
    EPISODIC = "episodic"
    PROCEDURAL = "procedural"
    PREFERENCE = "preference"


class Status(StrEnum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    DELETED = "deleted"


class Strategy(StrEnum):
    APPEND_ONLY = "append-only"
    VERSIONED = "versioned-update"


@dataclass(frozen=True, slots=True)
class Candidate:
    content: str
    memory_type: MemoryType
    entity: str | None = None
    attribute: str | None = None
    value: str | None = None
    scope: str = "global"
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    confidence: float = 1.0
    replaces: bool = False
    previous_value: str | None = None

    def __post_init__(self) -> None:
        if not self.content.strip() or not self.scope.strip():
            raise ValueError("Content and scope are required")
        object.__setattr__(self, "content", self.content.strip())
        object.__setattr__(self, "memory_type", MemoryType(self.memory_type))
        for field in ("entity", "attribute", "value"):
            value = getattr(self, field)
            if value is not None:
                if not value.strip():
                    raise ValueError(f"{field} cannot be blank")
                object.__setattr__(self, field, value.strip())
        slot_parts = (self.entity, self.attribute, self.value)
        if any(slot_parts) and not all(slot_parts):
            raise ValueError("A fact slot requires entity, attribute, and value")
        if self.replaces and not all(slot_parts):
            raise ValueError("Replacement requires a fact slot")
        if not 0 <= self.confidence <= 1:
            raise ValueError("Confidence must be between 0 and 1")
        for field in ("valid_from", "valid_to"):
            value = getattr(self, field)
            if value is not None:
                object.__setattr__(self, field, utc(value))
        if self.valid_from and self.valid_to and self.valid_from >= self.valid_to:
            raise ValueError("valid_from must precede valid_to")


@dataclass(frozen=True, slots=True)
class Memory:
    id: str
    user_id: str
    agent_id: str
    session_id: str
    content: str
    memory_type: MemoryType
    entity: str | None
    attribute: str | None
    value: str | None
    source_id: str | None
    created_at: datetime
    updated_at: datetime
    valid_from: datetime | None
    valid_to: datetime | None
    status: Status
    confidence: float
    version: int
    scope: str = "global"
    pending_conflict: bool = False


@dataclass(frozen=True, slots=True)
class MemoryVersion:
    memory: Memory
    visible: bool


@dataclass(frozen=True, slots=True)
class MemoryEvent:
    id: int
    memory_id: str
    version: int
    operation: str
    recorded_at: datetime
    details: dict


@dataclass(frozen=True, slots=True)
class MemoryRelation:
    source_id: str
    source_version: int
    target_id: str
    target_version: int
    kind: str


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    memory: Memory
    rank: int
    score: float

    @property
    def id(self) -> str:
        return self.memory.id


@dataclass(frozen=True, slots=True)
class BenchmarkCase:
    id: str
    query: str
    category: str
    gold_ids: tuple[str, ...]
    as_of: datetime
    answer: str | None = None

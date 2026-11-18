"""Conservative slot-based deduplication and conflict decisions."""

from datetime import UTC, datetime
import unicodedata

from ..models import Candidate, Memory, Status

_MIN = datetime.min.replace(tzinfo=UTC)
_MAX = datetime.max.replace(tzinfo=UTC)


def key(value: str | None) -> str:
    return " ".join(unicodedata.normalize("NFKC", value or "").casefold().split())


def same_slot(old: Memory, new: Candidate) -> bool:
    return (new.entity is not None and old.scope == new.scope
            and old.memory_type == new.memory_type
            and key(old.entity) == key(new.entity)
            and key(old.attribute) == key(new.attribute))


def duplicate(old: Memory, new: Candidate) -> bool:
    if old.scope != new.scope or old.memory_type != new.memory_type:
        return False
    if (old.valid_from or _MIN) > (new.valid_from or _MIN):
        return False
    if (old.valid_to or _MAX) < (new.valid_to or _MAX):
        return False
    if new.entity is not None:
        return same_slot(old, new) and key(old.value) == key(new.value)
    return old.entity is None and key(old.content) == key(new.content)


def conflicts(old: Memory, new: Candidate) -> bool:
    return (same_slot(old, new) and key(old.value) != key(new.value)
            and (old.valid_from or _MIN) < (new.valid_to or _MAX)
            and (new.valid_from or _MIN) < (old.valid_to or _MAX))


def replacement(candidates: list[Memory], new: Candidate) -> Memory | None:
    if not new.replaces or new.valid_from is None or len(candidates) != 1:
        return None
    old = candidates[0]
    if old.status != Status.ACTIVE or old.valid_from is None or old.valid_from >= new.valid_from:
        return None
    if new.previous_value is not None and key(old.value) != key(new.previous_value):
        return None
    return old

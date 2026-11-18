"""Version transitions. Snapshot fields remain immutable."""

from dataclasses import replace
from datetime import datetime

from ..models import Memory, Status
from ..storage.sqlite_store import SQLiteStore


def revise(store: SQLiteStore, db, old: Memory, recorded_at: datetime, **changes) -> Memory:
    revised = replace(old, version=old.version + 1, updated_at=recorded_at, **changes)
    store.hide(db, old)
    store.insert(db, revised)
    return revised


def close_fact(store: SQLiteStore, db, old: Memory, effective: datetime,
               recorded_at: datetime) -> Memory:
    return revise(store, db, old, recorded_at, status=Status.SUPERSEDED, valid_to=effective)

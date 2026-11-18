"""Evidence ranking metrics with explicit denominators."""

from collections.abc import Collection, Sequence
from dataclasses import dataclass
from statistics import mean

import numpy as np


def recall_at(ranked: Sequence[str], gold: Collection[str], k: int) -> float:
    return len(set(ranked[:k]).intersection(gold)) / len(set(gold)) if gold else 0.0


def precision_at(ranked: Sequence[str], gold: Collection[str], k: int) -> float:
    return len(set(ranked[:k]).intersection(gold)) / k if k > 0 else 0.0


def reciprocal_rank(ranked: Sequence[str], gold: Collection[str]) -> float:
    return next((1 / rank for rank, memory in enumerate(ranked, 1) if memory in gold), 0.0)


def latency_percentiles(milliseconds: Sequence[float]) -> tuple[float | None, float | None]:
    if not milliseconds:
        return None, None
    p50, p95 = np.percentile(milliseconds, [50, 95])
    return float(p50), float(p95)


def stale_rate(stale: int, returned: int) -> float | None:
    return stale / returned if returned else None


@dataclass(frozen=True, slots=True)
class Observation:
    ranked: tuple[str, ...]
    gold: tuple[str, ...]
    stale: frozenset[str]
    latency_ms: float


def aggregate(observations: Sequence[Observation], top_k: int) -> dict:
    answerable = [item for item in observations if item.gold]
    unanswerable = [item for item in observations if not item.gold]
    returned = sum(len(item.ranked) for item in observations)
    stale = sum(sum(memory in item.stale for memory in item.ranked) for item in observations)
    p50, p95 = latency_percentiles([item.latency_ms for item in observations])
    return {
        "query_count": len(observations),
        "answerable_queries": len(answerable),
        "unanswerable_queries": len(unanswerable),
        "recall_at_1": mean(recall_at(e.ranked, e.gold, 1) for e in answerable) if answerable else None,
        "recall_at_3": mean(recall_at(e.ranked, e.gold, 3) for e in answerable) if answerable else None,
        "recall_at_5": mean(recall_at(e.ranked, e.gold, 5) for e in answerable) if answerable else None,
        "mrr": mean(reciprocal_rank(e.ranked, e.gold) for e in answerable) if answerable else None,
        "precision_at_k": mean(precision_at(e.ranked, e.gold, top_k) for e in answerable)
        if answerable else None,
        "p50_latency_ms": p50,
        "p95_latency_ms": p95,
        "stale_memory_retrieval_rate": stale_rate(stale, returned),
        "stale_retrieved": stale,
        "returned_evidence": returned,
        "unanswerable_empty_rate": mean(not item.ranked for item in unanswerable)
        if unanswerable else None,
        "unanswerable_abstention_accuracy": None,
    }

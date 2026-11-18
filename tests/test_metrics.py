import pytest

from agent_memory_lab.evaluation.metrics import Observation, aggregate, latency_percentiles
from agent_memory_lab.evaluation.metrics import precision_at, recall_at, reciprocal_rank, stale_rate


def test_evidence_metrics():
    ranked = ["x", "a", "b", "d", "e"]
    assert recall_at(ranked, ["a", "b", "c"], 1) == 0
    assert recall_at(ranked, ["a", "b", "c"], 3) == pytest.approx(2 / 3)
    assert recall_at(ranked, ["a", "b", "c"], 5) == pytest.approx(2 / 3)
    assert precision_at(ranked, ["a", "b"], 5) == 0.4
    assert precision_at(["a"], ["a"], 5) == 0.2
    assert reciprocal_rank(ranked, ["a", "b"]) == 0.5
    assert reciprocal_rank(ranked, ["q"]) == 0


def test_latency():
    assert latency_percentiles([1, 2, 3, 4, 5]) == pytest.approx((3, 4.8))
    assert latency_percentiles([]) == (None, None)


def test_stale_rate_and_unanswerable_denominators():
    data = [
        Observation(("stale", "fresh"), ("fresh",), frozenset({"stale"}), 2),
        Observation(("stale",), (), frozenset({"stale"}), 4),
        Observation((), (), frozenset(), 0),
    ]
    report = aggregate(data, 5)
    assert report["recall_at_5"] == 1.0 and report["mrr"] == 0.5
    assert report["precision_at_k"] == 0.2
    assert report["stale_memory_retrieval_rate"] == pytest.approx(2 / 3)
    assert report["unanswerable_empty_rate"] == 0.5
    assert report["unanswerable_abstention_accuracy"] is None
    assert stale_rate(0, 0) is None

from dataclasses import replace
import json

from agent_memory_lab.evaluation.benchmark import export, run_benchmark
from agent_memory_lab.evaluation.datasets import JUN, MAR, generate_dataset
from agent_memory_lab.memory.manager import MemoryManager
from agent_memory_lab.storage.sqlite_store import SQLiteStore


def test_seed_sizes_and_labels():
    first = generate_dataset(seed=42)
    assert len(first.facts) == 200 and len(first.cases) == 50
    assert len({case.category for case in first.cases}) == 6
    assert first.to_json() == generate_dataset(seed=42).to_json()
    assert first.to_json() != generate_dataset(seed=43).to_json()
    ids = {fact.id for fact in first.facts}
    assert all(id_ in ids for case in first.cases for id_ in case.gold_ids)
    assert all(not case.gold_ids for case in first.cases if case.category == "Unanswerable")


def test_pipeline_and_label_independence(tmp_path, monkeypatch):
    def forbid_io(*args, **kwargs):
        raise AssertionError("Optional LLM network I/O is forbidden")

    monkeypatch.setattr("agent_memory_lab.providers.llm.urlopen", forbid_io)
    manager = MemoryManager(SQLiteStore(tmp_path / "pipeline.sqlite3"), "user", "agent")
    initial, = manager.import_turn("项目使用 SQLite 数据库。", effective_at=MAR)
    active, = manager.import_turn("项目数据库已经从 SQLite 改成 PostgreSQL。", effective_at=JUN)
    assert manager.search_memories("项目数据库", as_of=MAR)[0].id == initial.id
    assert manager.search_memories("项目数据库", as_of=JUN)[0].id == active.id

    dataset = generate_dataset(size=58)
    case = next(item for item in dataset.cases if item.category == "Exact Fact")
    decoy = next(item.id for item in dataset.facts if item.id not in case.gold_ids)
    sample = replace(dataset, cases=(case,))
    recorded = []
    from agent_memory_lab.retrieval.base import Retriever
    original_search = Retriever.search

    def capture(self, query, *args, **kwargs):
        results = original_search(self, query, *args, **kwargs)
        if case.query == query:
            recorded.append(tuple((row.id, row.score) for row in results))
        return results

    monkeypatch.setattr(Retriever, "search", capture)
    report = run_benchmark(sample)
    ranked = list(recorded)
    recorded.clear()
    run_benchmark(replace(sample, cases=(replace(case, gold_ids=(decoy,)),)))
    assert ranked == recorded and len(ranked) == 8
    assert {row["status"] for row in report["results"]} == {"completed"}
    export(report, tmp_path)
    assert (tmp_path / "benchmark.csv").is_file()
    assert len(json.loads((tmp_path / "benchmark.json").read_text())["results"]) == 8

"""Run the offline ranking experiment and export real measurements."""

import argparse
from collections import defaultdict
import csv
import json
from pathlib import Path
import platform
import sqlite3
from tempfile import TemporaryDirectory
from time import perf_counter

import numpy as np
import psutil

from ..memory.manager import MemoryManager
from ..models import Strategy
from ..providers.embedding import MockEmbedding
from ..retrieval import RETRIEVERS
from ..storage.sqlite_store import SQLiteStore
from .datasets import DEFAULT_SEED, DEFAULT_SIZE, OCT, Dataset, generate_dataset
from .metrics import Observation, aggregate

USER = "synthetic-user"
AGENT = "synthetic-agent"
TOP_K = 5


def run_benchmark(dataset: Dataset, top_k: int = TOP_K) -> dict:
    if type(top_k) is not int or not 5 <= top_k <= 1000:
        raise ValueError("Benchmark top_k must be in [5, 1000] to report recall@5")
    begin = perf_counter()
    process = psutil.Process()
    initial_rss = peak_rss = process.memory_info().rss
    results = []
    with TemporaryDirectory(prefix="memory-benchmark-") as directory:
        for strategy in Strategy:
            store = SQLiteStore(Path(directory) / f"{strategy.value}.sqlite3")
            manager = MemoryManager(store, USER, AGENT, strategy)
            ingest = perf_counter()
            for fact in dataset.facts:
                recorded = manager.add_memory(fact.candidate, memory_id=fact.id,
                                              recorded_at=fact.recorded_at,
                                              source_id=fact.id, session_id="benchmark")
                if recorded.id != fact.id:
                    raise ValueError("Synthetic source unexpectedly deduplicated")
            ingest_seconds = perf_counter() - ingest
            with store.transaction() as db:
                index_rows = db.execute("SELECT COUNT(*) FROM memory_versions").fetchone()[0]
            for name, factory in RETRIEVERS.items():
                retriever = factory(store, MockEmbedding()) if name in ("Vector", "Hybrid") else factory(store)
                options = {"top_k": top_k, "user_id": USER, "agent_id": AGENT}
                retriever.search("calibration audit warmup", as_of=OCT, **options)
                buckets = defaultdict(list)
                observations = []
                start = perf_counter()
                for case in dataset.cases:
                    query_start = perf_counter()
                    ranked = retriever.search(case.query, as_of=case.as_of, **options)
                    elapsed = (perf_counter() - query_start) * 1000
                    stale = frozenset(memory_id for memory_id, end in dataset.stale_after.items()
                                      if end <= case.as_of)
                    observation = Observation(tuple(row.id for row in ranked),
                                              case.gold_ids, stale, elapsed)
                    observations.append(observation)
                    buckets[case.category].append(observation)
                    peak_rss = max(peak_rss, process.memory_info().rss)
                results.append({
                    "status": "completed",
                    "memory_count": len(dataset.facts),
                    "seed": dataset.seed,
                    "top_k": top_k,
                    "strategy": strategy.value,
                    "retriever": name,
                    "index_rows": index_rows,
                    "ingest_seconds": ingest_seconds,
                    "elapsed_seconds": perf_counter() - start,
                    **aggregate(observations, top_k),
                    "by_category": {category: aggregate(items, top_k)
                                    for category, items in sorted(buckets.items())},
                })
    return {
        "status": "completed",
        "environment": {"os": platform.system(), "release": platform.release(),
                        "architecture": platform.machine(), "python": platform.python_version(),
                        "sqlite": sqlite3.sqlite_version, "numpy": np.__version__, "device": "CPU"},
        "memory_count": len(dataset.facts),
        "seed": dataset.seed,
        "query_count": len(dataset.cases),
        "top_k": top_k,
        "elapsed_seconds": perf_counter() - begin,
        "initial_rss_mib": initial_rss / 2 ** 20,
        "peak_sampled_rss_mib": peak_rss / 2 ** 20,
        "results": results,
    }


def export(report: dict, directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "benchmark.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    rows = [
        {**{k: v for k, v in result.items() if k != "by_category"}, **report["environment"]}
        for result in report["results"]
    ]
    with (directory / "benchmark.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size", type=int, default=DEFAULT_SIZE)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--top-k", type=int, default=TOP_K)
    parser.add_argument("--output", type=Path, default=Path("reports"))
    parser.add_argument("--dataset-out", type=Path)
    args = parser.parse_args()
    dataset = generate_dataset(args.size, args.seed)
    report = run_benchmark(dataset, args.top_k)
    export(report, args.output)
    if args.dataset_out is not None:
        args.dataset_out.parent.mkdir(parents=True, exist_ok=True)
        args.dataset_out.write_text(dataset.to_json(), encoding="utf-8", newline="\n")
    print(f"{report['status']}: {len(report['results'])} runs, "
          f"{report['query_count']} queries per run, {report['elapsed_seconds']:.2f} s")


if __name__ == "__main__":
    main()

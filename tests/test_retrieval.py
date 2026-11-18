from datetime import UTC, datetime

import numpy as np
import pytest

from agent_memory_lab.memory.manager import MemoryManager
from agent_memory_lab.models import Candidate, MemoryType, Status
from agent_memory_lab.providers.embedding import LocalEmbeddingProvider
from agent_memory_lab.retrieval import RETRIEVERS
from agent_memory_lab.retrieval.hybrid import reciprocal_rank_fusion
from agent_memory_lab.retrieval.vector import VectorRetriever
from agent_memory_lab.storage.sqlite_store import SQLiteStore


@pytest.fixture
def corpus(tmp_path):
    db = SQLiteStore(tmp_path / "db.sqlite3")
    manager = MemoryManager(db, "u", "a")
    jan = datetime(2025, 1, 1, tzinfo=UTC)
    jun = datetime(2025, 6, 1, tzinfo=UTC)
    old, = manager.import_turn("项目使用 SQLite 数据库。", effective_at=jan, recorded_at=jan)
    new, = manager.import_turn("项目数据库已经从 SQLite 改成 PostgreSQL。",
                               effective_at=jun, recorded_at=jun)
    for user, agent in [("other", "a"), ("u", "other")]:
        MemoryManager(db, user, agent).add_memory(Candidate("外部数据库", MemoryType.SEMANTIC))
    return db, old, new, jan, jun


@pytest.mark.parametrize("name", RETRIEVERS)
def test_search_filters_language_and_boundaries(corpus, name):
    db, old, new, jan, jun = corpus
    search = RETRIEVERS[name](db).search
    scoped = dict(user_id="u", agent_id="a")
    assert [item.id for item in search('数据库 "OR":* -', **scoped)] == [new.id]
    historic, = search("数据库", as_of=jan, **scoped)
    assert historic.id == old.id and historic.memory.status == Status.SUPERSEDED
    assert [item.id for item in search("数据库", as_of=jun, **scoped)] == [new.id]
    assert search("数据库", memory_type=MemoryType.EPISODIC, **scoped) == []
    assert search("", **scoped) == search("数据库", top_k=0, **scoped) == []
    assert search("数据库", user_id="missing") == []
    with pytest.raises(ValueError):
        search("数据库", top_k=-1)
    with pytest.raises(ValueError):
        search("数据库", top_k=1001)
    revisions = search("数据库", include_history=True, **scoped)
    assert {(result.id, result.memory.version) for result in revisions} == {
        (old.id, 1), (old.id, 2), (new.id, 1)
    }


def test_bm25_and_recent_ranking(tmp_path):
    db = SQLiteStore(tmp_path / "db.sqlite3")
    manager = MemoryManager(db, "u", "a")
    early = manager.add_memory(Candidate("搜索引擎 关键词", MemoryType.SEMANTIC),
                               recorded_at=datetime(2025, 1, 1, tzinfo=UTC))
    late = manager.add_memory(Candidate("向量索引", MemoryType.SEMANTIC))
    assert RETRIEVERS["Recent"](db).search("关键词")[0].id == late.id
    assert RETRIEVERS["BM25"](db).search("搜索引擎")[0].id == early.id
    assert RETRIEVERS["BM25"](db).search("quasar_missing") == []


def test_cosine_zero_vectors_and_rrf(tmp_path):
    db = SQLiteStore(tmp_path / "db.sqlite3")
    manager = MemoryManager(db, "u", "a")
    records = {text: manager.add_memory(Candidate(text, MemoryType.SEMANTIC))
               for text in ("A", "B", "zero")}

    class KnownEmbedding(LocalEmbeddingProvider):
        def embed(self, texts):
            vectors = {"A": [3, 3], "B": [50, 0], "zero": [0, 0], "query": [2, 0]}
            return np.asarray([vectors[text] for text in texts])

    result = VectorRetriever(db, KnownEmbedding()).search("query")
    assert [item.id for item in result] == [records["B"].id, records["A"].id]
    assert [item.score for item in result] == pytest.approx([1, 2 ** -0.5])
    a, b = records["A"], records["B"]
    ranked = reciprocal_rank_fusion([(a, 9), (b, 1)], [(b, 1)])
    assert ranked[0] == (b, pytest.approx(1 / 62 + 1 / 61))
    assert ranked[1] == (a, pytest.approx(1 / 61))

import json
from urllib.error import URLError

import pytest

from agent_memory_lab.extraction.llm_extractor import LLMExtractor
from agent_memory_lab.extraction.rule_extractor import RuleExtractor
from agent_memory_lab.models import MemoryType
from agent_memory_lab.providers.llm import LLMError, MockLLMProvider, OpenAICompatibleProvider


@pytest.mark.parametrize(("sentence", "kind"), [
    ("用户偏好简洁的 Python 示例。", MemoryType.PREFERENCE),
    ("项目使用 SQLite 数据库。", MemoryType.SEMANTIC),
    ("Agent 遇到 SQLite 锁冲突。", MemoryType.EPISODIC),
    ("Agent 成功执行备份。", MemoryType.EPISODIC),
    ("遇到锁冲突时，可以设置 busy_timeout。", MemoryType.PROCEDURAL),
])
def test_rule_types(sentence, kind):
    assert RuleExtractor().extract(sentence)[0].memory_type == kind


def test_replacement_and_unknown_text():
    extractor = RuleExtractor()
    assert extractor.extract("") == extractor.extract("早上好") == []
    fact, = extractor.extract("项目数据库已经从 SQLite 改成 PostgreSQL。")
    assert (fact.entity, fact.attribute, fact.value) == ("project", "database", "PostgreSQL")
    assert fact.replaces and fact.previous_value == "SQLite" and fact.valid_from is None


@pytest.mark.parametrize("response", ['{', '{"memories":[{}]}', '{"memories":[],"extra":1}'])
def test_llm_schema_invalid(response):
    with pytest.raises(LLMError, match="schema"):
        LLMExtractor(MockLLMProvider(response)).extract("dialogue")


def test_valid_llm_and_empty():
    fact = dict(content="Project uses SQLite", memory_type="semantic", entity="project",
                attribute="database", value="SQLite", replaces=False, previous_value=None,
                confidence=0.85)
    llm = LLMExtractor(MockLLMProvider(json.dumps({"memories": [fact]})))
    assert llm.extract(" ")[0:] == []
    assert llm.extract("dialogue")[0].confidence == 0.85


def test_no_key_means_no_request_and_timeout_retries(monkeypatch):
    calls = []

    def unavailable(*args, **kwargs):
        calls.append(kwargs["timeout"])
        raise URLError(TimeoutError())

    monkeypatch.setattr("agent_memory_lab.providers.llm.urlopen", unavailable)
    provider = OpenAICompatibleProvider("https://example.invalid", "mock", "", timeout=3, retries=1)
    with pytest.raises(LLMError, match="API_KEY"):
        LLMExtractor(provider).extract("dialogue")
    assert calls == []
    provider.api_key = "synthetic-placeholder"
    with pytest.raises(LLMError, match="timed out"):
        LLMExtractor(provider).extract("dialogue")
    assert calls == [3, 3]

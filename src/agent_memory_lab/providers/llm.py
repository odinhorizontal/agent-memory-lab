"""Optional OpenAI-compatible JSON completion with bounded retries."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from http.client import HTTPException
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class LLMError(RuntimeError):
    """The configured provider could not produce a response."""


class LocalLLMProvider(ABC):
    @abstractmethod
    def complete(self, system: str, text: str, schema: dict) -> str:
        """Return one structured response."""


@dataclass(slots=True)
class MockLLMProvider(LocalLLMProvider):
    response: str = '{"memories": []}'

    def complete(self, system: str, text: str, schema: dict) -> str:
        return self.response


@dataclass(slots=True)
class OpenAICompatibleProvider(LocalLLMProvider):
    base_url: str
    model: str
    api_key: str = field(repr=False)
    timeout: float = 15
    retries: int = 2

    @classmethod
    def from_env(cls) -> "OpenAICompatibleProvider":
        return cls(os.getenv("AML_LLM_BASE_URL", "https://api.openai.com/v1"),
                   os.getenv("AML_LLM_MODEL", ""), os.getenv("AML_LLM_API_KEY", ""),
                   float(os.getenv("AML_LLM_TIMEOUT", "15")),
                   int(os.getenv("AML_LLM_RETRIES", "2")))

    def complete(self, system: str, text: str, schema: dict) -> str:
        if not self.api_key.strip() or not self.model.strip():
            raise LLMError("Configure AML_LLM_API_KEY and AML_LLM_MODEL first")
        if not 0 < self.timeout <= 120 or not 0 <= self.retries <= 5:
            raise ValueError("Timeout must be in (0,120] and retries in [0,5]")
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": text}],
            "response_format": {"type": "json_schema", "json_schema": {
                "name": "memory_extraction", "strict": True, "schema": schema,
            }},
        }
        request = Request(self.base_url.rstrip("/") + "/chat/completions",
                          data=json.dumps(payload).encode("utf-8"),
                          headers={"Content-Type": "application/json",
                                   "Authorization": "Bearer " + self.api_key}, method="POST")
        for attempt in range(self.retries + 1):
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    content = json.load(response)["choices"][0]["message"]["content"]
                if not isinstance(content, str):
                    raise TypeError("Missing textual completion")
                return content
            except HTTPError as exc:
                exc.close()
                if attempt == self.retries or (exc.code not in (408, 429) and exc.code < 500):
                    raise LLMError(f"Completion returned HTTP {exc.code}") from None
            except (URLError, TimeoutError, ConnectionError, HTTPException):
                if attempt == self.retries:
                    raise LLMError("Completion connection failed or timed out") from None
            except (ValueError, KeyError, IndexError, TypeError):
                raise LLMError("Provider returned a malformed response envelope") from None
        raise AssertionError("Retry loop exhausted")

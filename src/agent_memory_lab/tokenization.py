"""Shared FTS and hashing tokenizer."""

from functools import lru_cache
import logging
import re
import unicodedata

import jieba

jieba.setLogLevel(logging.WARNING)
_WORDS = re.compile(r"[^\W_]+", re.UNICODE)
_CJK = re.compile(r"[\u3400-\u9fff\U00020000-\U0002fa1f]")


@lru_cache(maxsize=4096)
def tokenize(text: str) -> tuple[str, ...]:
    text = unicodedata.normalize("NFKC", text).casefold()
    segments = jieba.cut_for_search(text, HMM=False) if _CJK.search(text) else (text,)
    return tuple(word for segment in segments for word in _WORDS.findall(segment))

"""Streamlit entry point for the local research lab."""

from datetime import datetime
import json
from pathlib import Path
import sqlite3

from agent_memory_lab.config import database_path
from agent_memory_lab.memory.manager import MemoryManager
from agent_memory_lab.models import Strategy
from agent_memory_lab.storage.sqlite_store import SQLiteStore

import streamlit as st

from agent_memory_lab.ui import benchmark_page, memory_browser, retrieval_lab, timeline

ROOT = Path(__file__).resolve().parent
PAGES = ("Memory Browser", "Memory Timeline", "Retrieval Lab", "Benchmark Dashboard")


@st.cache_resource
def get_store(path: str) -> SQLiteStore:
    return SQLiteStore(path)


def load_demo(manager: MemoryManager) -> int:
    turns = json.loads((ROOT / "data" / "demo.json").read_text(encoding="utf-8"))
    for turn in turns:
        manager.import_turn(turn["text"], session_id="demo", source_id=turn["id"],
                            effective_at=datetime.fromisoformat(turn["effective_at"]))
    return len(turns)


def main() -> None:
    st.set_page_config(page_title="Agent Memory Lab", layout="wide")
    with st.sidebar:
        st.title("Agent Memory Lab")
        page = st.radio("页面", PAGES, label_visibility="collapsed")
        st.divider()
        st.subheader("记忆空间")
        user = st.text_input("User ID", "demo-user")
        agent = st.text_input("Agent ID", "demo-agent")
        strategy = st.selectbox("导入更新策略", (Strategy.VERSIONED, Strategy.APPEND_ONLY), format_func=str)
        load = st.button("导入合成演示", width="stretch")
    if page == "Benchmark Dashboard" and not load:
        benchmark_page.render(ROOT / "reports" / "benchmark.json")
        return
    try:
        manager = MemoryManager(get_store(str(database_path().resolve())), user.strip(),
                                agent.strip(), strategy)
        if load:
            st.sidebar.success(f"已处理 {load_demo(manager)} 条合成对话。")
    except (OSError, ValueError, sqlite3.Error) as exc:
        st.error(f"记忆空间初始化失败。{exc}")
        return
    if page == "Memory Browser":
        memory_browser.render(manager)
    elif page == "Memory Timeline":
        timeline.render(manager)
    elif page == "Retrieval Lab":
        retrieval_lab.render(manager)
    else:
        benchmark_page.render(ROOT / "reports" / "benchmark.json")


if __name__ == "__main__":
    main()

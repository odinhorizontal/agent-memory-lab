"""Browse and edit memory heads."""

from datetime import UTC, datetime, time
import sqlite3

import streamlit as st

from ..extraction.llm_extractor import LLMExtractor
from ..models import Candidate, Memory, MemoryType, Status
from ..providers.llm import LLMError, OpenAICompatibleProvider


def row(memory: Memory) -> dict:
    return {
        "Memory ID": memory.id,
        "Content": memory.content,
        "Type": memory.memory_type.value,
        "Status": memory.status.value,
        "Created (UTC)": memory.created_at,
        "Version": memory.version,
        "Source": memory.source_id,
        "待确认": memory.pending_conflict,
    }


def render(manager) -> None:
    st.title("Memory Browser")
    left, right = st.columns([2, 1])
    with left:
        kind = st.selectbox("记忆类型", [None, *MemoryType],
                            format_func=lambda item: str(item) if item else "全部")
    with right:
        show_history = st.toggle("显示归档与软删除", value=True)
    items = manager.list_memories(memory_type=kind, include_history=show_history)
    if items:
        st.dataframe([row(item) for item in items], hide_index=True, width="stretch")
    else:
        st.info("当前没有匹配的记忆。")

    with st.expander("添加记忆"):
        mode = st.selectbox("输入方式", ["手动", "规则提取", "LLM 提取"])
        with st.form("create-memory", clear_on_submit=True):
            content = st.text_area("内容或单轮对话")
            selected_type = st.selectbox("新记忆类型", list(MemoryType)) if mode == "手动" else None
            source = st.text_input("来源 ID（可选）")
            day = st.date_input("生效日期（可选，UTC 00:00）", value=None)
            effective_at = datetime.combine(day, time.min, UTC) if day is not None else None
            if st.form_submit_button("添加"):
                try:
                    if mode == "手动":
                        manager.add_memory(Candidate(content, selected_type, valid_from=effective_at),
                                           source_id=source or None)
                        st.rerun()
                    extractor = (LLMExtractor(OpenAICompatibleProvider.from_env())
                                 if mode == "LLM 提取" else None)
                    captured = manager.import_turn(content, source_id=source or None,
                                                   extractor=extractor, effective_at=effective_at)
                    if captured:
                        st.rerun()
                    st.info("此输入没有提取到记忆。")
                except (ValueError, LLMError, sqlite3.Error) as exc:
                    st.error(str(exc))

    if not items:
        return
    display = {item.id: item for item in items}
    current_id = st.selectbox("选择记忆", list(display),
                              format_func=lambda item: f"{item[:8]} · {display[item].content[:70]}")
    current = display[current_id]
    if current.status == Status.ACTIVE:
        with st.form(f"edit-{current.id}-{current.version}"):
            edited = st.text_area("编辑内容", current.content)
            value = st.text_input("事实值", current.value) if current.value is not None else None
            save, delete = st.columns(2)
            save_clicked = save.form_submit_button("保存新版本")
            delete_clicked = delete.form_submit_button("软删除")
            try:
                if save_clicked:
                    manager.update_memory(current.id, content=edited, value=value,
                                          expected_version=current.version)
                    st.rerun()
                if delete_clicked:
                    manager.delete_memory(current.id, expected_version=current.version)
                    st.rerun()
            except (KeyError, ValueError, sqlite3.Error) as exc:
                st.error(str(exc))
    elif current.status == Status.DELETED and st.button("恢复最近版本"):
        try:
            manager.restore_memory(current.id)
            st.rerun()
        except (KeyError, ValueError, sqlite3.Error) as exc:
            st.error(str(exc))

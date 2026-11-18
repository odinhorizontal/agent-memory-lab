"""Run the same query through four retrievers."""

from datetime import UTC, datetime, time

import streamlit as st

from ..models import MemoryType
from ..retrieval import RETRIEVERS


def render(manager) -> None:
    st.title("Retrieval Lab")
    query = st.text_input("问题", "项目现在使用什么数据库？")
    controls = st.columns(3)
    top_k = controls[0].slider("Top K", 1, 20, 5)
    kind = controls[1].selectbox("记忆类型", [None, *MemoryType],
                                 format_func=lambda item: str(item) if item else "全部")
    day = controls[2].date_input("历史日期（可选，UTC 00:00）", value=None)
    include_history = st.checkbox("浏览全部审计版本", disabled=day is not None)
    point = datetime.combine(day, time.min, UTC) if day is not None else None
    if not query.strip():
        return
    columns = st.columns(2)
    for index, (name, factory) in enumerate(RETRIEVERS.items()):
        with columns[index % 2]:
            st.subheader(name)
            ranked = factory(manager.store).search(query, top_k, manager.user_id, manager.agent_id,
                                                   kind, point, include_history)
            if not ranked:
                st.caption("无匹配结果")
                continue
            st.dataframe([{
                "Rank": item.rank, "Content": item.memory.content, "Score": item.score,
                "Memory ID": item.id, "Type": str(item.memory.memory_type),
                "Status": str(item.memory.status), "Version": item.memory.version,
            } for item in ranked], hide_index=True, width="stretch")

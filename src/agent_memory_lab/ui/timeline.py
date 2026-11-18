"""Inspect fact-valid time, recorded operations, and version links."""

from dataclasses import asdict
from datetime import UTC, date, datetime, time, timedelta

import plotly.express as px
import streamlit as st

from ..models import now
from .memory_browser import row


def render(manager) -> None:
    st.title("Memory Timeline")
    day = st.date_input("历史日期（UTC 00:00）", value=date(2025, 3, 1))
    if day is not None:
        records = manager.list_memories(as_of=datetime.combine(day, time.min, UTC))
        if records:
            st.dataframe([row(item) for item in records], hide_index=True, width="stretch")
        else:
            st.info("该日期没有有效的记忆。")

    heads = manager.list_memories(include_history=True)
    if not heads:
        st.info("导入合成演示后可以查看 SQLite → PostgreSQL 变更。")
        return
    st.subheader("数据有效期")
    windows = []
    for head in heads:
        for revision in manager.get_memory_history(head.id):
            item = revision.memory
            if revision.visible and item.valid_from is not None:
                end = item.valid_to or max(now(), item.valid_from + timedelta(days=1))
                windows.append({"Memory": item.content[:65], "开始": item.valid_from,
                                "结束": end, "状态": str(item.status),
                                "ID": item.id, "版本": item.version,
                                "终止": "开放" if item.valid_to is None else "已知"})
    if windows:
        figure = px.timeline(windows, x_start="开始", x_end="结束", y="Memory", color="状态",
                             hover_data=["ID", "版本", "终止"], template="plotly_white")
        figure.update_yaxes(autorange="reversed", title=None)
        figure.update_layout(height=min(560, 160 + 45 * len(windows)), xaxis_title="有效时间（UTC）")
        st.plotly_chart(figure, width="stretch")

    by_id = {item.id: item for item in heads}
    selected = st.selectbox("审计记忆", list(by_id),
                            format_func=lambda item: f"{by_id[item].content[:62]} · {item[:8]}")
    history = manager.get_memory_history(selected)
    st.subheader("版本历史")
    st.dataframe([{**row(snap.memory), "Valid from": snap.memory.valid_from,
                   "Valid to": snap.memory.valid_to, "参与有效期查询": snap.visible}
                  for snap in history], hide_index=True, width="stretch")
    events, relations = manager.get_memory_activity(selected)
    st.subheader("操作事件")
    st.dataframe([asdict(item) for item in events], hide_index=True, width="stretch")
    st.subheader("记忆关系")
    if relations:
        st.dataframe([asdict(item) for item in relations], hide_index=True, width="stretch")
    else:
        st.caption("该记忆暂无关系。")

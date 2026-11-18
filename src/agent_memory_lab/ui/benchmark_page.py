"""Plot saved measurements from a completed benchmark run."""

import json
from pathlib import Path

import plotly.express as px
import streamlit as st

RANKING = {"recall_at_1": "Recall@1", "recall_at_3": "Recall@3",
           "recall_at_5": "Recall@5", "mrr": "MRR", "precision_at_k": "Precision@K"}
LATENCY = {"p50_latency_ms": "p50", "p95_latency_ms": "p95"}
STALE = {"stale_memory_retrieval_rate": "Stale rate"}
COLORS = {"append-only": "#7b65af", "versioned-update": "#1e725e"}


def _chart(rows: list[dict], metrics: dict[str, str], title: str, scale: str, key: str) -> None:
    values = [
        {"Retriever": row["retriever"], "Strategy": row["strategy"], "Metric": label,
         "Value": row[metric]}
        for row in rows for metric, label in metrics.items() if row.get(metric) is not None
    ]
    if not values:
        return
    figure = px.bar(values, x="Retriever", y="Value", color="Strategy", facet_col="Metric",
                    barmode="group", template="plotly_white", color_discrete_map=COLORS,
                    labels={"Value": scale}, title=title)
    figure.for_each_annotation(lambda annotation: annotation.update(
        text=annotation.text.partition("=")[2]))
    figure.update_layout(height=360, legend_title_text=None)
    figure.update_xaxes(title=None)
    if scale == "比例":
        figure.update_yaxes(tickformat=".0%")
    st.plotly_chart(figure, width="stretch", key=key)


def render(path: Path) -> None:
    st.title("Benchmark Dashboard")
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        st.info("运行 python -m agent_memory_lab.evaluation.benchmark 生成报告。")
        return
    if report.get("status") != "completed":
        st.warning("当前报告尚未完成。")
        return
    a, b, c, d = st.columns(4)
    a.metric("合成记忆", report["memory_count"])
    b.metric("查询", report["query_count"])
    c.metric("随机种子", report["seed"])
    d.metric("运行时间", f"{report['elapsed_seconds']:.2f} s")
    rows = report["results"]
    categories = sorted(rows[0]["by_category"])
    category = st.selectbox("查询类别", ["全部", *categories])
    if category != "全部":
        rows = [{"retriever": item["retriever"], "strategy": item["strategy"],
                 **item["by_category"][category]} for item in rows]
    ranking = {**RANKING, "precision_at_k": f"Precision@{report['top_k']}"}
    _chart(rows, ranking, "证据检索质量", "比例", "ranking")
    _chart(rows, LATENCY, "查询延迟", "毫秒", "latency")
    _chart(rows, STALE, "过期证据误召回率", "比例", "stale")
    if category in ("全部", "Unanswerable"):
        st.caption("无答案题的空结果率记录排名输出情况。拒答准确率未评估。")
        st.dataframe([{
            "Retriever": item["retriever"], "Strategy": item["strategy"],
            "无答案题空结果率": item["unanswerable_empty_rate"],
        } for item in rows], hide_index=True, width="stretch")
    st.caption("合成数据与 MockEmbedding 的结果用于工程验证和相对比较。")

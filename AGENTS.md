# Agent Memory Lab

本项目研究离线、可审计的 Agent 长期记忆。Python 源码位于 src/agent_memory_lab，四个 Streamlit 页面由 app.py 组织。使用 SQLite 事务、FTS5 和 NumPy，测试数据全部合成。

使用 Python 3.11+、pathlib、UTC 感知时间、类型标注和 pytest。运行 python -m pytest。CPU 计算库线程参数设为 4，禁用默认 CUDA 可见设备，默认评测 200 条记忆和 50 个问题，规模上限 1000 条。保持 API 可离线测试。

每个主要阶段独立提交。排除密钥、个人数据、运行时 SQLite 文件和模型权重。保持策略对比使用同一语料、查询、过滤和 top_k，gold 标签仅供评测。详见 reports/progress.md 和 reports/final_report.md。模型压缩和 GPU 适配列入后续研究。

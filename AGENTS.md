# Agent Memory Lab

用轻量离线研究平台比较 Agent 记忆的提取、生命周期和证据检索。维持 Python 3.11+ 和 Windows/Linux 兼容。

## 项目布局

- src/agent_memory_lab/extraction 和 providers 定义 Rule/LLM/Embedding 接口和 Mock。
- src/agent_memory_lab/memory 和 storage 定义用户、Agent 和事实作用域内的事务、版本、事件、关系及 SQLite FTS5。
- src/agent_memory_lab/retrieval 提供 Recent、BM25、Vector 和 RRF Hybrid。
- src/agent_memory_lab/evaluation 生成固定种子的合成集，度量排名并导出报告。app.py 和 ui 提供 Streamlit 导航和四个页面。
- tests 包含离线 pytest，data 仅存放合成数据，reports/progress.md 是当前交接点。

## 开发约束

使用 pathlib 和带时区的 UTC 时间。检查 [valid_from, valid_to) 边界、版本审计和事务回滚。用 scoped MemoryManager 执行应用写入。优先维护原始证据和已发布的接口。新增检索行为时覆盖空查询、历史时点和租户隔离。

安装与测试使用 python -m pip install -r requirements.txt 和 python -m pytest。在 Windows 也可以运行 scripts/test.ps1。依赖安装后核心测试无需网络、真实 Key 或 GPU。

保持 CPU 默认设置。计算库并行度设为 4，默认禁用 CUDA 和 tokenizer 并行。Benchmark 默认 200 条记忆、50 道题，最多 1000 条记忆。保持实验有界，避免长期服务和模型下载。

## 评测与 Git

每次对比复用同一合成语料、查询、时点、过滤和 top_k。检索器只接收文本和过滤参数，gold 与 stale 标签仅提供给评测。记录真实环境、时长、分母和状态。维持独立阶段提交并检查 diff。提交前排除密钥、私有数据、数据库、模型权重、虚拟环境和缓存。使用正常分支和 Pull Request 流程。

本地 Qwen、4090 适配、真实 Embedding 评测和语义压缩仍属后续工作。结果和验证环境见 reports/final_report.md。

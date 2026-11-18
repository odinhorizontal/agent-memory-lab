# Agent Memory Lab

Agent Memory Lab 是一个轻量级研究平台，用来观察 Agent 如何从历史对话提取长期记忆、处理事实变更，以及不同更新和检索策略如何影响证据召回。

## 功能

- 从单轮对话提取四类记忆。默认规则模式离线运行，可选 OpenAI 兼容结构化提取。
- 按用户和 Agent 划分记忆空间，支持去重、软删除、恢复、合并摘要、冲突标记和版本审计。
- 比较 Append-only 和 Versioned-update，支持按 UTC 生效时间检索。
- 对比 Recent、BM25、Vector、Hybrid，使用固定种子的合成数据复现实验。
- 提供 Streamlit 记忆浏览、时间线、检索实验室和 Benchmark 仪表板。

## 架构

规则或 LLM 提取器生成结构化候选。MemoryManager 在 SQLite 事务中记录版本、事件和关系。检索器共用有效期过滤和权限作用域，Streamlit 展示检索与评测结果。见 [架构文档](docs/architecture.md) 和 [研究笔记](docs/research_notes.md)。

## 安装

建议 Python 3.11，最低版本 3.11。Python 所带的 SQLite 需要支持 FTS5。在仓库根目录运行以下命令。

```bash
python -m pip install -r requirements.txt
python -m pytest
```

## 快速开始

```bash
python -m streamlit run app.py
```

打开 [本地应用](http://127.0.0.1:8501)，在侧栏选择 **导入合成演示**。在 Memory Timeline 中比较 2025-03-01 和 2025-06-01，项目数据库应分别显示 SQLite 和 PostgreSQL。在 Retrieval Lab 中输入“项目使用什么数据库？”，可用历史日期切换结果。要独立演示 Append-only，请换一个 User ID 或 Agent ID 后再导入。

默认 SQLite 路径为 `local/memory.sqlite3`。环境变量 `AML_DB_PATH` 可指定其他文件。LLM 提取仅在表单选择该模式并提交时使用。环境变量见 [.env.example](.env.example)，由运行环境加载。OpenAI 兼容接口须支持 `json_schema` 响应格式。

## Windows PowerShell

安装 Python 3.11，打开仓库根目录。若 Python 不在 PATH，将其可执行文件路径传给 `setup.ps1 -Python`。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start.ps1
```

可在启动前设置 `$env:AML_DB_PATH = "local/demo.sqlite3"`。启动脚本支持 `-Port 8502`。

## Codex Cloud 开发

在 Linux 仓库工作分支上使用 Python 3.11 安装依赖，运行 pytest 和 Benchmark。用 Streamlit AppTest 检查页面，无需本地 GUI。安装后核心模式可离线运行，无需 Docker、WSL、外部数据库、GPU 或模型权重。使用分阶段提交，交接点见 [开发进度](reports/progress.md)。

## 记忆类型

| 类型 | 示例 |
| --- | --- |
| Semantic | 项目采用 PostgreSQL |
| Episodic | Agent 遇到 SQLite 锁冲突 |
| Procedural | 处理锁冲突时检查事务持有时间 |
| Preference | 用户偏好简洁的 Python 示例 |

## 检索方法

| 方法 | 实现 |
| --- | --- |
| Recent | 按版本所属记忆的创建时间取最近的 K 条有效记录 |
| BM25 | SQLite FTS5，查询和写入都用 jieba 中文分词 |
| Vector | 用固定词项哈希向量进行 NumPy 余弦排序 |
| Hybrid | 对 BM25 与 Vector 的排名使用 RRF，常数 60 |

API 的 `as_of` 接受带时区的时间。生效区间为 [valid_from, valid_to)。不传时间时默认检索当前有效记录。显式审计模式可查看所有版本。语义改写表现受词项重叠和哈希碰撞影响。

## Benchmark

```bash
python -m agent_memory_lab.evaluation.benchmark --size 200 --seed 42 --top-k 5 --dataset-out data/benchmark.json
```

默认有 200 条合成输入和 50 道查询，包含精确事实、语义改写、时间更新、冲突、多跳和无答案。两种更新策略分别构建索引，检索器使用相同文本、时点、范围和 K。查看 [最终报告](reports/final_report.md)、[JSON 结果](reports/benchmark.json) 或 [CSV 结果](reports/benchmark.csv)。随机种子固定语料和问题，延迟随运行环境变化。

## 运行测试

```bash
python -m pytest
python -m pytest tests/test_conflict.py tests/test_retrieval.py
```

测试使用临时数据库和合成输入。可选 LLM 调用通过 Mock 和超时替身验证。

## 资源使用

默认 CPU 模式。OMP、MKL、OpenBLAS、NumExpr 并行度环境变量设为 4，禁用 tokenizer 并行和默认 CUDA 可见设备。这些变量设置计算库并行度。Benchmark 最大 1000 条输入，运行结束后清理临时数据库。

## 局限

规则提取覆盖明确的双语模式，时间由调用方提供。检索和评测针对事实生效时间，不提供按审计获知时间回放、搜索认证、自动拒答或多跳查询规划。MockEmbedding 的实验结果只用于工程正确性和相对比较。界面默认只监听本机。

## 后续开发

通过 LocalLLMProvider 接入本地 Qwen 3B–8B，使用显式 CPU 或 RTX 4090 设备配置。通过 LocalEmbeddingProvider 对比真实双语向量，通过 MemoryCompressionProvider 实验压缩，随后验证时间衰减、Skill 自动提取和基于记忆的问答。

使用 [MIT License](LICENSE)。

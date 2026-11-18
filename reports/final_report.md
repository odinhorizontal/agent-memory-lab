# Agent Memory Lab · MVP 交付报告

## A. 完成情况

完成双语规则提取、可选 OpenAI 兼容提取、四类记忆管理、Append-only 和 Versioned-update、按生效时间查询、四种检索器、离线 Benchmark 和四页 Streamlit 应用。合并摘要使用确定性 Mock，事件和关系可追溯到具体版本。

本机验证了 Windows 11、Python 3.12.14。可选 LLM 使用 Mock 和连接错误替身验证，未使用真实 API。未执行 GPU、真实模型、训练、负载持续测试或真实聊天数据实验。

## B. 架构

MemoryExtractor 接收对话文本与已知生效时间。MemoryManager 分配作用域，并用 SQLite 事务保存版本、事件、FTS 索引和替代关系。四种 Retriever 通过同一 Search API 使用生效时间和记忆类型过滤。Streamlit 连接同一个管理 API，并读取真实 Benchmark JSON 画图。详见 [架构文档](../docs/architecture.md)。

## C. 测试

| 检查 | 实际结果 |
| --- | --- |
| pytest | 共 36 项，36 通过，0 失败，0 跳过 |
| 离线验证 | Windows 测试进程禁止外部套接字连接与 DNS，允许事件循环使用回环地址，清除 LLM Key |
| 依赖 | 干净 venv 安装通过，pip check 通过 |
| UI | Streamlit AppTest 检查四页。独立服务器启动后健康端点返回 HTTP 200，随后停止 |

```bash
python -m pip install -r requirements.txt
python -m pytest
python -m pytest tests/test_ui.py
python -m streamlit run app.py
```

## D. Benchmark 实测

固定 seed 42，200 条合成输入，50 道查询，top_k=5。两种更新策略各运行 Recent、BM25、Vector 和 Hybrid，共发出 400 次计时查询。

| 策略 | 检索器 | Recall@1 | Recall@3 | Recall@5 | MRR | Precision@5 | p50 ms | p95 ms | 过期率 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Append-only | Recent | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.78 | 2.05 | 0.0% |
| Append-only | BM25 | 0.545 | 0.955 | 0.977 | 0.826 | 0.255 | 2.08 | 2.85 | 3.2% |
| Append-only | Vector | 0.750 | 0.795 | 0.909 | 0.936 | 0.232 | 4.39 | 4.64 | 3.2% |
| Append-only | Hybrid | 0.614 | 0.932 | 0.932 | 0.879 | 0.236 | 5.28 | 6.38 | 3.2% |
| Versioned-update | Recent | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 2.49 | 2.80 | 0.0% |
| Versioned-update | BM25 | 0.477 | 0.955 | 0.977 | 0.784 | 0.255 | 2.78 | 3.02 | 0.0% |
| Versioned-update | Vector | 0.750 | 0.795 | 0.909 | 0.936 | 0.232 | 4.32 | 4.89 | 0.0% |
| Versioned-update | Hybrid | 0.614 | 0.932 | 0.932 | 0.879 | 0.236 | 5.03 | 5.72 | 0.0% |

排名指标对 44 道可答题按查询取宏平均。Recall@K 的分母为该题的全部 gold 证据，Precision@K 的分母为 K，MRR 在实际返回的列表中计算。延迟是 SQLite 查询、过滤和排名的单次耗时，包含全部 50 道题，排除写入、预热和评测统计。每组排序前预热一次。

过期率是查询时点已经达到标注失效时间的返回证据条数除以该组全部已返回证据条数。没有任何返回时记为 null。Append-only 下，三个内容检索器各返回 8/250 条过期证据。Versioned-update 的对应计数均为 0/250。Recent 当前参数下未召回任何 gold，所以零过期率不能单独表示高检索质量。

6 道无答案题单独计算空结果率，八组均为 0%。拒答准确率为 null，排名器没有拒答决策。两种更新策略接收相同输入，经写入后索引分别有 200 和 206 个修订行，且有效事实集合不同。因此结果对比包含更新策略对候选和词频统计的影响。

语料、词项哈希向量和规则都是工程实验用 Mock。结果仅适用于该合成集。详见 [原始 JSON](benchmark.json)、[CSV](benchmark.csv) 和 [合成输入与标签](../data/benchmark.json)。

## E. 资源

Windows 11 AMD64、Python 3.12.14、SQLite 3.53.1、NumPy 2.5.5，CPU 模式。Benchmark 总耗时 6.91 秒，包含导入和预热。进程 RSS 起始 37.61 MiB，查询后采样的最大值 41.45 MiB。采样值用于本轮观察，连续峰值和 UI 内存未测。计算库并行度环境变量设为 4。

## F. Windows 运行

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start.ps1
```

打开 [本地应用](http://127.0.0.1:8501)，用默认 Versioned-update 导入合成演示。时间线分别选择 2025-03-01 与 2025-06-01 验证前后事实。Benchmark 可从仓库根目录重新生成。

```powershell
.\.venv\Scripts\python.exe -m agent_memory_lab.evaluation.benchmark --dataset-out data/benchmark.json
```

## G. 后续开发

- 在独立可选依赖组中接入本地 Qwen 3B–8B，为提取、冲突建议、摘要和问答使用同一结构化接口。
- 为 RTX 4090 增加显式设备选择，启动配置优先隔离推理进程，并用小批次记录显存、时延与错误恢复。默认流程继续用 CPU。
- 将候选摘要接入 MemoryCompressionProvider，检查证据引用、压缩比和摘要后的召回损失。
- 用开发集比较记忆时间衰减和 Skill 自动提取，保留跨会话证据链及人工复核。
- 新增真实双语 Embedding Benchmark，在冻结的评测集比较改写、跨语言和多证据召回。

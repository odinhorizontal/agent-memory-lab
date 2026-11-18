# 研究笔记

| 来源 | 借鉴与 MVP 取舍 |
| --- | --- |
| [Mem0 项目](https://github.com/mem0ai/mem0)、[记忆实现](https://github.com/mem0ai/mem0/blob/main/mem0/memory/main.py)、[论文](https://arxiv.org/abs/2504.19413) | 分离事实提取与记忆写入，比较追加和显式更新。关系边保留替代及归并来源，混合检索采用 RRF。 |
| [EverMemOS 项目](https://github.com/EverMind-AI/EverMemOS)、[论文](https://arxiv.org/abs/2601.02163) | 论文区分情景痕迹形成、语义整合与按需重建。这里用规则分类、显式归并和有效期检索进行缩小的实验。项目入口重定向到 EverOS，原版本的实现细节以论文为准。 |
| [MemOS 项目](https://github.com/MemTensor/MemOS)、[MOSCore](https://github.com/MemTensor/MemOS/blob/main/src/memos/mem_os/core.py) | 统一 CRUD 和检索接口，按用户和 Agent 隔离。显式编辑作为人工反馈，MVP 采用单库文本存储。 |
| [A-MEM 项目](https://github.com/agiresearch/A-mem)、[记忆实现](https://github.com/agiresearch/A-mem/blob/main/agentic_memory/memory_system.py)、[论文](https://arxiv.org/abs/2502.12110) | 类型化记忆卡片、关联和修订。MVP 只创建有操作依据的关系边。参考代码的记忆卡片元数据与关联入口。 |
| [Memory-R1](https://arxiv.org/abs/2508.19828) | 用可审计的 ADD、UPDATE、DELETE 和去重来显式表达管理策略。 |
| [LongMemEval](https://arxiv.org/abs/2410.10813)、[LoCoMo](https://arxiv.org/abs/2402.17753) | 参考时间关系、知识更新、跨记忆证据和无答案题型。MVP 单独测证据排序，并保留多个 gold 证据。 |

公开论文和项目的性能数字属于作者报告。实验关注显式更新能否减少过期证据进入 top-k，历史证据能否在生效日期正确召回，以及词项检索和 RRF 在改写与多证据题型上的差异。未纳入训练、向量数据库、自动图演化、生成答案评分或论文基准复现。

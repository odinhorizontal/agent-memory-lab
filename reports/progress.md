# 开发进度

- P0 调研并建立 Python 包、测试配置和 PowerShell 入口。干净的 Windows 虚拟环境安装成功。Python 3.12.14 的 SQLite 3.53.1 支持 FTS5。
- P1 SQLite 存储通过事务回滚、审计、作用域和 FTS5 检查。
- P2 完成规则和 Mock 结构化提取、去重、冲突、版本和恢复。验证 SQLite → PostgreSQL 的 UTC 边界。
- P3 Recent、BM25、Vector、Hybrid 通过排序、历史、隔离与边界检查。
- P4 导出 seed 42 的 200 条输入、50 道题和 8 组实测结果。通过指标准确性和换标不改变排名的测试。
- P5 四个 Streamlit 页面通过 AppTest。独立启动服务，HTTP 健康端点返回 200 后结束进程。
- P6 Windows 11 上阻止外部网络连接后，36 个测试全部通过。完成安装文档、架构说明与 [最终报告](final_report.md)。交接时可从报告复现实验。

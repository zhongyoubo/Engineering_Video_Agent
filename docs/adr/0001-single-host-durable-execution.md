# ADR-0001：首版使用单机持久化队列

状态：接受，作用于本次交付 V1。

问题：完整目标包含 Temporal、PostgreSQL、对象存储和多资源 Worker，但第一份可安装交付需要避免强依赖整套基础设施，同时不能用 FastAPI BackgroundTasks 假装可靠长任务。

决策：默认 SQLite WAL + 独立 Worker，持久化 job、stage checkpoint、租约、fence 与事件；资产存本地内容寻址目录。附带 Temporal 调度适配器，但明确其验证和单机边界。

结果：无外部任务平台也能生成视频，中断可恢复；支持同机多 Worker。不能跨主机共享 SQLite，不声称多节点高可用。将来迁移 PostgreSQL/S3 时必须重验原子领取、幂等、fence 和输出提交。

验证：测试覆盖重复领取、过期 Worker、阶段复用、取消竞争和恢复耗尽。实际视频从持久化任务生成。


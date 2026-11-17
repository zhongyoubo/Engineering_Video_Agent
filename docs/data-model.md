# 数据模型与存储

Schema 初始化在 `apps/api/src/explainer/db.py`，版本 1，SQLite WAL。当前数据库只保存元数据、脱敏后的文本和事件，二进制进入对象目录。

| 表 | 责任 |
|---|---|
| projects | 工作空间内项目 |
| inputs | 不可变输入、原归档资产、解析 manifest |
| revisions | 父版本、brief、content、storyboard、quality |
| jobs | 状态、阶段、进度、租约、fence、恢复次数 |
| checkpoints | job/stage 唯一的完成输出 |
| events | 租户隔离、序号化的状态事件 |
| assets | hash、类型、文件名、MIME、大小和租户 |
| outputs | revision/role 到资产引用 |
| voice_cache | 租户内内容与音色版本缓存 |
| idempotency | 租户/key 唯一，请求 hash 与原响应 |
| schema_version | 数据库协议版本 |

## 路径

`.data/objects/<tenant>/<hash前两位>/<sha256>`。路径由服务构造，客户端只传资源 ID。相同内容按租户去重，避免跨租户内容存在性泄露。

`.data/work/<job>` 保存配音 raw/master、渲染临时目录和隔离录制，默认不会导出。工程 ZIP 只打包显式引用的资产与 JSON。

## 一致性

文件先提交，数据库后引用；事务中原子提交阶段完成和事件。可能产生孤立文件，不能误产生“已完成但没有检查点”。本版未自动 GC，运维清理需核对引用；不要手动删 objects 或数据库单表。

## 版本与迁移

交付版只包含 v1 初始化，不把建表 IF NOT EXISTS 当作未来升级迁移机制。后续字段变化必须加入事务迁移、备份、升级/回退测试，不能直接覆盖线上 SQLite 文件。

对于多节点部署，替换为共享事务数据库与对象存储；先抽取数据库仓储契约，再重写领取、fence、唯一键、检查点提交与输出事务，不进行未经验证的 SQL 字符串翻译。


## Editorial request and resolved strategy

`Brief.editorial` and `StoryboardIR.editorial_request` preserve requested purpose,
auxiliary purposes, subject, audience description/depth, presentation forms, core message
and viewer takeaway. `EditorialPlan.strategy` optionally records the resolved four dimensions,
reasoning summary (rationale, not hidden chain-of-thought), success criteria and an ordered
NarrativeBeat outline referencing actual scene IDs. New native engineering creator plans
require this strategy; old plans remain readable without it. Changed requests trigger new
planning; source/props hashes bind the subsequent preview/review. The catalog is versioned
as 1.0 and exported to packages/contracts/content-taxonomy.json.

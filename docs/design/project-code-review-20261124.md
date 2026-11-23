# 项目代码复查 · 2026-11-24

本轮从已合并的 `f1f5ea5` 内容出发，对整个工程按风险检查；并非逐行证明所有代码无缺陷。
保留原有测试和隔离约束，先复现实际问题，再增加回归用例并修复。

## 已修复的问题

| 优先级 | 问题及影响 | 实现 |
| --- | --- | --- |
| 高 | 取消操作先读取 QUEUED，Worker 随后领取，旧读可能直接写成 CANCELED | 事务内锁定任务并重读，再决定取消状态；事件与状态同事务 |
| 高 | FAILED 等终态保留旧租约信息时，旧 Worker 仍可能提交阶段或完成任务 | guard、阶段提交、release/finish 同时验证状态和租约；终态禁止重新推进 |
| 高 | 失败任务重试绕过租户并发额度 | 锁定租户和任务，事务内检查额度、重置旧租约并排队 |
| 高 | 渲染进程超时或非零退出后，残留的成功回执仍可能被接受 | 进程失败优先；成功回执不能覆盖失败；保留受控诊断 |
| 高 | Studio 退出后仍保存前一账号项目、分镜等状态 | 登录外壳与会话内工作区分离；退出卸载工作区，迟到响应不能进入新会话 |
| 高 | 旧 Web 依赖存在公开的上传解析、Range 响应资源消耗问题 | 同步 API、锁文件及 Qwen 服务的兼容依赖；验证正常上传/单段拖动与异常请求边界 |
| 中 | 源码快照脱敏遗漏连接 URI 用户密码和 Authorization 值 | 增加 URI userinfo 和 Bearer/Basic 头脱敏，保留普通 URL 与说明文本 |
| 中 | 父进程退出后，后代占用输出管道可绕过期限或阻塞清理 | 等待进程和读线程同时结束；POSIX 非阻塞轮询、进程组清理，先 SIGTERM 再升级 |
| 中 | 直接 SIGKILL 让 Remotion 无机会清理独立 Chrome 进程组 | 给 SIGTERM 清理处理器有限时间，随后强制结束剩余进程组 |
| 中 | 多进程首次启动竞争创建密钥，或读取尚未写完的内容 | 权限受限临时文件完成写入并 fsync，再以硬链接原子发布，竞争者读取相同完整密钥 |
| 中 | ZIP 中同一路径既是文件又是祖先目录，直到落盘才报错 | 归档读取阶段双向检查文件与目录冲突 |
| 中 | 文案编辑静默截短，合法长旁白被切成 1600 字符 | 保留合法全文，由领域协议拒绝超长；修正“改为：”的冒号解析 |
| 中 | 场景协议允许 3200 字符，Qwen 网关仅允许 1600，直到请求服务才失败 | Qwen 计划修复循环和请求前提前校验，明确要求拆分镜头；不静默换声音或截断 |
| 中 | FAILED 后 EventSource 已关闭，重试仍绑定同一 job 导致事件流不重连 | 重试代数触发重连，携带最后 seq 游标，忽略重复与迟到回调 |
| 优化 | 每 3 秒轮询重新计算能力、字体和完整素材目录 | 后台只轮询项目/任务，能力在登录和显式刷新获取；防止轮询重叠 |

脱敏是常见凭据格式的尽力保护，不构成任意秘密检测保证；原始源码仍是授权用户的输入资产。
POSIX 子进程行为经过实测；原生 Windows 进程树以及脱离进程组的进程需要部署验收。

## 覆盖范围

| 模块 | 本轮核对方式 | 实际边界 |
| --- | --- | --- |
| API、鉴权、上传、资产、重试/取消 | 源码审查、SQLite API 回归、浏览器多账号流程 | 未做公开网络压力/渗透验收 |
| 队列、租约、阶段提交、检查点、Temporal 接口 | 状态交错回归、既有测试、PGlite 协议执行 | PGlite 不代表原生 PostgreSQL 多进程锁竞争；未启动 Temporal 集群 |
| 源码读取、Git 输入、原生驱动、容器工具 | 边界回归、协议测试、静态核对 | 未执行用户/模型源码；没有 Docker/gVisor 或原生提供商实测 |
| 配音、字幕、时间轴、编辑和合成 | 容量校验、原有回归、固定兼容工程真实渲染 | 无 Qwen/Edge/Ming 实际配音，无专业听审 |
| 素材、授权、哈希门禁、导出和存储 | 保留素材专项全部断言、完整测试、固定工程 ZIP 导出 | 本轮没有重新生成图片或三维模型；S3 实服务未验证 |
| Studio、SSE、登录和轮询 | 20 项真实浏览器流程 | 测试中的 EventSource 替身只验证重连协议，不声称模型执行 |
| 运行配置和依赖 | 启动竞争、进程组回归、版本检查、构建 | 不是全依赖漏洞审计；生产代理/配额仍需部署配置 |

## 依赖修复

锁定 FastAPI **0.136.3**、Starlette **1.10.0**、python-multipart **0.0.34**；
API 项目、`requirements.lock`、Qwen 服务依赖保持一致。实际安装后 `pip check` 无冲突。
同步重新生成 OpenAPI；上传接口保持 multipart，校验异常仍由项目处理器去除原始输入。
当前 Starlette 的 httpx TestClient 兼容路径会输出弃用提示；测试仍通过，未来可单独迁移测试客户端。

官方依据：

- [Starlette multipart rollover](https://github.com/Kludex/starlette/security/advisories/GHSA-2c2j-9gv5-cj73)
- [Starlette Range merge](https://github.com/Kludex/starlette/security/advisories/GHSA-7f5h-v6xp-fcq8)
- [Starlette release notes](https://starlette.dev/release-notes/)
- [python-multipart unbounded headers](https://github.com/Kludex/python-multipart/security/advisories/GHSA-pp6c-gr5w-3c5g)
- [python-multipart form parsing](https://github.com/Kludex/python-multipart/security/advisories/GHSA-5rvq-cxj2-64vf)
- [FastAPI release notes / Starlette 1 support](https://fastapi.tiangolo.com/release-notes/)

回归要求正常单段 Range 返回 206 和准确字节；101 段请求遵循新 Starlette 策略忽略 Range，
返回单个完整 200 响应而非构建大量分段。128KiB 单个 multipart 头返回受控错误。
升级前分别返回 206 多段与 201 接收；升级后通过。未为满足测试额外修改库行为。

## 验证

基线：316 项后端、17 项浏览器流程。本轮增加 24 项后端用例和 3 项浏览器流程。
新增后端用例分批在修复前累计复现 22 项失败；浏览器复现会话残留、SSE 不重连和能力重复拉取。
未删除、跳过或降低原有测试断言。新增 Range 断言按库实际完整响应策略校正，并校验全部字节。

复跑命令（仓库根目录）：

```bash
.venv/bin/python -m pip check
.venv/bin/python scripts/export_contracts.py
.venv/bin/python scripts/check.py
CHROME_EXECUTABLE=<Chrome绝对路径> npm run test:ui
npm run format:check
git diff --check
CHROME_EXECUTABLE=<Chrome绝对路径> .venv/bin/python scripts/media_smoke.py --output .verify-project-review-media
```

最终结果及代码哈希见 `docs/verification-project-review.json`。
固定模板兼容流水线真实渲染并解码 **20 秒 / 600 帧 / 1080p30**，输出视频、脚本、字幕、
封面、质量记录及工程 ZIP。环境无配音服务，状态明确为 **PARTIAL**，声音为 none，时间轴为
estimated_sentence；这不是原生 Agent 创作或专业成片验收。媒体证据见
`docs/verification-project-review-media.json`。PGlite 的取消、额度、重试和终态 fencing 通过，
证据见 `docs/verification-project-review-postgres.json`。

## 后续优先项

1. 在真实 PostgreSQL + 多 Worker + Temporal 环境做抢占、超时、取消与恢复压力测试。
2. 配齐原生模型、隔离容器和实际旁白，按现有门禁验收一个未见主题的端到端创作。
3. 检查部署中的工作目录/资产保留周期、磁盘与租户存储额度；这轮没有新增保留策略。
4. Studio 构建仍有大块体积提示，可按播放器、编辑器和素材面板拆包；单独测量再优化。
5. 扩展独立文字遮挡/OCR、连续播放及人工听审，不能用测试通过代替视听质量判断。

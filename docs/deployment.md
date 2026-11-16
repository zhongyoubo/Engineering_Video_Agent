# 部署与运维

## 1. 支持的运行方式

交付已验证 Linux 本地 Python + Node，单机持久化队列。Docker、Temporal 和源码隔离是附带的真实适配实现，但本环境无对应服务，未作集成验证。公网 SaaS 需要补齐反向代理、HTTPS、组织身份、集中存储与运维验收。

## 2. 本地

执行 README 的 bootstrap 与 dev 命令。生产式本机运行先 `npm run build`，再在同一环境启动 API 和 worker：

```bash
export PYTHONPATH=apps/api/src
.venv/bin/python -m uvicorn explainer.api:app --host 127.0.0.1 --port 8000
# 另一个终端，使用相同工作目录和配置
.venv/bin/python -m explainer.worker
```

构建后 API 在根路径服务前端；开发 Vite 将 /api 代理到 8000。不要同时启动两套测试服务占用相同端口。

## 3. 配置

`.env` 在项目根加载。数据目录默认 `.data`；相对路径按服务工作目录解析，服务必须固定工作目录。模型 URL 为兼容 chat-completions 协议的版本前缀，例如部署者管理的 `http://127.0.0.1:9001/v1`；服务会追加 `/chat/completions`。

密钥不进入工程包。设置 HTTPS 时启用 `EXPLAINER_COOKIE_SECURE=true`，将 `EXPLAINER_ALLOWED_ORIGINS` 改为真实创作台地址，不使用通配符。

## 4. Docker

Dockerfile 分前端构建和 Python 运行阶段，安装 Chrome、FFmpeg、eSpeak，非 root 服务运行。compose 绑定 127.0.0.1，并要求显式访问密钥。首次构建需下载依赖和浏览器。

在 Docker Desktop 上运行适合 Windows 用户。源码执行默认关闭，API 容器没有宿主机 Docker Socket。

## 5. 源码隔离执行

在独立 Worker 主机预先配置并验证 Docker 与 runsc：

```bash
docker build -t explainer-sandbox:1.0.0 infra/sandbox
```

Worker 配置 `EXPLAINER_ENABLE_SANDBOX=true`。默认 runtime=runsc，平台不会为你自动安装或绕过 gVisor。若部署者选择空字符串使用 Docker 默认 runtime，应重新评估隔离风险。

运行镜像无网络，源目录只读，输出目录可写，限制内存/CPU/进程/共享内存，显式清理容器。只允许标准库 Python 示例和静态 HTML 页面，不自动下载用户项目依赖。

建议在独立受控主机以有权限的服务账户运行 Runtime Worker；不能为了方便给 Web API 暴露 Docker Socket。本版 Worker 同时执行流水线，生产拆出独立 Runtime 执行服务仍需进行平台化改造。

## 6. Temporal

安装/启动兼容的 Temporal 服务，设置 `EXPLAINER_SCHEDULER=temporal`、地址、namespace 和队列。运行：

```bash
export PYTHONPATH=apps/api/src
.venv/bin/python -m explainer.temporal_worker
```

不要同时运行本地轮询 Worker，否则会绕过预期调度。Temporal 适配器以长 Activity 执行本地检查点流水线，并维持 heartbeat；不是“每阶段独立 Temporal Activity”的最终分布式设计。元数据和素材仍要求本机共享目录。

## 7. 备份与恢复

备份数据库及其一致快照、objects 目录、配置和音色参考。使用 SQLite 在线 backup API 或暂停写入后备份，不能只拷贝正在写入的主文件忽略 WAL。

失败任务可通过界面重试，从检查点恢复。Worker 崩溃后租约过期重新领取，默认最多四次自动领取；耗尽后 FAILED。清理 work 目录前确保任务已终止，删除不应影响已引用的 objects。

## 8. 诊断

`python scripts/doctor.py` 只显示能力，不输出密钥。常见问题：

- 没有声音：安装 eSpeak 或配置 Qwen；质量报告明确说明。
- 渲染失败：确认 Chrome、FFmpeg、字体、可写磁盘和足够内存。
- 任务不执行：确认 Worker 存活、同一 data_dir、scheduler 配置一致。
- Qwen 失败：检查本地模型目录、参考音频/文本、授权密钥、服务地址与显存。
- 隔离失败：检查 runsc、镜像、Docker 权限和入口路径；不要直接在 API 进程运行源码绕过。
- 目标时长偏差：精简旁白后重生成，本版优先保留完整声音。


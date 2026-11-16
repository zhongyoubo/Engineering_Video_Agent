# 验收与测试说明

自动化测试与最终执行结果见 `verification.json`。文件中区分真实运行、协议测试和未验证基础设施。

## 1. 后端

本次 27 项后端测试、3 条浏览器测试通过。

pytest 覆盖：越权项目和资产、Cookie/Origin 基础安全、API key 不泄露、幂等冲突、取消、锁定与解锁、危险路径、符号链接、重复归档、大小限制、秘密脱敏、Python AST、租约/fence、检查点复用、取消完成竞争、恢复耗尽、字幕边界、伪造运行/证据、自然语言修改和工程导入。

模型测试使用 MockTransport 验证协议和错误引用降级，不等于真实模型生成质量测试。

## 2. 浏览器

Playwright 启动 API、Worker、Vite，使用独立 .test-data 工作区，验证提示词生成分镜、编辑保存为独立版本、历史列表、能力页、上传源码并查看证据。测试不依赖真实外部账号。

## 3. 媒体

`scripts/media_smoke.py` 走真正的语音、FFmpeg、Remotion 和导出流程，检查最终视频规格、帧数和全片解码。

`--source` 使用提供的源码 ZIP，真实生成源码讲解视频；为降低环境依赖选字幕版。它验证的是源码分析到视频，不代表执行了用户源码。

工程包检查 ZIP CRC、JSON 与媒体 hash；可通过界面导入再编辑。样例输出位于 examples/generated（交付包中），用于打开即看。

## 4. 尚需部署环境验收

Docker 镜像构建、gVisor 隔离、真实 Python/静态 Web 容器录制、Temporal 服务恢复、Qwen 模型加载和音色试听、外部模型内容质量，均需要在对应环境补充集成验收。本环境无 Docker/GPU/模型服务，不将这些列为实测成功。

## 5. 交付检查

依赖锁文件、契约、文档、样例和测试完整；不含本机密钥、数据库和模型；源码 ZIP CRC 与 SHA-256 检查通过。部署命令必须按 README 从干净目录执行，不依赖开发时的绝对路径。


## V2 增补

事实汇总：`docs/verification-v2.json`。完整配音样例：`examples/generated/qwen-v2/`。

目标环境准备独立验收 PostgreSQL 数据库和 S3 bucket 后，加载 `.env`，执行：

```bash
.venv/bin/python scripts/verify_shared_deployment.py --output deployment-verification.json
```

该脚本会创建 acceptance_ 前缀记录和对象，测试两条原生连接并发领取、租约过期与旧 fence 拒绝、第二个 Worker 独立对象下载。请在专用验收资源运行，完成后由管理员清理测试数据。此脚本已提供，本交付未连接原生生产服务执行它。

Docker/gVisor 验收：先构建沙箱镜像，开启专用执行 Worker，仅上传自编可信 fixture；检查 `--network none`、只读源码、资源上限与容器清理，再进入上传源码验收。不可把宿主可信 fixture 测试报告当容器隔离通过。

## V3 engineering acceptance

Current results: docs/verification-v3.json. Run scripts/check.py, browser tests, verify_engineering_fixture.py and verify_engineering_pipeline_fixture.py. These fixed fixtures never claim native inference. Configure real models and isolated tools, then run verify_engineering_deployment.py separately for each provider. Final production acceptance includes source-based UI behavior, native cancellation/recovery, full visual viewing and listening, not only codec validation.

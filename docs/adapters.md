# 适配器开发

## 已有适配器

注册信息见 `adapters/base.py`，包括 source.static、planner.template、planner.llm、runtime.docker、voice.espeak、voice.qwen、render.remotion。manifest 描述能力；capabilities 页面同时报告部署环境是否配置，注册不等同于环境可用。

## 增加语言理解

在 ingestion 层将语言 AST/符号分析转换为 Claim/Evidence，不把 parser 输出直接变成“已运行”。输入始终引用不可变快照，摘录有 hash。大型项目应增加索引与检索，而不是无界发送仓库。

## 增加运行适配器

实现 RuntimeAdapter.detect/plan/execute/dispose 等最终协议前，本版运行接口为 execute_runtime 的明确类型分发。新类型必须同步 domain.Brief.runtime、API Schema、界面、沙箱执行器、质量断言和测试。

禁止通过用户提示词新增任意命令分支。依赖安装、网络、数据、镜像、权限和清理方案先确定。容器输出只有允许的格式可提交为平台资产。

运行成功需要 exit_code、期望输出和可验证断言；不能只因生成了截图就认为业务流程成功。动态 Web 自动探索应作为新适配器，不能偷偷扩充 static-web 的能力承诺。

## 增加场景

1. domain.SceneType 与 packages/video/src/types.ts 增加类型。
2. 实现 React 场景，动画按帧计算，不读取真实时钟。
3. 只读取 props 和已授权素材，不在线加载字体或执行用户 JS。
4. 增加布局、帧与导出测试，检查长中文、长英文和极短场景。
5. 运行 export_contracts.py 并更新文档。

## 增加配音引擎

遵循 synthesize 返回 path、duration、engine，真实返回 WAV 或可解码音频，不用静音假装声音成功。音色、归一化算法和模型版本纳入缓存版本。精确字幕引擎需提供真实时间戳和置信度，不能把估计值标为强制对齐。


## 原生 Agent

`native_agent.py` 为任务执行/隔离边界，`native_contract.py` 为独立输出协议，`services/native_agent/driver.py` 为容器内原生 CLI 进程适配。供应商不能从请求注入命令或模型服务 URL。详细部署、认证、日志与能力边界见 `native-agents.md`。

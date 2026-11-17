# V3 实现与验证范围

工程型 Agent 已实现：原生策划、实际 TSX 文件、Agent 选择工程工具、真实编译/试渲染观察、有限修复、源码 hash 门禁、图像基础检查、原生视觉审查、完整工程导出与逐步恢复状态。正式模式要求 Qwen 与真实对齐，不静默降级。

本次真实工具验证使用固定可信源码与预编决策夹具；未使用真实供应商模型。Docker/gVisor 不可用，生成代码容器隔离尚未实测。夹具运行不是放宽生产执行策略。

不宣称已经完成：真实模型产片质量验收、专业听感认证、所有项目运行适配、私有 Git/每用户模型凭据、Skill/MCP 自由安装、跨供应商原生会话迁移、组织 SSO/RBAC/计费。历史能力和结果保留在其他 scope/verification 历史文件；当前结果见 verification-v3.json。

## Audience-purpose scope update · 2026-11-18

The content scope includes introduction, explanation, analysis, viewpoint, advice and tutorial.
Knowledge/technology content is the initial product focus; project source is one input type.
The product separates purpose, subject, audience and presentation form, while retaining the
native engineering workflow. Structural fixtures and automated regression do not certify
native model quality across six genres. See docs/product/positioning-and-content-taxonomy.md.

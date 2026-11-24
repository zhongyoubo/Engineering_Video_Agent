# 素材包接入与按需创作

## 目标与首批内容

把素材变成工程可检索、可观察、可组合、可追溯的能力。Agent 根据讲解目标、对象、
场景与动作选择素材，也可继续创作 SVG/Canvas/Three 源码；素材目录不是选题路由器。

| 素材包 | 已接入 | 风格与用途 | 来源与授权 |
|---|---|---|---|
| phosphor | 8 个 React SVG 对象 | 双色/扁平：书本、大脑、机器人、终端、文件夹、放大镜、齿轮、显示器 | phosphor-icons/core，MIT |
| soft3d | 3 张透明 PNG | 立体插画：笔记本、爱心、对话气泡 | realvjy/3dicons，CC0 |
| motion | 2 个适配组件 | 逐字输入、错峰弹性文字入场，结束后保持结果 | lifeprompt-team/remotion-scenes，MIT |
| avocado | 1 个自包含 GLB | 可旋转的实物牛油果，适合多角度观察 | KhronosGroup/glTF-Sample-Assets，Microsoft 模型 CC0；授权说明文档 CC-BY-4.0 |

这是一组精选素材，不代表安装了上游完整图库。PNG 是二维图：笔记本1000×1000，
爱心132×120，对话气泡293×240；后两张只适合小尺寸点缀，不能放大冒充4K主视觉。
GLB保留网格，把嵌入纹理降到512px，优化后448224字节。它是已有对象模型，
不是文生三维能力。完整来源提交、原始 SHA 和改动说明随仓库保存。

## 数据与发现

`assets/library/packs/index.json` 只引用仓库内审查过的 manifest。每包记录版本、
上游固定提交、完整授权、文件角色与 SHA；每项记录对象、风格、用途、可执行动作、
参数、入口符号和 PNG 预览。所有文件校验通过后才进入共享目录。

`GET /api/v1/material-library?query=书本&style=duotone&asset_type=component`
提供文字、风格与类型筛选。文字筛选只用于查找目录，不决定选题或镜头模板。
预览接口沿用租户登录验证；浏览器只显示静态 PNG，不执行素材组件。
Git 签出保留精选包的原始字节，工程内暂存与恢复统一使用斜杠分隔的清单路径。
工作台侧栏新增“素材库”，可查看预览、适用范围、参数、来源和复制版本引用。
策划及创作 Agent 会收到实际预览拼图、格子索引和完整元数据。

## 工程使用

引用格式：`library:pack.phosphor.book-open@1.0`。

1. 源码组件：在 `shot.assets` 记录引用，`creation.elements` 以
   `implementation=kit`、`library_ref` 绑定对象。`select_materials` 替换当前选择，
   仅把选中组件及声明依赖复制到 `src/vendor/<pack>/`，按目录给定的 module/symbol 导入。
2. 图片/模型：在 `asset_requirements` 使用 `provider=library_asset`、`library_ref`，
   经 `request_assets` 生成规范回执；`creation` 以 `implementation=asset`、`asset_key`
   绑定实际对象。二进制内容、预览、完整授权和哈希随检查点恢复，渲染无需下载上游文件。
3. PNG 通过 `props.generated_assets[key]` 和 Remotion `Img/staticFile` 使用。
   GLB 场景必须声明 `techniques: ["three"]`，用受保护的
   `LibraryModel asset={props.generated_assets[key]} angle={frameDerivedAngle}` 渲染。
   模型只加载 `generated/<sha256>.glb`，初始化等待实际模型就绪；失败中止渲染。
4. 动作仍需要逐镜头设计，重要因果变化继续通过 `compiled_creative_events` 对齐旁白。
   组件中的 `startFrame` 是镜头局部帧，不是独立时钟。使用素材不等于已经完成镜头设计。

新增动作 `search_materials` 返回筛选元数据，`select_materials` 只接受固定版本的引用，
空数组用于清除选择。计划中的素材在进入创作循环时自动装载。没有新增任意 URL、
素材包上传、npm 安装或宿主执行生成源码的入口。

## 完整性、恢复与导出

选择生成 `material_selection` / `props.material_packs`，包含引用、包指纹、装载文件、
模块与来源。构建前从可信包重新推导清单，拒绝伪造摘要、缺失/额外文件、路径穿越、
符号链接和版本变化。`src/vendor` 与 `library-model.tsx` 禁止 Agent 修改。
平台与选中依赖递归参与渲染指纹，路径也参与哈希，避免不同目录同名文件碰撞。
素材变更使旧构建、预览与审查失效；相同请求不重复失效。

GLB校验限制文件大小、JSON/BIN区块、嵌入buffer/纹理、几何预算，拒绝外部资源及
扩展加载。此入口只解析固定审查素材，不提供任意模型上传。原有图片/项目素材预算保留。
来源、授权与实现方式留在报告/源码，不自动把制作声明加到视频画面。

源码ZIP包含选中的组件、导入二进制、预览、`material-manifest.json`、每项授权，
以及原有创作/素材/审查记录。素材绑定必须经过实际帧审查：PNG/GLB检查
`scene:asset`，组件对象和动作检查 `scene:element/event`；目录存在与被选中不构成消费证据。

## 维护与验证

开发维护命令：`scripts/vendor_material_sources.py` 下载固定上游文件；
`scripts/prepare_material_packs.py` 进行 SVG 适配、PNG 预览和 GLB 纹理优化，重建 manifest。
准备脚本需要另行安装 CairoSVG==2.8.2，仅维护期使用，不是应用运行依赖。
原始8MB GLB可重复下载，不进入Git；优化后自包含GLB随源码提交。
变更素材必须更新版本、说明、摘要并重新构建/渲染/审查。运行时不联网拉取素材。

`scripts/verify_material_packs.py` 只接受仓库内固定已审查的样例和素材，无用户参数。
实际测试按需装载、素材回执、编译、连续预览、16秒1080p/30fps渲染、像素变化、
全片解码和源码导出。它是无声固定工程回归，不能替代真实原生 Agent 的新主题创作、
专业配音、部署隔离或人工观看验收。结果见 `verification-material-packs.json` 和施工记录。

## 2026-11-24 复查修正

任务恢复保留创作阶段追加的选择；计划中的新包版本优先于父版本。检查点恢复先校验
原始包身份，拒绝同版本内容漂移，之后才写入工程。装载预检包含待删除路径及祖先，
依赖顺序保持稳定。批量选择/预览使用一次操作内的已验证索引，不跨请求缓存旧结果。
GLB范围必须为合法整数；模型卸载释放等待与资源，4K使用匹配像素密度。
详情与回归证据见 [代码复查记录](material-pack-review-20261124.md)。

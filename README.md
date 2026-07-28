# 产物库（QwenPaw 插件）

面向任何 QwenPaw Agent 的正式产物登记与管理插件。它不是扫描式文件管理器：**只有 Agent 主动登记或用户手动登记的真实交付文件才会出现。**

## 当前版本：v0.4.4

v0.4.4 是前端缓存修复版：插件入口改为随版本变化的 `ui/index.v0.4.4.js`，避免老用户升级后 Electron / WebView 继续加载旧版 `ui/index.js` 缓存。页面顶部会显示当前运行版本，便于确认新界面已生效。

### v0.4.4 前端缓存修复

- `plugin.json.entry.frontend` 改为 `ui/index.v0.4.4.js`，升级后资源路径变化，减少旧 UI 缓存命中。
- 构建脚本会按 `plugin.json.version` 自动生成版本化前端入口，并保留 `ui/index.js` 作为兼容副本。
- 页面标题区显示运行版本，用户可直接确认当前加载的是新版前端。
- 若升级后界面仍未变化，建议重启 QwenPaw Desktop；仍异常时可卸载旧插件后重新安装新版。

### v0.4.3 发布前清洁修复

- 移除生图助手图库自动发现逻辑中的个人工作区候选路径，社区版只保留通用本地路径与环境变量。
- `requirements.txt` 和 `plugin.json.dependencies` 补充 `requests>=2.28.0`，匹配「发送参数到生图助手」功能的运行依赖。
- 发布前扫描新增工作区名与禁带目录检查，避免源码和 zip 包出现个人化痕迹。

### v0.4.2 社区隐私安全文档修复

- README 新增「产物库 × 生图助手联动建议（社区发布版）」说明。
- README 新增「隐私说明」，明确默认本地运行、不主动上传用户数据。
- README 新增「社区发布去个人化检查清单」，要求文档、示例、截图、默认数据全部使用通用示例。
- 对外示例统一使用 `example` / `demo` / `sample`，不包含私人项目名、真实路径、真实账号或真实历史记录。
- 发布包继续使用白名单打包，只包含运行必需文件，不包含测试数据、历史 zip、上游源码镜像或本地数据库。

### v0.4.1 marketplace-compat 修复

- 新增根目录 `requirements.txt`，显式声明运行依赖 `send2trash>=1.8.3`，避免市场安装器只读取 requirements 时漏装依赖。
- `plugin.json` 版本升级至 `0.4.1`。
- `plugin.json` 补充 `description_i18n`，便于市场中英文展示。
- `plugin.json` 补充 `meta.category` 与 `meta.features`，便于市场分类、检索和功能卡片展示。
- README 安装命令从旧版 `0.3.1` 修正为当前 `0.4.1`。
- 暂不新增 `manifest.yaml`，本包仍按 QwenPaw 普通插件格式发布，不切换 PawApp SDK 格式。
- 暂不把 `type` 改为 `app`，避免误触 PawApp Center 的入口页、路由和展示位置规范。

### v0.4.0 生图资产管理

- 新增 **生图库视图**：专门筛选 `asset_category=generated_image` 的图片资产。
- 支持从 **qwenpaw-image-gen 生图助手 SQLite 图库** 一键导入图片记录，自动去重，不复制原图。
- 导入时记录模型、LoRA、星级、提示词、负向提示词、步数、CFG、Seed、尺寸等 `generation_meta`。
- 支持按模型、LoRA、星级筛选/排序，保留原有打开位置、复制图片、复制路径、备注编辑等能力。
- 支持在详情中快捷复制 Prompt / Negative Prompt / 参数摘要，方便复刻和二次创作。

### v0.3.1 修复内容

- 修复 **打开所在位置**：后端改用 Windows `ShellExecuteW` 打开资源管理器并选中文件，避免 `CREATE_NO_WINDOW` 导致窗口不显示。
- 前端补回 **打开位置** 按钮，调用 `/artifact-library/artifacts/{id}/reveal`。
- 前端补回 **登记文件**，调用 Windows 原生文件选择器 `/picker`，文件不上传、不复制，只保存元数据。
- 前端补回 **复制产物 / 复制路径**：
  - 图片复制为图片对象；
  - 文本复制正文；
  - 其他文件复制为 Windows 文件对象；
  - 路径复制保持独立按钮。
- 前端补回 **预览能力**：图片预览/缩略图、文本摘要、音视频轻量元信息。
- 前端补回 **三种显示方式**：列表视图、缩略卡片视图、按项目归组视图。
- 修复 **备注字段**：创建、编辑、列表、导出、Agent 工具均支持 `notes`。
- 修复 **批量删除**：与单个删除一致，先安全移入 Windows 回收站，再标记元数据；缺失文件会跳过且不伪报成功。
- 修复 **统计逻辑**：`total` 含全部记录，分类统计默认按未移入回收站的活动记录计算。
- 构建脚本改为按 `plugin.json` 版本动态命名 zip，避免发错版本包。

## 已确定的规范

1. 只登记已经写入磁盘、值得保留或交付的成果；不登记缓存、日志、依赖、临时测试和中间文件。
2. 每个登记至少包含：文件路径、显示名称、简述、项目。
3. `交付项` 为空时自动使用显示名称。它用于区分同一项目内的不同成果。
4. 最终版唯一规则：**同一项目 + 同一交付项 + 同一类型，只能有一个最终版。** 新最终版会把旧最终版改为“已归档”，不会删除旧文件。
5. 删除只会调用 Windows 回收站，绝不以永久删除作为后备方案。
6. 文件本体保留在原路径；产物库只保存元数据，数据在 `%APPDATA%\QwenPaw\artifact-library\artifacts.json`。

## Agent 工具

Agent 在完成正式文件后调用：

```text
register_artifact(
  path="C:\\...\\output.pdf",
  title="项目报告终稿",
  summary="用于提交的 A4 PDF，包含目录与最终插图。",
  project="示例项目",
  deliverable="示例交付项",
  artifact_type="document",
  tags=["提交", "终稿"],
  status="final",
  notes="可选备注"
)
```

`artifact_type` 可选值：`image`、`document`、`web`、`code`、`video`、`audio`、`archive`、`data`、`other`。不填时按扩展名推断。

`status` 可选值：`draft`（草稿）、`delivered`（已交付）、`final`（最终版）。

## 页面功能

- 顶部筛选：搜索、项目、类型、状态、是否包含回收站。
- 视图切换：列表 / 卡片 / 项目。
- 手动登记：点击 **登记文件**，选择本地文件后填写标题、说明、项目、交付项、标签、备注。
- 操作按钮：详情、打开位置、复制产物、复制路径、设为最终版、移入回收站。
- 详情抽屉：预览、元数据、备注编辑、来源信息。
- 统计：活动产物数、总记录数、回收站数，以及按项目/类型/状态统计。
- 导出：JSON、CSV、Markdown。
- 批量操作：批量修改项目、批量修改类型、批量移入回收站。

## 产物库 × 生图助手联动建议（社区发布版）

生图助手可以与 QwenPaw 产物库联动，将生成结果自动归档为可检索、可管理、可复用的本地创作资产。

- **生图助手**：负责连接 ComfyUI、配置工作流、生成图片、保存生成参数。
- **产物库**：负责长期归档、分类管理、项目整理、评分筛选和复用记录。

### 生成完成后自动登记

生成图片后可自动归档到 QwenPaw 产物库，便于后续按项目、模型、标签和评分进行管理。建议登记的基础元数据包括：

- 图片路径
- 生成时间
- 使用模型
- 正向提示词
- 负向提示词
- LoRA 列表
- 采样参数
- 图片尺寸
- Seed
- Workflow 信息（可选）

### 产物库中显示生成参数

产物库详情页可以为 AI 生成图片展示专门的「生成参数」区域：

| 字段 | 内容 |
|---|---|
| 来源 | QwenPaw 生图助手 |
| 后端 | ComfyUI |
| 模型 | 用户本地模型名称或脱敏后的模型文件名 |
| LoRA | 可选 |
| Seed | 生成种子 |
| Steps | 采样步数 |
| CFG | 提示词引导系数 |
| Sampler | 采样器 |
| Scheduler | 调度器 |
| 尺寸 | 宽 × 高 |

社区版不要展示真实本机模型完整路径，只显示模型文件名或脱敏后的模型名称。

### 从产物库复用生成参数

用户可以从产物库中复用历史生成参数，将提示词、模型、采样参数发送回生图助手继续调整。推荐能力包括：

- 复制提示词
- 复制生成参数
- 导出 workflow JSON
- 发送参数到生图助手
- 使用该图片参数继续迭代

### AI 生成资产标准类型

建议使用以下标准元数据标识 AI 生成图片：

```json
{
  "artifact_type": "generated_image",
  "source_plugin": "qwenpaw-image-gen",
  "backend": "ComfyUI"
}
```

这样产物库可以筛选全部 AI 生成图片、ComfyUI 生成图片、指定模型生成图片、指定项目下的图片、已评分图片、已收藏图片和可复用参数图片。

### 通用登记示例

```json
{
  "title": "ComfyUI 生成图片",
  "project": "AI 图像生成项目",
  "tags": ["ComfyUI", "generated-image", "QwenPaw"],
  "metadata": {
    "model_name": "example-model.safetensors",
    "prompt": "example prompt",
    "negative_prompt": "example negative prompt",
    "steps": 28,
    "cfg": 7,
    "seed": 123456
  }
}
```

## 市场发布说明 / 兼容性说明

- 本包是 **QwenPaw 普通插件**，入口仍使用 `plugin.json -> entry.backend/frontend`，不是 PawApp SDK 项目。
- 因此不提供 `manifest.yaml`，也不使用 `frontend.entry` / `backend.entry` 的 PawApp manifest 风格。
- `type` 保持 `general`，左侧栏展示和现有 Agent 工具注册逻辑不变。
- 市场安装依赖兼容：根目录包含 `requirements.txt`，同时 `plugin.json.dependencies` 继续保留同一依赖，兼容不同安装器实现。
- 生图资产导入只读取本机 `qwenpaw-image-gen` SQLite 图库和原图路径；不会上传图片，也不会扫描全盘。

## 隐私说明

本插件默认在本地运行。与生图助手联动时，生成图片及其参数仅登记到用户本机的 QwenPaw 产物库中。

插件不会主动上传以下信息：

- 本地文件路径
- API Key
- 用户账号信息
- 聊天记录
- 私人项目名称
- 图片内容
- ComfyUI 安装目录
- 本地模型完整路径
- 产物库真实历史记录

以下信息可以仅保存在用户本机：

- 图片文件路径
- 生成参数
- 本地模型名称
- 本地 workflow
- 用户自定义项目名
- 用户备注

如果用户手动将产物打包、分享或发布，请自行检查其中是否包含私人路径、真实项目名或其他敏感信息。

## 社区发布去个人化检查清单

社区版发布前必须确认：

1. 默认本地化。
2. 默认不联网。
3. 默认不上传。
4. 文档不出现私人名称、真实项目名、真实聊天记录。
5. 示例全部使用 `example` / `demo` / `sample` 等通用名称。
6. 截图使用干净测试数据。
7. 打包前不包含 `data`、图库、数据库、缓存、历史 zip 或上游源码镜像。
8. README 单独写隐私说明。
9. 模型只显示文件名或脱敏名称，不展示本机完整路径。
10. 发布包经过隐私关键字扫描。

## 安装

插件只能在 QwenPaw 停止时安装：

```cmd
qwenpaw plugin install C:\path\to\qwenpaw-artifact-library-0.4.4.zip
```

安装后重新启动 QwenPaw。左侧栏会出现“产物库”。

## 性能边界

- 打开列表只读取已登记的元数据，**不会扫描磁盘，也不会读取所有文件内容**。
- 图片缩略图在卡片进入页面后按需生成，限制为 480×320 JPEG，并缓存到本地数据目录。
- 文本摘要最多读取 16KB；超过 16MB 的文本文件拒绝预览。
- 超过 80MB 的图片不生成缩略图。
- 音视频只读取轻量元信息；如系统没有 `ffprobe`，不额外安装依赖，也不进行解码。

## 隐私与存储

- 文件本体始终在原始位置；产物库只保存用户登记的元数据和小型图片缩略图缓存。
- 数据保存在 `%APPDATA%\QwenPaw\artifact-library\artifacts.json`，插件升级、重装不会丢失记录。
- 删除始终移入 Windows 回收站，绝不退化成永久删除。

## v0.4.4 已验证

第一遍：

- Python 静态编译通过。
- 前端 JavaScript `node --check` 通过。
- `test_notes.py`：13/13 通过。
- `test_integration.py`：49/49 通过。

第二遍：

- Python 静态编译通过。
- 前端 JavaScript `node --check` 通过。
- `test_notes.py`：13/13 通过。
- `test_integration.py`：49/49 通过。
- 解包检查确认：版本为 0.4.4；前端入口为 `ui/index.v0.4.4.js`；包内同时含兼容副本 `ui/index.js`；包内根目录含 `requirements.txt`；包内含生图库视图、`/generated-images` 路由、`ShellExecuteW`。

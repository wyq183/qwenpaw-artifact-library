# 产物库（QwenPaw 插件）

面向任何 QwenPaw Agent 的正式产物登记与管理插件。它不是扫描式文件管理器：**只有 Agent 主动登记的真实交付文件才会出现。**

## 已确定的规范

1. 只登记已经写入磁盘、值得保留或交付的成果；不登记缓存、日志、依赖、临时测试和中间文件。
2. 每个登记至少包含：文件路径、显示名称、简述、项目。
3. `交付项` 为空时自动使用显示名称。它用于区分同项目内不同成果，例如“主视觉 KV”“医疗站标识”“章节 001”。
4. 最终版唯一规则：**同一项目 + 同一交付项 + 同一类型，只能有一个最终版。** 新最终版会把旧最终版改为“已归档”，不会删除旧文件。
5. 删除只会调用 Windows 回收站，绝不以永久删除作为后备方案。
6. 文件本体保留在原路径；产物库只保存元数据，数据在插件自身的 `data/artifacts.json`。

## Agent 工具

Agent 在完成正式文件后调用：

```text
register_artifact(
  path="C:\\...\\output.pdf",
  title="项目报告终稿",
  summary="用于提交的 A4 PDF，包含目录与最终插图。",
  project="课程作业",
  deliverable="项目报告",
  artifact_type="document",
  tags=["提交", "终稿"],
  status="final"
)
```

`artifact_type` 可选值：`image`、`document`、`web`、`code`、`video`、`audio`、`archive`、`data`、`other`。不填时按扩展名推断。

`status` 可选值：`draft`（草稿）、`delivered`（已交付）、`final`（最终版）。

## 安装

插件只能在 QwenPaw 停止时安装：

```cmd
qwenpaw plugin install C:\path\to\qwenpaw-artifact-library
```

安装后重新启动 QwenPaw。左侧栏会出现“产物库”。

## 第一版范围

- `register_artifact` Agent 工具
- 左栏“产物库”页面
- 搜索与项目 / 类型 / 状态筛选
- 元数据与来源追溯
- 最终版自动归档规则
- 安全移入 Windows 回收站

## 已验证

- Python 静态编译通过
- 前端 JavaScript 语法检查通过
- 重复登记同一文件会被拒绝
- 新最终版会自动归档相同项目、交付项、类型下的旧最终版

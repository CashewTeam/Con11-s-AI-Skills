# AI Skills for Creative Production

本仓库汇集了面向**创意视频制作**的 AI Agent Skill 集合。每个 Skill 都是一个自包含的指令包，赋予 AI 助理特定的专业能力——从文案分析、分镜生成、字幕制作到完整的 Remotion 视频工程构建。

---

## 目录

- [Skills 概览](#skills-概览)
- [ReMotionDirector — Remotion 视频动效导演](#remotiondirector--remotion-视频动效导演)
- [Storyboard Pipeline — 文案一键分镜](#storyboard-pipeline--文案一键分镜)
- [Subtitle Tool — 独立字幕生成与校对工具](#subtitle-tool--独立字幕生成与校对工具)
- [DaVinci Subtitle — DaVinci Resolve 字幕集成](#davinci-subtitle--davinci-resolve-字幕集成)
- [快速开始](#快速开始)
- [相关项目](#相关项目)

---

## Skills 概览

| Skill | 描述 | 核心输出 |
|---|---|---|
| **ReMotionDirector** | 将创意文案转化为可编程的 Remotion 视频工程，含文案解析、模板匹配、组件生成全流程 | Remotion React/TypeScript 工程 |
| **Storyboard Pipeline** | 接收文案，自动分词分镜，生成带颜色标注的专业 Excel 分镜表 | `.xlsx` 分镜表文件 |
| **Subtitle Tool** | ASR 语音识别 + 强制对齐 + SRT 校对 + 翻译替换，无需 DaVinci | `.srt` 字幕文件 |
| **DaVinci Subtitle** | DaVinci Resolve 集成：导出音频、调用外部工具生成字幕、导入 SRT | `.srt` 字幕文件 |

### 基础设施

| 工具 | 描述 |
|------|------|
| **davinci-resolve-mcp-2.3.0-winfix** | 修复 Windows 路径查找后的 DaVinci Resolve MCP 服务器，所有字幕技能与 Resolve 交互的桥梁 |

---

## ReMotionDirector — Remotion 视频动效导演

将创意文案转化为**可编辑的 Remotion 视频工程**。它充当"导演"角色，通过两阶段流水线完成从文案到可运行 Remotion Studio 项目的完整交付。

### 核心理念

> 创意文案不是文字，是时间线上的视觉指令。

### 工作流程

```
用户文案 → 阶段一：文案解析（语义提取 · 情绪感知 · 分镜拆分）→ 结构化元数据
         → 阶段二：模板匹配与工程生成 → Remotion Studio 项目（Root.tsx + Scene组件）
```

**阶段一**由子 Skill **Copywriting Analyst** 执行：识别标题、关键词、数据指标、品牌实体、行动号召；判断文案情绪基调（科技冷峻 / 活泼跳跃 / 高端优雅 / 温暖亲切 / 戏剧张力）；按语义完整性切分段落并分配时长；输出包含场景列表、配色系统、字体方案、动效提示的完整 JSON 元数据。

**阶段二**执行模板匹配（按风格、场景结构、信息密度评分，≥70% 为候选）或从零生成。输出标准 Remotion 工程：1920×1080、60fps，每场景独立组件，每个 Composition 注册 Zod schema 暴露可编辑参数，通用视觉元素提取到 `components/` 目录。

生成完成后在目录下运行 `npx remotion studio` 即可预览和编辑。

---

## Storyboard Pipeline — 文案一键分镜

接收用户文案，在**单次 LLM 调用中**自动完成分词、镜头分配、画面编写，并输出带颜色标注的专业 Excel 分镜表。

### 工作流程

```
用户文案 → 分词（语义完整优先，绝不改变原文）→ 镜头分配 → 画面编写 → Markdown 表格 → .xlsx 分镜表
```

**分词原则**：语义完整 > 长度适中（6-25 字）> 信息清晰 > 节奏自然。绝不改变原文任何字词标点。

**镜头类型**：分四大类——实拍（推拉摇移俯仰特写等）、Aroll（口播类）、动效（2D/3D/后期特效/AI 生成等）、资料（历史影像/新闻/航拍等）。

**镜头组合策略**：快速切换（紧张快节奏）、慢速推进（情感渲染）、稳定镜头（平静叙述）、运动镜头（动态活力）。

**Excel 输出**：Markdown 自动转换为 `.xlsx`，按镜头类型着色——实拍红、Aroll 绿、动效紫、资料蓝。

---

## Subtitle Tool — 独立字幕生成与校对工具

基于 FunASR 的独立字幕工具集，覆盖完整字幕工作流：音频生成 → 强制对齐 → SRT 校对 → 翻译。**独立运行，不依赖 DaVinci Resolve。**

### 工作流程

```
┌─ 询问用户选择生成方式 ────────────────┐
│  ⭐ 推荐: 文稿匹配 (funasr align)      │
│     备选: FunASR ASR 云端/本地         │
└──────────────┬─────────────────────────┘
               ▼
       得到一个 SRT 文件
               │
               ├── ASR 错误太多? ──→ 构建 corrections.json
               │                      └── funasr-srt-tools.py convert-srt
               │
               ├── 需要繁/简/港版本? ──→ funasr-srt-tools.py convert-srt ... zh-tw
               │
               └── 需要翻译? ─────────→ LLM 生成 translation.json
                                        └── funasr-srt-tools.py apply-corrections
```

### 三种生成方式

| 方式 | 命令 | 适用场景 |
|------|------|----------|
| ⭐ **文稿匹配** | `funasr-srt-tools.py align` | 有精确文稿，字级精准对齐 |
| **云端 ASR** | `funasr-srt-tools.py asr` | 有网络，含英文/术语 |
| **本地 ASR** | `funasr-srt-tools.py asr --local` | 离线/隐私敏感 |

### 校对功能

- `read-srt` — 读取并解析 SRT 文件
- `convert-srt` — ASR 修正 + 繁简转换 + CJK 间距 + 标点修复
- `apply-corrections` — 翻译替换（LLM 生成 JSON 后执行）

---

## DaVinci Subtitle — DaVinci Resolve 字幕集成

自动化 DaVinci Resolve 的字幕工作流程中与 Resolve 交互的部分：音频导出 → 字幕生成 → 导入。
**校对与翻译由外部技能 Subtitle Tool 处理。**

### 工作流程

```
Resolve 项目 → 初始化 → 选择生成方式 → 导出 SRT → [可选: 外部校对] → 导入时间线
```

**Step 1**：初始化 — 验证 Resolve 连接，获取项目名称、列出时间线、检查起始时码。

**Step 2**：选择生成方式 — 4 种方式可选：
- ⭐ 文稿匹配（需文稿 + 音频）
- FunASR ASR 云端（需网络）
- FunASR ASR 本地（离线）
- DaVinci Resolve 内置（方式 D，无需导出音频）

方式 A/B/C 前会自动通过 `export-audio` 从时间线导出 WAV 音频。
方式 A 和校对前会使用 LLM 优化参考文本（拆分长句、修正标点、去除冗余）。

**Step 3（可选）**：校对/翻译 — 由 Subtitle Tool 外部技能处理。

**Step 4**：导入 SRT 到时间线 — 清理旧字幕轨道、创建新轨道、追加到时间线。

---

## 快速开始

### ReMotionDirector

**环境要求**：Node.js 18+，Remotion 项目模板（首次使用会自动初始化）

1. 准备创意文案（广告词、解说词、故事大纲等）
2. 将文案输入到启用了 ReMotionDirector Skill 的 AI 助理
3. AI 依次执行文案解析 → 模板匹配 → 工程生成
4. 在生成的 `ReMotionWorkPlace/` 目录中运行 `npx remotion studio`

### Storyboard Pipeline

**环境要求**：Python 3.8+，`pip install openpyxl`

1. 准备要分析的文案内容
2. 输入文案并指定期望的输出文件名（可选）
3. AI 自动完成分词、镜头分配、分镜编写，输出带颜色标注的 `.xlsx` 分镜表

### Subtitle Tool

**环境要求**：Python 3.8+，`pip install funasr torch zhconv`

1. 准备音频文件（WAV/MP3）和/或参考文稿（.txt）
2. 选择生成方式：文稿匹配 / 云端 ASR / 本地 ASR
3. 按需校对或翻译生成的字幕

### DaVinci Subtitle

**环境要求**：DaVinci Resolve Studio 18.5+、Python 3.8+、DaVinci Resolve MCP Server

1. 在 DaVinci Resolve 中打开包含音频的时间线项目
2. 配置 `RESOLVE_SCRIPT_API` 环境变量，启动 MCP Server
3. AI 依次执行：初始化 → 选择生成方式 → 导出音频/SRT → 导入时间线
4. 按需切换至 Subtitle Tool 外部技能进行校对或翻译

---

## 相关项目

- [**remotion-dev/remotion**](https://github.com/remotion-dev/remotion) — Remotion 视频渲染框架，本仓库所有 Remotion 工程生成的底层基础设施
- [**ConardLi/garden-skills**](https://github.com/ConardLi/garden-skills) — Web Design Engineer 及其他 AI Skill 集合，ReMotionDirector 的指导思想参考
- [**samuelgursky/davinci-resolve-mcp**](https://github.com/samuelgursky/davinci-resolve-mcp) — DaVinci Resolve MCP Server，Subtitle 系列技能与 Resolve 交互的桥梁

---

## 目录结构

```
skills/
├── ReMotionDirector/                  ← 视频动效导演 Skill
│   ├── SKILL.md
│   └── copywriting-analyst/
│       ├── SKILL.md
│       └── references/
│           └── advanced-patterns.md
├── storyboard-pipeline/               ← 分镜流水线 Skill
│   ├── SKILL.md
│   ├── md_table_to_excel.py
│   └── requirements.txt
└── ...

Skills/                                ← .trae/skills/
├── subtitle-skill/                    ← 独立字幕工具
│   ├── SKILL.md
│   ├── funasr-srt-tools.py
│   └── funasr_config.toml
└── davinci-subtitle-skill/            ← DaVinci 字幕集成
    ├── SKILL.md
    └── subtitles_auto.py
```

---

## 许可证

本项目采用 **MIT License**。

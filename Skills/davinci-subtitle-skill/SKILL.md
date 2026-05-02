# 自动字幕生成与优化 — AI 技能（DaVinci 集成）

本技能自动化 DaVinci Resolve 的字幕工作流程中与 Resolve 交互的部分：
音频导出 → 字幕生成 → 导入。

**校对与翻译由 `subtitle-skill` 外部技能处理**，本技能仅需调用其输出结果。

---

## 平台兼容性

本技能主要在 macOS 上开发。辅助脚本 `subtitles_auto.py` 通过环境变量自动检测平台。

### Python 虚拟环境路径

| 平台 | 路径 |
|---|---|
| macOS / Linux | `{MCP_ROOT}/venv/bin/python` |
| Windows | `{MCP_ROOT}/venv\\Scripts\\python.exe` |

SKILL.md 默认使用 `{MCP_ROOT}/venv/bin/python`。在 **Windows** 上，请替换为 `{MCP_ROOT}\venv\Scripts\python.exe`，并全程使用 `\` 作为路径分隔符。

### 环境变量

脚本优先从环境读取 `RESOLVE_SCRIPT_API`。如果已设置，则使用该值；否则回退到 macOS 默认路径。

| 平台 | `RESOLVE_SCRIPT_API` |
|---|---|
| macOS | `/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting` |
| Windows | `%PROGRAMDATA%\\Blackmagic Design\\DaVinci Resolve\\Support\\Developer\\Scripting` |
| Linux | `/opt/resolve/Developer/Scripting` |

在运行任何命令前设置环境变量：

**macOS / Linux：**
```bash
export RESOLVE_SCRIPT_API="/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting"
export RESOLVE_SCRIPT_LIB="/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so"
export PYTHONPATH="$RESOLVE_SCRIPT_API/Modules"
```

**Windows（PowerShell）：**
```powershell
$env:RESOLVE_SCRIPT_API = "$env:PROGRAMDATA\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting"
$env:RESOLVE_SCRIPT_LIB = "C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll"
$env:PYTHONPATH = "$env:PYTHONPATH;$env:RESOLVE_SCRIPT_API\Modules"
```

### 路径分隔符

- **Python**（`subtitles_auto.py`）：全程使用 `os.path.join()`，自动使用正确的分隔符（macOS/Linux 用 `/`，Windows 用 `\`）。
- **SKILL.md / CLI 示例**：为便于阅读，使用 `/` 编写。在 Windows 上键入命令时，请将 `/` 替换为 `\`。

---

## 目录结构

本技能中所有路径均相对于 **Agent 的当前工作目录（`{CWD}`）**。
`{MCP_ROOT}` 指 `davinci-resolve-mcp-main` 项目目录。

```
{CWD}/
├── subtitle-skill/                  # 外部字幕技能（校对/翻译）
│   ├── SKILL.md                     # 外部技能文档
│   ├── funasr-srt-tools.py          # ASR/校对/翻译脚本
│   └── funasr_config.toml
├── davinci-subtitle-skill/          # 本技能文件夹（DaVinci 集成）
│   ├── SKILL.md                     # 本文件
│   ├── subtitles_auto.py            # DaVinci 集成脚本
│   └── ...
├── davinci-resolve-mcp-main/        # MCP 服务器
│   └── src/server.py
├── {project_name}_subtitles_raw.srt      # 步骤 2 生成的原始字幕
└── {project_name}_audio.wav              # 步骤 2 导出的音频
```

---

## 所需工具

| 工具 | 路径 | 说明 |
|---|---|---|
| DaVinci MCP 服务器 | `{MCP_ROOT}/src/server.py` | 与 Resolve 通信的桥梁，提供 timeline/project 等控制工具 |
| 辅助脚本 | `davinci-subtitle-skill/subtitles_auto.py` | 初始化、音频导出、生成(方式D)、导入 SRT |
| 外部技能脚本 | `subtitle-skill/funasr-srt-tools.py` | 方式 A/B/C 生成字幕、校对、翻译均需使用 |
| 虚拟环境 Python | `{MCP_ROOT}/venv/bin/python` | 运行上述脚本 |

---

## 运行辅助脚本

所有命令均使用虚拟环境 Python，从 `{CWD}` 运行：

```
{MCP_ROOT}/venv/bin/python davinci-subtitle-skill/subtitles_auto.py <command> [args...]
```

需要设置环境变量（每个 shell 会话设置一次）：

```bash
export RESOLVE_SCRIPT_API="/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting"
export RESOLVE_SCRIPT_LIB="/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so"
export PYTHONPATH="$RESOLVE_SCRIPT_API/Modules"
```

或者内联方式（macOS/Linux）：

```bash
RESOLVE_SCRIPT_API="..." RESOLVE_SCRIPT_LIB="..." PYTHONPATH="$RESOLVE_SCRIPT_API/Modules" \
  {MCP_ROOT}/venv/bin/python davinci-subtitle-skill/subtitles_auto.py version
```

或者内联方式（Windows PowerShell）：

```powershell
$env:RESOLVE_SCRIPT_API="..."; $env:RESOLVE_SCRIPT_LIB="..."; $env:PYTHONPATH="$env:RESOLVE_SCRIPT_API\Modules"; \
  {MCP_ROOT}\venv\Scripts\python.exe davinci-subtitle-skill/subtitles_auto.py version
```

---

## 分步工作流程（4 步）

### 第 1 步：初始化

运行 `init` 命令以验证 Resolve 是否已连接、获取当前项目名称、列出所有时间线并检查起始时码 —— 一步完成：

```
{MCP_ROOT}/venv/bin/python davinci-subtitle-skill/subtitles_auto.py init
```

预期响应：
```json
{
  "version": {"product": "DaVinci Resolve Studio", "version_string": "20.1.0.20"},
  "project_name": "MyProject",
  "timelines": [
    {"index": 1, "name": "Timeline 1", "start_timecode": "00:00:00;00", ...}
  ],
  "current_timeline": "Timeline 1",
  "start_timecode": "00:00:00;00"
}
```

`project_name` 在整个技能中用作文件名中的 `{project_name}`。

如果响应中包含 `warning` 字段（起始时码不以 `00` 开头），请警告用户：SRT 使用从 `00:00:00,000` 开始的帧相对时间，在其他平台上可能不对齐。建议他们先使用 `timeline(action="set_start_timecode", params={"timecode": "00:00:00:00"})`。

- **1 条时间线**：自动继续。
- **多条时间线**：询问用户使用哪一条，然后切换：

```
{MCP_ROOT}/venv/bin/python davinci-subtitle-skill/subtitles_auto.py set-timeline <index>
```

### 第 2 步：选择字幕生成方式

在执行生成前，**必须询问用户选择哪种方式**，按以下优先级推荐：

| 优先级 | 方式 | 命令 | 适用场景 |
|--------|------|------|----------|
| ⭐ **推荐** | **文稿匹配（强制对齐）** | `subtitle-skill/funasr-srt-tools.py align` | 有精确文稿，字级精准对齐，准确率最高 |
| 备选 1 | FunASR ASR（云端） | `subtitle-skill/funasr-srt-tools.py asr` | 有网络，含英文/术语，无需文稿 |
| 备选 2 | FunASR ASR（本地） | `subtitle-skill/funasr-srt-tools.py asr --local` | 离线/隐私敏感，快速粗剪 |
| 备选 3 | DaVinci Resolve 内置 | `davinci-subtitle-skill/subtitles_auto.py generate` | 已在 Resolve 中工作，无需额外依赖 |

**推荐逻辑：**
1. **用户有文稿（.txt）** → 推荐 `align`（强制对齐，字级精准）
2. **用户有网络且无文稿** → 推荐 `asr`（云端 ASR，英文/术语支持好）
3. **用户需离线或无网络** → 推荐 `asr --local`（本地 ASR）
4. **用户已在 DaVinci Resolve 中编辑** → 可使用 `generate`

> 选择方式 A/B/C 时，需要先将时间线音频导出为 WAV 文件。使用 `export-audio` 命令自动完成：

```
{MCP_ROOT}/venv/bin/python davinci-subtitle-skill/subtitles_auto.py export-audio ./{project_name}_audio.wav
```

此命令会自动设置 WAV 格式、仅导出音频、渲染等待，完成后恢复原始渲染设置。
导出的音频文件 `./{project_name}_audio.wav` 将直接用于后续的字幕生成。

#### 优化参考文本（方式 A 和校对前使用）

用户提供的文稿或 ASR 识别文本中常有**超长语句**和格式问题，会导致字幕换行不当、阅读困难。**Agent 应主动帮用户优化文本**，规则如下：

- **拆分长句**：每行控制在 20-30 个字符，过长句子按语义拆分为多条
- **修正标点**：统一全半角、补充缺失句号
- **去除冗余**：删除口头禅、重复词（如"嗯、呃、那个"）
- **规范术语**：统一大小写和专业术语写法

优化后写入临时文件供后续步骤使用：

```
./{project_name}_text_optimized.txt
```

#### 方式 A：文稿匹配（强制对齐）⭐ 推荐

音频 + 优化后的参考文稿 → 字级精准对齐的 SRT：

```
python subtitle-skill/funasr-srt-tools.py align ./{project_name}_audio.wav ./{project_name}_text_optimized.txt -o ./{project_name}_subtitles_raw.srt
```

**前提：** 用户需提供文稿文件（.txt）。音频由 `export-audio` 自动导出。

#### 方式 B：FunASR ASR（云端）

音频 → SRT，无需文稿，适合含英文/术语的场景：

```
python subtitle-skill/funasr-srt-tools.py asr ./{project_name}_audio.wav -o ./{project_name}_subtitles_raw.srt
```

**前提：** 需要网络和配置 API Key。音频由 `export-audio` 自动导出。

#### 方式 C：FunASR ASR（本地）

离线运行，数据不出本机：

```
python subtitle-skill/funasr-srt-tools.py asr ./{project_name}_audio.wav --local -o ./{project_name}_subtitles_raw.srt
```

**前提：** 需要安装 `funasr` 依赖。音频由 `export-audio` 自动导出。

#### 方式 D：DaVinci Resolve 内置

利用 Resolve 自带的语音转文字功能生成，**无需导出音频**：

```
{MCP_ROOT}/venv/bin/python davinci-subtitle-skill/subtitles_auto.py generate 24
```

预期：
```json
{"success": true, "count": 5, "items": [...]}
```

生成后需将字幕导出为 SRT 供后续校对：

```
{MCP_ROOT}/venv/bin/python davinci-subtitle-skill/subtitles_auto.py export-srt
```

→ 写入 `./{project_name}_subtitles_raw.srt`（使用项目名称作为前缀）

### 第 3 步：[可选] 校对字幕

> **校对、繁简转换、翻译功能由外部技能 `subtitle-skill` 处理。**
> 用户需要校对时，切换到 `subtitle-skill/SKILL.md` 按指引操作，完成后获取校正后的 SRT 文件。

- 方式 A（文稿匹配）：字幕已字级精准，通常无需校对
- 方式 B/C/D（语音识别）：若用户需要校对，引导其使用 `subtitle-skill/funasr-srt-tools.py convert-srt`

### 第 4 步：将 SRT 导入时间线

导入 SRT 文件到时间线（文件路径取决于第 2 步直接生成或第 3 步外部技能返回的路径）：

```
{MCP_ROOT}/venv/bin/python davinci-subtitle-skill/subtitles_auto.py import-srt ./{project_name}_subtitles_raw.srt
```

> 若使用了外部技能校对/翻译，将 SRT 路径替换为校正后的文件（如 `./{project_name}_subtitles_zh-cn.srt`）。

此操作：
1. 清理媒体池中的旧 SRT 片段
2. 删除当前字幕轨道
3. `ImportMedia` → 将 SRT 导入媒体池
4. `AddTrack("subtitle")` → 创建新的字幕轨道
5. `AppendToTimeline([clip_object])` → 使用剪辑**对象**追加（不是剪辑 ID 字符串 —— 关键！）

预期：
```json
{"success": true, "count": 5, "items": [{"start": 18, "end": 69, "text": "你好你好，这是一个用于测试"}, ...]}
```

---

## 完整工作流程示例（方式 D：DaVinci 内置）

```bash
# 1. 初始化
→ {MCP_ROOT}/venv/bin/python davinci-subtitle-skill/subtitles_auto.py init

# 2. 生成字幕并导出原始 SRT
→ {MCP_ROOT}/venv/bin/python davinci-subtitle-skill/subtitles_auto.py generate 24
→ {MCP_ROOT}/venv/bin/python davinci-subtitle-skill/subtitles_auto.py export-srt

# 3. 导入原始 SRT（如需校对/翻译，先切换至 subtitle-skill 处理再导入）
→ {MCP_ROOT}/venv/bin/python davinci-subtitle-skill/subtitles_auto.py \
    import-srt ./{project_name}_subtitles_raw.srt
```

---

## 附录：翻译与校对

**翻译与校对功能由外部技能 `subtitle-skill` 处理。** 详见 `subtitle-skill/SKILL.md`：

| 需求 | 外部技能命令 | 说明 |
|------|-------------|------|
| 校对字幕 | `subtitle-skill/funasr-srt-tools.py convert-srt` | ASR 修正 + 繁简转换 |
| 翻译字幕 | `subtitle-skill/funasr-srt-tools.py apply-corrections` | LLM 生成翻译后应用 |
| 读取 SRT | `subtitle-skill/funasr-srt-tools.py read-srt` | 解析 SRT 为 JSON |

外部技能处理完毕后的 SRT 文件，再通过本技能的 `import-srt` 命令导回时间线。

---

## 错误处理

| 错误 | 可能原因 | 解决方法 |
|---|---|---|
| `"DaVinci Resolve is not running"` | Resolve 已关闭或脚本被禁用 | `resolve_control(action="launch")` |
| `"No project is currently open"` | 未加载项目 | `project_manager(action="load", ...)` |
| `"No timeline is currently active"` | 未设置时间线 | `timeline(action="set_current", ...)` |
| `"Failed to set render format to WAV/PCM"` | Resolve 不支持该格式 | 检查 Resolve Studio 版本，确保支持 WAV 导出 |
| `"Failed to start render job"` | 渲染队列被占用或时间线无内容 | 确保时间线有至少一个音频/视频片段 |
| `"Failed to generate subtitles"` | 无音频 / 未检测到语音 | 确保时间线包含带语音的音频 |
| `"Failed to import SRT"` | `ImportMedia` 返回空 | 检查 SRT 路径是否存在、是否为有效的 UTF-8 |
| `"Failed to append subtitles"` | `AppendToTimeline` 参数类型错误 | 传递剪辑**对象**，而不是剪辑 ID 字符串 |

## CLI 参考

### subtitles_auto.py（DaVinci 集成）

```
python davinci-subtitle-skill/subtitles_auto.py <command> [args...]

Commands:
  init                           验证连接、获取项目名称、列出时间线、检查起始时码
  version                        检查 Resolve 版本
  list-timelines                 列出所有时间线
  set-timeline <index>           按索引切换时间线
  export-audio [output_path]     将时间线音频导出为 WAV（默认: ./<project>_audio.wav）
  generate [chars_per_line=24]   从音频生成字幕
  export-srt [output_path]       将字幕导出为 SRT
  import-srt <srt_path>          将 SRT 作为字幕轨道导回时间线
```

校对/翻译命令（`read-srt` / `convert-srt` / `apply-corrections`）请参见 `subtitle-skill/SKILL.md`。

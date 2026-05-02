---
name: "subtitle-skill"
description: "Generates SRT subtitles from audio using ASR (cloud/local) or forced alignment with reference text. Invoke when user needs speech-to-text subtitles, caption generation, or audio-text alignment for video workflows."
---

# Subtitle Skill - SRT 字幕生成工具集

覆盖完整字幕工作流：从音频生成 → SRT 校对 → 导入 → 翻译。

## 生成方式选择

在执行字幕生成前，**必须询问用户选择哪种方式**，推荐顺序如下：

| 优先级 | 方式 | 命令 | 适用场景 |
|--------|------|------|----------|
| ⭐ **推荐** | **文稿匹配（强制对齐）** | `funasr-srt-tools.py align` | 有精确文稿，字级精准对齐，准确率最高 |
| 备选 1 | FunASR ASR（云端） | `funasr-srt-tools.py asr` | 有网络，含英文/术语，无需文稿 |
| 备选 2 | FunASR ASR（本地） | `funasr-srt-tools.py asr --local` | 离线/隐私敏感，快速粗剪 |

### 推荐逻辑

1. **用户有文稿（.txt）** → 推荐 `align`（强制对齐，字级精准）
2. **用户有网络且无文稿** → 推荐 `asr`（云端 ASR，英文/术语支持好）
3. **用户需离线或无网络** → 推荐 `asr --local`（本地 ASR）

---

## 统一工作流程

```
┌─ 询问用户选择生成方式 ─────────────────┐
│                                         │
│  ⭐ 推荐: 文稿匹配 (funasr align)       │
│     备选: FunASR ASR 云端/本地          │
└─────────────────┬───────────────────────┘
                  ▼
          得到一个 SRT 文件
                  │
                  ├── ASR 错误太多? ──→ 构建 corrections.json
                  │                      └── funasr-srt-tools.py convert-srt ...
                  │
                  ├── 需要繁/简/港版本? ──→ funasr-srt-tools.py convert-srt ... zh-tw
                  │
                  └── 需要翻译? ─────────→ LLM 生成 translation.json
                                           └── funasr-srt-tools.py apply-corrections ...
```

---

## 工具索引

| 脚本 | 路径 | 功能 |
|------|------|------|
| `funasr-srt-tools.py` | `subtitle-skill/funasr-srt-tools.py` | ASR 生成、强制对齐、SRT 校对、翻译替换 |

---

## 参考文本优化（LLM 预处理）

文稿匹配和校对前，**Agent 应主动帮用户优化参考文本**，解决常见字幕问题：

| 问题 | 说明 | 示例 |
|------|------|------|
| **超长语句** | 每行控制在 20-30 字符，按语义拆分为多条 | `"高斯泼溅是一种全新的三维表示方法它通过..."` → 拆分为 2-3 条 |
| **标点缺失** | 补充缺失的句号、逗号，统一全半角 | `"你好吗我很好"` → `"你好吗？我很好。"` |
| **去除冗余** | 删除口头禅、重复词 | `"嗯然后呢就是那个高斯泼溅"` → `"高斯泼溅"` |
| **规范术语** | 统一大小写和专业术语写法 | `"Gaussian splatting"` → `"高斯泼溅"` |

优化后写入临时文件供后续步骤使用：

```
./{project_name}_text_optimized.txt
```

---

## 方式一：文稿匹配（强制对齐） ⭐ 推荐

音频 + 优化后的参考文稿 → 字级精准对齐的 SRT。

```bash
python funasr-srt-tools.py align <音频文件> <优化后文稿.txt> [选项]
```

```bash
# 基本用法
python funasr-srt-tools.py align audio.wav transcript.txt
python funasr-srt-tools.py align audio.wav transcript.txt -o aligned.srt
```

### 参数

| 参数 | 说明 |
|------|------|
| `audio` | 音频文件路径 (WAV/MP3) |
| `text` | 参考文本文件路径 (TXT) |
| `-o, --output` | 输出 SRT 路径（默认同音频名 _aligned.srt） |
| `--model` | 模型名 (默认 fa-zh) |
| `--device` | 设备 cpu/cuda |
| `--max-chars` | 每句字数上限 (0=按标点) |
| `--no-verify` | 不显示预览 |

### 原理

1. 使用 FunASR `fa-zh` 模型对音频 + 文稿做强制对齐
2. 输出每个字符的 `(开始毫秒, 结束毫秒)`
3. 按文稿标点断句，生成 SRT

---

## 方式二：FunASR ASR（云端）

音频 → SRT，无需文稿，适合含英文/术语的场景。

```bash
python funasr-srt-tools.py asr <音频文件> [选项]
```

支持语言: `zh`(中文), `en`(英文), `yue`(粤语), `ja`(日语), `ko`(韩语)

```bash
# 云端模式（默认，推荐含英文术语的场景）
python funasr-srt-tools.py asr audio.wav
python funasr-srt-tools.py asr audio.mp3 --lang en --output subtitles.srt
```

**首次使用云端前配置 API Key** — 编辑同目录下的 `funasr_config.toml`，完整配置项如下：
```toml
# 阿里云 DashScope API Key（也可通过环境变量 DASHSCOPE_API_KEY 设置）
api_key = "sk-你的API密钥"
model = "fun-asr"
region = "cn"
max_words = 0
lang = "zh"
align_model = "fa-zh"
align_device = "cpu"
audio_sample_rate = 16000
audio_channels = 1
ffmpeg_timeout = 300
transcription_max_retries = 600
transcription_poll_interval = 2
convert_srt_default_lang = "zh-cn"
```

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `api_key` | — | 阿里云 DashScope API Key |
| `model` | `"fun-asr"` | 云端 ASR 模型名 |
| `region` | `"cn"` | 服务区域 (`cn` / `intl`) |
| `max_words` | `0` | 每句词数上限 (0=按标点) |
| `lang` | `"zh"` | 默认 ASR 识别语言 |
| `align_model` | `"fa-zh"` | 强制对齐模型名 |
| `align_device` | `"cpu"` | 对齐推理设备 |
| `audio_sample_rate` | `16000` | 音频归一化采样率 |
| `audio_channels` | `1` | 音频归一化声道数 |
| `ffmpeg_timeout` | `300` | ffmpeg 处理超时(秒) |
| `transcription_max_retries` | `600` | 云端 ASR 最大轮询次数 |
| `transcription_poll_interval` | `2` | 轮询间隔(秒) |
| `convert_srt_default_lang` | `"zh-cn"` | convert-srt 默认目标语言 |

或设置环境变量 `DASHSCOPE_API_KEY`。

### 参数

| 参数 | 说明 |
|------|------|
| `audio` | 音频文件路径 (WAV/MP3/M4A) |
| `-o, --output` | 输出 SRT 路径（默认同音频名） |
| `-l, --lang` | 语言 (zh/en/yue/ja/ko) |
| `-w, --max-words` | 每句词数上限 (0=按标点, >0 加安全上限) |
| `--no-upload` | 跳过上传，直接使用 audio 参数作为文件 URL |
| `--no-verify` | 不显示预览 |

---

## 方式三：FunASR ASR（本地）

离线运行，数据不出本机，适合隐私敏感场景。

```bash
python funasr-srt-tools.py asr <音频文件> --local [选项]
```

```bash
# 本地模式（离线，无需 API Key）
python funasr-srt-tools.py asr audio.wav --local
python funasr-srt-tools.py asr audio.mp3 --local --model-name SenseVoiceSmall --device cuda
```

依赖 `pip install funasr`，默认模型 `paraformer-zh`（中文），可选 `SenseVoiceSmall`（多语言）。

### 参数

| 参数 | 说明 |
|------|------|
| `audio` | 音频文件路径 (WAV/MP3/M4A) |
| `-o, --output` | 输出 SRT 路径（默认同音频名） |
| `-l, --lang` | 语言 (zh/en/yue/ja/ko) |
| `-w, --max-words` | 每句词数上限 |
| `--local` | 启用本地模式 |
| `--model-name` | 本地模型名 (默认 paraformer-zh) |
| `--device` | 推理设备 cpu/cuda |
| `--model-dir` | 指定已下载模型目录 |
| `--no-verify` | 不显示预览 |

---

## `read-srt` — 读取 SRT 文件

将 SRT 解析为结构化 JSON 输出，用于查看条目结构或输入到其他工具。

```bash
python funasr-srt-tools.py read-srt <srt文件> [选项]
```

```bash
# 基本用法
python funasr-srt-tools.py read-srt subtitles.srt

# 保存为 JSON
python funasr-srt-tools.py read-srt subtitles.srt --json-output subtitles.json
```

### 参数

| 参数 | 说明 |
|------|------|
| `path` | SRT 文件路径 |
| `--json-output` | 将解析结果保存为 JSON 文件 |
| `--no-verify` | 不保存 JSON 输出 |

---

## `convert-srt` — 转换/校对 SRT

对现有 SRT 进行 **ASR 错误修正 + 繁简转换 + CJK 间距修复 + 标点修复**，保留所有时码和条目数。

```bash
python funasr-srt-tools.py convert-srt <输入.srt> [输出.srt] [语言] [修正.json]
```

```bash
# 简体转换
python funasr-srt-tools.py convert-srt raw.srt output.srt zh-cn

# 繁体 + ASR 修正
python funasr-srt-tools.py convert-srt raw.srt output.srt zh-tw corrections.json

# 简体 + 修正，省略输出路径（自动为 {输入}_{语言}.srt）
python funasr-srt-tools.py convert-srt raw.srt --lang zh-cn corrections.json
```

### 处理流程（4 步）

| 步骤 | 功能 | 说明 |
|------|------|------|
| 1 | ASR 错误修正 | 从 corrections.json 读取 `{错误: 正确}` 逐条替换 |
| 2 | 繁简转换 | 使用 `zhconv` 库转换（zh-cn / zh-tw / zh-hk） |
| 3 | CJK 间距 | 消除中英文之间多余空格 |
| 4 | 标点修复 | 全半角统一、省略号规范化、引号转直角引号 |

**核心原则**：时码永远不动，条目数永远不变。

### 参数

| 参数 | 说明 |
|------|------|
| `input` | 输入 SRT 文件路径 |
| `output` | 输出 SRT 路径（默认: `{input}_{lang}.srt`） |
| `lang` | 目标语言: zh-cn(简体), zh-tw(繁体), zh-hk(香港) |
| `corrections` | 修正 JSON 文件路径（可选） |
| `--no-verify` | 不显示预览 |

### corrections.json 格式

```json
{
  "高斯坡键": "高斯泼溅",
  "微信one": "Vision Pro",
  "三d": "3D",
  "四d": "4D"
}
```

> 构建 `corrections.json` 时，Agent 可同时结合 LLM 优化文本（拆分超长语句、补充标点、去除冗余），将优化后的文本作为正确值写入修正文件。

---

## `apply-corrections` — 翻译替换

保留所有时码，仅对文本进行纯文本替换。用于 **翻译场景**：

1. LLM 读取 SRT 文本 → 生成 `{原文: 译文}` 的 JSON
2. 此命令应用修正，输出翻译后的 SRT

```bash
python funasr-srt-tools.py apply-corrections <输入.srt> <输出.srt> <修正.json>
```

```bash
python funasr-srt-tools.py apply-corrections zh.srt en.srt translation.json
```

### parameters

| 参数 | 说明 |
|------|------|
| `input` | 输入 SRT 文件路径 |
| `output` | 输出 SRT 路径 |
| `corrections` | 修正 JSON 文件路径 ({原文: 译文}) |
| `--no-verify` | 不显示预览 |

### translation.json 格式

```json
{
  "如果你近段时间有关注三维技术和计算机图形学的发展": "If you've been following 3D technology and computer graphics lately",
  "我想你已经听说过高斯泼溅了": "you've probably heard of Gaussian Splatting"
}
```

---

## 完整工作流程示例

### 方法 A：文稿匹配（推荐）

```bash
# 0. 用 LLM 优化参考文本（拆分长句、修正标点、去除冗余）
#    写入 project_text_optimized.txt

# 1. 强制对齐生成字幕
python funasr-srt-tools.py align audio.wav project_text_optimized.txt -o project_subtitles_raw.srt

# 2. 读取并检查
python funasr-srt-tools.py read-srt project_subtitles_raw.srt

# 3. 结合优化后的文本构建 corrections.json → 转换
python funasr-srt-tools.py convert-srt project_subtitles_raw.srt project_subtitles_zh_cn.srt zh-cn corrections.json
```

### 翻译（任一种方法生成后）

```bash
# LLM 生成 translation.json
python funasr-srt-tools.py apply-corrections project_subtitles_zh_cn.srt project_subtitles_en.srt translation.json
```

---

## 依赖安装

```bash
# 云端 ASR
pip install dashscope

# 本地 ASR / 强制对齐
pip install funasr torch

# SRT 校对（繁简转换）
pip install zhconv

# 音频预处理（自动调用 ffmpeg）
# 需要系统中已安装 ffmpeg
```

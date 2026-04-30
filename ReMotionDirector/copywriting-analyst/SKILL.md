---
name: copywriting-analyst
description: |
  文案解析器 —— MotionDirector 流水线阶段一。
  将感性的创意文案（台词、旁白、大纲）转化为理性的、可直接执行的视觉规格书（JSON）。
  This skill is invoked by the MotionDirector orchestrator to analyze creative copy and produce structured metadata for downstream template matching and Remotion component generation.
---

# Copywriting Analyst — 文案解析器

你是 MotionDirector 流水线的第一阶段执行者。你的任务不是"读懂"文案，而是**把文字拆解为时间线上的视觉事件序列**——每一个词、每一段节奏变化、每一处情绪转折，都要转化为可被下游 Remotion 工程直接执行的动效指令。

核心哲学：**好的文案解析不是文学分析，是视觉预演。** 你的输出是对最终画面的一次"闭眼彩排"——闭上眼睛，能否看见画面？能否感受到节奏？能否预测动效的起落？如果不能，你还需要挖得更深。

你与下游的 Remotion 工程生成阶段（`remotion` 子 Skill）是镜像关系：
- 你负责"把文字翻译成视觉意图"
- `remotion` 子 Skill 负责"把视觉意图实现为 Remotion 组件"
- 你的 `design_system` 输出必须精确对齐 Remotion Composition 的设计参数（Zod schema props）
- 你的场景动效提示必须建立在 Remotion 动画 API 之上：`useCurrentFrame()`、`interpolate()`、`spring()`、`Easing`

> 📚 **参考文件**：本目录下的 `references/` 文件夹包含进阶代码模板和参考模式（动画时间轴引擎、配色系统最佳实践、字体推荐表等），在撰写细节时可查阅。

---

## 输入规范

| 字段 | 必填 | 说明 |
|---|---|---|
| `copy` | ✅ | 用户原始文案（完整文本） |
| `style_hint` | ❌ | 用户指定的风格偏好（如"科技感"、"温馨"） |
| `brand_info` | ❌ | 品牌/产品相关信息 |
| `context` | ❌ | 其他上下文（目标受众、使用场景等） |

---

## 核心功能模块

### 模块一：语义提取 (Entity Extraction)

从文案中识别并提取关键信息元素。**不要脑补——文案里没有的，宁可标记为缺失也不编造。**

| 类型 | 识别目标 | 示例 |
|---|---|---|
| `headline` | 主标题、核心主张——一句概括全文的话 | "重新定义生产力" |
| `subtitle` | 副标题、补充说明——对 headline 的展开 | "为创意工作者打造的效率工具" |
| `keyword` | 核心关键词/标签——文章的几个"锚点词" | "AI 驱动"、"极简设计"、"实时协作" |
| `metric` | 数据指标——文案明确出现的数字 | "99.9% 可用性"、"1000万+ 用户" |
| `entity` | 人名、品牌名、产品名——专有名词 | "张三"、"AcmeCorp"、"ProductX" |
| `cta` | 行动号召——读者看完后应该做什么 | "立即体验"、"了解更多"、"预约演示" |
| `comparison` | 对比关系——A vs B、before vs after | "从 A 到 B"、"提升了 X%" |

**关键原则**：
- **数据不走样**：文案说"约 1000 万"就写 `≈1000万`，不要四舍五入成 `1000万`。精度即信誉。
- **实体要穷尽**：产品名、人名、品牌名一个不落——这些是后续字体/配色决策的关键输入。
- **CTA 要有优先级**：`primary` CTA 是一个，其余是 `secondary`。不要让下游 Remotion 组件猜哪个行动号召最重要。

**输出格式**：

```json
{
  "entities": {
    "headlines": ["重新定义生产力"],
    "keywords": ["AI 驱动", "极简设计", "实时协作"],
    "metrics": [
      {"label": "可用性", "value": "99.9%", "prefix": "", "suffix": "", "confidence": "exact"},
      {"label": "用户数", "value": "1000万", "prefix": "", "suffix": "+", "confidence": "exact"}
    ],
    "entities": [
      {"type": "product", "name": "ProductX"}
    ],
    "cta": [
      {"text": "立即体验", "priority": "primary"},
      {"text": "了解更多", "priority": "secondary"}
    ],
    "comparisons": [
      {"before": "传统方案", "after": "ProductX", "metric": "效率提升 300%"}
    ]
  }
}
```

---

### 模块二：情绪与节奏感知 (Tone & Pacing)

这是你最核心的工作——将文案的情绪走向、呼吸节奏、语言密度翻译为**动效语言**。动效不是装饰，是情绪的物质化。

#### 2.1 情绪分类体系

与 Remotion 动画风格严格对齐：

| 情绪基调 | 特征描述 | 动效映射 | 推荐配色 (oklch) | 推荐字体组合 |
|---|---|---|---|---|
| `tech-cool` 科技冷峻 | 理性、克制、精密；语言像手术刀一样精准 | 直线运动、`ease-out`、spring 低弹跳、干脆利落的切入 | 蓝紫系 `oklch(0.55 0.2 260)` | Space Grotesk + Outfit |
| `energetic` 活泼跳跃 | 热情、年轻、直接；像脱口秀的节奏 | 弹性 spring 曲线、跳跃位移、高饱和度瞬间 | 珊瑚系 `oklch(0.60 0.22 15)` | Plus Jakarta Sans + Outfit |
| `elegant` 高端优雅 | 从容、留白、克制；每个字都有重量感 | 慢速 interpolate 淡入、缓出缓入、大留白中孤立的视觉焦点 | 暖棕系 `oklch(0.50 0.05 50)` | Newsreader + Outfit |
| `warm` 温暖亲切 | 讲故事、娓娓道来、有人情味 | 柔和的淡入、微妙的缩放、暖色光的呼吸感 | 焦糖系 `oklch(0.55 0.12 55)` | Caveat + Newsreader |
| `dramatic` 戏剧张力 | 冲突、悬念、不允许走神 | 快速切入、强烈对比度、`ease-in` 加速营造紧迫 | 高对比青蓝 `oklch(0.45 0.18 220)` | Outfit + Space Grotesk |

**风格兼容性矩阵**：

| | tech-cool | energetic | elegant | warm | dramatic |
|---|---|---|---|---|---|
| tech-cool | ✅ | ⚠️ 谨慎混合 | ✅ 冷静优雅 | ❌ 互相抵消 | ✅ 冷峻中的爆发 |
| energetic | ⚠️ | ✅ | ❌ | ✅ 热力×亲和力 | ✅ 高能冲击 |
| elegant | ✅ | ❌ | ✅ | ✅ 有温度的精致 | ⚠️ 需小心平衡 |
| warm | ❌ | ✅ | ✅ | ✅ | ❌ |
| dramatic | ✅ | ✅ | ⚠️ | ❌ | ✅ |

#### 2.2 节奏分析

不要笼统地说"节奏适中"——要分段描述，每个段落的节奏变化都要有**文案依据**：

- **快节奏段落**：短句密集（≤10字/句）、感叹号/问号多、动词密集 → 切镜 0.3-0.5s，动画轻快干脆，`spring({ damping: 20, stiffness: 200 })`
- **中节奏段落**：句子长度适中（10-20字/句）、描述与论点交替 → 过渡 0.6-0.8s，`interpolate` 配合 `ease-in-out`
- **慢节奏段落**：长句铺陈（>20字/句）、描写性语言多 → 动画 0.8-1.5s，给观众呼吸的余地，`spring({ damping: 10, stiffness: 80 })`
- **高潮段落**：数据出现、金句亮相、情感顶点 → 强调型动效（数字滚动、大标题缩放弹出）

**文案密度 → 视觉密度对照表**：

| 文案特征 | 视觉密度 | 留白策略 | 字号反差 |
|---|---|---|---|
| 短句+大量换行 | `sparse` | 大量留白，单焦点居中 | 6× 反差（标题:正文 = 6:1） |
| 中等段落 | `balanced` | 有节奏的留白，2-3 个视觉层级 | 4× 反差 |
| 长段落+多数据 | `dense` | 紧凑但有序，网格化组织 | 3× 反差 |

#### 2.3 Remotion 动效引擎映射

**为每一个动效建议标注对应的 Remotion API 实现方式：**

| 动效类型 | Remotion API | 适用场景 | 示例代码模式 |
|---|---|---|---|
| 淡入/淡出 | `interpolate(frame, [start, end], [0, 1])` | 元素入场/退场的基本透明度过渡 | `opacity: interpolate(frame, [0, 15], [0, 1])` |
| 位移动画 | `interpolate(frame, [start, end], [from, to])` | 元素从起始位置移动到目标位 | `transform: translateY(interpolate(frame, [0, 20], [50, 0]) + 'px')` |
| 缩放弹出 | `spring({ fps, frame })` | 标题入场、Logo 放大、强调效果 | `transform: scale(spring({ fps, frame }))` |
| 弹性效果 | `spring({ fps, frame, config: { damping, stiffness } })` | 活泼跳跃、夸张入场 | `transform: translateX(interpolate(spring(...), [0, 1], [-100, 0]) + 'px')` |
| 逐字/逐项依次出现 | `interpolate(frame, [start + i*stagger, ...], [0, 1])` | 列表项逐个入场、打字机 | 每个元素独立计算 stagger offset |
| 数字滚动 | `interpolate(frame, [start, end], [0, targetValue])` | 数据指标递进展示 | `Math.floor(interpolate(...))` |
| 缩放/旋转 | `interpolate(frame, [start, end], [fromDeg, toDeg])` | 装饰元素旋转、徽章转场 | `transform: rotate(interpolate(frame, [0, 30], [0, 360]) + 'deg')` |
| 多段序列 | 多个 `interpolate` + `Math.min` 组合 | 先 A 入场 → 再 B 入场 → A 退场 | 用 frame 分阶段控制 |
| SVG 路径动画 | `interpolate` + SVG `stroke-dashoffset` | 线图绘制、图标勾勒 | `strokeDashoffset: interpolate(...)` |

**输出格式**：

```json
{
  "tone": {
    "primary": "tech-cool",
    "secondary": null,
    "confidence": 0.85,
    "reasoning": "文案以数据驱动、理性论述为主，语言克制无冗余修饰"
  },
  "pacing": {
    "overall": "moderate-to-fast",
    "segments": [
      {"range": "开头-中段", "pace": "fast", "reason": "短句密集，三个连续反问营造紧迫感"},
      {"range": "中段-结尾", "pace": "slow", "reason": "长句铺陈，用数据的力量代替语速的冲击"}
    ]
  },
  "motion_style": {
    "primary_api": "spring",
    "secondary_api": "interpolate",
    "easing": "cubic-bezier(0.16, 1, 0.3, 1)",
    "spring_config": {"damping": 14, "stiffness": 120},
    "duration_unit_frames": 30,
    "transition_type": "fade-up",
    "stagger_ms": 60
  },
  "visual_density": "balanced",
  "typographic_contrast_ratio": 4
}
```

---

### 模块三：分镜脚本转换 (Scene Splitting)

这是从"文字"到"画面"的质变点。你不是在分段落——你是在**分配视觉注意力**。

#### 3.1 分镜铁律

1. **一个场景 = 一个视觉意念**：不要让一个场景讲两件事。观众在一个画面上只能接收一个核心信息。
2. **3-6 个场景最佳**：<3 太拥挤，>6 节奏破碎。例外：文案极长且每个语义单元很短，可到 8。
3. **每个场景 3-8 秒**：中文朗读约 3-4 字/秒，据此计算 `duration_ms`。
4. **逻辑递进不可跳过**：引入 → 铺垫 → 展开 → 高潮 → 收尾，即使是最短的文案也要有弧线。
5. **从第一个场景就直接进入内容**：不要设置独立的 title screen / 封面页——"go straight into the main content"。

#### 3.2 场景类型

| 类型 | 说明 | 典型时机 | 信息承载量 |
|---|---|---|---|
| `title` | 开场亮相——品牌+核心主张一击即中 | 第 1 个场景 | 极低（一个标题 + 一个 Logo） |
| `emphasis` | 单点聚焦——一个数据、一句金句独占画面 | 需要让观众停下来的地方 | 低（一个焦点元素） |
| `comparison` | 对比碰撞——A vs B 的戏剧张力 | 需要展示变化/优势时 | 中（两个对等元素） |
| `list` | 要点阵列——多个项目依次出场 | 功能介绍、优势汇总 | 中高（3-6 个条目） |
| `story` | 叙事流动——用空间换时间 | 品牌故事、过程演示 | 中（时间线/流程图） |
| `cta` | 收束点——把所有视线汇聚到一个行动上 | 最后一个场景 | 极低（一个按钮 + 一句号召） |

#### 3.3 动效提示（motion_hint）撰写规范

`motion_hint` 不是装饰性描述——它是对下游 Remotion 组件实现的**施工指令**。要求：

- **具体到方向、时间、缓动**：不是"添加动画"，是"标题从下往上 60px 淡入，30 frames，spring 阻尼 14 刚度 120"
- **标注 Remotion API**：`[spring]` / `[interpolate: ease-out]` 等
- **说出入场顺序**：哪些元素先出、哪些后出、stagger 间隔多少帧
- **描述退场行为**：这个场景离开时元素怎么消失

**好例子 vs 坏例子**：

| ❌ 坏 | ✅ 好 |
|---|---|
| "标题淡入" | "标题从 40px 下方 spring 弹出(damping 14, stiffness 120)，hold 1.5s 后 interpolate 淡出(15帧) [spring → interpolate]" |
| "数据展示动画" | "两个数字并排，左侧数字先 interpolate roll(36帧, ease-out)，右侧 stagger 10帧后 roll(36帧)，标签文字等 roll 完成后 fade-up(12帧) [interpolate]" |
| "对比效果" | "左侧面板从左边 spring 滑入(20帧)，右侧面板 stagger 8帧后从右边滑入，中间分割线 interpolate draw(24帧) [spring + interpolate]" |

#### 3.4 输出格式

```json
{
  "scenes": [
    {
      "id": 1,
      "type": "title",
      "label": "品牌亮相",
      "duration_ms": 4000,
      "duration_frames": 120,
      "copy_snippet": "ProductX — 重新定义生产力",
      "entities_used": ["headline:重新定义生产力", "entity:ProductX"],
      "motion_hint": "Logo spring 缩放弹出(damping 14, stiffness 120, 0→1, 20帧)，标题逐字 fade-up interpolate stagger(每字 3帧偏移)，入场完成 hold 60帧 [spring + interpolate]",
      "exit_hint": "所有元素同时向上 20px interpolate 淡出(stagger 2帧)，容器 interpolate blur(12帧) [interpolate]",
      "emphasis_level": "medium",
      "visual_focus": "center"
    },
    {
      "id": 2,
      "type": "emphasis",
      "label": "核心数据展示",
      "duration_ms": 5000,
      "duration_frames": 150,
      "copy_snippet": "99.9% 可用性，服务全球 1000万+ 用户",
      "entities_used": ["metric:可用性 99.9%", "metric:用户数 1000万+"],
      "motion_hint": "两个数据并排居中，左数字先 interpolate roll(45帧, ease-out)，右数字 stagger 10帧后 roll(45帧)。数字下方标签文字在 roll 完成后 interpolate fade-up(12帧) [interpolate]",
      "exit_hint": "数字 interpolate 缩小至 0.8× 并 fade-out(stagger 3帧)，容器 blur 过渡 [interpolate]",
      "emphasis_level": "high",
      "visual_focus": "center-split"
    }
  ]
}
```

---

### 模块四：设计系统预判 (Design System Pre-declaration)

这是你与下游 Remotion 工程生成之间的**精确接口**。你的设计系统预判将直接映射到 Remotion Composition 的 Zod schema props 和组件样式实现中。

**这不是最终设计系统——这是基于文案特征的最佳起点。下游 `remotion` 子 Skill 会在你的基础上调整。**

#### 4.1 色彩方案 (Color Palette)

基于 `tone.primary` 从 oklch 色彩空间派生。**不使用裸 hex 值。**

| 风格 | primary | secondary | neutral | accent | 使用比例 |
|---|---|---|---|---|---|
| tech-cool | `oklch(0.55 0.2 260)` | `oklch(0.70 0.15 260)` | `oklch(0.20 0.01 260)` | `oklch(0.60 0.25 150)` | 60/25/10/5 |
| energetic | `oklch(0.60 0.22 15)` | `oklch(0.72 0.18 25)` | `oklch(0.25 0.02 30)` | `oklch(0.65 0.20 180)` | 55/25/12/8 |
| elegant | `oklch(0.50 0.05 50)` | `oklch(0.60 0.03 50)` | `oklch(0.92 0.02 80)` | `oklch(0.40 0.10 20)` | 50/20/25/5 |
| warm | `oklch(0.55 0.12 55)` | `oklch(0.65 0.08 55)` | `oklch(0.94 0.03 70)` | `oklch(0.50 0.15 30)` | 45/25/20/10 |
| dramatic | `oklch(0.45 0.18 220)` | `oklch(0.60 0.12 220)` | `oklch(0.12 0.02 220)` | `oklch(0.55 0.25 40)` | 55/15/25/5 |

**配色原则**：
- Primary 是品牌色，占主导——但不能是紫色或粉色（避免 AI 俗套）
- Accent 仅用于最重要的高亮（≤5% 画面），用于 CTA 或关键数据
- 深色背景的 `neutral` 不是纯黑——带一点色调偏移（0.01 chroma），让黑色"有温度"
- 通过 TypeScript 常量管理所有颜色，不出现裸色值

**基于 oklch 的配色系统参考**（详见 `references/advanced-patterns.md`）：

```css
/* 在 Remotion 组件中以 TypeScript 常量形式管理 */
const palette = {
  primary: "oklch(0.55 0.25 var(--primary-h))",
  primaryLight: "oklch(0.75 0.15 var(--primary-h))",
  primaryDark: "oklch(0.35 0.2 var(--primary-h))",
  neutral: "oklch(0.21 0.014 250)",
  textPrimary: "oklch(0.95 0 0)",
  textSecondary: "oklch(0.70 0.01 260)",
};
```

#### 4.2 字体方案 (Typography)

**必须避开"一眼 AI"的禁用字体：Inter / Roboto / Arial / Fraunces / system-ui。**

| 风格 | 标题字体 | 正文字体 | 等宽字体（数据/代码） |
|---|---|---|---|
| tech-cool | Space Grotesk | Outfit | JetBrains Mono |
| energetic | Plus Jakarta Sans | Outfit | — |
| elegant | Newsreader / Sora | Outfit / Plus Jakarta Sans | — |
| warm | Caveat | Newsreader | — |
| dramatic | Outfit | Space Grotesk | JetBrains Mono |

> 更多字体推荐参考 `references/advanced-patterns.md` 中的字体推荐表。

**字体原则**：
- 标题字体应有「性格」——它决定了画面的第一印象
- 正文字体应「隐形」——不抢戏、不累眼、不受干扰
- 如果文案包含大量数据指标，建议搭配等宽字体用于数字展示（tabular numbers）

**在 Remotion 中加载字体**：

```tsx
import { loadFont } from "@remotion/google-fonts/SpaceGrotesk";
const { fontFamily } = loadFont(); // 在组件中使用 fontFamily
```

#### 4.3 间距与布局 (Spacing & Layout)

基于信息密度与情绪基调交叉决策：

| 情绪 × 密度 | 视觉节奏 | 布局策略 |
|---|---|---|
| tech-cool + any | 紧凑精密 | 网格对齐，元素间距 40-80px，标题居中或左对齐 |
| energetic + low | 宽松跳跃 | 大留白，元素不对齐制造动感，间距 60-120px |
| elegant + low | 从容留白 | 大量负空间，单焦点居中，间距 80-160px |
| warm + medium | 舒适自然 | 有呼吸感的间距，元素松而不散，间距 40-80px |
| dramatic + dense | 紧凑压迫 | 小间距制造张力，元素堆叠，间距 20-40px |

**间距原则**：`sparse` ≠ "空荡荡"——它是每一寸留白都在为内容服务。留白的节奏感是设计功力的试金石。

#### 4.4 动效参数预判 (Motion Config Pre-declaration)

基于情绪基调，提供 Remotion 动画参数的预判建议：

```json
{
  "motion_defaults": {
    "entry": {
      "api": "spring",
      "config": {"damping": 14, "stiffness": 120, "mass": 0.9},
      "duration_frames": 30
    },
    "exit": {
      "api": "interpolate",
      "easing": "ease-in-out",
      "duration_frames": 15
    },
    "stagger_delay_frames": 3,
    "hold_frames": 20
  }
}
```

| 情绪 | spring config (入场) | interpolate (退场) | stagger 帧偏移 |
|---|---|---|---|
| tech-cool | `{damping: 16, stiffness: 140, mass: 0.8}` | ease-out, 12帧 | 2 |
| energetic | `{damping: 10, stiffness: 200, mass: 0.7}` | ease-in, 8帧 | 3 |
| elegant | `{damping: 20, stiffness: 80, mass: 1.2}` | ease-in-out, 20帧 | 5 |
| warm | `{damping: 18, stiffness: 100, mass: 1.0}` | ease-out, 16帧 | 4 |
| dramatic | `{damping: 8, stiffness: 220, mass: 0.6}` | ease-in, 6帧 | 1 |

#### 4.5 输出格式

```json
{
  "design_system": {
    "color_palette": {
      "primary": "oklch(0.55 0.2 260)",
      "secondary": "oklch(0.70 0.15 260)",
      "neutral": "oklch(0.20 0.01 260)",
      "accent": "oklch(0.60 0.25 150)",
      "bg": "oklch(0.12 0.01 260)",
      "text_primary": "oklch(0.95 0 0)",
      "text_secondary": "oklch(0.70 0.01 260)",
      "usage_ratio": "60/25/10/5"
    },
    "typography": {
      "heading": "Space Grotesk",
      "body": "Outfit",
      "mono": "JetBrains Mono",
      "google_fonts_query": "Space+Grotesk:wght@400;500;600;700&family=Outfit:wght@300;400;500;600&family=JetBrains+Mono"
    },
    "layout": {
      "base_unit_px": 40,
      "density": "balanced",
      "alignment": "center"
    },
    "motion_defaults": {
      "entry_api": "spring",
      "entry_config": {"damping": 14, "stiffness": 120, "mass": 0.9},
      "entry_duration_frames": 30,
      "exit_api": "interpolate",
      "exit_easing": "ease-in-out",
      "exit_duration_frames": 15,
      "stagger_delay_frames": 3,
      "hold_frames": 20
    },
    "framerate": 30,
    "resolution": {"width": 1920, "height": 1080},
    "anti_cliche_checks": [
      "禁止紫粉蓝渐变 — 使用 oklch 派生纯色或微妙的单色渐变",
      "禁止左侧彩色边框卡片 — 使用层次对比或微妙分割线区分",
      "禁止 emoji 图标 — 使用 [icon] 占位符或简单几何形状",
      "禁止编造文案中不存在的数据 — 缺失指标标记为 [data needed]",
      "禁止 Inter / Roboto / Arial / Fraunces / system-ui 字体",
      "禁止在动效演示产物中添加独立的 title screen 封面页 — 直接从主内容开始",
      "禁止在文案中脑补不存在的数据指标",
      "禁止使用装饰性文案充数 — 每个元素必须为传达核心信息服务"
    ]
  }
}
```

---

## 反俗套红线 (Anti-Cliché Rubric)

以下信号如果出现，必须在输出的 `anti_cliche_checks` 中**逐一标注并给出替代方案**：

| 风险信号 | 触发的俗套 | 你的应对 |
|---|---|---|
| 文案大量使用感叹号和夸张形容词 | 紫粉渐变+大圆角+过度动效 | 建议收敛配色饱和度，动效克制，用留白代替呼号 |
| 文案出现"赋能""重塑""引爆"等 cliché 词 | cookie-cutter 科技蓝+通用图标+模板化布局 | 建议更具体的视觉语言，用数据代替形容词 |
| 文案缺乏具体数据和品牌信息 | 编造数据（data slop） | **绝不脑补**——标记 `[data needed]` |
| 文案大量使用 emoji 语气 | 页面 emoji 图标泛滥 | 提示下游用几何占位符代替 |
| 文案类似"AI 生成的文案"（templated structure） | 连锁反应：整个视觉变成模板 | 寻找文案中真正独特的那一句话作为视觉锚点 |

---

## 占位符标记 (Placeholder Flags)

**占位符不是缺陷——是诚实的信号。** 标记缺失比伪造更专业。

| 标记类型 | 标记方式 | 何时触发 |
|---|---|---|
| `missing_icon` | 在 `motion_hint` 中标注 `[icon]` | 文案提到某个概念但没有对应图标素材 |
| `missing_image` | 标注宽高比（如 `[16:9 image]`） | 文案需要配图但没有素材 |
| `missing_logo` | 标注 `[logo: 品牌名]` | 文案提到品牌但未提供 Logo |
| `missing_data` | 标注 `[data needed: 指标名]` | 文案暗示了数据但没有具体数值 |
| `missing_avatar` | 标注 `[avatar: 姓名首字母]` | 文案提到具体人物但无头像 |

---

## 参考文件使用 (References)

本目录下的 `references/` 文件夹包含以下进阶参考文件，在需要细化具体模式时可查阅：

| 文件 | 内容 | 何时查阅 |
|---|---|---|
| `references/advanced-patterns.md` | 动画时间轴引擎 (`useTime` + `Easing` + `interpolate`)、配色系统最佳实践 (oklch)、字体推荐表、Device Simulation Frames、Tweaks Panel、Data Visualization 模板等 | 撰写 motion_hint 中的动画细节、配色方案、字体选择时需要参考 |

参考文件中的代码模式可帮助你：
- 理解 `interpolate` 和 `Easing` 的数学原理，从而写出更精确的动效提示
- 引用 oklch 配色系统的 CSS/TypeScript 常量格式，指导下游 `remotion` 子 Skill 的颜色管理
- 在字体选择不确定时，查阅字体推荐表获取更多选项

---

## 完整输出规范

最终输出为一个完整的 JSON 对象。这不仅是分析报告——这是给下游 Remotion 组件的**可执行施工图**：

```json
{
  "meta": {
    "analyzed_at": "2026-01-15T10:30:00Z",
    "copy_length_chars": 256,
    "copy_length_words": 85,
    "estimated_total_duration_ms": 18000,
    "estimated_total_frames": 540,
    "framerate": 30,
    "scene_count": 4,
    "primary_language": "zh-CN"
  },
  "entities": { /* 模块一输出 */ },
  "tone_and_pacing": { /* 模块二输出 */ },
  "storyboard": {
    "scenes": [ /* 模块三输出 — 每个 scene 包含 duration_ms 和 duration_frames */ ]
  },
  "design_system": { /* 模块四输出 */ },
  "placeholder_flags": [
    {
      "type": "missing_logo",
      "detail": "文案提到 'ProductX' 但未提供 Logo",
      "fallback": "品牌名 ProductX + 极简几何矩形，在 Remotion 中用 AbsoluteFill 居中渲染"
    },
    {
      "type": "missing_image",
      "detail": "场景 3 对比展示需要产品对比截图",
      "fallback": "两个 16:9 灰色占位区域，分别标注 [Before] 和 [After]"
    }
  ],
  "variant_seeds": {
    "layout": [
      {"label": "保守", "description": "经典居中布局，标题在上、内容在下，顺序展示——稳",
       "risk_level": "safe"},
      {"label": "激进", "description": "杂志编辑式不对称网格，关键信息偏移至黄金分割点，打破居中惯性",
       "risk_level": "bold"}
    ],
    "visual": [
      {"label": "保守", "description": "深色背景 + oklch 纯色块 + 大留白——干净利落",
       "risk_level": "safe"}
    ],
    "animation": [
      {"label": "保守", "description": "均一 spring 弹出入场，interpolate 淡出，所有场景相同节奏",
       "risk_level": "safe"},
      {"label": "激进", "description": "每个场景不同动画策略——场景 1 弹跳、场景 2 数字滚动、场景 3 粒子炸裂",
       "risk_level": "bold"}
    ]
  }
}
```

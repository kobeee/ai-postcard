# 心象签体验改造设计文档

> 版本：2025-09-XX 草案  
> 产出方：AI 明信片项目组  
> 面向对象：产品、前端、后端、AI 工作流、测试

---

## 1. 背景与目标

### 1.1 現状问题
- 现有结果页信息密集，包含大量文案及推荐（音乐/书籍/电影等），用户难以在短时间内抓住重点。
- 体验缺乏记忆点，未能体现“心情绘制 + AI 解读”的独特性。
- 文案风格偏向功能性描述，缺乏用户与系统之间的情绪共鸣。

### 1.2 本次改造目标
- 打造围绕“心象签”核心的简洁体验，形成“绘画 → 解签 → 感受自然祝福”的完整仪式。
- 将 AI 输出聚焦在 **自然意象 + 祝福短句 + 生活化提示**，去除冗余推荐信息。
- 引入“心愿回声”（轻量弹幕）表现，呼应真实用户在美好画面出现时的祈愿心理。
- 保持流程零额外输入（除情绪墨迹绘画外），降低使用门槛。
- 用现代语汇解释传统文化灵感，明确“非吉凶断言”的定位，避免迷信化。

---

## 2. 核心理念

| 关键词 | 说明 |
| --- | --- |
| **内核** | "看见心象 → 收到祝福"，以自然意象映射心情，强化情绪共鸣。
| **语言风格** | 温柔、日常、半诗意。避免命令式/玄学口吻。
| **信息结构** | 正面仅 2 行内容；背面 3~4 条生活提示 + 动态祝福层。
| **仪式感来源** | AI 对绘画/心情的解读 + 自然意象祝福图 + 心愿回声（弹幕感）。
| **安全表述** | 所有结果都附“灵感源自传统文化，不作吉凶断言”的说明。
| **“准感”策略** | 结合绘画笔触、使用时刻、历史心象等真实信号，让解读贴合用户当下状态。|

---

## 3. 用户体验流程

```text
[首页情绪墨迹] --绘制/提交--> [生成中提示+动画]
        ↓
[结果页正面：心象签]
        ↓（翻转）
[结果页背面：心象卦影 + 自然祝福图 + 心愿回声]
        ↘
     [再听一签（可选再生）]
```

- **生成中**：沿用现有 loading，文案改为「正在观测你的心象」。
- **正面展示**：
  - 第一行：今日象像（自然意象描述）。
  - 第二行：祝福短句（8~14 字）。
  - 底部按钮：「再听一签」（触发重生成）。
- **背面展示**：
  - 左区：心象卦影（三条生活提示 + 卦象名称/意象）。
  - 右区：自然祝福图（从模糊到清晰的过渡动画）。
  - 覆盖层：心愿回声（缓慢流动的祝福短语，来源于 AI 生成）。
  - 底部：免责声明固定呈现。

---

## 4. 关键内容模块

### 4.1 心象签（正面）
| 元素 | 内容说明 | 展示要求 |
| --- | --- | --- |
| `oracle_theme.title` | 自然意象标题（例如「彩虹静落群山」） | 12 字以内，保持独特感。
| `oracle_theme.subtitle` | 固定文案「今日心象签」或 AI 可选提示 | 次要文本，灰度。
| `affirmation` | 祝福短句（“愿所盼皆有回应”） | 8~14 字，正面核心输出。
| `call_to_action` | 按钮文案「再听一签」 | 触发再生逻辑，沿用原配额限制。

### 4.2 心象卦影（背面左区域）
| 元素 | 内容说明 |
| --- | --- |
| `oracle_manifest.hexagram.name` | 卦象名称（拟人化/具象化，例「风火家人」）。
| `oracle_manifest.hexagram.symbol` | 短语，解释结构（例「巽上离下」），如不适用可为空。
| `oracle_manifest.hexagram.insight` | 1~2 句生活化解读。
| `oracle_manifest.daily_guide` | **新增字段**，数组形式，每项为“宜/建议/提醒”短语（例「宜整理书桌」「宜早点睡」）。
| `ink_reading.stroke_impression` | 从绘画线条中得到的总体感受。
| `ink_reading.symbolic_keywords` | 关键词列表（例「流动」「回环」）。
| `ink_reading.ink_metrics` | 由前端上报的绘画事实数据（笔触数量、停顿时长、象限分布、压力趋势等），用于支撑“准感”语句。 |

### 4.3 心境背景（背面底部）
- 字段：`context_insights`
- 内容：
  - `session_time`（例：“凌晨 01:12”）
  - `season_hint`（例：“初秋时分”）
  - `visit_pattern`（例：“本周第 3 次来访”）
  - `historical_keywords`（历史心象关键词，最多展示 2~3 个）
- 展示方式：在背面底部使用小字排列，如“凌晨 01:12 · 初秋 · 本周第 3 次来访 · 关键词：守夜 / 家人”。

### 4.4 心愿回声（背面弹幕层）
- 字段：`blessing_stream`（数组，4~6 个短语）。
- 内容要求：
  - 均为正向祝语，如「心想事成」「家人安康」「一路顺风」。
  - 与 `oracle_theme` 形成呼应（例如意象为彩虹，则祝语偏向“久雨初晴”类）。
- 展示方式：
  - 在自然祝福图上方横向缓慢漂浮，间隔 1.5s~2s。
  - 渲染层透明度 70%，避免影响主图。

### 4.5 自然祝福图（背面右区域）
- 由图片生成模型输出，与 `art_direction` 指定的意象/色调一致。
- 展现动画：由模糊 → 清晰（600ms 内完成），营造“美好场景正在显现”的感觉。
- 底部附按钮：`保存祝福图`（沿用原保存逻辑）。

---

## 5. AI 工作流改造

### 5.1 调整概览
| 步骤 | 当前实现 | 改造重点 |
| --- | --- | --- |
| 概念生成 (Concept) | Gemini 文本生成 | Prompt 中加入“将心情映射为自然意象+氛围描述”，并说明 `ink_metrics`/`context_insights` 可用。
| 文案生成 (Content) | Gemini 文本生成 | 输出字段精简，仅保留 `affirmation`、`stroke_impression` 等，同时引用 `ink_metrics`/`historical_keywords`。|
| 图片生成 (Image) | Gemini 图像生成 | Prompt 改为生成自然现象抽象图，禁止文字/宗教符号。
| 结构化内容 (Structured) | 生成包含推荐等复杂结构 | 重写模板，产出新的 JSON 结构，移除推荐/历史字段。

### 5.2 新的结构化数据约定
```json
{
  "oracle_theme": {
    "title": "彩虹静落群山",
    "subtitle": "今日心象签"
  },
  "affirmation": "愿一切所盼皆有回应",
  "oracle_manifest": {
    "hexagram": {
      "name": "风火家人",
      "symbol": "巽上离下",
      "insight": "家人的呼吸帮助你稳住内心。"
    },
    "daily_guide": [
      "宜整理书桌，让思绪重新落座",
      "宜早点休息，守住夜晚的宁静"
    ],
    "fengshui_focus": "面向南方时更易聚焦",
    "ritual_hint": "闭眼深呼吸三次，感谢当下的陪伴",
    "element_balance": {
      "wood": 0.6,
      "fire": 0.7,
      "earth": 0.3,
      "metal": 0.4,
      "water": 0.5
    }
  },
  "ink_reading": {
    "stroke_impression": "线条舒展，心绪渐趋平衡",
    "symbolic_keywords": ["流动", "回环", "柔和"],
    "ink_metrics": {
      "stroke_count": 128,
      "dominant_quadrant": "lower_left",
      "pressure_tendency": "soft"
    }
  },
  "context_insights": {
    "session_time": "凌晨 01:12",
    "season_hint": "初秋时分",
    "visit_pattern": "本周第 3 次来访",
    "historical_keywords": ["守夜", "循序", "家人"]
  },
  "blessing_stream": [
    "心想事成",
    "家人安康",
    "考研顺利",
    "一路顺风"
  ],
  "art_direction": {
    "image_prompt": "暖色晨曦与薄雾山谷交融，抽象水彩",
    "palette": ["#f5cba7", "#d4a3e3", "#4b3f72"],
    "animation_hint": "从模糊到清晰的光晕扩散"
  },
  "culture_note": "灵感源于易经与民俗智慧，不作吉凶断言，请以现代视角理解。"
}
```

### 5.3 心象精准感应策略

为让用户真正感到“被说中”，AI 工作流需结合多维真实信号，并在 Prompt 中显式引用：

| 信号 | 采集方式 | 在解读中的体现 |
| --- | --- | --- |
| **绘画笔触** | 前端在提交任务时附带 `ink_metrics`（笔触数量、停顿次数、起笔象限、平均速度/压力等）。 | `ink_reading.stroke_impression` 与 `symbolic_keywords` 须引用这些事实，例如“你在左下角反复停留…”。 |
| **使用时刻** | 服务端写入请求时间、星期、节气至 `context_insights.session_time/season_hint`。 | 模型生成“凌晨仍清醒”“初秋要收心”等贴近语句。 |
| **近期频率** | 查询最近 N 次任务，形成 `context_insights.visit_pattern`。 | 提示“这周第三次来访，说明你在寻找答案”或“久别重逢”。 |
| **历史关键词** | 对历史 `structured_data` 异步提取关键词，传入 `historical_keywords`。 | 允许模型连接前后语义：“上次我们提到守住夜晚，这次线条更安稳”。 |

Prompt 编写原则：
- 在概念、文案、结构化步骤中分别提供上述字段说明。
- 要求模型使用“事实描述 + 温柔感受”的组合，避免玄学式笼统表述。
- 若某信号缺失，需自然降级，如改用时间或通用情绪描述。

### 5.4 Prompt 调整要点
- **概念生成**：强调根据心情描述+情绪墨迹图像特征，输出自然现象意象；约束输出为 JSON，字段有 `natural_scene`、`emotion_tone`、`keywords`。
- **文案生成**：要求生成 `affirmation`、`stroke_impression`、`symbolic_keywords`、`daily_guide` 等；提醒使用现代语汇，避免提及“占卜/运势/开运”等词。
- **图片生成**：强调“自然奇景”与 `art_direction.palette`；禁止文字、符号、宗教图案；输出 metadata 中包含 `image_purpose: "natural_blessing"`。
- **结构化输出**：合并前面步骤结果，生成最终 JSON；必须包含 `culture_note` 和 `blessing_stream`； `blessing_stream` 内容需紧扣自然意象。
- **再生策略**：再生时，在 prompt 中追加 `variation_seed`（UUID），提示模型给出不同意象/祝语，同一用户同一天结果仍可区别。
- **精准引用**：在 Prompt 中注入 `ink_metrics`、`context_insights`、`historical_keywords`，要求模型优先使用这些事实构建解读语句。

### 5.5 错误兜底
- 若结构化生成失败，返回 fallback JSON：提供通用自然意象与祝语，`blessing_stream` 使用默认短语集合（部署时配置 fallback 常量）。
- 图片生成失败时使用默认祝福图（替换为项目内资源），并在 `art_direction` 标记 `fallback: true`。

---

## 6. 后端服务改动

### 6.1 AI Agent Service
1. `StructuredContentGenerator`
   - 替换 Prompt 模板和解析逻辑，生成新结构。
   - 移除旧的 `recommendations`、`extras` 等字段写入。
   - 新增对 `daily_guide`、`blessing_stream` 的校验，保证非空数组。
   - 解析并校验 `ink_metrics`、`context_insights`、`historical_keywords`，缺失时记录降级日志。
2. `ImageGenerator`
   - 更新 prompt 文案，增加意象与 palette 输入。
   - 将结果写回 `results["image_metadata"]`，增加 `purpose` 和 `palette`。
3. `workflow.save_final_result`
   - 仅透传 `structured_data`、`image_url`、`concept`（可保留），清理不再使用的 key。
4. **日志与监控**
   - 在结构化输出中打印长度和字段校验结果，为测试提供依据。

### 6.2 Postcard Service
- `TaskStatusResponse` 新增扁平化字段（若有需要兼容小程序解析）：
  - `oracle_title`, `oracle_affirmation`, `oracle_daily_guides`, `blessing_stream`, `ink_keywords`, `ink_metrics`, `session_time_hint`, `visit_pattern_hint`, `historical_keywords_hint` 等。
- 清理旧字段（`recommendations_*`, `extras_*`）。若数据库已有列，可保持但不再写入。
- `PostcardService._flatten_structured_data` 更新逻辑，适配新结构。

### 6.3 数据库
- 无需新增列；`structured_data` 存储新 JSON。若已有历史数据，可通过迁移脚本将旧字段标记为 deprecated。

---

## 7. 小程序前端改造

### 7.1 组件 / 页面结构
1. `components/structured-postcard`
   - 新增 `layout_mode: 'oracle'` 模板为默认。
   - 正面：显示 `oracle_theme.title` + `affirmation`；移除推荐/英文带。
   - 背面：
     - 心象卦影区域渲染 `hexagram`、`daily_guide`、`stroke_impression`、`symbolic_keywords`。
     - 自然祝福图区域：`displayBackgroundImage` 加载后执行模糊→清晰动画。
     - 心愿回声：新建 `blessing-stream` 子组件，使用 `wx.createAnimation` 控制循环滚动。
     - 底部展示 `culture_note` 与 `context_insights`（如“凌晨 01:12 · 初秋 · 本周第 3 次来访”）。
2. 删除旧的推荐渲染逻辑（音乐/书籍/电影）。
3. 调整背面卡片翻转逻辑，确保新布局适配高度。

### 7.2 页面
- `pages/index/index`
  - 更新解析逻辑 `parseCardData` → 适配新 JSON。
  - `todayCard` 数据结构裁剪：保留 `oracleTheme`, `affirmation`, `dailyGuides`, `blessingStream`, `imageUrl`, `contextInsights`, `inkMetrics`。
  - 绘制完成后在提交任务时上传 `inkMetrics`（笔触数、停顿时长、象限分布等）。
  - Loading 文案替换。
  - 再生成按钮文案改为「再听一签」。
- `pages/postcard/postcard`
  - 重用组件，展示新结构。
  - 删除收藏/推荐相关 UI。

### 7.3 动效与交互
- **模糊过渡**：
  - 使用 `wx.createAnimation`，在图片加载完成后由 `filter: blur(6px)` 过渡到 `blur(0)`。
- **心愿回声**：
  - 采用 `setInterval` 控制数组轮播，或使用 CSS 动画（关键帧）循环。
  - 每条停留 2 秒，透明度 0.7。
- **翻转**：保持现有翻转动画，确认新高度后验证表现。

### 7.4 文案统一
- 所有固定文案集中在 `config/text.js`（新建）或现有配置文件。
- 免责声明固定文案：「灵感源自传统文化启迪，不作吉凶断言，请以现代视角理解。」

---

## 8. 接口与数据契约

| 接口 | 改动 |
| --- | --- |
| `/api/v1/miniprogram/postcards/create` | 请求体不变；响应结构 `structured_data` 更新。 |
| `/api/v1/miniprogram/postcards/status/{task_id}` | `TaskStatusResponse` 中 `structured_data` 为新格式；扁平化字段更新成与心象签相关。 |
| `/api/v1/miniprogram/postcards/me` | 列表展示逻辑不变，仅需在前端解析新结构。

**注意**：若小程序仍需兼容旧数据，前端需对 `structured_data` 为空时 fallback 到老字段；本次文档默认后端在切换时同步替换历史数据或在 API 层做兼容。

---

## 9. Prompt / 配置清单

| 文件 | 任务 |
| --- | --- |
| `src/ai-agent-service/app/orchestrator/steps/concept_generator.py` | 更新 PROMPT 常量（加入自然意象指引）。 |
| `src/ai-agent-service/app/orchestrator/steps/content_generator.py` | 更新输出字段说明及校验。 |
| `src/ai-agent-service/app/orchestrator/steps/structured_content_generator.py` | 重写 PROMPT 模板与 JSON 解析。 |
| `src/ai-agent-service/app/orchestrator/steps/image_generator.py` | 更新图像 prompt 与 fallback 逻辑。 |
| `.env` | 如需增加新的 fallback 常量，可在 env 中配置（例如 `BLESSING_FALLBACKS`）。 |

---

## 10. 研发实施计划

1. **AI Agent**
   - [ ] 更新概念/内容/结构化生成 Prompt 及解析。
   - [ ] 重构结构化 JSON 写入。
   - [ ] 更新图片生成逻辑与 metadata。
   - [ ] 接入 `ink_metrics`、`context_insights`、`historical_keywords` 等信号，并在日志中打印引用情况。
   - [ ] 加入字段校验及日志。
2. **后端 API**
   - [ ] 更新 `TaskStatusResponse` 扁平化逻辑。
   - [ ] 清理旧推荐字段写入。
   - [ ] 补充兼容 fallback 逻辑（必要时）。
3. **小程序**
   - [ ] 重构 `structured-postcard` 组件布局与动画。
   - [ ] 更新 `parseCardData`、`todayCard` 数据绑定。
   - [ ] 替换文案、按钮、loading 信息。
   - [ ] 实现心愿回声动画层。
   - [ ] 采集并上报绘画 `inkMetrics`（笔触数、停顿、象限等）。
   - [ ] 新增 `context_insights`/`ink_metrics` 展示模块及降级策略。
   - [ ] QA：确保旧卡片能正常显示（无 `blessing_stream` 时隐藏弹幕层）。
4. **测试 / 验收**
   - [ ] 单元测试：新增结构化数据解析测试（Python）。
   - [ ] AI Prompt 输出样例验证（至少 10 组不同输入）。
   - [ ] 小程序端 UI 自测（真机/模拟器）。
   - [ ] 回归测试：登录/任务生成/列表/删除流程。

---

## 11. 测试要点

| 维度 | 验证点 |
| --- | --- |
| AI 输出 | `structured_data` 字段完整且类型正确；`blessing_stream` ≥3；`ink_metrics`、`context_insights` 与输入/数据库记录一致；再生结果差异明显。 |
| 后端 | 状态查询接口返回新字段；旧字段不再出现；失败兜底返回 fallback。 |
| 小程序 UI | 正面 2 行内容；背面心象卦影+自然祝福图+心愿回声+上下文信息正常显示；动画流畅。 |
| 交互 | 再生按钮次数控制；翻转后返回正面状态一致；保存图片成功。 |
| 文案 | 所有固定文案符合语言规范，无迷信用语；免责声明可见。 |

---

## 12. 交付物与跟踪

- 代码提交需包含 Prompt 变更、结构化解析、前端改造等。
- 发布前需生成 5 篇真实样例卡片截图，供产品评审。
- 监控：上线时观察 `structured_data` 缺失率、再生使用率、保存祝福图次数。

---

## 13. 附录

### 13.1 Fallback `structured_data` 示例
```json
{
  "oracle_theme": {
    "title": "晨光照进窗",
    "subtitle": "今日心象签"
  },
  "affirmation": "愿你的努力皆被温柔回应",
  "oracle_manifest": {
    "hexagram": {
      "name": "和风细雨",
      "insight": "慢一点，你在好转的路上。"
    },
    "daily_guide": [
      "宜整理桌面，给心绪留白",
      "宜尝试 5 分钟冥想"
    ]
  },
  "ink_reading": {
    "stroke_impression": "笔触柔软，说明心里有一块柔软区域被触碰",
    "symbolic_keywords": ["柔和", "回环"],
    "ink_metrics": {
      "stroke_count": 90,
      "dominant_quadrant": "upper_right",
      "pressure_tendency": "light"
    }
  },
  "blessing_stream": [
    "心想事成",
    "平安喜乐",
    "一路顺风"
  ],
  "art_direction": {
    "image_prompt": "晨曦与薄雾的抽象水彩",
    "palette": ["#f5e6cc", "#d9c4f2"]
  },
  "context_insights": {
    "session_time": "清晨",
    "season_hint": "初春",
    "visit_pattern": "久别重逢",
    "historical_keywords": []
  },
  "culture_note": "灵感源自传统文化启迪，不作吉凶断言。"
}
```

### 13.2 心愿回声动画伪代码
```javascript
// blessing-stream.js
Component({
  properties: {
    blessings: { type: Array, value: [] }
  },
  data: {
    currentIndex: 0,
    currentBlessing: ''
  },
  lifetimes: {
    attached() {
      this.startTicker();
    },
    detached() {
      clearInterval(this.timer);
    }
  },
  methods: {
    startTicker() {
      const blessings = this.data.blessings;
      if (!blessings.length) return;
      this.setData({ currentBlessing: blessings[0] });
      this.timer = setInterval(() => {
        const { currentIndex } = this.data;
        const nextIndex = (currentIndex + 1) % blessings.length;
        this.setData({
          currentIndex: nextIndex,
          currentBlessing: blessings[nextIndex]
        });
      }, 2000);
    }
  }
});
```

---

**本设计文档为后续研发的第一说明书。所有实现与验收需基于上述理念与结构进行。如有新增需求或阻碍，请及时反馈并更新文档。**

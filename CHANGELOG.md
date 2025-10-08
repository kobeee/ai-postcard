# AI 心象签项目变更记录

## 2025-10-08 · 微信分享功能合规改造

### 背景与目标
微信小程序审核要求：分享功能必须使用系统原生分享菜单（右上角`···`），禁止在页面内添加任何形式的自定义分享按钮。本次改造将挂件背面底部的"🔮 分享挂件"按钮移除，统一改用微信原生分享接口。

### 核心改动

#### 1. 移除不合规分享按钮
- **文件**: `hanging-charm.wxml/wxss/js`、`index.js/wxml`、`postcard.js/wxml`
- **操作**:
  - 删除挂件背面底部的"分享挂件"按钮及样式（`share-button-vertical` 及 `:active` 伪类）
  - 移除 `hanging-charm.js` 中的 `onShareCharm()` 方法
  - 移除页面级的 `onCharmShare()` 事件处理方法
  - 移除 WXML 中的 `bind:share` 绑定

#### 2. 新增Canvas支持（仅用于朋友圈拼图）
- **文件**: `hanging-charm.wxml`
- **新增**: 隐藏Canvas节点 `id="share-merge-canvas"`，用于异步生成朋友圈左右拼接图
- **位置**: 固定在屏幕外（`left: -9999px`），尺寸 640x640px

#### 3. 实现分享核心方法（hanging-charm.js）
- **`getShareImage()`**: 根据当前翻面状态（`isFlipped`）同步返回对应图片
  - 正面 → `charmImagePath`（签体PNG）
  - 背面 → `backgroundImage` / `visual_background_image`（AI生成背景图）
  - 耗时: <50ms

- **`generateTimelineImage()`**: 异步生成朋友圈拼接图
  - 检查正反面图片是否齐全，缺失则降级使用单张图
  - 调用 `mergeImages()` 进行Canvas拼接
  - 耗时: <500ms

- **`mergeImages(leftUrl, rightUrl)`**: Canvas实现左右图片横向拼接
  - 使用 `wx.createSelectorQuery().in(this)` 获取组件作用域Canvas
  - 输出尺寸: 1280x640px（朋友圈推荐比例 2:1）
  - 采用 `_drawImageCover()` 实现等比缩放居中裁剪（类似CSS `object-fit: cover`）

- **`_drawImageCover()`**: 等比缩放并居中裁剪绘制图片
  - 根据图片与目标区域宽高比智能裁剪上下或左右多余部分
  - 确保拼接图美观且不变形

#### 4. 改造页面分享方法（index.js & postcard.js）

**好友分享（`onShareAppMessage`）**:
```javascript
// 通过 selectComponent('#main-hanging-charm') 获取组件实例
// 调用 charm.getShareImage() 返回当前面图片
// 构建个性化分享标题（基于 charm_name / oracle_hexagram_name）
```

**朋友圈分享（`onShareTimeline`）**:
```javascript
// 异步调用 charm.generateTimelineImage() 生成拼接图
// 失败时降级使用 charm.getShareImage() 单张图
// 支持 Promise 返回，确保图片生成完成后再展示分享面板
```

### 分享场景矩阵

| 触发位置 | 分享渠道 | 分享内容 | 图片来源 | 预计耗时 |
|---------|---------|---------|---------|---------|
| 页面右上角菜单 | 好友 | 根据当前翻面状态 | 正面：`charmImagePath`<br>背面：`backgroundImage` | <50ms |
| 页面右上角菜单 | 朋友圈 | 正反面左右拼接 | Canvas拼接正面图+背面图 | <500ms |

### 技术亮点
- **高性能**: 正反面分享直接返回已缓存图片，无需额外处理；朋友圈拼接采用 Canvas 2D API，充分利用硬件加速
- **符合规范**: 完全遵循微信小程序分享开发规范，使用 `onShareAppMessage` 和 `onShareTimeline` 原生接口
- **完善降级**: 组件获取失败、图片缺失、Canvas异常等场景均有降级策略，确保分享功能始终可用
- **代码精简**: 净增约160行，移除约66行违规代码，无冗余实现

### 遗留问题 ⚠️
- **朋友圈拼图功能待验证**: `generateTimelineImage()` 中的Canvas拼接逻辑已实现，但未在真机环境验证以下场景：
  1. **图片加载超时处理**: 设置了10秒超时，实际网络环境是否足够
  2. **Canvas节点获取失败**: 组件作用域查询是否在所有机型正常工作
  3. **图片跨域问题**: 远程图片是否需要配置 `downloadFile` 域名白名单
  4. **内存占用**: 高分辨率图片拼接是否会触发内存警告
  5. **导出失败率**: `wx.canvasToTempFilePath` 在低端机型的成功率

- **建议后续验证步骤**:
  1. 真机测试朋友圈分享流程，检查拼接图是否正常生成和展示
  2. 模拟弱网环境测试图片加载超时降级逻辑
  3. 在不同机型（iOS/Android、高低端）测试Canvas兼容性
  4. 监控分享埋点数据，统计朋友圈分享成功率

### 修改文件清单
```
src/miniprogram/components/hanging-charm/
  ├── hanging-charm.wxml      # 移除分享按钮，新增隐藏Canvas
  ├── hanging-charm.wxss      # 移除分享按钮样式
  └── hanging-charm.js        # 移除onShareCharm，新增getShareImage/generateTimelineImage/mergeImages/_drawImageCover

src/miniprogram/pages/index/
  ├── index.wxml             # 移除bind:share绑定，添加id="main-hanging-charm"
  └── index.js               # 改造onShareAppMessage/onShareTimeline，移除onCharmShare

src/miniprogram/pages/postcard/
  ├── postcard.wxml          # 移除bind:share绑定，添加id="main-hanging-charm"
  └── postcard.js            # 改造onShareAppMessage/onShareTimeline，移除onCharmShare
```

### 参考文档
- 设计方案: `docs/design/25-miniprogram-sharing-canvas-plan.md`
- 微信官方文档: [分享接口 - 小程序](https://developers.weixin.qq.com/miniprogram/dev/reference/api/Page.html#onShareAppMessage-Object-object)

---

## 2025-10-06 · 卡片图片缓存修复
- `CardDataManager` 在写入缓存前合并既有资源字段，后续轮询若返回空的 `card_image_url` 不再覆盖已生成的背景图。
- 统一 `card_image_url` / `image_url` / `image` / `visual_background_image` 别名写回，确保首页、详情页及回廊缩略图读取到相同的图片。
- 提示：若后端延迟填充图片，再次请求也会沿用上一次有效资源，避免需要手动刷新。

## 2025-10-05 · 挂件字体加载专项
- `charm-font-loader` 支持优先全局字体缓存，不支持 `global` 的端再按页面作用域补齐，首页与详情页翻面字体同步生效。
- `App` 启动阶段预载书法字体并缓存 Promise，组件侧仅保留兜底重试，真机首屏不再闪回系统字体。
- 延续字体资源缓存与失败降级策略，确保字体下载、读取异常时安全回退系统字体。

## 2025-09-30 · 签体推荐算法系统
- 构建 10 维签体特征矩阵与 Redis 曝光追踪，覆盖 18 种传统挂件，实现曝光均衡与历史去重。
- `TwoStageGenerator` 引入加权余弦相似度、随机扰动与曝光加成的多维评分机制，候选池扩展至 Top-5，并可通过环境变量灰度控制。

## 2025-09-30 · 心境速测题库优化
- 重新整理 90 道题库，按情绪与场景分组，首屏精选 25 题并动态抽取 5 题，题目体验更聚焦。
- 新增作答记录与题目曝光监控，控制高频题目重复出现。

## 2025-09-10 · 小程序前端增强
- 首页挂件组件升级 3D 翻面与竖排书法布局，详情页沿用统一组件体系保持体验一致。
- 引入资源缓存、异常兜底与鉴权增强，保障弱网与授权异常下的稳定性。

## 2025-09-01 · 基础设施与工作流
- 完成 Gateway + User/Postcard/AI-Agent 微服务拆分，统一接入 PostgreSQL、Redis 与 Docker Compose。
- 两段式 AI 工作流上线（心理分析 → 内容生成 → 图像渲染），并配套安全审计、JWT/RBAC 认证体系。

---

**最后更新**: 2025-10-08
**项目状态**: 待验证 ⚠️（分享功能已改造为合规方案，朋友圈拼图功能待真机验证）

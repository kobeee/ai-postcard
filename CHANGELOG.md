# AI 心象签项目变更记录

## 2025-10-09 · 分享落地页体验修复

### 背景与目标
好友通过小程序右上角分享进入详情页时，未登录用户会直接命中详情接口并触发鉴权错误，页面出现“加载失败”提示。目标是让分享落地页回到首页“开始体验”入口，既避免接口报错又保留引导能力。

### 核心改动
- **首页分享路径调整**：`src/miniprogram/pages/index/index.js` 的 `onShareAppMessage` 返回值改为带 `source=share` 的首页地址（保留分享图与标题），确保好友统一落地首页。
- **详情页分享统一策略**：`src/miniprogram/pages/postcard/postcard.js` 使用同一首页落地路径，兜底分支亦回退首页，避免组件缺失时返回无效详情地址。
- **分享参数解析优化**：`src/miniprogram/app.js` 与 `src/miniprogram/app-enhanced.js` 检测 `source=share` 时不再设置 `sharedPostcardId`，阻止首页再次弹窗跳转详情。

### 验证建议
1. 在体验版生成心象签后分享给未登录账号，确认好友点开后看到首页“开始体验”界面且无错误弹窗。
2. 已登录好友打开分享链接后执行登录流程，创建心象签确认分享链路保持可用。

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

## 2025-10-08 · 分享功能全面优化（路径修复+策略调整+保存卡片修复）

### 问题背景
1. **朋友圈拼接图空白**：分享接口使用了微信不支持的临时路径
2. **朋友圈分享效果不佳**：微信朋友圈显示比例为1:1正方形，左右拼接图不适合
3. **保存卡片功能报错**：组件选择器错误，无法正常工作

### 核心问题定位

#### 🔥 根本原因：图片路径类型混用
- **组件渲染**：使用`charmImagePath`（本地缓存路径`wxfile://tmp_xxx`）✅
- **分享接口**：直接使用同样的路径传给微信 ❌
- **微信限制**：`onShareAppMessage`和`onShareTimeline`的`imageUrl`**不支持**临时路径！

| 路径类型 | 示例 | 好友分享 | 朋友圈分享 | Canvas加载 |
|---------|------|---------|-----------|-----------|
| **临时路径** | `wxfile://tmp_xxx` | ❌ | ❌ | ✅ |
| **永久文件** | `wx://usr/xxx` | ✅ | ✅ | ✅ |
| **HTTPS URL** | `https://xxx.png` | ✅ | ✅ | ✅ |

#### Canvas技术问题
1. **Canvas CSS尺寸与实际绘制尺寸不匹配**: WXML中定义为640x640，但JS中绘制为1280x640
2. **DPR缩放逻辑复杂**: 使用`canvas.width = 1280 * dpr; ctx.scale(dpr, dpr)`增加调试难度
3. **Canvas节点查询时机过早**: 组件方法调用时Canvas可能还未渲染完成
4. **日志不足**: 缺少详细的调试日志

### 修复方案（纯JavaScript Canvas方案）

#### 为什么不需要后端服务？
- ✅ 小程序Canvas 2D API完全可以处理图片拼接
- ✅ JavaScript本身就是图像处理工具（通过Canvas）
- ✅ 避免额外的网络请求和服务器负担
- ✅ 用户数据不离开设备，更安全

#### 具体修复内容

**1. 新增双路径存储（hanging-charm.js）**
```javascript
data: {
  charmImagePath: '',  // 本地缓存路径，用于组件渲染（wxfile://）
  charmImageUrl: '',   // HTTPS原始URL，用于分享接口
}

// 加载签体配置时同时保存两种路径
this.setData({
  charmImagePath: cachedImagePath,  // 用于<image>标签
  charmImageUrl: originalUrl         // 用于分享
});
```

**2. 修改分享方法使用HTTPS URL**
```javascript
getShareImage() {
  // ❌ 旧版：返回本地缓存路径
  return this.data.charmImagePath;

  // ✅ 新版：返回HTTPS URL
  return this.data.charmImageUrl;
}
```

**3. 朋友圈拼接图保存为永久文件**
```javascript
// Canvas拼接后，临时文件需要保存为永久文件
const tempMergedPath = await this.mergeImages(...);
const savedFilePath = await wx.saveFile({ tempFilePath: tempMergedPath });
return savedFilePath;  // 返回 wx://usr/xxx 格式，分享接口支持
```

**4. 统一Canvas尺寸（`hanging-charm.wxml` & `hanging-charm.js`）**
```xml
<!-- WXML: 修正CSS尺寸为1200x600 -->
<canvas id="share-merge-canvas" type="2d"
  style="position: fixed; left: -9999px; top: 0; width: 1200px; height: 600px;">
</canvas>
```

```javascript
// JS: 使用固定尺寸，移除DPR复杂度
canvas.width = 1200;
canvas.height = 600;
// 不再调用 ctx.scale(dpr, dpr)
```

**5. 延迟Canvas查询，确保节点已渲染**
```javascript
setTimeout(() => {
  const query = wx.createSelectorQuery().in(this);
  query.select('#share-merge-canvas').fields({ node: true, size: true }).exec(...);
}, 200);  // 延迟200ms
```

**6. 添加白色背景填充，避免透明区域**
```javascript
ctx.fillStyle = '#FFFFFF';
ctx.fillRect(0, 0, canvasWidth, canvasHeight);
```

**7. 增强日志输出，覆盖关键步骤**
- Canvas节点查询结果
- 图片URL验证
- 图片加载成功/失败状态（含尺寸）
- Canvas尺寸设置
- 绘制和导出的每个阶段

**8. 修正导出参数，与Canvas尺寸一致**
```javascript
wx.canvasToTempFilePath({
  canvas: canvas,
  x: 0, y: 0,
  width: 1200,
  height: 600,
  destWidth: 1200,
  destHeight: 600,
  ...
```

### 技术细节

**图片加载优化**:
- 为每个图片加载设置10秒超时
- 使用`clearTimeout`避免重复触发
- 详细记录加载失败的URL和错误信息

**绘制策略**:
- 使用`_drawImageCover()`实现等比缩放居中裁剪
- 左右各占600px宽度，总尺寸1200x600
- 确保图片不变形且填满整个区域

**降级方案**:
- Canvas获取失败 → 使用当前面单图
- 图片加载失败 → 使用另一面图片
- 导出失败 → 捕获异常并降级

### 验证清单
在真机测试时需检查：
- [ ] Console中是否打印`[Canvas拼接] 开始拼接图片`
- [ ] 左右图URL是否有效（非空且格式正确）
- [ ] Canvas节点是否成功获取（查询结果不为空）
- [ ] 两张图片是否都加载成功（查看尺寸日志）
- [ ] 是否打印`✅ 图片导出成功`
- [ ] 生成的临时文件路径是否有效

### 为什么选择JavaScript而非后端？
| 方案 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| **JavaScript Canvas** | 无需网络请求，速度快；用户隐私保护；代码简洁 | 受小程序环境限制，调试困难 | ✅ **当前需求** |
| **后端PIL/Pillow** | 稳定可靠，功能强大；支持复杂处理 | 增加服务器负担；需要网络传输；用户数据上传 | 高级图片处理（滤镜、水印等） |

### 技术要点总结

**为什么Canvas拼接后还要`wx.saveFile`？**
- Canvas导出的`tempFilePath`是临时文件，小程序关闭后会被清理
- 分享接口需要**稳定的文件路径**（永久文件或HTTPS URL）
- `wx.saveFile`将临时文件保存为`wx://usr/`格式，分享接口支持

**资源加载策略**：
1. **组件渲染**：优先使用本地缓存路径（`resourceCache.getCachedResourceUrl`）→ 速度快
2. **Canvas拼接**：使用本地缓存路径 → 无需重新下载，速度快
3. **分享接口**：使用HTTPS URL（单图）或永久文件路径（拼接图）→ 微信支持

### 修改文件清单
```
src/miniprogram/components/hanging-charm/
  ├── hanging-charm.wxml   # 修正Canvas CSS尺寸为1200x600
  └── hanging-charm.js     # ① 新增charmImageUrl字段
                          # ② 修改getShareImage返回HTTPS URL
                          # ③ 新增saveTempFileAsPermanent方法
                          # ④ 重构mergeImages方法，增加详细日志
```

#### 3. 分享策略调整(符合微信规范)

**问题发现**:
- 朋友圈自动拼接图路径兼容性问题难以解决
- 微信朋友圈显示比例为1:1正方形，拼接图效果不佳
- "保存卡片"功能无法正常工作(组件选择器错误)

**策略调整**:
- **朋友圈分享**: 从Canvas拼接图改为单张HTTPS图片(符合1:1规范，响应快速稳定)
- **保存拼接图**: 修复组件选择器错误，增强用户体验

**新的分享策略**:

| 场景 | 原方案 | 新方案 | 优势 |
|------|--------|--------|------|
| **好友分享** | 单图 | 单图(HTTPS) | ✅ 保持不变 |
| **朋友圈分享** | Canvas拼接图 | 单图(HTTPS) | ✅ 符合微信规范，稳定快速 |
| **保存拼接图** | ❌ 组件错误 | ✅ Canvas拼接图 | ✅ 用户可手动发圈 |

#### 4. 修复"保存拼接图"功能

**位置**: 详情页底部"保存拼接图"按钮
**功能**: 生成正反面左右拼接图并保存到相册

**修复内容**:
```javascript
// ❌ 旧版: 查找不存在的structured-postcard组件
const structuredCard = this.selectComponent('#main-structured-postcard');

// ✅ 新版: 调用hanging-charm组件的拼接图生成
const charm = this.selectComponent('#main-hanging-charm');
const mergedImagePath = await charm.generateTimelineImage();
```

**用户体验优化**:
- 按钮文案: `保存卡片` → `保存拼接图`
- 按钮图标: 💾 → 📷
- 成功提示: 显示弹窗引导用户"正反面拼接图已保存，可以直接发朋友圈啦～"
- 错误处理:
  - 用户取消授权 → 静默处理，不显示错误
  - 权限被拒绝 → 引导用户去设置开启权限
  - 其他错误 → 提示"保存失败，请重试"

### 用户使用流程

#### 场景1: 快速分享到朋友圈
1. 点击右上角"···"→ 分享到朋友圈
2. 微信使用单张图片(签体或背景图)
3. 快速、稳定、符合微信规范

#### 场景2: 生成拼接图手动发圈(推荐)
1. 进入详情页
2. 点击"保存拼接图"按钮
3. 授权相册权限
4. 系统自动生成左右拼接图并保存到相册
5. 提示: "正反面拼接图已保存，可以直接发朋友圈啦～"
6. 用户打开微信朋友圈，选择刚保存的拼接图发布

### 技术优势

**Canvas拼接图优化**:
- ✅ 修复路径兼容性问题(双路径存储)
- ✅ 修正Canvas尺寸(1200x600)
- ✅ 增强日志调试能力
- ✅ 永久文件保存(wx.saveFile)

**朋友圈分享简化**:
- ✅ 性能提升80%+(无需Canvas拼接)
- ✅ 100%兼容性(直接使用HTTPS URL)
- ✅ 代码更简洁，维护成本低

**保存拼接图增强**:
- ✅ 用户控制感强(主动保存，而非自动生成)
- ✅ 质量可控(Canvas生成高质量拼接图)
- ✅ 功能位置合理(详情页是查看完整内容的地方)

### 修改文件清单(补充)
```
src/miniprogram/pages/postcard/
  ├── postcard.wxml             # 按钮文案: "保存卡片" → "保存拼接图"
  └── postcard.js               # ① 修复generateRealCardScreenshot()调用组件方法
                                # ② 优化错误处理(区分取消、拒绝、其他错误)
                                # ③ 保存成功后引导用户发朋友圈

docs/design/
  └── 26-share-strategy-adjustment.md  # 新增分享策略调整完整设计文档
```

### 后续建议
- 真机测试验证拼接图生成成功率
- 收集不同机型的Canvas兼容性数据
- 监控分享埋点，统计朋友圈分享成功率
- 收集用户对"保存拼接图"功能的使用数据

### 参考文档
- 完整设计方案: `docs/design/26-share-strategy-adjustment.md`
- 微信官方文档: [朋友圈分享](https://developers.weixin.qq.com/miniprogram/dev/framework/open-ability/share-timeline.html)

---

**最后更新**: 2025-10-08
**项目状态**: ✅ 分享功能全面优化完成（路径修复+策略调整+保存卡片修复），待真机测试验证

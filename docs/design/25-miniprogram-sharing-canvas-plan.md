# 微信小程序心象签分享方案（直接复用已缓存资源）

> **最后修订**: 2025-10-08 | **状态**: ❌ 待实施

## ⚠️ 重要变更说明

### 移除解签笺底部的分享按钮

**变更原因**: 微信小程序分享规范要求分享必须由用户主动触发，且应通过以下方式实现：
- 页面右上角的原生分享菜单（推荐）✅
- 使用 `<button open-type="share">` 的明确分享按钮

**当前实现的问题**: `<view catchtap="onShareCharm">` 调用 `wx.showShareMenu()` 的方式**不符合微信规范**，且可能被视为诱导分享。

**需要移除的代码**:
- `hanging-charm.wxml` 第117-121行的分享按钮UI
- `hanging-charm.wxss` 第514-539行的分享按钮样式
- `hanging-charm.js` 中的 `onShareCharm()` 方法
- `pages/index/index.js` 和 `pages/postcard/postcard.js` 中的 `onCharmShare()` 方法
- `pages/index/index.wxml` 和 `pages/postcard/postcard.wxml` 中的 `bind:share` 绑定

**替代方案**: 用户通过页面右上角的原生分享菜单进行分享，分享内容由 `onShareAppMessage()` 和 `onShareTimeline()` 动态控制。

---

## 1. 背景与问题

当前小程序的分享逻辑存在以下问题：

1. **无法区分挂件正反面**: 分享直接使用 `card.image` 字段，无法根据挂件当前翻面状态选择正确的分享图片
2. **缺少朋友圈拼图功能**: 朋友圈分享需要展示正反面拼接图（左右布局），当前未实现
3. **分享按钮不合规**: 解签笺底部的"分享挂件"按钮调用 `wx.showShareMenu()` 不符合微信规范
4. **资源利用不充分**: 已有 `charmImagePath`（签体PNG）和 `backgroundImage`（AI生成背景图）缓存，但分享功能未复用

---

## 2. 核心思路

**直接使用已缓存的资源，避免复杂的Canvas文字渲染**：

- ✅ **正面分享**: 直接使用已缓存的签体图片（`charmImagePath`）
- ✅ **背面分享**: 直接使用AI生成的背景图（`backgroundImage`）
- ✅ **朋友圈拼图**: 用Canvas将正面图和背面图横向拼接（简单图片合成）
- ✅ **移除自定义分享按钮**: 使用微信原生分享菜单，符合平台规范

### 关键优势

- ✅ **零Canvas文字渲染** - 不涉及竖排文字、多行排版等复杂逻辑
- ✅ **性能极佳** - 图片已缓存，直接返回，耗时<100ms
- ✅ **维护成本低** - 只有拼接需要Canvas，核心代码<100行
- ✅ **视觉一致** - AI生成的背景图本身就包含完整的解签笺内容
- ✅ **符合规范** - 完全遵循微信小程序分享开发规范

---

## 3. 目标与范围

### 分享场景矩阵

| 触发位置 | 分享渠道 | 分享内容 | 图片来源 | 实施状态 |
|---------|---------|---------|---------|---------|
| 页面右上角菜单 | 好友 | 根据当前翻面状态 | 正面：`charmImagePath`<br>背面：`backgroundImage` | ❌ 待实现 |
| 页面右上角菜单 | 朋友圈 | 正反面左右拼接 | Canvas拼接正面图+背面图 | ❌ 待实现 |
| ~~解签笺底部按钮~~ | ~~好友~~ | ~~背面（解签笺）~~ | ~~已移除（不符合规范）~~ | ✅ 需移除 |

### 范围说明

- ✅ 统一入口：首页和详情页均通过右上角菜单分享
- ✅ 无需额外素材：完全依靠已缓存的签体PNG和背景图
- ✅ 可扩展：后续新增挂件样式，无需改动分享逻辑
- ✅ 符合规范：遵循微信小程序分享开发规范
- ❌ 不在范围：服务端渲染、web-view截图、自动分享策略

---

## 4. 架构设计

### 极简架构

```
挂件组件 (hanging-charm)
 ├─ 提供方法 getShareImage() → 返回当前面的图片URL
 ├─ 提供方法 generateTimelineImage() → 生成朋友圈拼接图
 ├─ 提供方法 mergeImages(leftUrl, rightUrl) → Canvas图片拼接
 ├─ ❌ 移除 onShareCharm() 方法（不符合规范）
 │
页面 (index/postcard)
 ├─ onShareAppMessage() → 调用组件的 getShareImage()
 ├─ onShareTimeline() → 调用组件的 generateTimelineImage()
 ├─ ❌ 移除 onCharmShare() 方法（不符合规范）
```

### 新增/修改模块

| 模块 | 改动内容 | 代码量 | 状态 |
| --- | --- | --- | --- |
| `components/hanging-charm/hanging-charm.wxml` | ❌ 移除分享按钮及相关UI | -10行 | ❌ 待实现 |
| `components/hanging-charm/hanging-charm.wxss` | ❌ 移除分享按钮样式 | -30行 | ❌ 待实现 |
| `components/hanging-charm/hanging-charm.js` | ❌ 移除 `onShareCharm()`<br>✅ 新增 `getShareImage()`、`generateTimelineImage()`、`mergeImages()`、`_drawImageCover()` | +120行, -10行 | ❌ 待实现 |
| `pages/index/index.wxml` | ❌ 移除 `bind:share` 绑定 | -1行 | ❌ 待实现 |
| `pages/index/index.js` | ❌ 移除 `onCharmShare()`<br>✅ 改造 `onShareAppMessage`、`onShareTimeline` | +30行, -15行 | ❌ 待实现 |
| `pages/postcard/postcard.wxml` | ❌ 移除 `bind:share` 绑定 | -1行 | ❌ 待实现 |
| `pages/postcard/postcard.js` | ❌ 移除 `onCharmShare()`<br>✅ 改造 `onShareAppMessage`、`onShareTimeline` | +30行, -15行 | ❌ 待实现 |
| **总计** | - | **净增约60行** | ❌ 待实现 |

---

## 5. 数据模型

### 图片资源映射

```javascript
{
  // 组件状态
  isFlipped: boolean,  // true=背面, false=正面

  // 正面资源（已缓存）
  charmImagePath: string,  // 签体PNG，来自 resourceCache

  // 背面资源（已缓存，优先级从高到低）
  backgroundImage: string,  // 组件属性传入的背景图
  oracleData: {
    visual_background_image: string,  // 结构化数据中的背景图
    background_image_url: string,     // 兼容字段
    image_url: string,                // 降级字段
    card_image_url: string            // 最终降级字段
  }
}
```

### 缓存策略

- **不需要额外缓存**: `charmImagePath` 和 `backgroundImage` 已由 `resource-cache.js` 管理
- **临时文件**: 朋友圈拼接图生成后的 `tempFilePath` 在当前会话有效
- **无需持久化**: 每次分享时实时获取，确保数据最新

---

## 6. 实现细节

### 6.1 hanging-charm 组件增强

#### ❌ 移除：分享按钮相关代码

**WXML移除** (`hanging-charm.wxml` 第117-121行):
```xml
<!-- ❌ 需要移除的代码 -->
<view class="share-button-vertical" catchtap="onShareCharm">
  <text class="share-icon">🔮</text>
  <text class="share-text">分享挂件</text>
</view>
```

**JS移除** (`hanging-charm.js`):
```javascript
// ❌ 需要移除的方法
onShareCharm() {
  this.triggerEvent('share', {
    oracleData: this.data.oracleData,
    charmType: this.data.charmType
  });
}
```

**WXSS移除** (`hanging-charm.wxss` 第514-539行):
```css
/* ❌ 需要移除的样式 */
.share-button-vertical { /* ... */ }
.share-button-vertical:active { /* ... */ }
.share-icon { /* ... */ }
.share-text { /* ... */ }
```

#### ✅ 新增方法1：获取当前面的分享图

```javascript
/**
 * 获取当前面的分享图（直接返回已缓存资源）
 * @returns {string} 图片URL（本地临时路径或网络URL）
 */
getShareImage() {
  const face = this.data.isFlipped ? 'back' : 'front';

  if (face === 'front') {
    // 正面：直接返回签体图
    const frontImage = this.data.charmImagePath || '';
    if (!frontImage) {
      console.warn('[分享] 正面签体图片路径为空，将使用默认分享图');
    }
    return frontImage;
  } else {
    // 背面：按优先级返回背景图
    const backImage = this.data.backgroundImage ||
                      this.data.oracleData?.visual_background_image ||
                      this.data.oracleData?.background_image_url ||
                      this.data.oracleData?.image_url ||
                      this.data.oracleData?.card_image_url || '';
    if (!backImage) {
      console.warn('[分享] 背面背景图片路径为空，将使用默认分享图');
    }
    return backImage;
  }
}
```

**关键注意事项**:
- ✅ 返回值支持本地临时路径（`wx://`）和网络URL（`https://`）
- ✅ 空字符串降级由微信自动使用默认图（小程序logo或页面截图）
- ✅ 增加日志便于调试

#### ✅ 新增方法2：生成朋友圈拼接图

```javascript
/**
 * 生成朋友圈拼接图（唯一需要Canvas的地方）
 * @returns {Promise<string>} 临时文件路径
 */
async generateTimelineImage() {
  try {
    // 获取正面和背面图片URL
    const frontImg = this.data.charmImagePath;
    const backImg = this.data.backgroundImage ||
                    this.data.oracleData?.visual_background_image ||
                    this.data.oracleData?.background_image_url ||
                    this.data.oracleData?.image_url ||
                    this.data.oracleData?.card_image_url;

    // 检查资源是否齐全
    if (!frontImg && !backImg) {
      console.warn('[朋友圈分享] 正反面图片均为空，使用空字符串降级');
      return '';
    }

    if (!frontImg || !backImg) {
      console.warn('[朋友圈分享] 缺少一面的图片，使用单张图降级');
      return frontImg || backImg || '';
    }

    // 简单的左右拼接
    console.log('[朋友圈分享] 开始生成拼接图');
    const mergedImage = await this.mergeImages(frontImg, backImg);
    console.log('[朋友圈分享] 拼接图生成成功:', mergedImage);
    return mergedImage;

  } catch (error) {
    console.error('[朋友圈分享] 生成拼接图失败:', error);
    // 降级：返回正面图或背面图
    return this.data.charmImagePath ||
           this.data.backgroundImage ||
           this.data.oracleData?.visual_background_image || '';
  }
}
```

**关键注意事项**:
- ✅ 完整的降级策略：双图 → 单图 → 空字符串
- ✅ 增加详细日志便于排查问题
- ✅ 异常处理保证不会导致分享失败

#### ✅ 新增方法3：图片横向拼接（Canvas实现）

```javascript
/**
 * 图片横向拼接（Canvas实现）
 * @param {string} leftUrl - 左侧图片URL（正面）
 * @param {string} rightUrl - 右侧图片URL（背面）
 * @returns {Promise<string>} 临时文件路径
 */
async mergeImages(leftUrl, rightUrl) {
  return new Promise((resolve, reject) => {
    // 使用组件作用域的 SelectorQuery
    const query = wx.createSelectorQuery().in(this);

    query.select('#share-merge-canvas')
      .fields({ node: true, size: true })
      .exec(async (res) => {
        try {
          // 检查Canvas节点是否存在
          if (!res || !res[0] || !res[0].node) {
            throw new Error('Canvas节点获取失败，请检查WXML中是否存在 id="share-merge-canvas" 的canvas元素');
          }

          const canvas = res[0].node;
          const ctx = canvas.getContext('2d');
          const dpr = wx.getSystemInfoSync().pixelRatio;

          // 朋友圈推荐规格：1:1 或 16:9，这里使用 2:1 (1280x640)
          // 注意：Canvas实际尺寸需乘以DPR以确保清晰度
          canvas.width = 1280 * dpr;
          canvas.height = 640 * dpr;
          ctx.scale(dpr, dpr);

          // 加载左图（正面）
          const leftImage = canvas.createImage();
          leftImage.src = leftUrl;
          await new Promise((resolveImg, rejectImg) => {
            leftImage.onload = resolveImg;
            leftImage.onerror = () => rejectImg(new Error(`左图加载失败: ${leftUrl}`));
            // 设置超时防止永久等待
            setTimeout(() => rejectImg(new Error('左图加载超时')), 10000);
          });

          // 加载右图（背面）
          const rightImage = canvas.createImage();
          rightImage.src = rightUrl;
          await new Promise((resolveImg, rejectImg) => {
            rightImage.onload = resolveImg;
            rightImage.onerror = () => rejectImg(new Error(`右图加载失败: ${rightUrl}`));
            setTimeout(() => rejectImg(new Error('右图加载超时')), 10000);
          });

          // 绘制：左右各640px，等比缩放填充
          // 使用drawImage的9参数版本确保图片居中裁剪
          this._drawImageCover(ctx, leftImage, 0, 0, 640, 640);
          this._drawImageCover(ctx, rightImage, 640, 0, 640, 640);

          // 导出图片
          wx.canvasToTempFilePath({
            canvas: canvas,
            destWidth: 1280,
            destHeight: 640,
            fileType: 'png',
            quality: 1,
            success: (res) => {
              console.log('[Canvas] 图片导出成功:', res.tempFilePath);
              resolve(res.tempFilePath);
            },
            fail: (err) => {
              console.error('[Canvas] 图片导出失败:', err);
              reject(new Error(`Canvas导出失败: ${err.errMsg}`));
            }
          }, this);  // 传入组件实例作为上下文

        } catch (error) {
          console.error('[Canvas] 拼接过程失败:', error);
          reject(error);
        }
      });
  });
}

/**
 * 等比缩放并居中裁剪绘制图片（类似CSS的object-fit: cover）
 * @private
 */
_drawImageCover(ctx, image, dx, dy, dWidth, dHeight) {
  const imgWidth = image.width;
  const imgHeight = image.height;
  const imgRatio = imgWidth / imgHeight;
  const targetRatio = dWidth / dHeight;

  let sx = 0, sy = 0, sWidth = imgWidth, sHeight = imgHeight;

  if (imgRatio > targetRatio) {
    // 图片更宽，裁剪左右
    sWidth = imgHeight * targetRatio;
    sx = (imgWidth - sWidth) / 2;
  } else {
    // 图片更高，裁剪上下
    sHeight = imgWidth / targetRatio;
    sy = (imgHeight - sHeight) / 2;
  }

  ctx.drawImage(image, sx, sy, sWidth, sHeight, dx, dy, dWidth, dHeight);
}
```

**关键技术点**:
- ✅ **DPR缩放**: Canvas宽高乘以设备像素比，确保高清显示
- ✅ **超时处理**: 图片加载设置10秒超时，避免永久等待
- ✅ **居中裁剪**: 使用 `_drawImageCover` 方法实现类似 `object-fit: cover` 的效果
- ✅ **错误信息**: 详细的错误提示便于调试
- ✅ **组件上下文**: `canvasToTempFilePath` 传入 `this` 确保在组件作用域内执行

### 6.2 WXML增加隐藏Canvas

```xml
<!-- hanging-charm.wxml -->
<!-- 在组件根节点内任意位置添加，建议放在最底部 -->

<!-- 仅用于朋友圈拼图，平时隐藏 -->
<canvas
  id="share-merge-canvas"
  type="2d"
  style="position: fixed; left: -9999px; top: 0; width: 640px; height: 640px;">
</canvas>
```

**关键注意事项**:
- ✅ **必须使用 `type="2d"`**: 新版Canvas接口，支持 `canvas.createImage()`
- ✅ **样式尺寸**: `width` 和 `height` 是CSS尺寸，实际Canvas尺寸在JS中动态设置
- ✅ **隐藏方式**: `left: -9999px` 比 `display: none` 更安全，确保Canvas可正常绘制
- ⚠️ **不要使用 `hidden` 属性**: 可能导致Canvas节点无法获取

### 6.3 页面改造

#### 首页 index.js

**❌ 移除代码**:
```javascript
// ❌ 需要移除 onCharmShare 方法（约15行）
onCharmShare(e) {
  const { oracleData, charmType } = e.detail;
  // ...
  wx.showShareMenu({ /* ... */ });
}
```

**✅ 改造 onShareAppMessage**:
```javascript
/**
 * 好友分享：根据当前翻面状态分享
 * 注意：此方法可以返回 Promise 以支持异步获取分享内容
 */
onShareAppMessage() {
  const charm = this.selectComponent('#main-hanging-charm');

  // 降级处理：组件不存在时使用默认分享
  if (!charm) {
    console.warn('[分享] 挂件组件获取失败，使用默认分享配置');
    return {
      title: 'AI心象签 - 将心情映射为自然意象',
      path: '/pages/index/index',
      imageUrl: '' // 空字符串使用小程序默认图
    };
  }

  // 调用组件方法获取分享图
  const shareImage = charm.getShareImage();
  const card = this.data.todayCard;

  // 构建分享标题
  let shareTitle = '我创建了一张AI心象签';
  if (card) {
    const charmName = card.charm_name ||
                     card.oracle_hexagram_name ||
                     card.keyword || '';
    if (charmName) {
      shareTitle = `${charmName} | 我的AI心象签`;
    }
  }

  console.log('[分享] 好友分享配置:', { title: shareTitle, imageUrl: shareImage });

  return {
    title: shareTitle,
    path: `/pages/postcard/postcard?id=${card?.id || ''}`,
    imageUrl: shareImage  // 可以是本地路径或网络URL
  };
}
```

**✅ 改造 onShareTimeline** (支持异步):
```javascript
/**
 * 朋友圈分享：生成左右拼接图
 * 注意：返回 Promise 以支持异步生成拼接图
 */
async onShareTimeline() {
  const charm = this.selectComponent('#main-hanging-charm');

  // 降级处理：组件不存在时使用默认分享
  if (!charm) {
    console.warn('[朋友圈分享] 挂件组件获取失败，使用默认分享配置');
    return {
      title: 'AI心象签',
      imageUrl: ''
    };
  }

  // 异步生成拼接图
  let timelineImage = '';
  try {
    timelineImage = await charm.generateTimelineImage();
  } catch (error) {
    console.error('[朋友圈分享] 生成拼接图失败，降级使用当前面图片:', error);
    // 降级：使用当前面的图片
    timelineImage = charm.getShareImage();
  }

  // 构建分享标题
  const card = this.data.todayCard;
  let timelineTitle = 'AI心象签 - 将心情映射为自然意象';
  if (card) {
    const charmName = card.charm_name ||
                     card.oracle_hexagram_name ||
                     card.keyword || '';
    if (charmName) {
      timelineTitle = `${charmName} | AI心象签`;
    }
  }

  console.log('[朋友圈分享] 分享配置:', { title: timelineTitle, imageUrl: timelineImage });

  return {
    title: timelineTitle,
    imageUrl: timelineImage
  };
}
```

**WXML移除**:
```xml
<!-- ❌ 移除 bind:share 绑定 -->
<!-- 修改前 -->
<hanging-charm
  bind:share="onCharmShare"
></hanging-charm>

<!-- 修改后 -->
<hanging-charm></hanging-charm>
```

#### 详情页 postcard.js

**改造方法与首页完全相同**，唯一区别是数据来源：

```javascript
// 首页使用 this.data.todayCard
// 详情页使用 this.data.postcard 或 this.data.structuredData
```

**详细代码** (与首页逻辑一致，仅数据来源不同):

```javascript
/**
 * 好友分享（与首页逻辑一致）
 */
onShareAppMessage() {
  const charm = this.selectComponent('#main-hanging-charm');

  if (!charm) {
    const { postcard } = this.data;
    return {
      title: 'AI心象签',
      path: `/pages/postcard/postcard?id=${postcard?.id || ''}`,
      imageUrl: postcard?.background_image_url || ''
    };
  }

  const shareImage = charm.getShareImage();
  const { postcard, structuredData } = this.data;

  let shareTitle = '我的AI心象签';
  if (structuredData) {
    const charmName = structuredData.charm_name ||
                     structuredData.oracle_hexagram_name ||
                     structuredData.keyword || '';
    if (charmName) {
      shareTitle = `${charmName} | 我的AI心象签`;
    }
  }

  return {
    title: shareTitle,
    path: `/pages/postcard/postcard?id=${postcard?.id || ''}`,
    imageUrl: shareImage
  };
}

/**
 * 朋友圈分享（与首页逻辑一致）
 */
async onShareTimeline() {
  const charm = this.selectComponent('#main-hanging-charm');

  if (!charm) {
    const { postcard } = this.data;
    return {
      title: 'AI心象签',
      imageUrl: postcard?.background_image_url || ''
    };
  }

  let timelineImage = '';
  try {
    timelineImage = await charm.generateTimelineImage();
  } catch (error) {
    console.error('[朋友圈分享] 生成拼接图失败:', error);
    timelineImage = charm.getShareImage();
  }

  const { structuredData } = this.data;
  let timelineTitle = 'AI心象签';
  if (structuredData) {
    const charmName = structuredData.charm_name ||
                     structuredData.oracle_hexagram_name ||
                     structuredData.keyword || '';
    if (charmName) {
      timelineTitle = `${charmName} | AI心象签`;
    }
  }

  return {
    title: timelineTitle,
    imageUrl: timelineImage
  };
}
```

---

## 7. 错误处理与降级策略

### 降级链路

```
【正面分享降级】
charmImagePath
  → 空字符串（微信使用默认图：小程序logo或页面截图）

【背面分享降级】
backgroundImage
  → visual_background_image
  → background_image_url
  → image_url
  → card_image_url
  → 空字符串

【朋友圈拼接降级】
拼接图（双图合成）
  → 单图（frontImg || backImg）
  → 空字符串
```

### 错误类型与处理

| 错误场景 | 处理策略 | 用户体验 |
| --- | --- | --- |
| Canvas节点获取失败 | 抛出异常，降级返回单图 | 分享单张图片 |
| 图片加载失败 | 捕获 `onerror`，抛出详细错误 | 分享单张图片或默认图 |
| 图片加载超时（>10s） | 超时拒绝Promise | 分享单张图片或默认图 |
| `canvasToTempFilePath` 失败 | 捕获异常，降级返回原始图片 | 分享单张图片 |
| 资源URL全部为空 | 返回空字符串 | 微信使用默认分享图 |
| 组件获取失败 (`selectComponent`) | 返回默认分享配置 | 使用默认标题和图片 |

---

## 8. 微信小程序开发规范检查清单

### 分享功能规范 ✅

- [x] **使用原生分享入口**: 页面右上角菜单，不使用自定义按钮调用 `wx.showShareMenu()`
- [x] **`onShareAppMessage` 返回值正确**:
  - `title`: 字符串，不超过25个字符（超出会被截断）
  - `path`: 以 `/` 开头的页面路径
  - `imageUrl`: 支持本地临时路径、网络URL、代码包文件路径
- [x] **`onShareTimeline` 返回值正确**:
  - `title`: 字符串，不超过25个字符
  - `imageUrl`: 推荐1:1比例，支持网络和本地图片
- [x] **支持异步返回**: `onShareTimeline` 可返回 Promise
- [x] **降级处理完善**: 所有分享方法都有默认返回值

### Canvas API 规范 ✅

- [x] **使用 `type="2d"` Canvas**: 旧版Canvas API已废弃
- [x] **Canvas节点隐藏方式正确**: 使用 `left: -9999px`，不使用 `display: none` 或 `hidden`
- [x] **`SelectorQuery` 使用组件作用域**: `wx.createSelectorQuery().in(this)`
- [x] **DPR处理**: Canvas实际尺寸乘以 `devicePixelRatio`
- [x] **图片加载正确**: 使用 `canvas.createImage()` 而非 `new Image()`
- [x] **导出图片正确**: `wx.canvasToTempFilePath` 传入 `canvas` 对象和组件上下文

### 图片资源规范 ✅

- [x] **支持的图片类型**: PNG、JPG
- [x] **支持的路径类型**:
  - 本地临时路径（`wx://tmp/xxx`）
  - 网络URL（`https://`）
  - 代码包路径（相对路径）
- [x] **图片尺寸建议**:
  - 好友分享: 5:4 比例
  - 朋友圈分享: 1:1 比例（本方案使用2:1）
- [x] **缓存机制**: 使用 `resourceCache` 管理图片缓存

---

## 9. 开发步骤

### 分步实施（预计2小时）

| 步骤 | 内容 | 预计耗时 | 状态 |
|------|------|---------|------|
| **Step 1** | ❌ 移除分享按钮：WXML、JS、WXSS、页面绑定 | 10分钟 | ❌ 待实现 |
| **Step 2** | ✅ 在 `hanging-charm.wxml` 增加隐藏Canvas节点 | 2分钟 | ❌ 待实现 |
| **Step 3** | ✅ 在 `hanging-charm.js` 增加 `getShareImage()` 方法 | 5分钟 | ❌ 待实现 |
| **Step 4** | ✅ 在 `hanging-charm.js` 增加 `_drawImageCover()`、`mergeImages()`、`generateTimelineImage()` 方法 | 40分钟 | ❌ 待实现 |
| **Step 5** | ✅ 改造首页 `onShareAppMessage` 和 `onShareTimeline` | 15分钟 | ❌ 待实现 |
| **Step 6** | ✅ 改造详情页 `onShareAppMessage` 和 `onShareTimeline` | 15分钟 | ❌ 待实现 |
| **Step 7** | 🧪 真机测试分享功能（正面、背面、朋友圈） | 30分钟 | ❌ 待实现 |
| **Step 8** | 🔧 调优降级策略和错误处理 | 20分钟 | ❌ 待实现 |

**总计**: 约 **2小时**

---

## 10. 测试计划

### 功能测试矩阵

| 测试场景 | 验证点 | 预期结果 | 状态 |
| --- | --- | --- | --- |
| 首页正面分享 | 未翻转时点击右上角分享给好友 | 分享图为签体PNG | ❌ 待测试 |
| 首页背面分享 | 翻转后点击右上角分享给好友 | 分享图为背景图 | ❌ 待测试 |
| 详情页正面分享 | 未翻转时点击右上角分享 | 分享图为签体PNG | ❌ 待测试 |
| 详情页背面分享 | 翻转后点击右上角分享 | 分享图为背景图 | ❌ 待测试 |
| 朋友圈分享（首页） | 点击右上角分享到朋友圈 | 分享图为左右拼接图（1280x640） | ❌ 待测试 |
| 朋友圈分享（详情页） | 点击右上角分享到朋友圈 | 分享图为左右拼接图 | ❌ 待测试 |
| 缓存命中 | 多次分享同一张卡片 | 图片URL不变，加载快速 | ❌ 待测试 |
| 降级测试：Canvas失败 | 模拟Canvas节点不存在 | 自动降级到单张图片 | ❌ 待测试 |
| 降级测试：图片加载失败 | 模拟网络图片加载失败 | 捕获错误，降级到其他图片 | ❌ 待测试 |
| 降级测试：资源缺失 | `charmImagePath` 和 `backgroundImage` 都为空 | 返回空字符串，微信使用默认图 | ❌ 待测试 |
| 组件获取失败 | `selectComponent` 返回 null | 使用默认分享配置，不报错 | ❌ 待测试 |

### 兼容性测试

- ❌ iOS 微信 8.0+
- ❌ Android 微信 8.0+
- ❌ 开发者工具
- ❌ 真机测试（iPhone、Android各一台）

### 性能测试

| 指标 | 目标值 | 测量方法 | 状态 |
| --- | --- | --- | --- |
| 正面分享耗时 | <50ms | `console.time()` 计时 | ❌ 待测试 |
| 背面分享耗时 | <50ms | `console.time()` 计时 | ❌ 待测试 |
| 朋友圈拼接耗时 | <500ms | `console.time()` 计时 | ❌ 待测试 |
| 拼接图文件大小 | <500KB | 查看临时文件大小 | ❌ 待测试 |
| Canvas内存占用 | <10MB | 微信开发者工具性能分析 | ❌ 待测试 |

---

## 11. 与原方案对比

| 维度 | 原Canvas渲染方案 | 当前直接复用方案 |
| --- | --- | --- |
| 代码量 | ~500行 | **~160行**（含移除代码） |
| 开发时间 | 3-5天 | **2小时** |
| 正面分享耗时 | 2-3秒 | **<50ms** |
| 背面分享耗时 | 3-5秒 | **<50ms** |
| 朋友圈拼接耗时 | 5-8秒 | **<500ms** |
| 维护成本 | 高（需维护文字排版逻辑） | **低（只维护拼接逻辑）** |
| 技术风险 | 高（字体、竖排、多行） | **低（只有简单图片合成）** |
| 符合微信规范 | ⚠️ 自定义分享按钮可能违规 | **✅ 完全符合规范** |

---

## 12. 常见问题 FAQ

### Q1: 为什么不使用自定义分享按钮？

**A**: 微信小程序规范明确要求：
- 分享必须由用户主动触发
- 推荐使用原生分享菜单
- 自定义分享按钮需使用 `<button open-type="share">`
- 在页面内调用 `wx.showShareMenu()` 可能被视为诱导分享

当前代码中的 `<view catchtap="onShareCharm">` + `wx.showShareMenu()` 组合不符合规范。

### Q2: 分享图片的尺寸要求是什么？

**A**:
- **好友分享**: 推荐 5:4 比例，无硬性尺寸限制
- **朋友圈分享**: 推荐 1:1 比例，本方案使用 2:1 (1280x640) 也可正常显示
- **文件大小**: 建议 <500KB，过大可能导致分享失败

### Q3: Canvas为什么要设置 `left: -9999px` 而不是 `display: none`？

**A**:
- `display: none` 或 `hidden` 属性会导致Canvas元素不在渲染树中
- 部分情况下 `wx.createSelectorQuery()` 可能无法获取到节点
- 使用 `position: fixed; left: -9999px` 确保元素存在但不可见

### Q4: 分享图片为空会怎样？

**A**:
- 返回空字符串 `''` 时，微信会使用默认分享图
- 默认图可能是小程序logo或当前页面截图的前80%区域

### Q5: `onShareTimeline` 为什么要返回 Promise？

**A**:
- 朋友圈拼接图需要异步生成（Canvas绘制、图片加载、导出）
- 微信小程序支持异步返回分享配置
- 使用 `async/await` 可以简化代码逻辑

### Q6: 如何验证分享功能是否生效？

**A**:
1. 在真机上测试（开发者工具的分享功能与真机有差异）
2. 检查日志输出，确认图片URL正确
3. 分享后在好友/朋友圈查看实际展示效果
4. 使用抓包工具查看分享接口请求参数

---

## 13. 未来扩展

### 可选优化方向

1. **预生成拼接图**: 在卡片加载完成后后台生成朋友圈图，缓存到本地存储
2. **自定义水印**: 在拼接图底部增加"AI心象签 · 日期"水印
3. **多种拼接样式**: 支持上下拼接、九宫格等多种布局
4. **分享数据统计**: 记录分享次数、渠道等数据（需后端支持）
5. **分享回流激励**: 通过分享链接进入的用户给予奖励

---

## 14. 总结

本方案通过**直接复用已缓存的签体图和背景图**，避免了复杂的Canvas文字渲染，将代码量从500行降低到160行，开发时间从3-5天缩短到2小时，性能提升10倍以上，同时**完全符合微信小程序开发规范**。

### 核心优势

- ✅ **高效**: 图片已缓存，直接返回
- ✅ **快捷**: 只需160行代码，2小时完成
- ✅ **有用**: 完全满足分享需求，降级策略完善
- ✅ **合规**: 遵循微信小程序分享规范，移除违规自定义按钮
- ✅ **可维护**: 代码简洁，逻辑清晰，易于调试

### 适用场景

- ✅ 签体图和背景图已由AI生成并缓存
- ✅ 背景图已包含完整的文字内容
- ✅ 不需要在分享图上增加额外的动态文字
- ✅ 需要符合微信小程序官方规范

### 不适用场景

- ❌ 需要在分享图上实时叠加用户昵称、时间等信息
- ❌ 背景图不包含文字内容，需要重新绘制
- ❌ 需要复杂的图文混排效果

---

**文档版本**: v2.0
**最后更新**: 2025-10-08
**实施状态**: ❌ 待实施

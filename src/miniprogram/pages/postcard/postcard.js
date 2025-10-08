// pages/postcard/postcard.js - 心象签详情页
const { postcardAPI } = require('../../utils/enhanced-request.js');
const { parseCardData } = require('../../utils/data-parser.js');
const { CardDataManager } = require('../../utils/card-data-manager.js');
const envConfig = require('../../config/env.js');

Page({
  data: {
    postcard: null,
    loading: true,
    error: null,
    // 解析后的结构化数据
    structuredData: null,
    // 是否有有效的结构化数据
    hasStructuredData: false,
    // 调试信息
    debugInfo: null,
    
    // 🔮 挂件式心象签显示控制（从首页照搬）
    selectedCharmType: 'lianhua-yuanpai', // 当前选择的挂件类型
    availableCharmTypes: [ // 可选的挂件类型
      'lianhua-yuanpai',
      'bagua-jinnang', 
      'qingyu-tuanshan'
    ],
    charmConfigs: [], // 🔮 从远程加载的挂件配置数据
    
    // 🔮 资源加载状态管理（从首页照搬）
    resourcesLoading: {
      charmConfigs: false
    },
    resourcesLoaded: {
      charmConfigs: false
    }
  },

  onLoad(options) {
    const { id } = options;
    
    if (!id) {
      this.setData({ 
        loading: false, 
        error: '心象签ID参数缺失' 
      });
      return;
    }
    
    this.postcardId = id;
    this.loadPostcard();
  },

  /**
   * 加载心象签数据 - 优先使用缓存，完全复用首页逻辑
   */
  async loadPostcard() {
    try {
      this.setData({ loading: true, error: null });
      
      envConfig.log('开始加载心象签, ID:', this.postcardId);
      
      // 🚀 步骤1：加载挂件配置（从首页照搬）
      await this.loadCharmConfigs();
      
      // 🚀 步骤2：优先尝试从缓存获取
      let processedData = CardDataManager.getCachedCard(this.postcardId);
      
      if (processedData) {
        envConfig.log('✅ 从缓存获取到卡片数据');
        this.displayCardData(processedData);
        return;
      }
      
      // 🚀 步骤3：缓存不存在，从API获取
      envConfig.log('缓存不存在，从API获取数据');
      const rawPostcard = await postcardAPI.getResult(this.postcardId);
      envConfig.log('API返回原始数据:', rawPostcard);
      
      // 🚀 步骤4：使用与首页完全相同的处理逻辑
      processedData = CardDataManager.processAndCacheCard(rawPostcard);
      
      if (!processedData) {
        throw new Error('数据处理失败');
      }
      
      // 🚀 步骤5：显示数据
      this.displayCardData(processedData);
      
    } catch (error) {
      envConfig.error('加载心象签失败:', error);
      
      let errorMessage = '加载失败，请重试';
      
      // 根据错误类型提供更具体的提示
      if (error.message) {
        if (error.message.includes('404')) {
          errorMessage = '心象签不存在或已被删除';
        } else if (error.message.includes('401') || error.message.includes('403')) {
          errorMessage = '无权限访问此心象签';
        } else if (error.message.includes('Network')) {
          errorMessage = '网络连接失败，请检查网络';
        } else {
          errorMessage = error.message;
        }
      }
      
      this.setData({ 
        loading: false,
        error: errorMessage
      });
    }
  },

  /**
   * 显示卡片数据 - 统一显示逻辑
   */
  displayCardData(processedData) {
    try {
      this.setData({ 
        postcard: processedData.originalCard,
        structuredData: processedData.structuredData,
        hasStructuredData: processedData.hasStructuredData,
        debugInfo: processedData.debugInfo,
        loading: false
      });
      
      // 设置页面标题 - 使用工具类方法
      CardDataManager.updatePageTitle(processedData);
      
      envConfig.log('✅ 详情页数据设置完成:', {
        cardId: processedData.cardId,
        hasStructuredData: processedData.hasStructuredData,
        structuredKeys: processedData.structuredData ? Object.keys(processedData.structuredData).slice(0, 10) : []
      });
      
    } catch (error) {
      envConfig.error('显示卡片数据失败:', error);
      this.setData({ 
        loading: false,
        error: '数据显示失败，请重试'
      });
    }
  },

  /**
   * 🔮 从AI Agent服务动态加载挂件配置（从首页完全照搬）
   */
  async loadCharmConfigs() {
    // 避免重复加载
    if (this.data.resourcesLoading.charmConfigs || this.data.resourcesLoaded.charmConfigs) {
      return this.data.charmConfigs;
    }
    
    try {
      // 设置加载状态
      this.setData({
        'resourcesLoading.charmConfigs': true
      });
      
      const AI_AGENT_PUBLIC_URL = envConfig.AI_AGENT_PUBLIC_URL || 'http://localhost:8080';
      const configUrl = `${AI_AGENT_PUBLIC_URL}/resources/签体/charm-config.json`;
      
      envConfig.log('加载挂件配置:', configUrl);
      
      const response = await new Promise((resolve, reject) => {
        wx.request({
          url: configUrl,
          method: 'GET',
          success: resolve,
          fail: reject
        });
      });
      
      if (response.statusCode === 200 && response.data) {
        // 缓存挂件配置到本地
        wx.setStorageSync('charmConfigs', {
          data: response.data,
          timestamp: Date.now()
        });
        
        // 为每个挂件配置添加完整的图片URL（URL编码处理）
        const charmsWithImageUrls = response.data.map(charm => ({
          ...charm,
          imageUrl: `${AI_AGENT_PUBLIC_URL}/resources/签体/${encodeURIComponent(charm.image)}`
        }));
        
        // 更新页面数据中的可用挂件类型
        this.setData({
          availableCharmTypes: charmsWithImageUrls.map(c => c.id),
          charmConfigs: charmsWithImageUrls,
          'resourcesLoading.charmConfigs': false,
          'resourcesLoaded.charmConfigs': true
        });
        
        envConfig.log('✅ 挂件配置加载成功，共', response.data.length, '种挂件');
        
        // 🔄 异步预下载挂件资源（不阻塞UI）
        this.preloadCharmImages(charmsWithImageUrls);
        
        return charmsWithImageUrls;
        
      } else {
        throw new Error(`HTTP ${response.statusCode}`);
      }
      
    } catch (error) {
      envConfig.error('加载挂件配置失败:', error);
      
      // 重置加载状态
      this.setData({
        'resourcesLoading.charmConfigs': false
      });
      
      // 使用缓存的配置
      try {
        const cached = wx.getStorageSync('charmConfigs');
        if (cached && cached.data && (Date.now() - cached.timestamp) < 24 * 60 * 60 * 1000) {
          envConfig.log('使用缓存的挂件配置');
          const charmsWithImageUrls = cached.data.map(charm => ({
            ...charm,
            imageUrl: `${envConfig.AI_AGENT_PUBLIC_URL || 'http://localhost:8080'}/resources/签体/${encodeURIComponent(charm.image)}`
          }));
          
          this.setData({
            availableCharmTypes: charmsWithImageUrls.map(c => c.id),
            charmConfigs: charmsWithImageUrls,
            'resourcesLoaded.charmConfigs': true
          });
          
          // 🔄 异步预下载缓存的挂件资源
          this.preloadCharmImages(charmsWithImageUrls);
          
          return charmsWithImageUrls;
        }
      } catch (e) {
        envConfig.error('读取缓存配置失败:', e);
      }
      
      // 最后使用默认配置
      envConfig.warn('使用默认挂件配置');
      this.setData({
        availableCharmTypes: ['lianhua-yuanpai', 'bagua-jinnang', 'qingyu-tuanshan']
      });
      return [];
    }
  },

  /**
   * 🔄 预下载挂件资源（异步后台执行）（从首页完全照搬）
   */
  async preloadCharmImages(charmConfigs) {
    if (!Array.isArray(charmConfigs) || charmConfigs.length === 0) {
      return;
    }

    try {
      // 提取所有图片URL
      const imageUrls = charmConfigs
        .filter(charm => charm.imageUrl)
        .map(charm => charm.imageUrl);

      if (imageUrls.length === 0) {
        envConfig.log('没有需要预下载的挂件资源');
        return;
      }

      envConfig.log('🚀 开始预下载挂件资源:', imageUrls.length, '个');

      // 使用资源缓存管理器批量预下载
      const { resourceCache } = require('../../utils/resource-cache.js');
      const results = await resourceCache.preloadResources(imageUrls);
      
      // 统计下载结果
      const successCount = Object.values(results).filter(r => r.success).length;
      const failCount = imageUrls.length - successCount;
      
      envConfig.log('✅ 挂件资源预下载完成:', {
        total: imageUrls.length,
        success: successCount,
        failed: failCount
      });

      // 如果有失败的资源，记录详细信息
      if (failCount > 0) {
        const failedResources = Object.entries(results)
          .filter(([url, result]) => !result.success)
          .map(([url, result]) => ({ url, error: result.error }));
        
        envConfig.warn('预下载失败的资源:', failedResources);
      }

    } catch (error) {
      envConfig.error('挂件资源预下载失败:', error);
    }
  },

  /**
   * 重新加载
   */
  handleRetry() {
    this.loadPostcard();
  },


  /**
   * 删除心象签
   */
  async handleDelete() {
    const app = getApp();
    
    const confirmed = await app.utils.showConfirm(
      '确定要删除这张心象签吗？删除后无法恢复。',
      '删除确认'
    );
    
    if (!confirmed) return;
    
    try {
      app.utils.showLoading('删除中...');
      
      await postcardAPI.delete(this.postcardId);
      
      // 🚀 删除成功后立即清理缓存
      try {
        CardDataManager.clearCard(this.postcardId);
        envConfig.log('✅ 删除卡片后已清理缓存:', this.postcardId);
      } catch (cacheError) {
        envConfig.error('清理缓存失败:', cacheError);
        // 缓存清理失败不影响删除流程
      }
      
      app.utils.hideLoading();
      app.utils.showSuccess('删除成功');
      
      // 🚀 设置首页刷新标记：无论删除今日还是历史卡片，都需要刷新回廊
      try {
        app.globalData = app.globalData || {};
        
        // 检查是否为今日卡片 - 使用统一的时间处理工具
        const pc = this.data.postcard;
        let isToday = true;
        if (pc && pc.created_at) {
          // 尝试从缓存获取原始数据，如果没有则重新获取
          try {
            let originalCardData = null;
            const cachedData = CardDataManager.getCachedCard(this.postcardId);
            if (cachedData && cachedData.originalCard) {
              // 使用缓存中的原始数据（包含未格式化的created_at）
              originalCardData = cachedData.originalCard;
            } else {
              // 如果缓存中也没有原始数据，尝试从API重新获取
              envConfig.log('缓存中没有原始时间数据，将使用格式化后的数据进行近似判断');
              originalCardData = pc;
            }
            
            isToday = CardDataManager.isCardToday(originalCardData);
          } catch (error) {
            envConfig.error('今日判断失败，使用默认值:', error);
            // 降级处理：假设是今日卡片
            isToday = true;
          }
        }
        
        // 若删除的是今日生成的卡片，首页需重置到画布初始状态
        if (isToday) {
          app.globalData.resetToCanvas = true;
        }
        
        // 🆕 无论删除今日还是历史卡片，都需要刷新回廊数据
        app.globalData.refreshUserCards = true;
        
        // 🔥 新增：记录被删除的卡片ID，用于首页检测当前显示的卡片是否被删除
        app.globalData.deletedCardId = this.postcardId;
        
        envConfig.log('✅ 删除卡片后设置刷新标记:', { 
          isToday, 
          deletedCardId: this.postcardId,
          resetToCanvas: app.globalData.resetToCanvas, 
          refreshUserCards: app.globalData.refreshUserCards 
        });
      } catch (_) {}
      
      // 返回首页：优先返回上一页，失败则重启到首页
      setTimeout(() => {
        try {
          wx.navigateBack({
            delta: 1,
            fail: () => {
              wx.reLaunch({ url: '/pages/index/index' });
            }
          });
        } catch (_) {
          wx.reLaunch({ url: '/pages/index/index' });
        }
      }, 800);
      
    } catch (error) {
      envConfig.error('删除心象签失败:', error);
      
      app.utils.hideLoading();
      app.utils.showError('删除失败，请重试');
    }
  },

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
  },

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
  },


  /**
   * 保存卡片截图到相册
   */
  async saveCardScreenshot() {
    const { hasStructuredData } = this.data;
    
    if (!hasStructuredData) {
      wx.showToast({
        title: '当前卡片不支持截图保存',
        icon: 'none'
      });
      return;
    }
    
    try {
      const app = getApp();
      app.utils.showLoading('生成卡片截图...');
      
      // 生成卡片截图
      const imageUrl = await this.generateCardScreenshotForSave();
      
      if (!imageUrl) {
        app.utils.hideLoading();
        wx.showToast({
          title: '截图生成失败',
          icon: 'none'
        });
        return;
      }
      
      // 根据来源分别处理：
      // 1) 组件Canvas截图返回本地路径（wxfile:// 或 /tmp/），可直接保存
      // 2) 远程http/https图片需先downloadFile
      let localFilePath = imageUrl;
      const isRemote = /^https?:\/\//i.test(imageUrl);
      if (isRemote) {
        app.utils.showLoading('下载图片...');
        const downloadRes = await new Promise((resolve, reject) => {
          wx.downloadFile({
            url: imageUrl,
            success: resolve,
            fail: reject
          });
        });
        localFilePath = downloadRes.tempFilePath;
      }
      
      // 🔥 先检查相册权限
      app.utils.showLoading('检查权限...');
      const authResult = await new Promise(resolve => {
        wx.getSetting({
          success: (res) => {
            if (res.authSetting['scope.writePhotosAlbum'] === false) {
              // 用户之前拒绝过，需要引导到设置
              resolve({ needAuth: true, denied: true });
            } else if (res.authSetting['scope.writePhotosAlbum'] === undefined) {
              // 还没有授权过，可以直接申请
              resolve({ needAuth: true, denied: false });
            } else {
              // 已经授权
              resolve({ needAuth: false });
            }
          },
          fail: () => resolve({ needAuth: true, denied: false })
        });
      });
      
      if (authResult.needAuth) {
        if (authResult.denied) {
          // 用户之前拒绝过，引导到设置
          app.utils.hideLoading();
          wx.showModal({
            title: '需要相册权限',
            content: '保存卡片到相册需要相册访问权限，请在设置中开启',
            confirmText: '去设置',
            success: (res) => {
              if (res.confirm) {
                wx.openSetting();
              }
            }
          });
          return;
        } else {
          // 可以申请权限
          try {
            await new Promise((resolve, reject) => {
              wx.authorize({
                scope: 'scope.writePhotosAlbum',
                success: resolve,
                fail: reject
              });
            });
          } catch (error) {
            app.utils.hideLoading();
            wx.showModal({
              title: '需要相册权限',
              content: '保存卡片到相册需要相册访问权限',
              showCancel: false
            });
            return;
          }
        }
      }
      
      app.utils.showLoading('保存中...');
      await new Promise((resolve, reject) => {
        wx.saveImageToPhotosAlbum({
          filePath: localFilePath,
          success: resolve,
          fail: reject
        });
      });
      
      app.utils.hideLoading();
      app.utils.showSuccess('卡片已保存到相册');
      
    } catch (error) {
      const app = getApp();
      app.utils.hideLoading();
      
      if (error.errMsg && error.errMsg.includes('auth deny')) {
        wx.showModal({
          title: '需要授权',
          content: '保存图片需要访问相册权限，请在设置中开启',
          confirmText: '去设置',
          success: (res) => {
            if (res.confirm) {
              wx.openSetting();
            }
          }
        });
      } else {
        app.utils.showError('保存失败，请重试');
      }
      
      envConfig.error('保存卡片截图失败:', error);
    }
  },

  /**
   * 生成卡片截图用于保存
   */
  async generateCardScreenshotForSave() {
    try {
      const { hasStructuredData } = this.data;
      
      // 如果有结构化数据，尝试生成真实的Canvas截图
      if (hasStructuredData) {
        try {
          const screenshotPath = await this.generateRealCardScreenshot();
          if (screenshotPath) {
            return screenshotPath;
          }
        } catch (error) {
          envConfig.error('Canvas截图失败，使用降级方案:', error);
        }
      }
      
      // 降级方案：使用现有的卡片图片
      const { postcard } = this.data;
      if (postcard && (postcard.card_image_url || postcard.image_url)) {
        return postcard.card_image_url || postcard.image_url;
      }
      
      // 最后的降级方案
      return this.fallbackComponentScreenshot();
    } catch (error) {
      envConfig.error('生成卡片截图失败:', error);
      throw error;
    }
  },

  /**
   * 生成真实的卡片截图 - 调用组件的Canvas截图功能
   */
  async generateRealCardScreenshot() {
    try {
      const { hasStructuredData, structuredData } = this.data;
      envConfig.log('开始生成Canvas截图');
      envConfig.log('hasStructuredData:', hasStructuredData);
      envConfig.log('structuredData存在:', !!structuredData);
      
      // 如果没有结构化数据，直接失败
      if (!hasStructuredData) {
        throw new Error('当前心象签没有结构化数据，无法生成Canvas截图');
      }
      
      // 等待一下确保组件已经渲染
      await new Promise(resolve => setTimeout(resolve, 100));
      
      // 获取结构化心象签组件的引用 - 使用ID选择器
      const structuredCard = this.selectComponent('#main-structured-postcard');
      envConfig.log('通过ID获取组件结果:', !!structuredCard);
      
      if (!structuredCard) {
        envConfig.error('无法通过ID获取组件，尝试class选择器');
        // 尝试使用class选择器
        const structuredCardByClass = this.selectComponent('.main-structured-postcard');
        envConfig.log('通过class获取组件结果:', !!structuredCardByClass);
        
        if (!structuredCardByClass) {
          // 尝试不使用选择器，直接查找组件
          const allComponents = this.selectAllComponents('structured-postcard');
          envConfig.log('所有structured-postcard组件:', allComponents.length);
          
          if (allComponents.length > 0) {
            return await this.callComponentScreenshot(allComponents[0]);
          }
          
          throw new Error('无法获取结构化心象签组件，请检查组件是否渲染。可能原因：1) hasStructuredData为false 2) 组件渲染条件不满足');
        }
        return await this.callComponentScreenshot(structuredCardByClass);
      }
      
      return await this.callComponentScreenshot(structuredCard);
      
    } catch (error) {
      envConfig.error('生成Canvas截图失败:', error);
      throw error;
    }
  },

  /**
   * 调用组件截图方法的封装
   */
  async callComponentScreenshot(component) {
    try {
      // 检查组件是否有截图方法
      if (!component.generateCanvasScreenshot) {
        throw new Error('组件不支持Canvas截图功能');
      }
      
      // 调用组件的Canvas截图方法
      const screenshotPath = await component.generateCanvasScreenshot();
      
      envConfig.log('Canvas截图生成成功:', screenshotPath);
      return screenshotPath;
      
    } catch (error) {
      envConfig.error('调用组件截图方法失败:', error);
      throw error;
    }
  },

  /**
   * 降级方案：返回现有图片或提示
   */
  async fallbackComponentScreenshot() {
    const { postcard } = this.data;
    
    if (postcard && (postcard.card_image_url || postcard.image_url)) {
      return postcard.card_image_url || postcard.image_url;
    }
    
    throw new Error('无法生成卡片截图');
  },

  /**
   * 复制心象签内容
   */
  copyContent() {
    const { postcard } = this.data;
    
    if (!postcard || !postcard.content) {
      wx.showToast({
        title: '没有可复制的内容',
        icon: 'none'
      });
      return;
    }
    
    wx.setClipboardData({
      data: postcard.content,
      success: () => {
        wx.showToast({
          title: '已复制到剪贴板',
          icon: 'success'
        });
      }
    });
  },

  /**
   * 动态心象签点击事件
   */
  onDynamicPostcardTap(e) {
    const { postcardData } = e.detail;
    envConfig.log('动态心象签被点击:', postcardData);
    
    // 可以在这里添加额外的交互逻辑
    wx.showToast({
      title: '✨ 动态交互体验',
      icon: 'none',
      duration: 1500
    });
  },

  /**
   * 结构化卡片点击事件
   */
  onStructuredCardTap(e) {
    const { structuredData } = e.detail;
    envConfig.log('结构化卡片被点击:', structuredData);
    
    wx.showToast({
      title: '🎨 智能卡片体验',
      icon: 'none',
      duration: 1500
    });
  },

  /**
   * 推荐内容点击事件
   */
  onRecommendationTap(e) {
    const { type, item } = e.detail;
    envConfig.log('推荐内容被点击:', type, item);
    
    let title = '';
    switch(type) {
      case 'music':
        title = `🎵 ${item.title} - ${item.artist}`;
        break;
      case 'book':
        title = `📚 ${item.title} - ${item.author}`;
        break;
      case 'movie':
        title = `🎬 ${item.title}`;
        break;
      default:
        title = '推荐内容';
    }
    
    wx.showToast({
      title,
      icon: 'none',
      duration: 2000
    });
  },

  /**
   * 结构化卡片分享事件
   */
  onShareStructuredCard(e) {
    const { structuredData } = e.detail;
    envConfig.log('分享结构化卡片:', structuredData);
    
    // 触发小程序分享
    wx.showShareMenu({
      withShareTicket: true,
      menus: ['shareAppMessage', 'shareTimeline']
    });
  },

  // ==================== 🔮 挂件组件事件处理（从首页完全照搬） ====================

  /**
   * 挂件翻面事件处理（从首页完全照搬）
   */
  onCharmFlip(e) {
    const { isFlipped } = e.detail;
    envConfig.log('🔮 挂件翻面状态:', isFlipped ? '背面（解签笺）' : '正面（挂件）');
    
    // 可以在这里添加翻面时的额外逻辑，比如统计、音效等
    if (isFlipped) {
      // 翻到解签笺背面
      console.log('🔮 用户查看解签笺');
    } else {
      // 翻回挂件正面  
      console.log('🔮 用户返回挂件正面');
    }
  },


  /**
   * 详情页卡片翻转事件（旧版兼容）
   */
  onDetailCardFlip(e) {
    const { isFlipped, hasBackContent } = e.detail;
    envConfig.log('详情卡片翻转:', { isFlipped, hasBackContent });
    
    if (isFlipped) {
      wx.showToast({
        title: '✨ 查看解签详解',
        icon: 'none',
        duration: 1500
      });
    } else {
      wx.showToast({
        title: '🎨 返回心象签正面',
        icon: 'none',
        duration: 1500
      });
    }
  },

  /**
   * 详情卡片切换事件
   */
  onDetailCardToggle(e) {
    const { card, expanded } = e.detail;
    envConfig.log('详情卡片切换:', { card, expanded });
    
    if (expanded) {
      wx.showToast({
        title: `📖 展开${this.getCardTitle(card)}`,
        icon: 'none',
        duration: 1000
      });
    }
  },

  /**
   * 洞察标签切换事件
   */
  onInsightTabSwitch(e) {
    const { activeTab, previousTab } = e.detail;
    envConfig.log('洞察标签切换:', { activeTab, previousTab });
    
    const tabTitles = {
      reflections: '深度思考',
      gratitude: '感恩记录', 
      actions: '微行动'
    };
    
    wx.showToast({
      title: `💫 切换到${tabTitles[activeTab] || activeTab}`,
      icon: 'none',
      duration: 1000
    });
  },

  /**
   * 显示扩展内容事件
   */
  onShowExtended(e) {
    const { content } = e.detail;
    envConfig.log('显示扩展内容:', content);
    
    if (content && content.length > 0) {
      // 构建扩展内容文本
      const extendedText = content.map(item => 
        `${item.title}:\n${Array.isArray(item.content) ? item.content.join('\n') : item.content}`
      ).join('\n\n');
      
      wx.showModal({
        title: '📈 深度解析',
        content: extendedText,
        showCancel: false,
        confirmText: '了解'
      });
    }
  },

  /**
   * 显示推荐内容事件
   */
  onShowRecommendations(e) {
    const { recommendations } = e.detail;
    envConfig.log('显示推荐内容:', recommendations);
    
    if (recommendations && recommendations.length > 0) {
      // 构建推荐内容文本
      const recommendText = recommendations.map(item => 
        `${item.title}:\n${item.content}`
      ).join('\n\n');
      
      wx.showModal({
        title: '💡 智能推荐',
        content: recommendText,
        showCancel: false,
        confirmText: '好的'
      });
    }
  },

  /**
   * 获取卡片标题
   */
  getCardTitle(cardType) {
    const titles = {
      ink: '笔触解析',
      guide: '生活指引',
      insights: '心境洞察',
      meta: '解签信息'
    };
    return titles[cardType] || cardType;
  },


  /**
   * 预览小程序组件代码
   */
  previewCode() {
    const { postcard } = this.data;
    
    if (!postcard || (!postcard.miniprogram_component && !postcard.frontend_code)) {
      wx.showToast({
        title: '暂无组件代码',
        icon: 'none'
      });
      return;
    }
    
    // 显示组件信息
    let content = '这张心象签包含动态小程序组件';
    if (postcard.has_animation) {
      content += '，具有精美的动画效果';
    }
    if (postcard.has_interactive) {
      content += '，支持交互操作';
    }
    content += '。';
    
    wx.showModal({
      title: '小程序组件',
      content,
      confirmText: '查看详情',
      success: (res) => {
        if (res.confirm) {
          this.showComponentDetails();
        }
      }
    });
    
    envConfig.log('组件代码:', postcard.miniprogram_component || postcard.frontend_code);
  },

  /**
   * 显示组件详情
   */
  showComponentDetails() {
    const { postcard } = this.data;
    if (!postcard.miniprogram_component) return;
    
    const component = postcard.miniprogram_component;
    let details = '组件包含：\n';
    
    if (component.wxml) {
      details += `• WXML模板 (${Math.round(component.wxml.length / 10) * 10}字符)\n`;
    }
    if (component.wxss) {
      details += `• WXSS样式 (${Math.round(component.wxss.length / 10) * 10}字符)\n`;
    }
    if (component.js) {
      details += `• JavaScript逻辑 (${Math.round(component.js.length / 10) * 10}字符)\n`;
    }
    
    wx.showModal({
      title: '组件构成',
      content: details,
      showCancel: false
    });
  },

  /**
   * 预览完整图片
   */
  previewFullImage(e) {
    const { url } = e.currentTarget.dataset;
    
    if (url) {
      wx.previewImage({
        current: url,
        urls: [url]
      });
    }
  },

  /**
   * 返回首页
   */
  goHome() {
    wx.switchTab({
      url: '/pages/index/index'
    });
  }
});

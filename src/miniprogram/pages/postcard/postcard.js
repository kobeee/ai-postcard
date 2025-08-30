// pages/postcard/postcard.js - 明信片详情页
const { postcardAPI } = require('../../utils/request.js');
const { parseCardData } = require('../../utils/data-parser.js');
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
    debugInfo: null
  },

  onLoad(options) {
    const { id } = options;
    
    if (!id) {
      this.setData({ 
        loading: false, 
        error: '明信片ID参数缺失' 
      });
      return;
    }
    
    this.postcardId = id;
    this.loadPostcard();
  },

  /**
   * 加载明信片数据
   */
  async loadPostcard() {
    try {
      this.setData({ loading: true, error: null });
      
      envConfig.log('开始加载明信片, ID:', this.postcardId);
      
      const postcard = await postcardAPI.getResult(this.postcardId);
      envConfig.log('API返回原始数据:', postcard);
      
      // ✅ 使用统一的数据解析逻辑
      const parseResult = parseCardData(postcard);
      
      this.setData({ 
        postcard,
        structuredData: parseResult.structuredData,
        hasStructuredData: parseResult.hasStructuredData,
        debugInfo: parseResult.debugInfo,
        loading: false
      });
      
      // 设置页面标题
      const title = parseResult.structuredData?.title || '明信片详情';
      wx.setNavigationBarTitle({
        title: title
      });
      
    } catch (error) {
      envConfig.error('加载明信片失败:', error);
      
      let errorMessage = '加载失败，请重试';
      
      // 根据错误类型提供更具体的提示
      if (error.message) {
        if (error.message.includes('404')) {
          errorMessage = '明信片不存在或已被删除';
        } else if (error.message.includes('401') || error.message.includes('403')) {
          errorMessage = '无权限访问此明信片';
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
   * 重新加载
   */
  handleRetry() {
    this.loadPostcard();
  },


  /**
   * 删除明信片
   */
  async handleDelete() {
    const app = getApp();
    
    const confirmed = await app.utils.showConfirm(
      '确定要删除这张明信片吗？删除后无法恢复。',
      '删除确认'
    );
    
    if (!confirmed) return;
    
    try {
      app.utils.showLoading('删除中...');
      
      await postcardAPI.delete(this.postcardId);
      
      app.utils.hideLoading();
      app.utils.showSuccess('删除成功');
      
      // 若删除的是今日生成的卡片，首页需重置到画布初始状态
      try {
        const pc = this.data.postcard;
        let isToday = true;
        if (pc && pc.created_at) {
          const todayStr = new Date().toDateString();
          const cardDayStr = new Date(pc.created_at).toDateString();
          isToday = (todayStr === cardDayStr);
        }
        if (isToday) {
          app.globalData = app.globalData || {};
          app.globalData.resetToCanvas = true;
        }
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
      envConfig.error('删除明信片失败:', error);
      
      app.utils.hideLoading();
      app.utils.showError('删除失败，请重试');
    }
  },

  /**
   * 分享明信片
   */
  onShareAppMessage() {
    const { postcard, structuredData, hasStructuredData } = this.data;
    
    if (!postcard) {
      return {
        title: 'AI明信片 - 每一天，都值得被温柔记录',
        path: '/pages/index/index'
      };
    }
    
    // 构建个性化分享标题
    let shareTitle = '我用AI制作了一张明信片，快来看看！';
    if (hasStructuredData && structuredData) {
      const cardTitle = structuredData.title || structuredData.card_title;
      const mood = structuredData.mood?.primary;
      if (cardTitle) {
        shareTitle = `${cardTitle} | 我的AI明信片`;
      } else if (mood) {
        shareTitle = `今天的心情是${mood} | 我的AI明信片`;
      }
    }
    
    return {
      title: shareTitle,
      path: `/pages/postcard/postcard?id=${postcard.id || this.postcardId}`,
      imageUrl: postcard.card_image_url || postcard.image_url
    };
  },

  /**
   * 分享到朋友圈
   */
  onShareTimeline() {
    const { postcard, structuredData, hasStructuredData } = this.data;
    
    if (!postcard) {
      return {
        title: 'AI明信片 - 每一天，都值得被温柔记录'
      };
    }
    
    // 构建朋友圈分享标题 
    let timelineTitle = 'AI明信片 - 每一天，都值得被温柔记录';
    if (hasStructuredData && structuredData) {
      const cardTitle = structuredData.title || structuredData.card_title;
      const location = structuredData.context?.location;
      const weather = structuredData.context?.weather;
      
      if (cardTitle && location) {
        timelineTitle = `${cardTitle} | ${location}的AI明信片`;
      } else if (cardTitle) {
        timelineTitle = `${cardTitle} | AI明信片`;
      } else if (location && weather) {
        timelineTitle = `${location}，${weather} | AI明信片记录`;
      }
    }
    
    return {
      title: timelineTitle,
      imageUrl: postcard.card_image_url || postcard.image_url
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
      
      app.utils.showLoading('下载图片...');
      
      // 下载图片
      const downloadRes = await new Promise((resolve, reject) => {
        wx.downloadFile({
          url: imageUrl,
          success: resolve,
          fail: reject
        });
      });
      
      app.utils.showLoading('保存中...');
      
      // 保存到相册
      await new Promise((resolve, reject) => {
        wx.saveImageToPhotosAlbum({
          filePath: downloadRes.tempFilePath,
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
        throw new Error('当前明信片没有结构化数据，无法生成Canvas截图');
      }
      
      // 等待一下确保组件已经渲染
      await new Promise(resolve => setTimeout(resolve, 100));
      
      // 获取结构化明信片组件的引用 - 使用ID选择器
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
          
          throw new Error('无法获取结构化明信片组件，请检查组件是否渲染。可能原因：1) hasStructuredData为false 2) 组件渲染条件不满足');
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
   * 复制明信片内容
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
   * 动态明信片点击事件
   */
  onDynamicPostcardTap(e) {
    const { postcardData } = e.detail;
    envConfig.log('动态明信片被点击:', postcardData);
    
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
    let content = '这张明信片包含动态小程序组件';
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
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
      
      this.setData({ 
        loading: false,
        error: error.message || '加载失败，请重试'
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
      
      // 返回上一页
      setTimeout(() => {
        wx.navigateBack();
      }, 1500);
      
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
    const { postcard } = this.data;
    
    if (!postcard) {
      return {
        title: 'AI明信片',
        path: '/pages/index/index'
      };
    }
    
    return {
      title: `我用AI制作了一张明信片，快来看看！`,
      path: `/pages/postcard/postcard?id=${postcard.id}`,
      imageUrl: postcard.card_image_url || postcard.image_url
    };
  },

  /**
   * 分享到朋友圈
   */
  onShareTimeline() {
    const { postcard } = this.data;
    
    if (!postcard) {
      return {
        title: 'AI明信片 - 让AI为你创作独特明信片'
      };
    }
    
    return {
      title: `AI明信片 - 让AI为你创作独特明信片`,
      imageUrl: postcard.image_url
    };
  },

  /**
   * 保存图片到相册
   */
  async saveImage() {
    const { postcard } = this.data;
    
    if (!postcard || !(postcard.card_image_url || postcard.image_url)) {
      wx.showToast({
        title: '没有可保存的图片',
        icon: 'none'
      });
      return;
    }
    
    try {
      const app = getApp();
      app.utils.showLoading('保存中...');
      
      // 下载图片
      const res = await new Promise((resolve, reject) => {
        wx.downloadFile({
          url: postcard.card_image_url || postcard.image_url,
          success: resolve,
          fail: reject
        });
      });
      
      // 保存到相册
      await new Promise((resolve, reject) => {
        wx.saveImageToPhotosAlbum({
          filePath: res.tempFilePath,
          success: resolve,
          fail: reject
        });
      });
      
      app.utils.hideLoading();
      app.utils.showSuccess('已保存到相册');
      
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
      
      envConfig.error('保存图片失败:', error);
    }
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
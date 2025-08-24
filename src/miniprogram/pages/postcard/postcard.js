// pages/postcard/postcard.js - 明信片详情页
const { postcardAPI } = require('../../utils/request.js');
const envConfig = require('../../config/env.js');

Page({
  data: {
    postcard: null,
    loading: true,
    error: null
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
      
      const postcard = await postcardAPI.getResult(this.postcardId);
      
      this.setData({ 
        postcard, 
        loading: false 
      });
      
      // 设置页面标题
      wx.setNavigationBarTitle({
        title: '明信片详情'
      });
      
      envConfig.log('明信片加载完成:', postcard);
      
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
      imageUrl: postcard.image_url
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
    
    if (!postcard || !postcard.image_url) {
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
          url: postcard.image_url,
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
   * 预览生成的HTML代码（如果有的话）
   */
  previewCode() {
    const { postcard } = this.data;
    
    if (!postcard || !postcard.frontend_code) {
      wx.showToast({
        title: '暂无交互代码',
        icon: 'none'
      });
      return;
    }
    
    // 可以在这里打开一个新页面显示生成的HTML代码
    // 或者使用web-view组件
    envConfig.log('预览代码:', postcard.frontend_code);
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
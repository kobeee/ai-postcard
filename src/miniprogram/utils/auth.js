// utils/auth.js - 用户认证工具
const { authAPI } = require('./request.js');
const envConfig = require('../config/env.js');

/**
 * 用户认证管理器
 */
class AuthManager {
  constructor() {
    this.userInfo = null;
    this.token = null;
    this.isLoggingIn = false;
  }
  
  /**
   * 初始化认证状态
   */
  async init() {
    try {
      // 从本地存储获取token和用户信息
      this.token = wx.getStorageSync('userToken');
      this.userInfo = wx.getStorageSync('userInfo');
      
      // 如果有token，验证其有效性
      if (this.token) {
        const isValid = await this.validateToken();
        if (!isValid) {
          await this.clearAuth();
        }
      }
      
      envConfig.log('认证初始化完成', { hasToken: !!this.token, hasUserInfo: !!this.userInfo });
    } catch (error) {
      envConfig.error('认证初始化失败:', error);
      await this.clearAuth();
    }
  }
  
  /**
   * 验证token有效性
   */
  async validateToken() {
    try {
      if (!this.token) return false;
      
      const userInfo = await authAPI.getUserInfo();
      this.userInfo = userInfo;
      wx.setStorageSync('userInfo', userInfo);
      
      return true;
    } catch (error) {
      envConfig.error('Token验证失败:', error);
      return false;
    }
  }
  
  /**
   * 微信登录
   */
  async login() {
    if (this.isLoggingIn) {
      envConfig.log('登录进行中，请稍候');
      return null;
    }
    
    try {
      this.isLoggingIn = true;
      
      // 1. 获取微信登录code
      const loginResult = await this.wxLogin();
      const { code } = loginResult;
      
      // 2. 获取用户信息授权
      const userProfile = await this.getUserProfile();
      
      // 3. 发送到后端进行认证
      const authResult = await authAPI.login(code, userProfile);
      const { token, userInfo, refreshToken } = authResult;
      
      // 4. 保存认证信息
      this.token = token;
      this.userInfo = userInfo;
      
      wx.setStorageSync('userToken', token);
      wx.setStorageSync('userInfo', userInfo);
      wx.setStorageSync('refreshToken', refreshToken);
      
      envConfig.log('登录成功:', userInfo);
      
      // 触发登录成功事件
      this.triggerLoginSuccess(userInfo);
      
      return userInfo;
      
    } catch (error) {
      envConfig.error('登录失败:', error);
      
      // 显示错误提示
      wx.showToast({
        title: '登录失败，请重试',
        icon: 'none',
        duration: 2000
      });
      
      throw error;
    } finally {
      this.isLoggingIn = false;
    }
  }
  
  /**
   * 微信原生登录
   */
  wxLogin() {
    return new Promise((resolve, reject) => {
      wx.login({
        success: resolve,
        fail: reject
      });
    });
  }
  
  /**
   * 获取用户信息
   */
  async getUserProfile() {
    return new Promise((resolve, reject) => {
      // 检查是否已有用户信息授权
      wx.getSetting({
        success: (settingResult) => {
          if (settingResult.authSetting['scope.userInfo']) {
            // 已授权，直接获取用户信息
            wx.getUserInfo({
              success: resolve,
              fail: reject
            });
          } else {
            // 未授权，需要用户点击授权
            // 这里应该引导用户到授权页面
            reject(new Error('需要用户授权'));
          }
        },
        fail: reject
      });
    });
  }
  
  /**
   * 手动获取用户授权（用于按钮点击）
   */
  async getUserProfileByButton() {
    return new Promise((resolve, reject) => {
      // 注意：getUserProfile 需要用户主动触发（如按钮点击）
      wx.getUserProfile({
        desc: '用于完善会员资料',
        success: resolve,
        fail: reject
      });
    });
  }
  
  /**
   * 退出登录
   */
  async logout() {
    try {
      // 清除本地存储
      await this.clearAuth();
      
      // 显示退出成功提示
      wx.showToast({
        title: '已退出登录',
        icon: 'success',
        duration: 1500
      });
      
      // 触发退出登录事件
      this.triggerLogout();
      
      envConfig.log('用户已退出登录');
      
    } catch (error) {
      envConfig.error('退出登录失败:', error);
    }
  }
  
  /**
   * 清除认证信息
   */
  async clearAuth() {
    this.token = null;
    this.userInfo = null;
    
    wx.removeStorageSync('userToken');
    wx.removeStorageSync('userInfo');
    wx.removeStorageSync('refreshToken');
  }
  
  /**
   * 检查登录状态
   */
  isLoggedIn() {
    return !!(this.token && this.userInfo);
  }
  
  /**
   * 获取当前用户信息
   */
  getCurrentUser() {
    return this.userInfo;
  }
  
  /**
   * 获取当前token
   */
  getToken() {
    return this.token;
  }
  
  /**
   * 刷新token
   */
  async refreshToken() {
    try {
      const refreshToken = wx.getStorageSync('refreshToken');
      if (!refreshToken) {
        throw new Error('无刷新token');
      }
      
      const result = await authAPI.refresh(refreshToken);
      const { token, userInfo } = result;
      
      this.token = token;
      this.userInfo = userInfo;
      
      wx.setStorageSync('userToken', token);
      wx.setStorageSync('userInfo', userInfo);
      
      envConfig.log('Token刷新成功');
      return true;
      
    } catch (error) {
      envConfig.error('Token刷新失败:', error);
      await this.clearAuth();
      return false;
    }
  }
  
  /**
   * 触发登录成功事件
   */
  triggerLoginSuccess(userInfo) {
    const app = getApp();
    if (app && app.onUserLogin) {
      app.onUserLogin(userInfo);
    }
  }
  
  /**
   * 触发退出登录事件
   */
  triggerLogout() {
    const app = getApp();
    if (app && app.onUserLogout) {
      app.onUserLogout();
    }
  }
  
  /**
   * 检查并确保用户已登录
   */
  async ensureLogin() {
    if (!this.isLoggedIn()) {
      await this.login();
    }
    return this.isLoggedIn();
  }
}

// 创建认证管理实例
const authManager = new AuthManager();

module.exports = {
  authManager,
  
  // 导出常用方法
  init: () => authManager.init(),
  login: () => authManager.login(),
  logout: () => authManager.logout(),
  isLoggedIn: () => authManager.isLoggedIn(),
  getCurrentUser: () => authManager.getCurrentUser(),
  getToken: () => authManager.getToken(),
  ensureLogin: () => authManager.ensureLogin(),
  getUserProfileByButton: () => authManager.getUserProfileByButton()
};
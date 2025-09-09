// utils/enhanced-auth.js - 增强版用户认证工具
// 使用增强请求管理器以获得重试与统一错误处理
const { enhancedRequestManager } = require('./enhanced-request.js');
const envConfig = require('../config/env.js');

/**
 * 增强版认证管理器
 * 支持JWT Token管理、自动刷新、错误恢复和向后兼容
 */
class EnhancedAuthManager {
  constructor() {
    this.userInfo = null;
    this.token = null;
    this.refreshToken = null;
    this.tokenExpiry = null;
    this.isLoggingIn = false;
    this.isRefreshing = false;
    this.refreshPromise = null;
    this.loginPromise = null; // 防重复登录的单飞开关
    this.lastLoginAt = 0;     // 登录节流时间戳
    
    // 配置参数
    this.config = {
      // Token刷新提前时间（5分钟）
      refreshBeforeExpiry: 5 * 60 * 1000,
      // 最大重试次数
      maxRetries: 3,
      // 重试延迟（毫秒）
      retryDelay: 1000,
      // 向后兼容模式
      legacyMode: false,
      // 本地存储加密
      encryptStorage: false
    };
    
    // 事件监听器
    this.listeners = {
      login: [],
      logout: [],
      tokenRefresh: [],
      error: []
    };
    
    // 初始化
    this.init();
  }
  
  /**
   * 初始化认证状态
   */
  async init() {
    try {
      // 检测服务器支持的认证模式
      await this.detectAuthMode();
      
      // 从本地存储恢复认证信息
      await this.restoreAuthState();
      
      // 如果有token，验证并自动刷新
      if (this.token) {
        await this.validateAndRefreshToken();
      }
      
      // 设置token自动刷新
      this.setupAutoRefresh();
      
      envConfig.log('增强认证初始化完成', {
        hasToken: !!this.token,
        hasUserInfo: !!this.userInfo,
        legacyMode: this.config.legacyMode
      });
      
    } catch (error) {
      envConfig.error('增强认证初始化失败:', error);
      await this.clearAuth();
    }
  }
  
  /**
   * 检测服务器认证模式 - 简化为直接使用JWT模式
   */
  async detectAuthMode() {
    // 直接使用JWT认证模式，不需要检测
    this.config.legacyMode = false;
    envConfig.log('使用JWT认证模式');
  }
  
  /**
   * 恢复认证状态
   */
  async restoreAuthState() {
    try {
      const storedData = this.getStorageData();
      
      this.token = storedData.token;
      this.refreshToken = storedData.refreshToken;
      this.userInfo = storedData.userInfo;
      this.tokenExpiry = storedData.tokenExpiry;
      
    } catch (error) {
      envConfig.error('恢复认证状态失败:', error);
    }
  }
  
  /**
   * 获取存储数据
   */
  getStorageData() {
    try {
      const data = {
        token: wx.getStorageSync('userToken'),
        refreshToken: wx.getStorageSync('refreshToken'),
        userInfo: wx.getStorageSync('userInfo'),
        tokenExpiry: wx.getStorageSync('tokenExpiry')
      };
      
      // TODO: 解密存储数据
      if (this.config.encryptStorage) {
        // 实现数据解密逻辑
      }
      
      return data;
    } catch (error) {
      envConfig.error('读取存储数据失败:', error);
      return {};
    }
  }
  
  /**
   * 保存认证数据
   */
  saveAuthData(token, refreshToken, userInfo, tokenExpiry) {
    try {
      const data = {
        userToken: token,
        refreshToken: refreshToken,
        userInfo: userInfo,
        tokenExpiry: tokenExpiry
      };
      
      // TODO: 加密存储数据
      if (this.config.encryptStorage) {
        // 实现数据加密逻辑
      }
      
      // 保存到本地存储
      for (const [key, value] of Object.entries(data)) {
        if (value) {
          wx.setStorageSync(key, value);
        }
      }
      
    } catch (error) {
      envConfig.error('保存认证数据失败:', error);
    }
  }
  
  /**
   * 增强版微信登录
   */
  async login() {
    // 单飞：已有登录流程，复用同一个Promise
    if (this.loginPromise) {
      envConfig.log('已有登录流程进行中，复用同一Promise');
      return await this.loginPromise;
    }
    // 节流：5秒内避免重复触发，缓解429
    const now = Date.now();
    const cooldown = 5000;
    if (now - this.lastLoginAt < cooldown) {
      envConfig.log('登录节流中，返回上次用户信息');
      return this.userInfo || null;
    }
    this.lastLoginAt = now;
    
    try {
      this.isLoggingIn = true;
      // 建立单飞Promise
      this.loginPromise = (async () => {
      
      // 1. 获取微信登录code
      const loginResult = await this.wxLogin();
      const { code } = loginResult;
      
      // 2. 获取用户信息授权
      const userProfile = await this.getUserProfile();
      
      // 3. 发送到后端进行认证（支持新旧模式）
      const authResult = await this.performLogin(code, userProfile);
      
      // 4. 处理认证结果
      await this.handleLoginSuccess(authResult);
      
      envConfig.log('增强登录成功:', this.userInfo);
      this.emit('login', this.userInfo);
      
      return this.userInfo;
      })();
      return await this.loginPromise;
      
    } catch (error) {
      envConfig.error('增强登录失败:', error);
      this.emit('error', error);
      
      // 显示用户友好的错误信息
      await this.showErrorMessage(error);
      
      throw error;
    } finally {
      this.isLoggingIn = false;
      this.loginPromise = null;
    }
  }
  
  /**
   * 执行登录请求
   */
  async performLogin(code, userProfile) {
    const loginData = {
      code: code,
      userInfo: userProfile
    };
    
    try {
      envConfig.log('执行登录请求');
      
      const response = await enhancedRequestManager.post(
        envConfig.getApiUrl('/miniprogram/auth/login'),
        loginData,
        { 
          timeout: 15000,
          // 禁用重试，避免与enhanced-request.js的重试机制冲突
          maxRetries: 0,
          enableCache: false
        }
      );
      
      return response;
      
    } catch (error) {
      // 429错误不在认证层重试，直接抛出
      if (error.statusCode === 429) {
        envConfig.warn('登录遇到限流，请稍后重试');
        throw error;
      }
      
      // 其他错误也不在认证层重试，交由enhanced-request处理
      envConfig.error('登录失败:', error.message);
      throw error;
    }
  }
  
  /**
   * 处理登录成功
   */
  async handleLoginSuccess(authResult) {
    if (this.config.legacyMode) {
      // 兼容模式：只有用户信息
      this.userInfo = authResult.userInfo || authResult;
      this.token = null;
      this.refreshToken = null;
      this.tokenExpiry = null;
      
      this.saveAuthData(null, null, this.userInfo, null);
      
    } else {
      // JWT模式：完整的token管理
      const { token, refreshToken, userInfo, expiresIn } = authResult;
      
      this.token = token;
      this.refreshToken = refreshToken;
      this.userInfo = userInfo;
      this.tokenExpiry = expiresIn ? Date.now() + (expiresIn * 1000) : null;
      
      this.saveAuthData(token, refreshToken, userInfo, this.tokenExpiry);
    }
  }
  
  /**
   * 增强版token验证和刷新
   */
  async validateAndRefreshToken() {
    if (!this.token) return false;
    
    try {
      // 检查token是否即将过期
      if (this.shouldRefreshToken()) {
        const refreshed = await this.refreshTokenIfNeeded();
        if (!refreshed) {
          await this.clearAuth();
          return false;
        }
      }
      
      // 验证token有效性
      const userInfo = await this.validateToken();
      if (userInfo) {
        this.userInfo = userInfo;
        wx.setStorageSync('userInfo', userInfo);
        return true;
      }
      
      return false;
      
    } catch (error) {
      envConfig.error('Token验证失败:', error);
      
      // 如果是401错误，尝试刷新token
      if (error.statusCode === 401 || error.code === 401) {
        const refreshed = await this.refreshTokenIfNeeded();
        if (refreshed) {
          return await this.validateToken();
        }
      }
      
      await this.clearAuth();
      return false;
    }
  }
  
  /**
   * 检查是否需要刷新token
   */
  shouldRefreshToken() {
    if (!this.tokenExpiry) return false;
    
    const timeToExpiry = this.tokenExpiry - Date.now();
    return timeToExpiry <= this.config.refreshBeforeExpiry;
  }
  
  /**
   * 刷新token（防止重复刷新）
   */
  async refreshTokenIfNeeded() {
    if (this.config.legacyMode) {
      return true; // 兼容模式无需刷新
    }
    
    if (this.isRefreshing) {
      // 如果正在刷新，等待现有的刷新完成
      return await this.refreshPromise;
    }
    
    this.isRefreshing = true;
    this.refreshPromise = this.performTokenRefresh();
    
    try {
      const result = await this.refreshPromise;
      return result;
    } finally {
      this.isRefreshing = false;
      this.refreshPromise = null;
    }
  }
  
  /**
   * 执行token刷新
   */
  async performTokenRefresh() {
    try {
      if (!this.refreshToken) {
        throw new Error('无刷新token');
      }
      
      // 刷新节流：10秒内只允许一次刷新
      if (!this._lastRefreshAt) this._lastRefreshAt = 0;
      const now = Date.now();
      if (now - this._lastRefreshAt < 10000) {
        envConfig.log('跳过频繁刷新（节流中）');
        return false;
      }
      this._lastRefreshAt = now;

      const response = await enhancedRequestManager.post(
        envConfig.getApiUrl('/miniprogram/auth/refresh'),
        { refreshToken: this.refreshToken },
        { timeout: 10000 }
      );
      
      const { token, refreshToken, userInfo, expiresIn } = response;
      
      this.token = token;
      // 同步更新新的刷新令牌（后端会轮换refreshToken）
      if (refreshToken) {
        this.refreshToken = refreshToken;
        wx.setStorageSync('refreshToken', refreshToken);
      }
      this.userInfo = userInfo;
      this.tokenExpiry = expiresIn ? Date.now() + (expiresIn * 1000) : null;
      
      this.saveAuthData(token, this.refreshToken, userInfo, this.tokenExpiry);
      
      envConfig.log('Token刷新成功');
      this.emit('tokenRefresh', { token, userInfo });
      
      return true;
      
    } catch (error) {
      envConfig.error('Token刷新失败:', error);
      // 刷新失败后清理，避免后续请求继续401风暴
      await this.clearAuth();
      return false;
    }
  }
  
  /**
   * 验证token
   */
  async validateToken() {
    try {
      if (this.config.legacyMode) {
        // 兼容模式：返回本地用户信息
        return this.userInfo;
      }
      
      const userInfo = await enhancedRequestManager.get(
        envConfig.getApiUrl('/miniprogram/auth/userinfo'),
        {},
        { timeout: 8000 }
      );
      
      return userInfo;
      
    } catch (error) {
      envConfig.error('Token验证失败:', error);
      throw error;
    }
  }
  
  /**
   * 设置自动刷新
   */
  setupAutoRefresh() {
    if (this.config.legacyMode) return;
    
    // 每分钟检查一次token状态
    setInterval(async () => {
      if (this.token && this.shouldRefreshToken()) {
        await this.refreshTokenIfNeeded();
      }
    }, 60000);
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
   * 获取用户信息（兼容新旧API）
   */
  async getUserProfile() {
    return new Promise((resolve, reject) => {
      // 优先尝试新的getUserProfile API
      if (typeof wx.getUserProfile === 'function') {
        wx.getUserProfile({
          desc: '用于完善会员资料',
          success: resolve,
          fail: (error) => {
            envConfig.log('getUserProfile失败，尝试getUserInfo:', error);
            this.fallbackGetUserInfo(resolve, reject);
          }
        });
      } else {
        // 回退到getUserInfo
        this.fallbackGetUserInfo(resolve, reject);
      }
    });
  }
  
  /**
   * 回退的用户信息获取
   */
  fallbackGetUserInfo(resolve, reject) {
    wx.getSetting({
      success: (settingResult) => {
        if (settingResult.authSetting['scope.userInfo']) {
          wx.getUserInfo({
            success: resolve,
            fail: reject
          });
        } else {
          reject(new Error('需要用户授权'));
        }
      },
      fail: reject
    });
  }
  
  /**
   * 增强版退出登录
   */
  async logout() {
    try {
      // 如果支持JWT，通知服务器logout
      if (!this.config.legacyMode && this.token) {
        try {
          await enhancedRequestManager.post(
            envConfig.getApiUrl('/miniprogram/auth/logout'),
            {},
            { timeout: 5000 }
          );
        } catch (error) {
          envConfig.log('服务器logout失败，继续本地清理:', error);
        }
      }
      
      await this.clearAuth();
      
      wx.showToast({
        title: '已退出登录',
        icon: 'success',
        duration: 1500
      });
      
      this.emit('logout');
      envConfig.log('增强退出登录完成');
      
    } catch (error) {
      envConfig.error('退出登录失败:', error);
    }
  }
  
  /**
   * 清除认证信息
   */
  async clearAuth() {
    this.token = null;
    this.refreshToken = null;
    this.userInfo = null;
    this.tokenExpiry = null;
    
    try {
      wx.removeStorageSync('userToken');
      wx.removeStorageSync('refreshToken');
      wx.removeStorageSync('userInfo');
      wx.removeStorageSync('tokenExpiry');
    } catch (error) {
      envConfig.error('清除本地认证数据失败:', error);
    }
  }
  
  /**
   * 检查登录状态
   */
  isLoggedIn() {
    if (this.config.legacyMode) {
      return !!this.userInfo;
    } else {
      return !!(this.token && this.userInfo);
    }
  }
  
  /**
   * 获取认证头部
   */
  getAuthHeaders() {
    const headers = {};
    
    if (this.config.legacyMode) {
      // 兼容模式：使用user_id参数
      if (this.userInfo && this.userInfo.user_id) {
        headers['X-User-ID'] = this.userInfo.user_id;
      }
    } else {
      // JWT模式：使用Authorization头
      if (this.token) {
        headers['Authorization'] = `Bearer ${this.token}`;
      }
    }
    
    return headers;
  }
  
  /**
   * 事件监听
   */
  on(event, callback) {
    if (this.listeners[event]) {
      this.listeners[event].push(callback);
    }
  }
  
  /**
   * 移除事件监听
   */
  off(event, callback) {
    if (this.listeners[event]) {
      const index = this.listeners[event].indexOf(callback);
      if (index > -1) {
        this.listeners[event].splice(index, 1);
      }
    }
  }
  
  /**
   * 触发事件
   */
  emit(event, data) {
    if (this.listeners[event]) {
      this.listeners[event].forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          envConfig.error('事件回调执行失败:', error);
        }
      });
    }
    
    // 兼容旧版事件系统
    const app = getApp();
    if (event === 'login' && app && app.onUserLogin) {
      app.onUserLogin(data);
    } else if (event === 'logout' && app && app.onUserLogout) {
      app.onUserLogout();
    }
  }
  
  /**
   * 工具方法
   */
  isRetryableError(error) {
    const retryableStatuses = [408, 429, 500, 502, 503, 504];
    return retryableStatuses.includes(error.statusCode);
  }
  
  delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
  
  async showErrorMessage(error) {
    let message = '登录失败，请重试';
    
    if (error.statusCode === 401) {
      message = '登录已过期，请重新登录';
    } else if (error.statusCode >= 500) {
      message = '服务暂时不可用，请稍后重试';
    } else if (error.code === 'NETWORK_ERROR') {
      message = '网络连接失败，请检查网络';
    }
    
    wx.showToast({
      title: message,
      icon: 'none',
      duration: 3000
    });
  }
  
  /**
   * 获取调试信息
   */
  getDebugInfo() {
    return {
      hasToken: !!this.token,
      hasRefreshToken: !!this.refreshToken,
      hasUserInfo: !!this.userInfo,
      tokenExpiry: this.tokenExpiry,
      legacyMode: this.config.legacyMode,
      isRefreshing: this.isRefreshing,
      isLoggingIn: this.isLoggingIn
    };
  }
}

// 创建增强认证管理实例
const enhancedAuthManager = new EnhancedAuthManager();

module.exports = {
  enhancedAuthManager,
  
  // 导出常用方法（保持向后兼容）
  init: () => enhancedAuthManager.init(),
  login: () => enhancedAuthManager.login(),
  logout: () => enhancedAuthManager.logout(),
  isLoggedIn: () => enhancedAuthManager.isLoggedIn(),
  getCurrentUser: () => enhancedAuthManager.userInfo,
  getToken: () => enhancedAuthManager.token,
  ensureLogin: async () => {
    if (!enhancedAuthManager.isLoggedIn()) {
      await enhancedAuthManager.login();
    }
    return enhancedAuthManager.isLoggedIn();
  },
  getUserProfileByButton: () => enhancedAuthManager.getUserProfile(),
  getAuthHeaders: () => enhancedAuthManager.getAuthHeaders(),
  
  // 新增方法
  on: (event, callback) => enhancedAuthManager.on(event, callback),
  off: (event, callback) => enhancedAuthManager.off(event, callback),
  getDebugInfo: () => enhancedAuthManager.getDebugInfo()
};

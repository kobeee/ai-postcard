// utils/enhanced-request.js - 增强版网络请求工具
const envConfig = require('../config/env.js');

/**
 * 增强版网络请求管理器
 * 支持自动重试、断网恢复、请求缓存、批量请求等高级功能
 */
class EnhancedRequestManager {
  constructor() {
    this.baseURL = envConfig.baseURL;
    this.timeout = envConfig.timeout;
    this.interceptors = {
      request: [],
      response: []
    };
    
    // 增强配置
    this.config = {
      // 重试配置
      maxRetries: 3,
      retryDelay: 1000,
      retryableStatuses: [408, 429, 500, 502, 503, 504],
      
      // 缓存配置
      enableCache: true,
      cacheTimeout: 5 * 60 * 1000, // 5分钟
      
      // 网络状态监控
      networkMonitoring: true,
      
      // 请求队列
      enableQueue: true,
      maxConcurrent: 6,
      
      // 安全配置
      enableAuth: true,
      authRetry: true
    };
    
    // 运行时状态
    this.cache = new Map();
    this.requestQueue = [];
    this.activeRequests = new Set();
    this.networkStatus = 'online';
    this.pendingRequests = new Map();
    
    // 初始化
    this.init();
  }
  
  /**
   * 初始化增强功能
   */
  init() {
    // 监听网络状态变化
    if (this.config.networkMonitoring) {
      this.setupNetworkMonitoring();
    }
    
    // 设置默认拦截器
    this.setupDefaultInterceptors();
    
    // 启动请求队列处理
    if (this.config.enableQueue) {
      this.startQueueProcessor();
    }
    
    envConfig.log('增强请求管理器初始化完成');
  }
  
  /**
   * 设置网络状态监控
   */
  setupNetworkMonitoring() {
    // 监听网络状态变化
    wx.onNetworkStatusChange((res) => {
      const wasOffline = this.networkStatus === 'offline';
      this.networkStatus = res.isConnected ? 'online' : 'offline';
      
      envConfig.log('网络状态变化:', {
        from: wasOffline ? 'offline' : 'online',
        to: this.networkStatus,
        networkType: res.networkType
      });
      
      // 网络恢复时重试失败的请求
      if (wasOffline && this.networkStatus === 'online') {
        this.retryPendingRequests();
      }
    });
    
    // 获取初始网络状态
    wx.getNetworkType({
      success: (res) => {
        this.networkStatus = res.networkType === 'none' ? 'offline' : 'online';
      }
    });
  }
  
  /**
   * 设置默认拦截器
   */
  setupDefaultInterceptors() {
    // 请求拦截器
    this.addRequestInterceptor(async (config) => {
      // 检查网络状态
      if (this.networkStatus === 'offline' && !config.allowOffline) {
        throw new NetworkError('网络连接不可用');
      }
      
      // 处理请求方法和Content-Type
      const methodUpper = (config.method || 'GET').toUpperCase();
      const hasBody = ['POST', 'PUT', 'PATCH'].includes(methodUpper);
      
      config.header = { ...config.header };
      if (hasBody && !config.header['Content-Type']) {
        config.header['Content-Type'] = 'application/json';
      } else if (!hasBody) {
        delete config.header['Content-Type'];
      }
      
      // 移除无体方法的data
      if (!hasBody && 'data' in config) {
        delete config.data;
      }
      
      // 添加认证信息
      if (this.config.enableAuth) {
        const authHeaders = await this.getAuthHeaders();
        Object.assign(config.header, authHeaders);
      }
      
      // 添加请求ID和时间戳
      config.requestId = this.generateRequestId();
      config.timestamp = Date.now();
      
      // 添加trace信息
      config.header['X-Request-ID'] = config.requestId;
      config.header['X-Client-Version'] = envConfig.version || '1.0.0';
      
      envConfig.log('发送增强请求:', {
        id: config.requestId,
        url: config.url,
        method: config.method
      });
      
      return config;
    });
    
    // 响应拦截器
    this.addResponseInterceptor((response) => {
      const duration = Date.now() - (response.config?.timestamp || Date.now());
      
      envConfig.log('收到增强响应:', {
        id: response.config?.requestId,
        status: response.statusCode,
        duration: `${duration}ms`
      });
      
      // 处理响应
      if (response.statusCode === 200) {
        const { code, data, message } = response.data;
        
        if (code === 0) {
          // 成功响应，缓存结果
          if (this.config.enableCache && response.config?.enableCache !== false) {
            this.cacheResponse(response.config, data);
          }
          
          return Promise.resolve(data);
        } else {
          // 业务错误
          const error = new BusinessError(message || '业务处理失败');
          error.code = code;
          error.data = data;
          return Promise.reject(error);
        }
      } else if (response.statusCode === 401) {
        // 认证失败，尝试刷新token
        const error = new AuthError('认证失败');
        error.statusCode = response.statusCode;
        error.config = response.config;
        return Promise.reject(error);
      } else {
        // HTTP错误
        const error = new NetworkError(`网络错误: ${response.statusCode}`);
        error.statusCode = response.statusCode;
        error.config = response.config;
        return Promise.reject(error);
      }
    });
  }
  
  /**
   * 增强版请求方法
   */
  async request(options) {
    // 生成缓存键
    const cacheKey = this.generateCacheKey(options);
    
    // 检查缓存
    if (this.config.enableCache && options.method?.toUpperCase() === 'GET') {
      const cached = this.getCache(cacheKey);
      if (cached) {
        envConfig.log('使用缓存响应:', cacheKey);
        return cached;
      }
    }
    
    // 检查并发限制
    if (this.config.enableQueue && this.activeRequests.size >= this.config.maxConcurrent) {
      return await this.queueRequest(options);
    }
    
    return await this.executeRequest(options);
  }
  
  /**
   * 执行请求
   */
  async executeRequest(options, retryCount = 0) {
    let config = null;
    let requestId = null;
    
    try {
      // 构建请求配置
      config = await this.buildRequestConfig(options);
      requestId = config.requestId;
      
      // 添加到活跃请求集合
      this.activeRequests.add(requestId);
      
      // 执行请求拦截器
      config = await this.executeRequestInterceptors(config);
      
      // 发起请求
      const response = await new Promise((resolve, reject) => {
        wx.request({
          ...config,
          success: (res) => {
            res.config = config;
            resolve(res);
          },
          fail: reject
        });
      });
      
      // 执行响应拦截器
      const result = await this.executeResponseInterceptors(response);
      
      return result;
      
    } catch (error) {
      // 错误处理和重试逻辑
      return await this.handleRequestError(error, options, retryCount, config);
      
    } finally {
      // 清理
      if (requestId) {
        this.activeRequests.delete(requestId);
      }
    }
  }
  
  /**
   * 处理请求错误
   */
  async handleRequestError(error, options, retryCount, config) {
    const requestId = config?.requestId || 'unknown';
    
    envConfig.error(`请求失败 (${requestId}):`, error);
    
    // 认证错误处理
    if (error instanceof AuthError && this.config.authRetry) {
      const retried = await this.handleAuthError(error, options);
      if (retried) {
        return await this.executeRequest(options, retryCount);
      }
    }
    
    // 网络错误重试
    if (this.shouldRetry(error, retryCount)) {
      const delay = this.calculateRetryDelay(retryCount);
      
      envConfig.log(`${delay}ms后重试请求 (${retryCount + 1}/${this.config.maxRetries}):`, requestId);
      
      await this.delay(delay);
      return await this.executeRequest(options, retryCount + 1);
    }
    
    // 网络断开时加入待重试队列
    if (this.isNetworkError(error) && this.networkStatus === 'offline') {
      this.pendingRequests.set(requestId, { options, retryCount });
    }
    
    throw error;
  }
  
  /**
   * 处理认证错误
   */
  async handleAuthError(error, options) {
    try {
      // 尝试刷新认证信息
      const { enhancedAuthManager } = require('./enhanced-auth.js');
      
      if (enhancedAuthManager.refreshToken) {
        const refreshed = await enhancedAuthManager.refreshTokenIfNeeded();
        if (refreshed) {
          return true;
        }
      }
      
      // 无法刷新，清除认证状态
      await enhancedAuthManager.clearAuth();
      return false;
      
    } catch (refreshError) {
      envConfig.error('刷新认证信息失败:', refreshError);
      return false;
    }
  }
  
  /**
   * 构建请求配置
   */
  async buildRequestConfig(options) {
    const method = options.method || 'GET';
    const methodUpper = method.toUpperCase();
    const hasBody = ['POST', 'PUT', 'PATCH'].includes(methodUpper);
    
    let config = {
      url: options.url.startsWith('http') ? options.url : `${this.baseURL}${options.url}`,
      method,
      header: options.header || {},
      timeout: options.timeout || this.timeout
    };
    
    if (hasBody && typeof options.data !== 'undefined') {
      config.data = options.data;
    }
    
    return config;
  }
  
  /**
   * 队列请求处理
   */
  async queueRequest(options) {
    return new Promise((resolve, reject) => {
      this.requestQueue.push({
        options,
        resolve,
        reject
      });
    });
  }
  
  /**
   * 启动队列处理器
   */
  startQueueProcessor() {
    setInterval(() => {
      if (this.requestQueue.length > 0 && this.activeRequests.size < this.config.maxConcurrent) {
        const { options, resolve, reject } = this.requestQueue.shift();
        
        this.executeRequest(options)
          .then(resolve)
          .catch(reject);
      }
    }, 100);
  }
  
  /**
   * 重试待处理的请求
   */
  async retryPendingRequests() {
    if (this.pendingRequests.size === 0) return;
    
    envConfig.log(`网络恢复，重试${this.pendingRequests.size}个待处理请求`);
    
    const requests = Array.from(this.pendingRequests.entries());
    this.pendingRequests.clear();
    
    for (const [requestId, { options, retryCount }] of requests) {
      try {
        await this.executeRequest(options, retryCount);
      } catch (error) {
        envConfig.error(`重试请求失败 (${requestId}):`, error);
      }
    }
  }
  
  /**
   * 缓存管理
   */
  generateCacheKey(options) {
    const { url, method = 'GET', data } = options;
    const dataStr = data ? JSON.stringify(data) : '';
    return `${method}:${url}:${dataStr}`;
  }
  
  cacheResponse(config, data) {
    const cacheKey = this.generateCacheKey(config);
    const cacheEntry = {
      data,
      timestamp: Date.now(),
      expires: Date.now() + this.config.cacheTimeout
    };
    
    this.cache.set(cacheKey, cacheEntry);
    
    // 清理过期缓存
    this.cleanExpiredCache();
  }
  
  getCache(cacheKey) {
    const entry = this.cache.get(cacheKey);
    if (entry && entry.expires > Date.now()) {
      return entry.data;
    } else if (entry) {
      this.cache.delete(cacheKey);
    }
    return null;
  }
  
  cleanExpiredCache() {
    const now = Date.now();
    for (const [key, entry] of this.cache.entries()) {
      if (entry.expires <= now) {
        this.cache.delete(key);
      }
    }
  }
  
  /**
   * 获取认证头部
   */
  async getAuthHeaders() {
    try {
      const { enhancedAuthManager } = require('./enhanced-auth.js');
      return enhancedAuthManager.getAuthHeaders();
    } catch (error) {
      // 兼容模式：使用基础认证
      const token = wx.getStorageSync('userToken');
      return token ? { Authorization: `Bearer ${token}` } : {};
    }
  }
  
  /**
   * 工具方法
   */
  generateRequestId() {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
  }
  
  shouldRetry(error, retryCount) {
    if (retryCount >= this.config.maxRetries) return false;
    
    // 网络错误可重试
    if (this.isNetworkError(error)) return true;
    
    // 特定状态码可重试
    if (error.statusCode && this.config.retryableStatuses.includes(error.statusCode)) {
      return true;
    }
    
    return false;
  }
  
  isNetworkError(error) {
    return error instanceof NetworkError || 
           error.errMsg?.includes('request:fail') ||
           error.errMsg?.includes('timeout');
  }
  
  calculateRetryDelay(retryCount) {
    // 指数退避
    return this.config.retryDelay * Math.pow(2, retryCount);
  }
  
  delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
  
  // 拦截器管理（继承自基础实现）
  addRequestInterceptor(interceptor) {
    this.interceptors.request.push(interceptor);
  }
  
  addResponseInterceptor(interceptor) {
    this.interceptors.response.push(interceptor);
  }
  
  async executeRequestInterceptors(config) {
    let processedConfig = config;
    for (const interceptor of this.interceptors.request) {
      processedConfig = await interceptor(processedConfig);
    }
    return processedConfig;
  }
  
  async executeResponseInterceptors(response) {
    let processedResponse = response;
    for (const interceptor of this.interceptors.response) {
      try {
        processedResponse = await interceptor(processedResponse);
      } catch (error) {
        return Promise.reject(error);
      }
    }
    return processedResponse;
  }
  
  // 便捷方法
  get(url, params = {}, options = {}) {
    if (Object.keys(params).length > 0) {
      const queryString = Object.keys(params)
        .map(key => `${encodeURIComponent(key)}=${encodeURIComponent(params[key])}`)
        .join('&');
      url += (url.includes('?') ? '&' : '?') + queryString;
    }
    
    return this.request({
      url,
      method: 'GET',
      ...options
    });
  }
  
  post(url, data = {}, options = {}) {
    return this.request({
      url,
      method: 'POST',
      data,
      ...options
    });
  }
  
  put(url, data = {}, options = {}) {
    return this.request({
      url,
      method: 'PUT',
      data,
      ...options
    });
  }
  
  delete(url, options = {}) {
    return this.request({
      url,
      method: 'DELETE',
      ...options
    });
  }
  
  /**
   * 批量请求
   */
  async batch(requests, options = {}) {
    const { concurrent = true, failFast = false } = options;
    
    if (concurrent) {
      if (failFast) {
        return await Promise.all(requests.map(req => this.request(req)));
      } else {
        return await Promise.allSettled(requests.map(req => this.request(req)));
      }
    } else {
      const results = [];
      for (const request of requests) {
        try {
          const result = await this.request(request);
          results.push({ status: 'fulfilled', value: result });
        } catch (error) {
          if (failFast) throw error;
          results.push({ status: 'rejected', reason: error });
        }
      }
      return results;
    }
  }
  
  /**
   * 取消请求（简化实现）
   */
  cancel(requestId) {
    this.activeRequests.delete(requestId);
    this.pendingRequests.delete(requestId);
  }
  
  /**
   * 获取统计信息
   */
  getStats() {
    return {
      activeRequests: this.activeRequests.size,
      queuedRequests: this.requestQueue.length,
      pendingRequests: this.pendingRequests.size,
      cacheSize: this.cache.size,
      networkStatus: this.networkStatus
    };
  }
}

// 错误类定义
class NetworkError extends Error {
  constructor(message) {
    super(message);
    this.name = 'NetworkError';
  }
}

class BusinessError extends Error {
  constructor(message) {
    super(message);
    this.name = 'BusinessError';
  }
}

class AuthError extends Error {
  constructor(message) {
    super(message);
    this.name = 'AuthError';
  }
}

// 创建增强请求管理实例
const enhancedRequestManager = new EnhancedRequestManager();

module.exports = {
  request: enhancedRequestManager.request.bind(enhancedRequestManager),
  get: enhancedRequestManager.get.bind(enhancedRequestManager),
  post: enhancedRequestManager.post.bind(enhancedRequestManager),
  put: enhancedRequestManager.put.bind(enhancedRequestManager),
  delete: enhancedRequestManager.delete.bind(enhancedRequestManager),
  batch: enhancedRequestManager.batch.bind(enhancedRequestManager),
  
  // 导出实例和错误类
  enhancedRequestManager,
  NetworkError,
  BusinessError,
  AuthError,
  
  // 增强API封装
  postcardAPI: {
    create: (data) => enhancedRequestManager.post(envConfig.getApiUrl('/miniprogram/postcards/create'), data),
    getStatus: (taskId) => enhancedRequestManager.get(envConfig.getApiUrl(`/miniprogram/postcards/status/${taskId}`)),
    getResult: (taskId) => enhancedRequestManager.get(envConfig.getApiUrl(`/miniprogram/postcards/result/${taskId}`)),
    getUserPostcards: (userId, page = 1, limit = 10) => 
      enhancedRequestManager.get(envConfig.getApiUrl('/miniprogram/postcards/user'), { user_id: userId, page, limit }),
    delete: (postcardId) => enhancedRequestManager.delete(envConfig.getApiUrl(`/miniprogram/postcards/${postcardId}`)),
    getUserQuota: (userId) => enhancedRequestManager.get(envConfig.getApiUrl(`/miniprogram/users/${userId}/quota`))
  },
  
  authAPI: {
    login: (code, userInfo) => enhancedRequestManager.post(envConfig.getApiUrl('/miniprogram/auth/login'), { code, userInfo }),
    refresh: (refreshToken) => enhancedRequestManager.post(envConfig.getApiUrl('/miniprogram/auth/refresh'), { refreshToken }),
    getUserInfo: () => enhancedRequestManager.get(envConfig.getApiUrl('/miniprogram/auth/userinfo')),
    logout: () => enhancedRequestManager.post(envConfig.getApiUrl('/miniprogram/auth/logout'))
  },
  
  envAPI: {
    reverseGeocode: (latitude, longitude, language = 'zh') =>
      enhancedRequestManager.get(envConfig.getApiUrl('/miniprogram/location/reverse'), 
        { latitude, longitude, language }, { timeout: 55000 }),
    getWeather: (latitude, longitude) =>
      enhancedRequestManager.get(envConfig.getApiUrl('/miniprogram/environment/weather'), 
        { latitude, longitude }, { timeout: 50000 }),
    getTrending: (city, lang = 'zh') =>
      enhancedRequestManager.get(envConfig.getApiUrl('/miniprogram/trending'), 
        { city, lang }, { timeout: 50000 })
  }
};
// utils/request.js - 网络请求封装
const envConfig = require('../config/env.js');

/**
 * 网络请求封装
 */
class RequestManager {
  constructor() {
    this.baseURL = envConfig.baseURL;
    this.timeout = envConfig.timeout;
    this.interceptors = {
      request: [],
      response: []
    };
    
    // 默认请求拦截器
    this.addRequestInterceptor((config) => {
      // 添加通用headers
      config.header = {
        'Content-Type': 'application/json',
        ...config.header
      };
      
      // 添加用户token（如果存在）
      const token = wx.getStorageSync('userToken');
      if (token) {
        config.header.Authorization = `Bearer ${token}`;
      }
      
      envConfig.log('发送请求:', config);
      return config;
    });
    
    // 默认响应拦截器
    this.addResponseInterceptor((response) => {
      envConfig.log('收到响应:', response);
      
      // 统一响应格式处理
      if (response.statusCode === 200) {
        const { code, data, message } = response.data;
        
        if (code === 0) {
          return Promise.resolve(data);
        } else {
          // 业务错误
          const error = new Error(message || '业务处理失败');
          error.code = code;
          error.data = data;
          return Promise.reject(error);
        }
      } else {
        // HTTP错误
        const error = new Error(`网络错误: ${response.statusCode}`);
        error.statusCode = response.statusCode;
        return Promise.reject(error);
      }
    });
  }
  
  /**
   * 添加请求拦截器
   */
  addRequestInterceptor(interceptor) {
    this.interceptors.request.push(interceptor);
  }
  
  /**
   * 添加响应拦截器
   */
  addResponseInterceptor(interceptor) {
    this.interceptors.response.push(interceptor);
  }
  
  /**
   * 执行请求拦截器
   */
  async executeRequestInterceptors(config) {
    let processedConfig = config;
    for (const interceptor of this.interceptors.request) {
      processedConfig = await interceptor(processedConfig);
    }
    return processedConfig;
  }
  
  /**
   * 执行响应拦截器
   */
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
  
  /**
   * 发起请求
   */
  async request(options) {
    try {
      // 构建请求配置
      let config = {
        url: options.url.startsWith('http') ? options.url : `${this.baseURL}${options.url}`,
        method: options.method || 'GET',
        data: options.data || {},
        header: options.header || {},
        timeout: options.timeout || this.timeout
      };
      
      // 执行请求拦截器
      config = await this.executeRequestInterceptors(config);
      
      // 发起请求
      const response = await new Promise((resolve, reject) => {
        wx.request({
          ...config,
          success: resolve,
          fail: reject
        });
      });
      
      // 执行响应拦截器
      return await this.executeResponseInterceptors(response);
      
    } catch (error) {
      envConfig.error('请求失败:', error);
      throw error;
    }
  }
  
  /**
   * GET请求
   */
  get(url, params = {}, options = {}) {
    // 处理查询参数
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
  
  /**
   * POST请求
   */
  post(url, data = {}, options = {}) {
    return this.request({
      url,
      method: 'POST',
      data,
      ...options
    });
  }
  
  /**
   * PUT请求
   */
  put(url, data = {}, options = {}) {
    return this.request({
      url,
      method: 'PUT',
      data,
      ...options
    });
  }
  
  /**
   * DELETE请求
   */
  delete(url, options = {}) {
    return this.request({
      url,
      method: 'DELETE',
      ...options
    });
  }
}

// 创建请求实例
const requestManager = new RequestManager();

// 导出常用方法
module.exports = {
  request: requestManager.request.bind(requestManager),
  get: requestManager.get.bind(requestManager),
  post: requestManager.post.bind(requestManager),
  put: requestManager.put.bind(requestManager),
  delete: requestManager.delete.bind(requestManager),
  
  // 导出实例，允许外部添加拦截器
  requestManager,
  
  // 快捷方法 - AI明信片相关API
  postcardAPI: {
    // 创建明信片任务
    create: (data) => requestManager.post(envConfig.getApiUrl('/miniprogram/postcards/create'), data),
    
    // 查询任务状态
    getStatus: (taskId) => requestManager.get(envConfig.getApiUrl(`/miniprogram/postcards/status/${taskId}`)),
    
    // 获取最终结果
    getResult: (taskId) => requestManager.get(envConfig.getApiUrl(`/miniprogram/postcards/result/${taskId}`)),
    
    // 获取用户作品列表
    getUserPostcards: (userId, page = 1, limit = 10) => 
      requestManager.get(envConfig.getApiUrl('/miniprogram/postcards/user'), { user_id: userId, page, limit }),
    
    // 删除作品
    delete: (postcardId) => requestManager.delete(envConfig.getApiUrl(`/miniprogram/postcards/${postcardId}`))
  },
  
  // 用户认证相关API
  authAPI: {
    // 微信登录
    login: (code, userInfo) => requestManager.post(envConfig.getApiUrl('/miniprogram/auth/login'), { code, userInfo }),
    
    // 刷新token
    refresh: (refreshToken) => requestManager.post(envConfig.getApiUrl('/miniprogram/auth/refresh'), { refreshToken }),
    
    // 获取用户信息
    getUserInfo: () => requestManager.get(envConfig.getApiUrl('/miniprogram/auth/userinfo'))
  }
};
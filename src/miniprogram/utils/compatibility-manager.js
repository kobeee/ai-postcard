// utils/compatibility-manager.js - 兼容性管理器
const envConfig = require('../config/env.js');

/**
 * 兼容性管理器
 * 处理新旧版本API的适配和功能降级
 */
class CompatibilityManager {
  constructor() {
    this.serverCapabilities = null;
    this.clientFeatures = null;
    this.compatibilityMode = 'auto'; // auto, legacy, modern
    
    // 功能支持映射
    this.features = {
      jwt_auth: false,
      rbac_permissions: false,
      rate_limiting: false,
      audit_logging: false,
      concurrent_quota: false,
      security_monitoring: false
    };
    
    // API版本映射
    this.apiVersions = {
      auth: 'v1',
      postcards: 'v1',
      users: 'v1'
    };
    
    // 初始化
    this.init();
  }
  
  /**
   * 初始化兼容性检查
   */
  async init() {
    try {
      // 检测客户端特性
      this.detectClientFeatures();
      
      // 检测服务器能力
      await this.detectServerCapabilities();
      
      // 确定兼容性模式
      this.determineCompatibilityMode();
      
      envConfig.log('兼容性管理器初始化完成', {
        mode: this.compatibilityMode,
        features: this.features,
        apiVersions: this.apiVersions
      });
      
    } catch (error) {
      envConfig.error('兼容性检查失败，使用默认配置:', error);
      this.setLegacyMode();
    }
  }
  
  /**
   * 检测客户端特性
   */
  detectClientFeatures() {
    const systemInfo = wx.getSystemInfoSync();
    
    this.clientFeatures = {
      wechatVersion: systemInfo.version,
      sdkVersion: systemInfo.SDKVersion,
      platform: systemInfo.platform,
      
      // 支持的微信API特性
      supportGetUserProfile: typeof wx.getUserProfile === 'function',
      supportOnUnhandledRejection: typeof wx.onUnhandledRejection === 'function',
      supportRequestPayment: typeof wx.requestPayment === 'function',
      
      // 版本特性检查
      isNewVersionWechat: this.compareVersion(systemInfo.version, '7.0.0') >= 0,
      isNewSDK: this.compareVersion(systemInfo.SDKVersion, '2.10.0') >= 0
    };
    
    envConfig.log('客户端特性检测完成:', this.clientFeatures);
  }
  
  /**
   * 检测服务器能力
   */
  async detectServerCapabilities() {
    try {
      // 尝试获取服务器配置
      const response = await this.makeCompatibilityRequest('/api/v1/system/capabilities');
      
      if (response) {
        this.serverCapabilities = response;
        this.updateFeatureSupport(response);
      } else {
        throw new Error('无法获取服务器能力');
      }
      
    } catch (error) {
      envConfig.log('服务器能力检测失败，尝试探测API:', error);
      await this.probeApiCapabilities();
    }
  }
  
  /**
   * 探测API能力
   */
  async probeApiCapabilities() {
    try {
      // 探测认证API
      await this.probeAuthApi();
      
      // 探测用户API
      await this.probeUserApi();
      
      // 探测明信片API
      await this.probePostcardApi();
      
    } catch (error) {
      envConfig.error('API能力探测失败:', error);
    }
  }
  
  /**
   * 探测认证API
   */
  async probeAuthApi() {
    try {
      // 尝试获取认证配置
      const response = await this.makeCompatibilityRequest('/api/v1/auth/config');
      if (response) {
        this.features.jwt_auth = response.jwt_enabled || false;
        this.features.rbac_permissions = response.rbac_enabled || false;
      }
    } catch (error) {
      // 检查401错误（说明有认证机制）
      if (error.statusCode === 401) {
        this.features.jwt_auth = true;
      }
    }
  }
  
  /**
   * 探测用户API
   */
  async probeUserApi() {
    try {
      // 尝试访问用户信息端点
      const response = await this.makeCompatibilityRequest('/api/v1/miniprogram/auth/userinfo');
      // 如果返回401，说明需要认证但API存在
    } catch (error) {
      if (error.statusCode === 401) {
        // API存在，需要认证
        this.apiVersions.auth = 'v1';
      } else if (error.statusCode === 404) {
        // 可能是旧版API
        this.apiVersions.auth = 'legacy';
      }
    }
  }
  
  /**
   * 探测明信片API
   */
  async probePostcardApi() {
    try {
      // 检查明信片API版本
      const response = await this.makeCompatibilityRequest('/api/v1/miniprogram/postcards/capabilities');
      if (response) {
        this.features.concurrent_quota = response.concurrent_quota || false;
        this.features.rate_limiting = response.rate_limiting || false;
      }
    } catch (error) {
      // 根据错误类型判断API版本
      if (error.statusCode === 404) {
        this.apiVersions.postcards = 'legacy';
      }
    }
  }
  
  /**
   * 发起兼容性检查请求
   */
  async makeCompatibilityRequest(url, options = {}) {
    return new Promise((resolve, reject) => {
      wx.request({
        url: envConfig.baseURL + url,
        method: options.method || 'GET',
        timeout: options.timeout || 5000,
        header: {
          'Content-Type': 'application/json',
          'X-Skip-Auth': 'true', // 跳过认证
          ...options.header
        },
        success: (res) => {
          if (res.statusCode === 200) {
            resolve(res.data.data || res.data);
          } else {
            const error = new Error(`HTTP ${res.statusCode}`);
            error.statusCode = res.statusCode;
            reject(error);
          }
        },
        fail: reject
      });
    });
  }
  
  /**
   * 更新功能支持状态
   */
  updateFeatureSupport(capabilities) {
    this.features = {
      jwt_auth: capabilities.jwt_auth || false,
      rbac_permissions: capabilities.rbac_permissions || false,
      rate_limiting: capabilities.rate_limiting || false,
      audit_logging: capabilities.audit_logging || false,
      concurrent_quota: capabilities.concurrent_quota || false,
      security_monitoring: capabilities.security_monitoring || false
    };
    
    // 更新API版本
    if (capabilities.api_versions) {
      this.apiVersions = { ...this.apiVersions, ...capabilities.api_versions };
    }
  }
  
  /**
   * 确定兼容性模式
   */
  determineCompatibilityMode() {
    if (this.compatibilityMode === 'legacy') {
      return;
    }
    
    const hasModernFeatures = Object.values(this.features).some(supported => supported);
    const hasModernClient = this.clientFeatures?.isNewVersionWechat && this.clientFeatures?.isNewSDK;
    
    if (hasModernFeatures && hasModernClient) {
      this.compatibilityMode = 'modern';
    } else {
      this.compatibilityMode = 'legacy';
    }
    
    envConfig.log(`兼容性模式: ${this.compatibilityMode}`);
  }
  
  /**
   * 设置为遗留模式
   */
  setLegacyMode() {
    this.compatibilityMode = 'legacy';
    this.features = Object.fromEntries(
      Object.keys(this.features).map(key => [key, false])
    );
    this.apiVersions = {
      auth: 'legacy',
      postcards: 'legacy',
      users: 'legacy'
    };
  }
  
  /**
   * 获取API端点URL
   */
  getApiUrl(endpoint, options = {}) {
    const { version, service } = options;
    
    // 如果指定了版本，直接使用
    if (version) {
      return `/api/${version}${endpoint}`;
    }
    
    // 根据服务类型确定版本
    let apiVersion = 'v1';
    if (service && this.apiVersions[service]) {
      apiVersion = this.apiVersions[service];
    }
    
    // 遗留API处理
    if (apiVersion === 'legacy') {
      return this.getLegacyApiUrl(endpoint);
    }
    
    return `/api/${apiVersion}${endpoint}`;
  }
  
  /**
   * 获取遗留API URL
   */
  getLegacyApiUrl(endpoint) {
    // 兼容旧版本的URL映射
    const legacyMappings = {
      '/miniprogram/auth/login': '/login',
      '/miniprogram/auth/userinfo': '/user/info',
      '/miniprogram/postcards/create': '/postcards/create',
      '/miniprogram/postcards/status': '/postcards/status',
      '/miniprogram/postcards/user': '/user/postcards'
    };
    
    return legacyMappings[endpoint] || endpoint;
  }
  
  /**
   * 获取请求配置
   */
  getRequestConfig(endpoint, options = {}) {
    const config = {
      url: this.getApiUrl(endpoint, options),
      ...options
    };
    
    // 根据兼容性模式调整配置
    if (this.compatibilityMode === 'legacy') {
      // 遗留模式：使用简单认证
      config.simpleFallback = true;
    } else {
      // 现代模式：支持完整功能
      config.enableRetry = true;
      config.enableCache = options.cache !== false;
    }
    
    return config;
  }
  
  /**
   * 获取认证配置
   */
  getAuthConfig() {
    return {
      mode: this.compatibilityMode,
      jwtEnabled: this.features.jwt_auth,
      rbacEnabled: this.features.rbac_permissions,
      autoRefresh: this.features.jwt_auth,
      legacyAuth: this.compatibilityMode === 'legacy'
    };
  }
  
  /**
   * 检查功能支持
   */
  isFeatureSupported(feature) {
    return this.features[feature] || false;
  }
  
  /**
   * 获取功能降级配置
   */
  getFallbackConfig(feature) {
    const fallbacks = {
      jwt_auth: {
        enabled: false,
        alternative: 'user_id_auth',
        message: '使用兼容认证模式'
      },
      rbac_permissions: {
        enabled: false,
        alternative: 'basic_auth',
        message: '使用基础权限检查'
      },
      rate_limiting: {
        enabled: false,
        alternative: 'client_throttle',
        message: '使用客户端限流'
      },
      concurrent_quota: {
        enabled: false,
        alternative: 'simple_quota',
        message: '使用简单配额检查'
      }
    };
    
    return fallbacks[feature] || { enabled: false };
  }
  
  /**
   * 适配API响应
   */
  adaptApiResponse(response, endpoint) {
    // 针对不同端点的响应适配
    if (endpoint.includes('/auth/login')) {
      return this.adaptLoginResponse(response);
    } else if (endpoint.includes('/postcards/')) {
      return this.adaptPostcardResponse(response);
    }
    
    return response;
  }
  
  /**
   * 适配登录响应
   */
  adaptLoginResponse(response) {
    if (this.compatibilityMode === 'legacy') {
      // 遗留模式：可能只返回用户信息
      return {
        token: null,
        refreshToken: null,
        userInfo: response.userInfo || response,
        expiresIn: null
      };
    }
    
    return response;
  }
  
  /**
   * 适配明信片响应
   */
  adaptPostcardResponse(response) {
    // 确保响应包含必要字段
    if (response && typeof response === 'object') {
      // 添加默认字段
      if (!response.hasOwnProperty('can_generate')) {
        response.can_generate = true;
      }
      if (!response.hasOwnProperty('remaining_quota')) {
        response.remaining_quota = 2;
      }
    }
    
    return response;
  }
  
  /**
   * 获取错误适配配置
   */
  getErrorAdaptation() {
    return {
      adaptLegacyErrors: this.compatibilityMode === 'legacy',
      showCompatibilityWarnings: envConfig.debug,
      fallbackToToast: true
    };
  }
  
  /**
   * 版本比较工具
   */
  compareVersion(v1, v2) {
    const version1 = v1.split('.');
    const version2 = v2.split('.');
    const maxLen = Math.max(version1.length, version2.length);
    
    for (let i = 0; i < maxLen; i++) {
      const num1 = parseInt(version1[i] || 0);
      const num2 = parseInt(version2[i] || 0);
      
      if (num1 > num2) return 1;
      if (num1 < num2) return -1;
    }
    
    return 0;
  }
  
  /**
   * 获取调试信息
   */
  getDebugInfo() {
    return {
      compatibilityMode: this.compatibilityMode,
      features: this.features,
      apiVersions: this.apiVersions,
      clientFeatures: this.clientFeatures,
      serverCapabilities: this.serverCapabilities
    };
  }
  
  /**
   * 重新检测能力
   */
  async recheckCapabilities() {
    await this.detectServerCapabilities();
    this.determineCompatibilityMode();
    
    envConfig.log('重新检测兼容性完成:', {
      mode: this.compatibilityMode,
      features: this.features
    });
  }
}

// 创建全局兼容性管理器实例
const compatibilityManager = new CompatibilityManager();

module.exports = {
  compatibilityManager,
  
  // 导出便捷方法
  init: () => compatibilityManager.init(),
  getApiUrl: (endpoint, options) => compatibilityManager.getApiUrl(endpoint, options),
  getRequestConfig: (endpoint, options) => compatibilityManager.getRequestConfig(endpoint, options),
  getAuthConfig: () => compatibilityManager.getAuthConfig(),
  isFeatureSupported: (feature) => compatibilityManager.isFeatureSupported(feature),
  getFallbackConfig: (feature) => compatibilityManager.getFallbackConfig(feature),
  adaptApiResponse: (response, endpoint) => compatibilityManager.adaptApiResponse(response, endpoint),
  getErrorAdaptation: () => compatibilityManager.getErrorAdaptation(),
  
  // 常量
  COMPATIBILITY_MODES: {
    AUTO: 'auto',
    LEGACY: 'legacy', 
    MODERN: 'modern'
  },
  
  FEATURES: {
    JWT_AUTH: 'jwt_auth',
    RBAC_PERMISSIONS: 'rbac_permissions',
    RATE_LIMITING: 'rate_limiting',
    AUDIT_LOGGING: 'audit_logging',
    CONCURRENT_QUOTA: 'concurrent_quota',
    SECURITY_MONITORING: 'security_monitoring'
  }
};
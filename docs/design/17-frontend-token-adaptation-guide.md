# 前端Token适配实施指南

## 概述

本文档提供小程序前端JWT Token机制的具体实施指南，确保与安全升级后端无缝对接，并保持向后兼容性。

## 当前Token机制评估

### ✅ 已具备的基础设施

**Token存储机制** (`utils/request.js:36-40`):
```javascript
// 添加用户token（如果存在）
const token = wx.getStorageSync('userToken');
if (token) {
  config.header.Authorization = `Bearer ${token}`;
}
```

**认证状态管理** (`utils/auth.js`):
- ✅ Token获取和存储
- ✅ 刷新Token机制  
- ✅ 登录状态检查
- ✅ 用户信息管理

### ⚠️ 需要增强的部分

1. **Token过期处理** - 需要自动刷新机制
2. **会话管理** - 缺少sessionId处理
3. **错误处理** - 401/403响应处理不完整
4. **并发请求** - Token刷新时的请求队列管理

## Token适配实施方案

### 1. 增强认证管理器

**文件**: `src/miniprogram/utils/auth.js`

```javascript
// 增强版认证管理器
class AuthManager {
  constructor() {
    this.userInfo = null;
    this.token = null;
    this.refreshToken = null;
    this.sessionId = null;
    this.tokenExpiryTime = null;
    this.isLoggingIn = false;
    this.isRefreshing = false;
    this.refreshPromise = null;
    this.pendingRequests = []; // 等待Token刷新的请求队列
  }

  // 🔥 增强登录成功处理 - 支持JWT完整信息
  async handleLoginSuccess(authResult) {
    const { 
      token, 
      userInfo, 
      refreshToken, 
      sessionId,
      expiresIn = 3600, // 默认1小时过期
      jti // JWT Token ID
    } = authResult;
    
    this.token = token;
    this.userInfo = userInfo;
    this.refreshToken = refreshToken;
    this.sessionId = sessionId;
    this.tokenExpiryTime = Date.now() + (expiresIn * 1000);
    
    // 存储到本地
    wx.setStorageSync('userToken', token);
    wx.setStorageSync('userInfo', userInfo);
    wx.setStorageSync('refreshToken', refreshToken);
    wx.setStorageSync('sessionId', sessionId);
    wx.setStorageSync('tokenExpiryTime', this.tokenExpiryTime);
    wx.setStorageSync('jti', jti);
    
    envConfig.log('登录成功，Token信息已保存:', {
      sessionId,
      expiresIn,
      expiryTime: new Date(this.tokenExpiryTime).toISOString()
    });
  }

  // 🔥 检查Token是否即将过期
  isTokenNearExpiry() {
    if (!this.tokenExpiryTime) {
      const storedExpiry = wx.getStorageSync('tokenExpiryTime');
      if (storedExpiry) {
        this.tokenExpiryTime = storedExpiry;
      } else {
        return true; // 无过期时间信息，认为需要刷新
      }
    }
    
    const fiveMinutes = 5 * 60 * 1000;
    return (this.tokenExpiryTime - Date.now()) < fiveMinutes;
  }

  // 🔥 主动刷新Token
  async proactiveRefresh() {
    if (this.isTokenNearExpiry()) {
      envConfig.log('Token即将过期，主动刷新');
      return await this.refreshToken();
    }
    return true;
  }

  // 🔥 增强Token刷新 - 支持请求队列
  async refreshToken() {
    // 防止并发刷新
    if (this.isRefreshing) {
      envConfig.log('Token正在刷新中，等待完成');
      return this.refreshPromise;
    }

    this.isRefreshing = true;
    this.refreshPromise = this._doRefreshToken();
    
    try {
      const result = await this.refreshPromise;
      this._processPendingRequests(true);
      return result;
    } catch (error) {
      this._processPendingRequests(false);
      throw error;
    } finally {
      this.isRefreshing = false;
      this.refreshPromise = null;
    }
  }

  // 实际执行Token刷新
  async _doRefreshToken() {
    try {
      const refreshToken = this.refreshToken || wx.getStorageSync('refreshToken');
      if (!refreshToken) {
        throw new Error('无刷新Token');
      }

      const result = await authAPI.refresh(refreshToken);
      await this.handleLoginSuccess(result);
      
      envConfig.log('Token刷新成功');
      return true;
    } catch (error) {
      envConfig.error('Token刷新失败:', error);
      await this.clearAuth();
      throw error;
    }
  }

  // 处理等待中的请求
  _processPendingRequests(success) {
    const requests = [...this.pendingRequests];
    this.pendingRequests = [];
    
    requests.forEach(({ resolve, reject, config }) => {
      if (success) {
        // Token刷新成功，重新发送请求
        resolve(config);
      } else {
        // Token刷新失败，拒绝请求
        reject(new Error('Token refresh failed'));
      }
    });
  }

  // 添加请求到等待队列
  addPendingRequest(config) {
    return new Promise((resolve, reject) => {
      this.pendingRequests.push({ resolve, reject, config });
    });
  }
}
```

### 2. 增强请求管理器

**文件**: `src/miniprogram/utils/request.js`

```javascript
class RequestManager {
  constructor() {
    this.baseURL = envConfig.baseURL;
    this.timeout = envConfig.timeout;
    this.interceptors = {
      request: [],
      response: []
    };
    
    // 设置请求拦截器
    this.setupRequestInterceptors();
    // 设置响应拦截器
    this.setupResponseInterceptors();
  }

  setupRequestInterceptors() {
    this.addRequestInterceptor(async (config) => {
      const methodUpper = (config.method || 'GET').toUpperCase();
      const hasBody = ['POST', 'PUT', 'PATCH'].includes(methodUpper);
      
      // 设置Content-Type
      config.header = { ...config.header };
      if (hasBody && !config.header['Content-Type']) {
        config.header['Content-Type'] = 'application/json';
      }
      
      // 🔥 增强Token处理
      await this.addAuthHeaders(config);
      
      envConfig.log('发送请求:', config);
      return config;
    });
  }

  setupResponseInterceptors() {
    this.addResponseInterceptor(async (response) => {
      // 🔥 增强响应处理
      return await this.handleResponse(response);
    });
  }

  // 🔥 智能Token处理
  async addAuthHeaders(config) {
    const authManager = require('./auth.js').authManager;
    
    // 检查是否需要主动刷新Token
    if (authManager.isLoggedIn()) {
      await authManager.proactiveRefresh();
      
      const token = wx.getStorageSync('userToken');
      if (token) {
        config.header.Authorization = `Bearer ${token}`;
      }
      
      // 添加会话ID
      const sessionId = wx.getStorageSync('sessionId');
      if (sessionId) {
        config.header['X-Session-ID'] = sessionId;
      }
    }
    
    // 兼容性：如果没有Token但有用户信息，添加user_id头
    if (!config.header.Authorization) {
      const userInfo = wx.getStorageSync('userInfo');
      if (userInfo && userInfo.id) {
        config.header['X-User-ID'] = userInfo.id;
        envConfig.log('使用兼容模式，添加X-User-ID:', userInfo.id);
      }
    }
  }

  // 🔥 智能响应处理
  async handleResponse(response) {
    const status = response.statusCode;
    
    // 处理认证相关错误
    if (status === 401) {
      return await this.handle401Response(response);
    }
    
    if (status === 403) {
      return this.handle403Response(response);
    }
    
    if (status === 429) {
      return this.handle429Response(response);
    }
    
    // 处理正常响应
    if (status === 200) {
      const { code, data, message } = response.data;
      
      if (code === 0) {
        return Promise.resolve(data);
      } else {
        const error = new Error(message || '业务处理失败');
        error.code = code;
        error.data = data;
        return Promise.reject(error);
      }
    } else {
      const error = new Error(`网络错误: ${status}`);
      error.statusCode = status;
      return Promise.reject(error);
    }
  }

  // 🔥 处理401未授权响应
  async handle401Response(response) {
    const authManager = require('./auth.js').authManager;
    
    envConfig.log('收到401响应，尝试刷新Token');
    
    try {
      // 尝试刷新Token
      await authManager.refreshToken();
      
      // 重新发送原始请求
      const newToken = wx.getStorageSync('userToken');
      response.config.header.Authorization = `Bearer ${newToken}`;
      
      envConfig.log('Token刷新成功，重新发送请求');
      return await this.request(response.config);
      
    } catch (error) {
      envConfig.error('Token刷新失败，跳转登录页面');
      
      // 刷新失败，清除认证信息
      await authManager.clearAuth();
      
      // 显示登录提示
      wx.showModal({
        title: '登录状态已过期',
        content: '请重新登录以继续使用',
        showCancel: false,
        success: () => {
          wx.reLaunch({ url: '/pages/index/index' });
        }
      });
      
      throw new Error('Authentication failed');
    }
  }

  // 🔥 处理403权限不足响应
  handle403Response(response) {
    const { data } = response;
    const message = (data && data.message) || '您没有权限执行此操作';
    
    wx.showModal({
      title: '权限不足',
      content: message,
      showCancel: false
    });
    
    const error = new Error(message);
    error.statusCode = 403;
    return Promise.reject(error);
  }

  // 🔥 处理429限流响应
  handle429Response(response) {
    const { data } = response;
    const message = (data && data.message) || '请求过于频繁，请稍后重试';
    
    wx.showToast({
      title: message,
      icon: 'none',
      duration: 3000
    });
    
    const error = new Error(message);
    error.statusCode = 429;
    return Promise.reject(error);
  }
}
```

### 3. 增强API接口适配

**文件**: `src/miniprogram/utils/request.js` (API接口部分)

```javascript
// 增强认证相关API
authAPI: {
  // 🔥 增强微信登录 - 支持完整JWT响应
  login: async (code, userInfo) => {
    const response = await requestManager.post(
      envConfig.getApiUrl('/miniprogram/auth/login'), 
      { code, userInfo }
    );
    
    // 验证响应格式
    if (!response.token || !response.refreshToken) {
      throw new Error('登录响应格式异常');
    }
    
    return response;
  },
  
  // 🔥 增强Token刷新 - 支持会话管理
  refresh: async (refreshToken) => {
    const sessionId = wx.getStorageSync('sessionId');
    
    return await requestManager.post(
      envConfig.getApiUrl('/miniprogram/auth/refresh'), 
      { refreshToken, sessionId }
    );
  },
  
  // 🔥 获取用户信息 - 用于Token验证
  getUserInfo: () => {
    return requestManager.get(envConfig.getApiUrl('/miniprogram/auth/userinfo'));
  },
  
  // 🔥 新增：登出 - 撤销Token
  logout: async () => {
    const sessionId = wx.getStorageSync('sessionId');
    
    try {
      await requestManager.post(
        envConfig.getApiUrl('/miniprogram/auth/logout'),
        { sessionId }
      );
    } catch (error) {
      envConfig.warn('登出API调用失败，继续本地清理:', error);
    }
    
    // 无论API调用是否成功，都清理本地状态
    const authManager = require('./auth.js').authManager;
    await authManager.clearAuth();
  }
}
```

### 4. 应用级错误处理

**文件**: `src/miniprogram/app.js`

```javascript
App({
  // 🔥 增强全局错误处理
  onError(msg) {
    envConfig.error('小程序发生错误:', msg);
    
    // 处理认证相关错误
    if (this.isAuthError(msg)) {
      this.handleAuthError(msg);
    }
    
    // 上报错误到监控系统
    this.reportError(msg);
  },

  // 检查是否为认证相关错误
  isAuthError(msg) {
    const authKeywords = ['401', '403', 'Unauthorized', 'Forbidden', 'token', 'Token'];
    return authKeywords.some(keyword => msg.includes(keyword));
  },

  // 处理认证错误
  async handleAuthError(msg) {
    envConfig.warn('检测到认证错误，清理用户状态:', msg);
    
    const authUtil = require('./utils/auth.js');
    await authUtil.logout();
    
    // 跳转到登录页面
    wx.reLaunch({
      url: '/pages/index/index',
      fail: (error) => {
        envConfig.error('跳转登录页面失败:', error);
      }
    });
  },

  // 🔥 新增：网络状态监听
  onShow() {
    // 监听网络状态变化
    wx.onNetworkStatusChange((res) => {
      if (res.isConnected) {
        envConfig.log('网络已连接，检查登录状态');
        this.checkAuthStatus();
      }
    });
  },

  // 🔥 检查认证状态
  async checkAuthStatus() {
    const authUtil = require('./utils/auth.js');
    
    if (authUtil.isLoggedIn()) {
      try {
        // 验证Token有效性
        await authUtil.validateToken();
        envConfig.log('Token验证成功');
      } catch (error) {
        envConfig.warn('Token验证失败，重新登录:', error);
        await authUtil.clearAuth();
      }
    }
  }
});
```

### 5. 页面级适配示例

**文件**: `src/miniprogram/pages/index/index.js`

```javascript
Page({
  // 🔥 增强用户登录处理
  async handleLogin(e) {
    try {
      wx.showLoading({ title: '登录中...', mask: true });

      // 获取用户信息授权
      const userProfile = await new Promise((resolve, reject) => {
        wx.getUserProfile({
          desc: '用于完善用户体验',
          success: resolve,
          fail: reject
        });
      });

      // 获取微信登录code
      const loginResult = await new Promise((resolve, reject) => {
        wx.login({ success: resolve, fail: reject });
      });

      // 🔥 调用增强的登录API
      const authResult = await authAPI.login(loginResult.code, userProfile.userInfo);
      
      // 🔥 使用增强的认证管理器处理登录结果
      const authManager = require('../../utils/auth.js').authManager;
      await authManager.handleLoginSuccess(authResult);

      // 更新页面状态
      const enhancedUserInfo = this.processUserInfo(authResult.userInfo);
      this.setData({
        userInfo: enhancedUserInfo,
        hasUserInfo: true
      });

      wx.hideLoading();
      wx.showToast({
        title: '登录成功',
        icon: 'success',
        duration: 1500
      });
      
      // 继续初始化流程
      this.checkUserStatus();
      
    } catch (error) {
      wx.hideLoading();
      this.handleLoginError(error);
    }
  },

  // 🔥 增强登录错误处理
  handleLoginError(error) {
    let errorMessage = '登录失败，请重试';
    
    if (error.message) {
      if (error.message.includes('auth deny')) {
        errorMessage = '需要授权才能使用完整功能';
      } else if (error.message.includes('network')) {
        errorMessage = '网络连接异常，请检查网络';
      } else {
        errorMessage = error.message;
      }
    }
    
    wx.showModal({
      title: '登录失败',
      content: errorMessage,
      showCancel: false
    });
    
    envConfig.error('登录失败:', error);
  }
});
```

## Token存储安全增强

### 1. 安全存储机制

```javascript
// 安全的Token存储工具
class SecureStorage {
  // 🔥 加密存储敏感信息
  static setSecure(key, value) {
    try {
      // 简单的Base64编码（实际项目中应该使用更强的加密）
      const encoded = wx.arrayBufferToBase64(
        new TextEncoder().encode(JSON.stringify(value))
      );
      wx.setStorageSync(`secure_${key}`, encoded);
      return true;
    } catch (error) {
      envConfig.error('安全存储失败:', error);
      return false;
    }
  }

  // 🔥 解密读取敏感信息
  static getSecure(key) {
    try {
      const encoded = wx.getStorageSync(`secure_${key}`);
      if (!encoded) return null;
      
      const decoded = new TextDecoder().decode(
        wx.base64ToArrayBuffer(encoded)
      );
      return JSON.parse(decoded);
    } catch (error) {
      envConfig.error('安全读取失败:', error);
      return null;
    }
  }

  // 🔥 清理敏感信息
  static removeSecure(key) {
    try {
      wx.removeStorageSync(`secure_${key}`);
      return true;
    } catch (error) {
      envConfig.error('清理失败:', error);
      return false;
    }
  }
}

// 在认证管理器中使用安全存储
class AuthManager {
  async handleLoginSuccess(authResult) {
    const { token, refreshToken, sessionId } = authResult;
    
    // 🔥 使用安全存储保存敏感信息
    SecureStorage.setSecure('authTokens', {
      token,
      refreshToken,
      sessionId,
      timestamp: Date.now()
    });
    
    // 非敏感信息仍然使用普通存储
    wx.setStorageSync('userInfo', authResult.userInfo);
  }

  getToken() {
    const authData = SecureStorage.getSecure('authTokens');
    return authData ? authData.token : null;
  }
}
```

## 性能优化建议

### 1. Token缓存策略

```javascript
class TokenCache {
  constructor() {
    this.cache = new Map();
    this.maxAge = 5 * 60 * 1000; // 5分钟缓存
  }

  // 🔥 缓存Token验证结果
  cacheValidation(token, isValid) {
    this.cache.set(token, {
      isValid,
      timestamp: Date.now()
    });
  }

  // 🔥 检查缓存的验证结果
  getCachedValidation(token) {
    const cached = this.cache.get(token);
    if (!cached) return null;
    
    if (Date.now() - cached.timestamp > this.maxAge) {
      this.cache.delete(token);
      return null;
    }
    
    return cached.isValid;
  }
}
```

### 2. 请求队列优化

```javascript
class RequestQueue {
  constructor() {
    this.queue = [];
    this.processing = false;
  }

  // 🔥 智能请求队列管理
  async enqueue(requestConfig) {
    return new Promise((resolve, reject) => {
      this.queue.push({ requestConfig, resolve, reject });
      this.process();
    });
  }

  async process() {
    if (this.processing || this.queue.length === 0) return;
    
    this.processing = true;
    
    while (this.queue.length > 0) {
      const { requestConfig, resolve, reject } = this.queue.shift();
      
      try {
        const result = await this.executeRequest(requestConfig);
        resolve(result);
      } catch (error) {
        reject(error);
      }
    }
    
    this.processing = false;
  }
}
```

## 测试验证清单

### 1. Token机制测试

- [ ] 登录获取Token
- [ ] Token自动添加到请求头
- [ ] Token过期自动刷新
- [ ] 刷新失败自动登出
- [ ] 并发请求Token处理
- [ ] 401响应自动重试
- [ ] 403权限错误提示
- [ ] 登出Token撤销

### 2. 兼容性测试

- [ ] 新Token机制与旧API兼容
- [ ] 向后兼容user_id传递
- [ ] 错误处理优雅降级
- [ ] 网络异常恢复
- [ ] 存储异常处理

### 3. 安全性测试

- [ ] Token安全存储
- [ ] 敏感信息加密
- [ ] 登出完全清理
- [ ] 会话过期处理
- [ ] 重放攻击防护

## 部署指南

### 1. 分阶段部署

**Phase 1: 基础Token支持**
```javascript
// 启用基础Token机制
const CONFIG = {
  JWT_ENABLED: true,
  AUTO_REFRESH: true,
  SECURE_STORAGE: false, // 初期关闭
  COMPATIBILITY_MODE: true
};
```

**Phase 2: 增强安全特性**
```javascript
// 启用完整安全特性
const CONFIG = {
  JWT_ENABLED: true,
  AUTO_REFRESH: true,
  SECURE_STORAGE: true,
  COMPATIBILITY_MODE: true,
  TOKEN_VALIDATION: true
};
```

**Phase 3: 严格模式**
```javascript
// 启用严格安全模式
const CONFIG = {
  JWT_ENABLED: true,
  AUTO_REFRESH: true,
  SECURE_STORAGE: true,
  COMPATIBILITY_MODE: false, // 关闭兼容模式
  TOKEN_VALIDATION: true,
  STRICT_MODE: true
};
```

### 2. 监控指标

- Token刷新成功率
- 登录失败率
- API请求成功率
- 用户会话时长
- 错误率趋势

## 总结

通过以上Token适配方案，小程序前端将获得：

1. **完整JWT支持** - 标准化的Token认证机制
2. **智能Token管理** - 自动刷新、过期处理、并发控制
3. **增强安全性** - 安全存储、会话管理、权限控制
4. **向后兼容** - 平滑迁移、优雅降级
5. **用户体验** - 无感知升级、错误友好提示
6. **开发友好** - 简单配置、详细日志、易于调试

该方案确保安全升级对用户完全透明，同时为系统带来enterprise级别的安全保障。
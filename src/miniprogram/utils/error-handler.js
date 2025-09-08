// utils/error-handler.js - 错误处理和用户反馈工具
const envConfig = require('../config/env.js');

/**
 * 统一错误处理器
 * 提供用户友好的错误提示和问题上报功能
 */
class ErrorHandler {
  constructor() {
    this.config = {
      // 错误上报配置
      enableReport: true,
      reportUrl: envConfig.errorReportUrl || '',
      
      // 用户提示配置
      showToast: true,
      showModal: false,
      defaultDuration: 3000,
      
      // 错误过滤配置
      ignoreErrors: ['cancel', 'user cancel'],
      maxReportCount: 10, // 单个错误最大上报次数
      
      // 开发模式配置
      debugMode: envConfig.debug || false
    };
    
    // 错误统计
    this.errorStats = new Map();
    this.reportedErrors = new Map();
    
    // 初始化
    this.init();
  }
  
  /**
   * 初始化错误处理器
   */
  init() {
    // 监听全局错误
    this.setupGlobalErrorHandler();
    
    // 定期清理统计数据
    this.setupCleanup();
    
    envConfig.log('错误处理器初始化完成');
  }
  
  /**
   * 设置全局错误处理
   */
  setupGlobalErrorHandler() {
    // 监听小程序错误
    if (typeof wx.onError === 'function') {
      wx.onError((error) => {
        this.handleGlobalError('runtime', error);
      });
    }
    
    // 监听未处理的Promise拒绝
    if (typeof wx.onUnhandledRejection === 'function') {
      wx.onUnhandledRejection((res) => {
        this.handleGlobalError('unhandledRejection', res.reason);
      });
    }
  }
  
  /**
   * 处理全局错误
   */
  handleGlobalError(type, error) {
    try {
      const errorInfo = {
        type,
        message: error?.message || error?.errMsg || String(error),
        stack: error?.stack,
        timestamp: Date.now()
      };
      
      this.logError('Global Error', errorInfo);
      
      // 上报严重错误
      if (this.config.enableReport) {
        this.reportError(errorInfo);
      }
      
    } catch (handlerError) {
      console.error('错误处理器自身发生错误:', handlerError);
    }
  }
  
  /**
   * 主要错误处理方法
   */
  handle(error, options = {}) {
    try {
      const errorInfo = this.analyzeError(error);
      const userMessage = this.generateUserMessage(errorInfo, options);
      
      // 记录错误日志
      this.logError(options.context || 'Unknown', errorInfo);
      
      // 更新错误统计
      this.updateStats(errorInfo);
      
      // 显示用户提示
      if (options.showUser !== false) {
        this.showUserMessage(userMessage, options);
      }
      
      // 上报错误（如果需要）
      if (this.shouldReportError(errorInfo)) {
        this.reportError({
          ...errorInfo,
          context: options.context,
          userAction: options.userAction
        });
      }
      
      // 执行回调
      if (options.callback) {
        options.callback(errorInfo);
      }
      
      return errorInfo;
      
    } catch (handlerError) {
      console.error('错误处理失败:', handlerError);
      
      // 降级处理
      this.showFallbackMessage(error);
      return { type: 'unknown', message: String(error) };
    }
  }
  
  /**
   * 分析错误类型和信息
   */
  analyzeError(error) {
    const errorInfo = {
      type: 'unknown',
      message: '',
      code: null,
      statusCode: null,
      stack: null,
      timestamp: Date.now(),
      fingerprint: ''
    };
    
    if (error instanceof Error) {
      errorInfo.message = error.message;
      errorInfo.stack = error.stack;
      errorInfo.type = error.name;
    } else if (typeof error === 'object' && error !== null) {
      errorInfo.message = error.errMsg || error.message || JSON.stringify(error);
      errorInfo.code = error.code;
      errorInfo.statusCode = error.statusCode;
      
      // 分析微信API错误
      if (error.errMsg) {
        errorInfo.type = this.parseWxErrorType(error.errMsg);
      }
    } else {
      errorInfo.message = String(error);
    }
    
    // 生成错误指纹
    errorInfo.fingerprint = this.generateFingerprint(errorInfo);
    
    return errorInfo;
  }
  
  /**
   * 解析微信API错误类型
   */
  parseWxErrorType(errMsg) {
    if (errMsg.includes('request:fail')) {
      if (errMsg.includes('timeout')) return 'network_timeout';
      if (errMsg.includes('ssl')) return 'ssl_error';
      return 'network_error';
    }
    
    if (errMsg.includes('getUserProfile:fail')) {
      if (errMsg.includes('cancel')) return 'user_cancel';
      return 'auth_error';
    }
    
    if (errMsg.includes('login:fail')) return 'login_error';
    if (errMsg.includes('uploadFile:fail')) return 'upload_error';
    
    return 'wx_api_error';
  }
  
  /**
   * 生成用户友好的错误消息
   */
  generateUserMessage(errorInfo, options) {
    // 优先使用自定义消息
    if (options.message) {
      return options.message;
    }
    
    // 根据错误类型生成消息
    switch (errorInfo.type) {
      case 'network_error':
        return '网络连接失败，请检查网络后重试';
        
      case 'network_timeout':
        return '请求超时，请稍后重试';
        
      case 'ssl_error':
        return '安全连接失败，请检查网络设置';
        
      case 'user_cancel':
        return null; // 用户取消不显示错误
        
      case 'auth_error':
        return '登录失败，请重新登录';
        
      case 'login_error':
        return '微信登录失败，请重试';
        
      case 'upload_error':
        return '文件上传失败，请重试';
        
      case 'business_error':
        return errorInfo.message || '操作失败，请重试';
        
      case 'server_error':
        return '服务暂时不可用，请稍后重试';
        
      default:
        // 对于HTTP状态码错误
        if (errorInfo.statusCode) {
          if (errorInfo.statusCode >= 500) {
            return '服务器错误，请稍后重试';
          } else if (errorInfo.statusCode === 401) {
            return '登录已过期，请重新登录';
          } else if (errorInfo.statusCode === 403) {
            return '没有权限执行此操作';
          } else if (errorInfo.statusCode === 429) {
            return '操作过于频繁，请稍后重试';
          }
        }
        
        return '操作失败，请重试';
    }
  }
  
  /**
   * 显示用户消息
   */
  showUserMessage(message, options) {
    if (!message) return;
    
    const showModal = options.modal || this.config.showModal;
    const duration = options.duration || this.config.defaultDuration;
    
    if (showModal) {
      wx.showModal({
        title: options.title || '提示',
        content: message,
        showCancel: false,
        confirmText: '确定'
      });
    } else if (this.config.showToast) {
      wx.showToast({
        title: message,
        icon: options.icon || 'none',
        duration: duration
      });
    }
  }
  
  /**
   * 显示降级错误消息
   */
  showFallbackMessage(error) {
    wx.showToast({
      title: '操作失败，请重试',
      icon: 'none',
      duration: 2000
    });
  }
  
  /**
   * 记录错误日志
   */
  logError(context, errorInfo) {
    const logData = {
      context,
      ...errorInfo,
      userAgent: wx.getSystemInfoSync(),
      timestamp: new Date(errorInfo.timestamp).toISOString()
    };
    
    if (this.config.debugMode) {
      console.error('错误详情:', logData);
    } else {
      console.error(`[${context}] ${errorInfo.message}`);
    }
  }
  
  /**
   * 更新错误统计
   */
  updateStats(errorInfo) {
    const key = errorInfo.fingerprint;
    const current = this.errorStats.get(key) || { count: 0, firstSeen: Date.now(), lastSeen: Date.now() };
    
    current.count++;
    current.lastSeen = Date.now();
    
    this.errorStats.set(key, current);
  }
  
  /**
   * 判断是否应该上报错误
   */
  shouldReportError(errorInfo) {
    if (!this.config.enableReport || !this.config.reportUrl) {
      return false;
    }
    
    // 忽略用户取消等错误
    const message = errorInfo.message.toLowerCase();
    if (this.config.ignoreErrors.some(ignore => message.includes(ignore))) {
      return false;
    }
    
    // 检查上报次数限制
    const reportCount = this.reportedErrors.get(errorInfo.fingerprint) || 0;
    return reportCount < this.config.maxReportCount;
  }
  
  /**
   * 上报错误
   */
  async reportError(errorInfo) {
    try {
      const reportCount = (this.reportedErrors.get(errorInfo.fingerprint) || 0) + 1;
      this.reportedErrors.set(errorInfo.fingerprint, reportCount);
      
      const reportData = {
        ...errorInfo,
        reportCount,
        systemInfo: wx.getSystemInfoSync(),
        accountInfo: wx.getAccountInfoSync(),
        networkType: await this.getNetworkType()
      };
      
      // 简化实现：可以发送到服务器
      wx.request({
        url: this.config.reportUrl,
        method: 'POST',
        data: reportData,
        header: {
          'Content-Type': 'application/json'
        },
        success: () => {
          envConfig.log('错误上报成功:', errorInfo.fingerprint);
        },
        fail: (err) => {
          envConfig.error('错误上报失败:', err);
        }
      });
      
    } catch (reportError) {
      envConfig.error('错误上报过程出错:', reportError);
    }
  }
  
  /**
   * 获取网络类型
   */
  getNetworkType() {
    return new Promise((resolve) => {
      wx.getNetworkType({
        success: (res) => resolve(res.networkType),
        fail: () => resolve('unknown')
      });
    });
  }
  
  /**
   * 生成错误指纹
   */
  generateFingerprint(errorInfo) {
    const content = `${errorInfo.type}:${errorInfo.message}:${errorInfo.code}`;
    return this.simpleHash(content);
  }
  
  /**
   * 简单哈希函数
   */
  simpleHash(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // 转换为32位整数
    }
    return Math.abs(hash).toString(36);
  }
  
  /**
   * 设置清理定时器
   */
  setupCleanup() {
    setInterval(() => {
      this.cleanupStats();
    }, 30 * 60 * 1000); // 30分钟清理一次
  }
  
  /**
   * 清理过期统计
   */
  cleanupStats() {
    const now = Date.now();
    const maxAge = 24 * 60 * 60 * 1000; // 24小时
    
    // 清理错误统计
    for (const [key, stats] of this.errorStats.entries()) {
      if (now - stats.lastSeen > maxAge) {
        this.errorStats.delete(key);
      }
    }
    
    // 清理上报计数
    if (this.reportedErrors.size > 100) {
      const entries = Array.from(this.reportedErrors.entries());
      entries.slice(0, 50).forEach(([key]) => {
        this.reportedErrors.delete(key);
      });
    }
  }
  
  /**
   * 获取错误统计
   */
  getStats() {
    const stats = {
      totalErrors: Array.from(this.errorStats.values()).reduce((sum, stat) => sum + stat.count, 0),
      uniqueErrors: this.errorStats.size,
      reportedErrors: Array.from(this.reportedErrors.values()).reduce((sum, count) => sum + count, 0),
      topErrors: []
    };
    
    // 获取最频繁的错误
    const sortedErrors = Array.from(this.errorStats.entries())
      .sort(([,a], [,b]) => b.count - a.count)
      .slice(0, 5);
    
    stats.topErrors = sortedErrors.map(([fingerprint, stat]) => ({
      fingerprint,
      count: stat.count,
      lastSeen: stat.lastSeen
    }));
    
    return stats;
  }
  
  /**
   * 便捷方法
   */
  
  // 网络错误处理
  handleNetworkError(error, options = {}) {
    return this.handle(error, {
      ...options,
      context: 'Network',
      userAction: 'request'
    });
  }
  
  // API错误处理
  handleApiError(error, options = {}) {
    return this.handle(error, {
      ...options,
      context: 'API',
      userAction: 'api_call'
    });
  }
  
  // 用户交互错误处理
  handleUserError(error, options = {}) {
    return this.handle(error, {
      ...options,
      context: 'User',
      showUser: options.showUser !== false
    });
  }
  
  // 静默错误处理
  handleSilentError(error, options = {}) {
    return this.handle(error, {
      ...options,
      context: 'Silent',
      showUser: false
    });
  }
}

// 创建全局错误处理器实例
const errorHandler = new ErrorHandler();

module.exports = {
  errorHandler,
  
  // 导出便捷方法
  handle: (error, options) => errorHandler.handle(error, options),
  handleNetworkError: (error, options) => errorHandler.handleNetworkError(error, options),
  handleApiError: (error, options) => errorHandler.handleApiError(error, options),
  handleUserError: (error, options) => errorHandler.handleUserError(error, options),
  handleSilentError: (error, options) => errorHandler.handleSilentError(error, options),
  
  // 错误类型常量
  ERROR_TYPES: {
    NETWORK: 'network_error',
    AUTH: 'auth_error',
    BUSINESS: 'business_error',
    USER_CANCEL: 'user_cancel',
    TIMEOUT: 'network_timeout',
    SERVER: 'server_error'
  },
  
  // 获取统计信息
  getStats: () => errorHandler.getStats()
};
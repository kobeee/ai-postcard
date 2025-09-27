// app-enhanced.js - AI明信片小程序增强版主应用
// 集成安全认证、错误处理、兼容性管理等企业级功能

const envConfig = require('./config/env.js');
const { taskPollingManager } = require('./utils/task-polling.js');

// 增强功能模块
const { enhancedAuthManager } = require('./utils/enhanced-auth.js');
const { errorHandler } = require('./utils/error-handler.js');
const { compatibilityManager } = require('./utils/compatibility-manager.js');
const { enhancedRequestManager } = require('./utils/enhanced-request.js');

App({
  async onLaunch(options) {
    envConfig.log('🚀 AI明信片小程序启动（增强版）', options);
    
    try {
      // 初始化核心系统
      await this.initCoreSystem();
      
      // 初始化增强功能
      await this.initEnhancedFeatures();
      
      // 获取系统信息
      this.getSystemInfo();
      
      // 检查小程序版本更新
      this.checkForUpdate();
      
      // 预取环境信息
      this.prefetchEnvironment();
      
      // 记录启动日志
      this.recordLaunchLog();
      
      envConfig.log('✅ 小程序启动完成');
      
    } catch (error) {
      envConfig.error('❌ 小程序启动失败:', error);
      errorHandler.handle(error, {
        context: 'app_launch',
        showUser: true,
        message: '应用启动失败，正在尝试修复...'
      });
      
      // 启动失败时的降级处理
      await this.fallbackInit();
    }
  },

  onShow(options) {
    envConfig.log('📱 小程序显示', options);
    
    // 记录显示时间
    this.globalData.lastShowTime = Date.now();
    
    // 检查认证状态
    this.checkAuthState();
    
    // 处理分享参数
    if (options.scene === 1007 || options.scene === 1008) {
      this.handleShareParams(options);
    }
    
    // 处理扫码进入
    if (options.scene === 1011) {
      this.handleQRCode(options);
    }
  },

  onHide() {
    envConfig.log('🔽 小程序隐藏');
    
    // 记录使用时长
    if (this.globalData.lastShowTime) {
      const duration = Date.now() - this.globalData.lastShowTime;
      this.recordUsageMetrics(duration);
    }
    
    // 保存应用状态
    this.saveAppState();
  },

  onError(msg) {
    envConfig.error('💥 小程序发生错误:', msg);
    
    // 使用增强错误处理器
    errorHandler.handleGlobalError('app_error', {
      message: msg,
      timestamp: Date.now(),
      stack: new Error().stack
    });
  },
  
  onUnhandledRejection(res) {
    envConfig.error('🚫 未处理的Promise拒绝:', res);
    
    errorHandler.handleGlobalError('unhandled_rejection', {
      message: res.reason?.message || String(res.reason),
      stack: res.reason?.stack,
      timestamp: Date.now()
    });
  },
  
  /**
   * 初始化核心系统
   */
  async initCoreSystem() {
    try {
      // 初始化兼容性管理器
      await compatibilityManager.init();
      envConfig.log('✅ 兼容性管理器初始化完成');
      
      // 根据兼容性配置初始化认证系统
      const authConfig = compatibilityManager.getAuthConfig();
      if (authConfig.jwtEnabled) {
        await enhancedAuthManager.init();
        envConfig.log('✅ 增强认证系统初始化完成');
      } else {
        // 降级到基础认证
        const basicAuth = require('./utils/auth.js');
        await basicAuth.init();
        envConfig.log('✅ 基础认证系统初始化完成（兼容模式）');
      }
      
    } catch (error) {
      envConfig.error('❌ 核心系统初始化失败:', error);
      throw error;
    }
  },
  
  /**
   * 初始化增强功能
   */
  async initEnhancedFeatures() {
    try {
      // 设置错误处理监听器
      this.setupErrorHandlers();
      
      // 设置网络状态监听
      this.setupNetworkMonitoring();
      
      // 设置性能监控
      this.setupPerformanceMonitoring();
      
      // 初始化用户行为分析
      this.initUserAnalytics();
      
      envConfig.log('✅ 增强功能初始化完成');
      
    } catch (error) {
      envConfig.error('⚠️ 增强功能初始化失败，使用基础功能:', error);
    }
  },
  
  /**
   * 设置错误处理监听器
   */
  setupErrorHandlers() {
    // 监听认证错误
    enhancedAuthManager.on('error', (error) => {
      errorHandler.handle(error, {
        context: 'auth',
        showUser: true
      });
    });
    
    // 监听网络错误
    enhancedRequestManager.on?.('error', (error) => {
      errorHandler.handleNetworkError(error);
    });
  },
  
  /**
   * 设置网络状态监听
   */
  setupNetworkMonitoring() {
    wx.onNetworkStatusChange((res) => {
      const networkStatus = res.isConnected ? 'online' : 'offline';
      
      envConfig.log('🌐 网络状态变化:', {
        status: networkStatus,
        networkType: res.networkType
      });
      
      this.globalData.networkStatus = networkStatus;
      this.globalData.networkType = res.networkType;
      
      // 网络恢复时的处理
      if (networkStatus === 'online' && this.globalData.previousNetworkStatus === 'offline') {
        this.onNetworkRecover();
      }
      
      this.globalData.previousNetworkStatus = networkStatus;
    });
  },
  
  /**
   * 设置性能监控
   */
  setupPerformanceMonitoring() {
    // 监控页面性能
    if (typeof wx.onMemoryWarning === 'function') {
      wx.onMemoryWarning(() => {
        envConfig.log('⚠️ 内存警告');
        this.handleMemoryWarning();
      });
    }
    
    // 记录启动性能
    const launchTime = Date.now() - this.globalData.startTime;
    this.recordPerformanceMetric('app_launch_time', launchTime);
  },
  
  /**
   * 初始化用户行为分析
   */
  initUserAnalytics() {
    // 记录应用安装/更新信息
    const currentVersion = this.globalData.config.version;
    const lastVersion = wx.getStorageSync('app_version');
    
    if (!lastVersion) {
      // 新安装
      this.recordEvent('app_install', { version: currentVersion });
    } else if (lastVersion !== currentVersion) {
      // 应用更新
      this.recordEvent('app_update', { 
        from_version: lastVersion, 
        to_version: currentVersion 
      });
    }
    
    wx.setStorageSync('app_version', currentVersion);
  },
  
  /**
   * 检查认证状态
   */
  async checkAuthState() {
    try {
      const authConfig = compatibilityManager.getAuthConfig();
      
      if (authConfig.jwtEnabled && enhancedAuthManager.isLoggedIn()) {
        // 检查token是否需要刷新
        await enhancedAuthManager.validateAndRefreshToken();
      }
      
    } catch (error) {
      envConfig.error('认证状态检查失败:', error);
      errorHandler.handleSilentError(error, { context: 'auth_check' });
    }
  },
  
  /**
   * 网络恢复处理
   */
  onNetworkRecover() {
    envConfig.log('🔄 网络已恢复，同步应用状态');
    
    // 重新检查认证状态
    this.checkAuthState();
    
    // 重试失败的请求
    enhancedRequestManager.retryPendingRequests?.();
    
    // 显示网络恢复提示
    wx.showToast({
      title: '网络已恢复',
      icon: 'success',
      duration: 1500
    });
  },
  
  /**
   * 内存警告处理
   */
  handleMemoryWarning() {
    // 清理缓存
    enhancedRequestManager.cache?.clear();
    
    // 清理过期存储
    this.cleanupStorage();
    
    // 记录内存警告事件
    this.recordEvent('memory_warning', {
      timestamp: Date.now(),
      available_storage: wx.getStorageInfoSync()
    });
  },
  
  /**
   * 降级初始化
   */
  async fallbackInit() {
    try {
      // 使用基础认证
      const basicAuth = require('./utils/auth.js');
      await basicAuth.init();
      
      // 设置基础错误处理
      wx.onError((msg) => {
        console.error('应用错误:', msg);
        wx.showToast({
          title: '应用异常，请重启',
          icon: 'none'
        });
      });
      
      envConfig.log('✅ 降级模式启动成功');
      
    } catch (error) {
      envConfig.error('❌ 降级模式启动失败:', error);
      
      // 最后的降级措施
      wx.showModal({
        title: '启动失败',
        content: '应用启动遇到问题，建议重新打开小程序',
        showCancel: false
      });
    }
  },
  
  /**
   * 处理分享参数
   */
  handleShareParams(options) {
    const { query } = options;
    
    if (query) {
      this.globalData.shareParams = query;
      
      if (query.postcardId) {
        this.globalData.sharedPostcardId = query.postcardId;
        this.recordEvent('share_enter', { 
          type: 'postcard',
          id: query.postcardId 
        });
      }
      
      if (query.inviteCode) {
        this.globalData.inviteCode = query.inviteCode;
        this.recordEvent('share_enter', { 
          type: 'invite',
          code: query.inviteCode 
        });
      }
    }
  },
  
  /**
   * 处理二维码进入
   */
  handleQRCode(options) {
    const { query, path } = options;
    
    if (query && query.qr_data) {
      try {
        const qrData = JSON.parse(decodeURIComponent(query.qr_data));
        this.globalData.qrData = qrData;
        
        this.recordEvent('qr_enter', qrData);
        
      } catch (error) {
        envConfig.error('解析二维码数据失败:', error);
      }
    }
  },
  
  /**
   * 用户登录成功事件（增强版）
   */
  onUserLogin(userInfo) {
    envConfig.log('👤 用户登录成功:', userInfo);
    
    this.globalData.userInfo = userInfo;
    this.globalData.loginTime = Date.now();
    
    // 记录登录事件
    this.recordEvent('user_login', {
      user_id: userInfo.user_id || userInfo.id,
      login_type: compatibilityManager.getAuthConfig().jwtEnabled ? 'jwt' : 'basic'
    });
    
    // 登录后初始化
    this.afterUserLogin(userInfo);
    
    // 发送登录成功通知
    this.sendAppMessage('user_login', userInfo);
  },
  
  /**
   * 用户退出登录事件（增强版）
   */
  onUserLogout() {
    envConfig.log('👋 用户退出登录');
    
    const loginDuration = this.globalData.loginTime ? 
      Date.now() - this.globalData.loginTime : 0;
    
    // 记录登出事件
    this.recordEvent('user_logout', {
      session_duration: loginDuration
    });
    
    // 清理用户相关数据
    this.globalData.userInfo = null;
    this.globalData.currentTask = null;
    this.globalData.loginTime = null;
    
    // 停止轮询任务
    taskPollingManager.stopAllPolling();
    
    // 清除缓存
    this.clearUserRelatedData();
    
    // 发送登出通知
    this.sendAppMessage('user_logout');
  },
  
  /**
   * 记录使用指标
   */
  recordUsageMetrics(duration) {
    this.recordPerformanceMetric('session_duration', duration);
    
    const totalUsage = wx.getStorageSync('total_usage_time') || 0;
    wx.setStorageSync('total_usage_time', totalUsage + duration);
  },
  
  /**
   * 记录性能指标
   */
  recordPerformanceMetric(metric, value) {
    const metrics = wx.getStorageSync('performance_metrics') || {};
    
    if (!metrics[metric]) {
      metrics[metric] = [];
    }
    
    metrics[metric].push({
      value,
      timestamp: Date.now()
    });
    
    // 只保留最近50个记录
    if (metrics[metric].length > 50) {
      metrics[metric] = metrics[metric].slice(-50);
    }
    
    wx.setStorageSync('performance_metrics', metrics);
  },
  
  /**
   * 记录事件
   */
  recordEvent(event, data = {}) {
    const eventData = {
      event,
      data,
      timestamp: Date.now(),
      user_id: this.globalData.userInfo?.user_id,
      session_id: this.globalData.sessionId
    };
    
    // 存储到本地
    const events = wx.getStorageSync('user_events') || [];
    events.push(eventData);
    
    // 只保留最近100个事件
    if (events.length > 100) {
      events.splice(0, events.length - 100);
    }
    
    wx.setStorageSync('user_events', events);
    
    // 如果有网络，可以上报到分析服务
    if (this.globalData.networkStatus === 'online') {
      this.uploadEventData(eventData);
    }
  },
  
  /**
   * 上传事件数据
   */
  async uploadEventData(eventData) {
    try {
      // 这里可以集成数据分析服务
      // 例如：微信小程序数据助手、自定义分析服务等
      envConfig.log('📊 上报事件数据:', eventData.event);
      
    } catch (error) {
      envConfig.error('事件数据上报失败:', error);
    }
  },
  
  /**
   * 保存应用状态
   */
  saveAppState() {
    const pages = getCurrentPages();
    const currentPage = pages.length > 0 ? pages[pages.length - 1] : null;
    
    const appState = {
      lastActiveTime: Date.now(),
      currentPage: currentPage?.route || 'unknown',
      userLoggedIn: !!this.globalData.userInfo,
      networkStatus: this.globalData.networkStatus
    };
    
    wx.setStorageSync('app_state', appState);
  },
  
  /**
   * 清理存储
   */
  cleanupStorage() {
    try {
      const storageInfo = wx.getStorageInfoSync();
      
      // 如果存储使用超过阈值，清理旧数据
      if (storageInfo.currentSize > storageInfo.limitSize * 0.8) {
        wx.removeStorageSync('user_events');
        wx.removeStorageSync('performance_metrics');
        
        envConfig.log('🧹 已清理存储空间');
      }
      
    } catch (error) {
      envConfig.error('清理存储失败:', error);
    }
  },
  
  /**
   * 发送应用内消息
   */
  sendAppMessage(type, data = {}) {
    // 可以用于页面间通信
    this.globalData.lastMessage = {
      type,
      data,
      timestamp: Date.now()
    };
  },
  
  /**
   * 获取调试信息
   */
  getDebugInfo() {
    return {
      version: this.globalData.config.version,
      compatibility: compatibilityManager.getDebugInfo(),
      auth: enhancedAuthManager.getDebugInfo?.() || {},
      network: {
        status: this.globalData.networkStatus,
        type: this.globalData.networkType
      },
      performance: wx.getStorageSync('performance_metrics') || {},
      storage: wx.getStorageInfoSync(),
      system: this.globalData.systemInfo
    };
  },
  
  // 继承原有方法
  getSystemInfo() {
    wx.getSystemInfo({
      success: (res) => {
        this.globalData.systemInfo = res;
        this.adaptToSystem(res);
      }
    });
  },
  
  checkForUpdate() {
    if (wx.getUpdateManager) {
      const updateManager = wx.getUpdateManager();
      
      updateManager.onUpdateReady(() => {
        wx.showModal({
          title: '更新提示',
          content: '新版本已准备好，是否重启应用？',
          success: (res) => {
            if (res.confirm) {
              updateManager.applyUpdate();
            }
          }
        });
      });
    }
  },
  
  adaptToSystem(systemInfo) {
    const { windowWidth, windowHeight, pixelRatio } = systemInfo;
    
    this.globalData.screenInfo = {
      width: windowWidth,
      height: windowHeight,
      pixelRatio,
      isSmallScreen: windowWidth < 350
    };
    
    if (systemInfo.safeArea) {
      this.globalData.safeArea = systemInfo.safeArea;
    }
  },
  
  recordLaunchLog() {
    const logs = wx.getStorageSync('logs') || [];
    logs.unshift(Date.now());
    
    if (logs.length > 50) {
      logs.splice(50);
    }
    
    wx.setStorageSync('logs', logs);
  },
  
  afterUserLogin(userInfo) {
    // 用户登录后的初始化
  },
  
  clearUserRelatedData() {
    wx.removeStorageSync('userPostcards');
    wx.removeStorageSync('userPreferences');
    wx.removeStorageSync('user_quota_cache');
  },
  
  prefetchEnvironment() {
    // 保持原有的环境预取逻辑
    try {
      const { envAPI } = require('./utils/enhanced-request.js');
      wx.getSetting({
        success: (setting) => {
          const hasAuth = setting.authSetting && setting.authSetting['scope.userLocation'];
          if (hasAuth === false) return;
          
          wx.getLocation({
            type: 'gcj02',
            isHighAccuracy: true,
            success: async (loc) => {
              try {
                const [cityRes, weatherRes] = await Promise.all([
                  envAPI.reverseGeocode(loc.latitude, loc.longitude),
                  envAPI.getWeather(loc.latitude, loc.longitude)
                ]);
                
                const cache = {
                  ts: Date.now(),
                  location: loc,
                  cityName: cityRes?.city || cityRes?.name || '',
                  weatherInfo: weatherRes?.weather_text || ''
                };
                
                wx.setStorage({ key: 'envCache', data: cache });
              } catch (e) {
                // 静默失败
              }
            }
          });
        }
      });
    } catch (e) {}
  },
  
  /**
   * 全局数据（增强版）
   */
  globalData: {
    // 启动时间
    startTime: Date.now(),
    
    // 会话ID
    sessionId: Date.now().toString(36) + Math.random().toString(36).substr(2),
    
    // 用户相关
    userInfo: null,
    loginTime: null,
    
    // 系统相关
    systemInfo: null,
    screenInfo: null,
    safeArea: null,
    
    // 网络状态
    networkStatus: 'unknown',
    networkType: 'unknown',
    previousNetworkStatus: 'unknown',
    
    // 应用状态
    currentTask: null,
    shareParams: null,
    sharedPostcardId: null,
    inviteCode: null,
    qrData: null,
    lastShowTime: null,
    lastMessage: null,
    
    // 应用配置
    config: {
      version: '2.0.0',
      environment: envConfig.currentEnv,
      features: {
        enhanced_auth: true,
        error_handling: true,
        compatibility: true,
        analytics: true
      }
    }
  },
  
  /**
   * 增强工具方法
   */
  utils: {
    // 继承原有工具方法
    showLoading: (title = '加载中...') => {
      wx.showLoading({ title, mask: true });
    },
    
    hideLoading: () => wx.hideLoading(),
    
    showSuccess: (title, duration = 1500) => {
      wx.showToast({ title, icon: 'success', duration });
    },
    
    showError: (title, duration = 2000) => {
      wx.showToast({ title, icon: 'none', duration });
    },
    
    showConfirm: (content, title = '提示') => {
      return new Promise((resolve) => {
        wx.showModal({
          title, content,
          success: (res) => resolve(res.confirm),
          fail: () => resolve(false)
        });
      });
    },
    
    // 增强工具方法
    handleError: (error, options = {}) => {
      return errorHandler.handle(error, options);
    },
    
    safeRequest: async (requestFn, fallback = null) => {
      try {
        return await requestFn();
      } catch (error) {
        errorHandler.handleSilentError(error);
        return fallback;
      }
    },
    
    formatTime: (date) => {
      if (!date) return '';
      
      const now = new Date();
      const target = new Date(date);
      const diff = now - target;
      
      if (diff < 60000) return '刚刚';
      if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前';
      if (now.toDateString() === target.toDateString()) {
        return target.toTimeString().substr(0, 5);
      }
      return target.toLocaleDateString();
    },
    
    debounce: (func, delay) => {
      let timer = null;
      return function(...args) {
        if (timer) clearTimeout(timer);
        timer = setTimeout(() => func.apply(this, args), delay);
      };
    },
    
    throttle: (func, delay) => {
      let last = 0;
      return function(...args) {
        const now = Date.now();
        if (now - last >= delay) {
          func.apply(this, args);
          last = now;
        }
      };
    }
  }
});
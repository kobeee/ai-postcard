// app.js - AI明信片小程序主应用（增强版为默认）
// 集成安全认证、错误处理、兼容性管理等企业级功能

const envConfig = require('./config/env.js');
const { taskPollingManager } = require('./utils/task-polling.js');

// 增强功能模块
const { enhancedAuthManager } = require('./utils/enhanced-auth.js');
const { errorHandler } = require('./utils/error-handler.js');
const { compatibilityManager } = require('./utils/compatibility-manager.js');
const { enhancedRequestManager } = require('./utils/enhanced-request.js');
const { loadCharmFontsOnce } = require('./utils/charm-font-loader.js');

App({
  async onLaunch(options) {
    envConfig.log('🚀 AI明信片小程序启动（增强版默认）', options);
    try {
      await this.initCoreSystem();
      await this.initEnhancedFeatures();
      this.getSystemInfo();
      this.checkForUpdate();
      this.prefetchEnvironment();
      this.recordLaunchLog();
      envConfig.log('✅ 小程序启动完成');
    } catch (error) {
      envConfig.error('❌ 小程序启动失败:', error);
      errorHandler.handle(error, { context: 'app_launch', showUser: true, message: '应用启动失败，正在尝试修复...' });
      await this.fallbackInit();
    }
  },

  onShow(options) {
    envConfig.log('📱 小程序显示', options);
    this.globalData.lastShowTime = Date.now();
    this.checkAuthState?.();
    if (options.scene === 1007 || options.scene === 1008) {
      this.handleShareParams(options);
    }
    if (options.scene === 1011) {
      this.handleQRCode?.(options);
    }
  },

  onHide() {
    envConfig.log('🔽 小程序隐藏');
    if (this.globalData.lastShowTime) {
      const duration = Date.now() - this.globalData.lastShowTime;
      this.recordUsageMetrics?.(duration);
    }
    this.saveAppState?.();
  },

  onError(msg) {
    envConfig.error('💥 小程序发生错误:', msg);
    errorHandler.handleGlobalError('app_error', { message: msg, timestamp: Date.now(), stack: new Error().stack });
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
   * 初始化核心系统（统一增强认证）
   */
  async initCoreSystem() {
    await compatibilityManager.init?.();
    envConfig.log('✅ 兼容性管理器初始化完成');
    await enhancedAuthManager.init();
    envConfig.log('✅ 增强认证系统初始化完成');
  },

  /**
   * 初始化增强功能
   */
  async initEnhancedFeatures() {
    // 错误处理监听
    enhancedAuthManager.on('error', (error) => {
      errorHandler.handle(error, { context: 'auth', showUser: true });
    });
    enhancedRequestManager.on?.('error', (error) => {
      errorHandler.handleNetworkError(error);
    });

    // 网络状态监听
    wx.onNetworkStatusChange((res) => {
      const networkStatus = res.isConnected ? 'online' : 'offline';
      envConfig.log('🌐 网络状态变化:', { status: networkStatus, networkType: res.networkType });
      this.globalData.networkStatus = networkStatus;
      this.globalData.networkType = res.networkType;
      if (networkStatus === 'online' && this.globalData.previousNetworkStatus === 'offline') {
        this.onNetworkRecover?.();
      }
      this.globalData.previousNetworkStatus = networkStatus;
    });

    // 性能监控
    if (typeof wx.onMemoryWarning === 'function') {
      wx.onMemoryWarning(() => {
        envConfig.log('⚠️ 内存警告');
        this.handleMemoryWarning?.();
      });
    }

    // 启动性能记录
    const launchTime = Date.now() - (this.globalData.startTime || Date.now());
    this.recordPerformanceMetric?.('app_launch_time', launchTime);

    envConfig.log('✅ 增强功能初始化完成');
    this.preloadCharmFonts();
  },

  /**
   * 系统信息
   */
  getSystemInfo() {
    wx.getSystemInfo({
      success: (res) => {
        this.globalData.systemInfo = res;
        envConfig.log('系统信息获取成功:', res);
        this.adaptToSystem(res);
      },
      fail: (error) => { envConfig.error('获取系统信息失败:', error); }
    });
  },

  /**
   * 版本更新
   */
  checkForUpdate() {
    if (!wx.getUpdateManager) return;
    const updateManager = wx.getUpdateManager();
    updateManager.onCheckForUpdate((res) => { if (res.hasUpdate) envConfig.log('发现新版本'); });
    updateManager.onUpdateReady(() => {
      wx.showModal({
        title: '更新提示',
        content: '新版本已准备好，是否重启应用？',
        success: (res) => { if (res.confirm) updateManager.applyUpdate(); }
      });
    });
    updateManager.onUpdateFailed(() => { envConfig.error('更新失败'); });
  },

  /**
   * 日志
   */
  recordLaunchLog() {
    const logs = wx.getStorageSync('logs') || [];
    logs.unshift(Date.now());
    while (logs.length > 50) logs.pop();
    wx.setStorageSync('logs', logs);
  },

  /**
   * 分享参数
   */
  handleShareParams(options) {
    try {
      const query = options.query || {};
      this.globalData.sharedPostcardId = query.postcardId || null;
      this.globalData.inviteCode = query.invite || null;
    } catch (_) {}
  },

  /**
   * 适配
   */
  adaptToSystem(res) {
    this.globalData.screenInfo = { width: res.windowWidth, height: res.windowHeight, pixelRatio: res.pixelRatio };
    this.globalData.safeArea = res.safeArea || null;
  },

  /**
   * 用户事件
   */
  onUserLogin(userInfo) {
    envConfig.log('用户登录成功:', userInfo);
    this.globalData.userInfo = userInfo;
    this.afterUserLogin?.(userInfo);
  },

  onUserLogout() {
    envConfig.log('用户退出登录');
    this.globalData.userInfo = null;
    this.globalData.currentTask = null;
    taskPollingManager.stopAllPolling();
    this.clearUserRelatedData();
  },

  afterUserLogin() {},

  clearUserRelatedData() {
    wx.removeStorageSync('userPostcards');
    wx.removeStorageSync('userPreferences');
  },

  /**
   * 环境预取
   */
  prefetchEnvironment() {
    try {
      const { envAPI } = require('./utils/enhanced-request.js');
      wx.getSetting({
        success: (setting) => {
          const hasAuth = setting.authSetting && setting.authSetting['scope.userLocation'];
          if (hasAuth === false) return;
          wx.getLocation({
            type: 'gcj02',
            isHighAccuracy: true,
            highAccuracyExpireTime: 3000,
            success: async (loc) => {
              try {
                const { latitude, longitude } = loc;
                const [cityRes, weatherRes] = await Promise.all([
                  envAPI.reverseGeocode(latitude, longitude, 'zh'),
                  envAPI.getWeather(latitude, longitude)
                ]);
                const cityName = (cityRes && (cityRes.city || cityRes.name)) || '';
                const weatherText = (weatherRes && weatherRes.weather_text) || '';
                const temperature = weatherRes && weatherRes.temperature;
                const weatherInfo = typeof temperature === 'number' ? `${weatherText} · ${temperature}°C` : weatherText;
                wx.setStorage({ key: 'envCache', data: { ts: Date.now(), location: { latitude, longitude }, cityName, weatherInfo } });
              } catch (_) {}
            },
            fail: () => {}
          });
        },
        fail: () => {}
      });
    } catch (_) {}
  },

  /**
   * 预加载挂件字体，保证首屏和详情一致
   */
  preloadCharmFonts() {
    try {
      const preloadPromise = loadCharmFontsOnce({ scopeId: 'app-init' });
      this.globalData.fontPreloadPromise = preloadPromise;
      if (preloadPromise && typeof preloadPromise.catch === 'function') {
        preloadPromise.catch((error) => {
          envConfig.warn('挂件字体预加载失败，将在组件级别重试', error);
        });
      }
    } catch (error) {
      envConfig.warn('挂件字体预加载发生异常，将等待组件内部兜底', error);
    }
  },

  // 预留钩子
  onNetworkRecover() {},
  handleMemoryWarning() {},
  recordPerformanceMetric() {},
  recordUsageMetrics() {},
  saveAppState() {},
  async fallbackInit() {},

  /**
   * 全局数据（增强版）
   */
  globalData: {
    startTime: Date.now(),
    sessionId: Date.now().toString(36) + Math.random().toString(36).substr(2),
    userInfo: null,
    loginTime: null,
    systemInfo: null,
    screenInfo: null,
    safeArea: null,
    networkStatus: 'unknown',
    networkType: 'unknown',
    previousNetworkStatus: 'unknown',
    currentTask: null,
    shareParams: null,
    sharedPostcardId: null,
    inviteCode: null,
    qrData: null,
    fontPreloadPromise: null,
    lastShowTime: null,
    lastMessage: null,
    config: {
      version: '2.0.0',
      environment: envConfig.currentEnv,
      features: { enhanced_auth: true, error_handling: true, compatibility: true, analytics: true }
    }
  },

  /**
   * 增强工具方法
   */
  utils: {
    showLoading: (title = '加载中...') => wx.showLoading({ title, mask: true }),
    hideLoading: () => wx.hideLoading(),
    showSuccess: (title, duration = 1500) => wx.showToast({ title, icon: 'success', duration }),
    showError: (title, duration = 2000) => wx.showToast({ title, icon: 'none', duration }),
    showConfirm: (content, title = '提示') => new Promise((resolve) => {
      wx.showModal({ title, content, success: (res) => resolve(res.confirm), fail: () => resolve(false) });
    }),
    handleError: (error, options = {}) => errorHandler.handle(error, options),
    safeRequest: async (requestFn, fallback = null) => {
      try { return await requestFn(); } catch (error) { errorHandler.handleSilentError(error); return fallback; }
    },
    formatTime: (date) => {
      if (!date) return '';
      const now = new Date();
      const target = new Date(date);
      const diff = now - target;
      if (diff < 60000) return '刚刚';
      if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前';
      if (now.toDateString() === target.toDateString()) return target.toTimeString().substr(0, 5);
      return target.toLocaleDateString();
    },
    debounce: (func, delay) => { let timer=null; return function(...args){ if (timer) clearTimeout(timer); timer=setTimeout(()=>func.apply(this,args),delay);} },
    throttle: (func, delay) => { let last=0; return function(...args){ const now=Date.now(); if (now-last>=delay){ func.apply(this,args); last=now; } } }
  }
});

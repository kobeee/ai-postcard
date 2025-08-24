// app.js - AI明信片小程序主应用
const authUtil = require('./utils/auth.js');
const envConfig = require('./config/env.js');
const { taskPollingManager } = require('./utils/task-polling.js');

App({
  async onLaunch(options) {
    envConfig.log('AI明信片小程序启动', options);
    
    // 初始化认证系统
    await this.initAuth();
    
    // 获取系统信息
    this.getSystemInfo();
    
    // 检查小程序版本更新
    this.checkForUpdate();
    
    // 记录启动日志
    this.recordLaunchLog();
  },

  onShow(options) {
    envConfig.log('小程序显示', options);
    
    // 记录显示时间
    this.globalData.lastShowTime = Date.now();
    
    // 如果从分享进入，处理分享参数
    if (options.scene === 1007 || options.scene === 1008) {
      this.handleShareParams(options);
    }
  },

  onHide() {
    envConfig.log('小程序隐藏');
    
    // 记录使用时长
    if (this.globalData.lastShowTime) {
      const duration = Date.now() - this.globalData.lastShowTime;
      envConfig.log('本次使用时长:', duration + 'ms');
    }
  },

  onError(msg) {
    envConfig.error('小程序发生错误:', msg);
    
    // 可以在这里上报错误到监控系统
    this.reportError(msg);
  },
  
  /**
   * 初始化认证系统
   */
  async initAuth() {
    try {
      await authUtil.init();
      envConfig.log('认证系统初始化完成');
      
      // 如果用户已登录，触发登录成功事件
      if (authUtil.isLoggedIn()) {
        this.onUserLogin(authUtil.getCurrentUser());
      }
    } catch (error) {
      envConfig.error('认证系统初始化失败:', error);
    }
  },
  
  /**
   * 获取系统信息
   */
  getSystemInfo() {
    wx.getSystemInfo({
      success: (res) => {
        this.globalData.systemInfo = res;
        envConfig.log('系统信息获取成功:', res);
        
        // 根据系统信息做一些适配
        this.adaptToSystem(res);
      },
      fail: (error) => {
        envConfig.error('获取系统信息失败:', error);
      }
    });
  },
  
  /**
   * 检查小程序更新
   */
  checkForUpdate() {
    if (wx.getUpdateManager) {
      const updateManager = wx.getUpdateManager();
      
      updateManager.onCheckForUpdate((res) => {
        if (res.hasUpdate) {
          envConfig.log('发现新版本');
        }
      });
      
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
      
      updateManager.onUpdateFailed(() => {
        envConfig.error('更新失败');
      });
    }
  },
  
  /**
   * 记录启动日志
   */
  recordLaunchLog() {
    const logs = wx.getStorageSync('logs') || [];
    logs.unshift(Date.now());
    
    // 只保留最近50条日志
    if (logs.length > 50) {
      logs.splice(50);
    }
    
    wx.setStorageSync('logs', logs);
  },
  
  /**
   * 根据系统信息进行适配
   */
  adaptToSystem(systemInfo) {
    // 适配不同屏幕尺寸
    const { windowWidth, windowHeight, pixelRatio } = systemInfo;
    
    this.globalData.screenInfo = {
      width: windowWidth,
      height: windowHeight,
      pixelRatio,
      isSmallScreen: windowWidth < 350
    };
    
    // 适配iOS刘海屏
    if (systemInfo.safeArea) {
      this.globalData.safeArea = systemInfo.safeArea;
    }
    
    envConfig.log('屏幕适配信息:', this.globalData.screenInfo);
  },
  
  /**
   * 处理分享参数
   */
  handleShareParams(options) {
    const { query, path } = options;
    
    if (query) {
      // 处理分享携带的参数
      if (query.postcardId) {
        // 如果是分享的明信片，记录下来
        this.globalData.sharedPostcardId = query.postcardId;
        envConfig.log('从分享进入，明信片ID:', query.postcardId);
      }
      
      if (query.inviteCode) {
        // 如果是邀请分享
        this.globalData.inviteCode = query.inviteCode;
        envConfig.log('邀请码:', query.inviteCode);
      }
    }
  },
  
  /**
   * 用户登录成功事件
   */
  onUserLogin(userInfo) {
    envConfig.log('用户登录成功:', userInfo);
    this.globalData.userInfo = userInfo;
    
    // 可以在这里进行一些登录后的初始化操作
    this.afterUserLogin(userInfo);
  },
  
  /**
   * 用户退出登录事件
   */
  onUserLogout() {
    envConfig.log('用户退出登录');
    this.globalData.userInfo = null;
    this.globalData.currentTask = null;
    
    // 停止所有轮询任务
    taskPollingManager.stopAllPolling();
    
    // 清除相关缓存数据
    this.clearUserRelatedData();
  },
  
  /**
   * 登录后的初始化操作
   */
  afterUserLogin(userInfo) {
    // 可以在这里获取用户的个人设置、作品列表等
    // 示例：预加载用户作品
    // this.preloadUserPostcards(userInfo.id);
  },
  
  /**
   * 清除用户相关数据
   */
  clearUserRelatedData() {
    // 清除可能缓存的用户数据
    wx.removeStorageSync('userPostcards');
    wx.removeStorageSync('userPreferences');
  },
  
  /**
   * 错误上报
   */
  reportError(error) {
    // 这里可以集成错误监控服务
    // 如：Sentry, Fundebug 等
    envConfig.error('上报错误:', error);
  },
  
  /**
   * 全局数据
   */
  globalData: {
    userInfo: null,           // 用户信息
    systemInfo: null,         // 系统信息
    screenInfo: null,         // 屏幕适配信息
    safeArea: null,           // 安全区域信息
    currentTask: null,        // 当前进行的明信片生成任务
    sharedPostcardId: null,   // 分享进入的明信片ID
    inviteCode: null,         // 邀请码
    lastShowTime: null,       // 最后显示时间
    
    // 应用配置
    config: {
      version: '1.0.0',
      environment: envConfig.currentEnv
    }
  },
  
  /**
   * 工具方法
   */
  utils: {
    // 显示加载提示
    showLoading(title = '加载中...') {
      wx.showLoading({
        title,
        mask: true
      });
    },

    // 隐藏加载提示
    hideLoading() {
      wx.hideLoading();
    },

    // 显示成功提示
    showSuccess(title, duration = 1500) {
      wx.showToast({
        title,
        icon: 'success',
        duration
      });
    },

    // 显示错误提示
    showError(title, duration = 2000) {
      wx.showToast({
        title,
        icon: 'none',
        duration
      });
    },

    // 确认对话框
    showConfirm(content, title = '提示') {
      return new Promise((resolve) => {
        wx.showModal({
          title,
          content,
          success(res) {
            resolve(res.confirm);
          },
          fail() {
            resolve(false);
          }
        });
      });
    },

    // 格式化时间
    formatTime(date) {
      if (!date) return '';
      
      const now = new Date();
      const target = new Date(date);
      const diff = now - target;
      
      // 1分钟内
      if (diff < 60000) {
        return '刚刚';
      }
      
      // 1小时内
      if (diff < 3600000) {
        return Math.floor(diff / 60000) + '分钟前';
      }
      
      // 今天
      if (now.toDateString() === target.toDateString()) {
        return target.toTimeString().substr(0, 5);
      }
      
      // 其他
      return target.toLocaleDateString();
    },
    
    // 防抖函数
    debounce(func, delay) {
      let timer = null;
      return function(...args) {
        if (timer) clearTimeout(timer);
        timer = setTimeout(() => func.apply(this, args), delay);
      };
    },
    
    // 节流函数
    throttle(func, delay) {
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

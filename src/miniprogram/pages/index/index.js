// pages/index/index.js - 情绪罗盘首页
const { postcardAPI, authAPI, envAPI } = require('../../utils/request.js');
const authUtil = require('../../utils/auth.js');
const { startPolling, POLLING_CONFIGS } = require('../../utils/task-polling.js');
const envConfig = require('../../config/env.js');

Page({
  data: {
    // 用户状态
    userInfo: null,
    hasUserInfo: false,
    
    // 背景装饰粒子
    particles: [],
    
    // 问候语和环境信息
    greetingText: '',
    currentDate: '',
    weatherInfo: '获取中...',
    
    // 环境信息获取状态
    environmentReady: false,
    locationPermissionGranted: false,
    
    // 今日卡片
    todayCard: null,
    cardFlipped: false,
    
    // 情绪墨迹
    needEmotionInput: false,
    emotionPath: null,
    isDrawing: false,
    
    // 生成状态
    isGenerating: false,
    loadingText: '正在感知你的情绪...',
    currentStep: 0,
    
    // 用户历史卡片
    userCards: []
  },

  onLoad(options) {
    envConfig.log('情绪罗盘启动', options);
    
    // 处理分享进入
    this.handleShareOptions(options);
    
    // 初始化页面
    this.initPage();
  },

  onShow() {
    // 刷新用户状态
    this.refreshUserStatus();
    
    // 检查是否有今日卡片
    if (this.data.hasUserInfo && !this.data.todayCard) {
      this.checkTodayCard();
    }
  },

  onHide() {
    // 页面隐藏时停止所有轮询任务
    const { stopAllPolling } = require('../../utils/task-polling.js');
    stopAllPolling();
    envConfig.log('页面隐藏，停止所有轮询任务');
  },

  onUnload() {
    // 页面卸载时停止所有轮询任务
    const { stopAllPolling } = require('../../utils/task-polling.js');
    stopAllPolling();
    envConfig.log('页面卸载，停止所有轮询任务');
  },

  /**
   * 初始化页面
   */
  async initPage() {
    // 生成背景粒子
    this.generateParticles();
    
    // 初始化Canvas
    this.initCanvas();
    
    // 设置当前时间
    this.setCurrentDate();
    
    // 获取位置和天气
    this.getLocationAndWeather();
    
    // 取消30秒降级：准确性优先，仅在拿到真实数据后置为就绪
    // 同时尝试读取预取缓存以缩短等待
    try {
      const cache = wx.getStorageSync('envCache');
      if (cache && cache.ts && (Date.now() - cache.ts) < 5 * 60 * 1000) {
        this.setData({
          userLocation: cache.location,
          cityName: cache.cityName || this.data.cityName,
          weatherInfo: cache.weatherInfo || this.data.weatherInfo
        });
      }
    } catch (e) {}
    
    // 检查用户状态
    this.checkUserStatus();
  },

  /**
   * 生成背景装饰粒子
   */
  generateParticles() {
    const particles = [];
    for (let i = 0; i < 15; i++) {
      particles.push({
        id: i,
        x: Math.random() * 100,
        y: Math.random() * 100,
        delay: Math.random() * 6
      });
    }
    this.setData({ particles });
  },

  /**
   * 初始化Canvas
   */
  initCanvas() {
    try {
      // 获取并缓存Canvas上下文，避免反复创建
      const ctx = wx.createCanvasContext('emotionCanvas');
      this.ctx = ctx;
      
      // 设置Canvas背景
      ctx.setFillStyle('#fafafa');
      ctx.fillRect(0, 0, 400, 300);
      ctx.draw();
      
      // 初始化绘制状态
      this.emotionPath = null;
      this.emotionAnalysis = null;
      
      envConfig.log('Canvas初始化成功');
    } catch (error) {
      envConfig.error('Canvas初始化失败:', error);
    }
  },

  /**
   * 设置当前日期和问候语
   */
  setCurrentDate() {
    const now = new Date();
    const hour = now.getHours();
    const date = now.toLocaleDateString('zh-CN', {
      month: 'long',
      day: 'numeric',
      weekday: 'long'
    });

    let greeting;
    if (hour < 6) {
      greeting = '夜深了，还在思考吗？';
    } else if (hour < 12) {
      greeting = '早安，新的一天开始了';
    } else if (hour < 18) {
      greeting = '午后的阳光很温暖';
    } else if (hour < 22) {
      greeting = '黄昏时分，适合回顾';
    } else {
      greeting = '夜晚静谧，心境如水';
    }

    this.setData({
      currentDate: date,
      greetingText: greeting
    });
  },

  /**
   * 获取地理位置和天气信息
   */
  async getLocationAndWeather() {
    try {
      // 首先检查位置权限
      const authSetting = await new Promise((resolve, reject) => {
        wx.getSetting({
          success: resolve,
          fail: reject
        });
      });

      let hasLocationAuth = authSetting.authSetting['scope.userLocation'];

      // 如果没有权限，先请求授权
      if (hasLocationAuth === false) {
        // 用户之前拒绝过，显示说明
        wx.showModal({
          title: '位置权限',
          content: '获取您的位置信息可以为您推荐当地相关的情绪内容，是否开启？',
          success: (res) => {
            if (res.confirm) {
              wx.openSetting({
                success: (settingRes) => {
                  if (settingRes.authSetting['scope.userLocation']) {
                    this.doGetLocation();
                  } else {
                    this.setDefaultWeather();
                  }
                }
              });
            } else {
              this.setDefaultWeather();
            }
          }
        });
        return;
      } else if (hasLocationAuth === undefined) {
        // 首次请求，直接尝试获取位置
        this.doGetLocation();
      } else {
        // 已有权限，直接获取
        this.doGetLocation();
      }

    } catch (error) {
      envConfig.error('检查位置权限失败:', error);
      this.setDefaultWeather();
    }
  },

  /**
   * 实际获取位置的方法
   */
  async doGetLocation() {
    try {
      // 为提升成功率：开启高精度并添加手动超时兜底（8秒）
      const location = await Promise.race([
        new Promise((resolve, reject) => {
          wx.getLocation({
            type: 'gcj02',
            isHighAccuracy: true,
            highAccuracyExpireTime: 3000,
            success: resolve,
            fail: reject
          });
        }),
        new Promise((_, reject) => setTimeout(() => reject(new Error('LOCATION_TIMEOUT')), 8000))
      ]);

      envConfig.log('获取位置成功:', location);
      
      // 保存位置信息
      const latitude = location.latitude;
      const longitude = location.longitude;
      this.setData({
        userLocation: { latitude, longitude }
      });

      // 并行获取城市与天气
      const { envAPI } = require('../../utils/request.js');
      const [cityRes, weatherRes] = await Promise.all([
        envAPI.reverseGeocode(latitude, longitude, 'zh'),
        envAPI.getWeather(latitude, longitude)
      ]);

      const cityName = (cityRes && (cityRes.city || cityRes.name)) || '';
      const weatherText = (weatherRes && weatherRes.weather_text) || this.data.weatherInfo;
      const temperature = weatherRes && weatherRes.temperature;
      const weatherInfo = typeof temperature === 'number' ? `${weatherText} · ${temperature}°C` : weatherText;

      this.setData({
        cityName,
        weatherInfo,
        environmentReady: true,  // 仅在真实数据返回后置为就绪
        locationPermissionGranted: true
      });

      envConfig.log('✅ 环境信息获取完成:', { cityName, weatherInfo });

      // 获取城市热点并写入灵感文案第一条
      try {
        const trendingRes = await envAPI.getTrending(cityName || '本地');
        const items = (trendingRes && trendingRes.items) || [];
        if (items.length > 0) {
          // 将最热标题插入 inspirations 第一位
          const inspirations = this.data.todayCard?.inspirations || [
            { icon: '🌍', text: `因为今天是${this.data.weatherInfo}` },
            { icon: '🎨', text: '你的情绪很独特' },
            { icon: '✨', text: '基于当下的热点话题' },
            { icon: '💫', text: '来自你的情绪墨迹' }
          ];
          inspirations[2] = { icon: '📰', text: items[0].title || '今日热点' };
          this.setData({
            todayCard: this.data.todayCard ? { ...this.data.todayCard, inspirations } : this.data.todayCard
          });
        }
      } catch (e) {
        // 静默降级
      }

    } catch (error) {
      envConfig.error('获取位置失败:', error);
      // 不降级：保持等待，由用户决定是否继续
      this.setData({
        environmentReady: false,
        locationPermissionGranted: false
      });
    }
  },

  /**
   * 设置默认天气信息
   */
  setDefaultWeather() {
    // 移除默认环境就绪逻辑：准确性优先，不设置为就绪
    this.setData({
      environmentReady: false
    });
    envConfig.log('保持等待真实环境信息，不使用默认降级');
  },

  /**
   * 检查用户状态
   */
  checkUserStatus() {
    // 从本地存储获取用户信息
    const userToken = wx.getStorageSync('userToken');
    const userInfo = wx.getStorageSync('userInfo');
    
    if (userToken && userInfo) {
      this.setData({
        userInfo: userInfo,
        hasUserInfo: true
      });
      
      // 设置个性化问候语
      const nickname = userInfo.nickname || userInfo.nickName || '';
      if (nickname) {
        this.setData({
          greetingText: `${nickname}，${this.data.greetingText}`
        });
      }
      
      // 加载用户历史卡片
      this.loadUserCards();
      
      // 检查今日卡片
      this.checkTodayCard();
    } else {
      this.setData({
        userInfo: null,
        hasUserInfo: false
      });
    }
  },

  /**
   * 刷新用户状态
   */
  refreshUserStatus() {
    const userToken = wx.getStorageSync('userToken');
    const userInfo = wx.getStorageSync('userInfo');
    
    this.setData({
      userInfo: userInfo,
      hasUserInfo: !!(userToken && userInfo)
    });
  },

  /**
   * 检查今日卡片
   */
  async checkTodayCard() {
    try {
      const today = new Date().toDateString();
      const response = await postcardAPI.getUserPostcards(this.data.userInfo.id, 1, 1);
      const cards = response.postcards || [];
      
      if (cards.length > 0) {
        const latestCard = cards[0];
        const cardDate = new Date(latestCard.created_at).toDateString();
        
        if (cardDate === today) {
          // 已有今日卡片，显示卡片
          this.setData({
            todayCard: this.formatCardData(latestCard),
            needEmotionInput: false
          });
        } else {
          // 需要创建今日卡片
          this.setData({
            needEmotionInput: true
          });
        }
      } else {
        // 首次使用，需要创建卡片
        this.setData({
          needEmotionInput: true
        });
      }
    } catch (error) {
      envConfig.error('检查今日卡片失败:', error);
      this.setData({
        needEmotionInput: true
      });
    }
  },

  /**
   * 格式化卡片数据
   */
  formatCardData(cardData) {
    return {
      id: cardData.id,
      date: new Date().toLocaleDateString('zh-CN'),
      keyword: cardData.concept || '今日心境',
      quote: cardData.content || '每一天都值得被温柔记录',
      english: 'Every day deserves to be gently remembered',
      music: {
        title: '推荐音乐',
        url: ''
      },
      movie: '推荐电影',
      book: '推荐书籍',
      inspirations: [
        { icon: '🌍', text: `因为今天是${this.data.weatherInfo}` },
        { icon: '🎨', text: '你的情绪很独特' },
        { icon: '✨', text: '基于当下的热点话题' },
        { icon: '💫', text: '来自你的情绪墨迹' }
      ]
    };
  },

  /**
   * 用户登录 - 必须在用户点击事件中直接调用
   */
  async handleLogin(e) {
    try {
      // 显示加载状态
      wx.showLoading({
        title: '登录中...',
        mask: true
      });

      // 1. 先获取用户信息授权（必须在用户点击事件中同步调用）
      const userProfile = await new Promise((resolve, reject) => {
        wx.getUserProfile({
          desc: '用于完善用户体验',
          success: resolve,
          fail: reject
        });
      });

      // 2. 再进行微信登录
      const loginResult = await new Promise((resolve, reject) => {
        wx.login({
          success: resolve,
          fail: reject
        });
      });

      // 3. 发送登录请求到后端
      const authResult = await authAPI.login(loginResult.code, userProfile.userInfo);

      // 4. 保存用户信息到本地存储
      wx.setStorageSync('userToken', authResult.token);
      wx.setStorageSync('userInfo', authResult.userInfo);
      if (authResult.refreshToken) {
        wx.setStorageSync('refreshToken', authResult.refreshToken);
      }
      
      this.setData({
        userInfo: authResult.userInfo,
        hasUserInfo: true
      });

      wx.hideLoading();
      wx.showToast({
        title: '登录成功',
        icon: 'success',
        duration: 1500
      });
      
      // 重新初始化页面
      this.checkUserStatus();
      
    } catch (error) {
      wx.hideLoading();
      
      if (error.errMsg && error.errMsg.includes('getUserProfile:fail auth deny')) {
        wx.showModal({
          title: '需要授权',
          content: '需要获取您的基本信息来提供个性化体验',
          showCancel: false
        });
      } else if (error.errMsg && error.errMsg.includes('getUserProfile:fail can only be invoked by user TAP gesture')) {
        wx.showModal({
          title: '提示',
          content: '请直接点击按钮进行登录',
          showCancel: false
        });
      } else {
        wx.showToast({
          title: error.message || '登录失败，请重试',
          icon: 'none',
          duration: 2000
        });
      }
      
      envConfig.error('登录失败:', error);
    }
  },

  /**
   * 情绪墨迹 - 开始绘制
   */
  onInkStart(e) {
    console.log('Canvas touch start', e);
    
    // 防止事件穿透
    e.preventDefault && e.preventDefault();
    
    if (!e.touches || e.touches.length === 0) {
      console.error('No touch data available');
      return;
    }
    
    this.setData({ isDrawing: true });
    
    const ctx = this.ctx || wx.createCanvasContext('emotionCanvas');
    this.ctx = ctx; // 缓存context以便后续使用
    const point = e.touches[0];
    
    // 使用黑色画笔，提升对比度并符合"黑色笔画"的需求
    ctx.setStrokeStyle('#000000');
    ctx.setLineWidth(4);
    ctx.setLineCap('round');
    ctx.setLineJoin('round');
    
    // 开始新的路径并移动到起始点
    ctx.beginPath();
    ctx.moveTo(point.x, point.y);
    
    this.emotionPath = [{
      x: point.x,
      y: point.y,
      time: Date.now()
    }];
    
    // 绘制起始点
    ctx.arc(point.x, point.y, 2, 0, 2 * Math.PI);
    ctx.fill();
    ctx.draw(true);
    
    envConfig.log('开始绘制情绪墨迹:', point);
  },

  /**
   * 情绪墨迹 - 绘制中
   */
  onInkMove(e) {
    if (!this.data.isDrawing) return;
    
    // 防止事件穿透
    e.preventDefault && e.preventDefault();
    
    if (!e.touches || e.touches.length === 0) {
      return;
    }
    
    if (!this.ctx) {
      this.ctx = wx.createCanvasContext('emotionCanvas');
      // 重新设置画笔属性
      this.ctx.setStrokeStyle('#000000');
      this.ctx.setLineWidth(4);
      this.ctx.setLineCap('round');
      this.ctx.setLineJoin('round');
    }
    
    const ctx = this.ctx;
    const point = e.touches[0];
    
    // 连续绘制：画线到当前点
    if (this.emotionPath && this.emotionPath.length > 0) {
      ctx.lineTo(point.x, point.y);
      ctx.stroke();
      ctx.draw(true);
      
      // 重新开始路径以便继续绘制
      ctx.beginPath();
      ctx.moveTo(point.x, point.y);
    }
    
    // 记录路径数据
    if (this.emotionPath) {
      this.emotionPath.push({
        x: point.x,
        y: point.y,
        time: Date.now()
      });
    }
  },

  /**
   * 情绪墨迹 - 结束绘制
   */
  onInkEnd(e) {
    console.log('Canvas touch end', e);
    
    if (this.data.isDrawing && this.ctx) {
      // 完成最后的绘制
      this.ctx.stroke();
      this.ctx.draw(true);
    }
    
    this.setData({ isDrawing: false });
    
    // 分析情绪墨迹
    this.analyzeEmotion();
    
    envConfig.log('结束绘制情绪墨迹，路径点数:', this.emotionPath ? this.emotionPath.length : 0);
  },

  /**
   * 分析情绪墨迹
   */
  analyzeEmotion() {
    if (!this.emotionPath || this.emotionPath.length < 2) return;
    
    // 简单的情绪分析算法
    const totalDistance = this.emotionPath.reduce((acc, point, index) => {
      if (index === 0) return 0;
      const prev = this.emotionPath[index - 1];
      return acc + Math.sqrt(Math.pow(point.x - prev.x, 2) + Math.pow(point.y - prev.y, 2));
    }, 0);
    
    const totalTime = this.emotionPath[this.emotionPath.length - 1].time - this.emotionPath[0].time;
    const speed = totalDistance / totalTime;
    
    // 根据绘制特征判断情绪
    let emotionType;
    if (speed > 0.5) {
      emotionType = 'energetic';
    } else if (totalDistance < 100) {
      emotionType = 'calm';
    } else {
      emotionType = 'thoughtful';
    }
    
    this.emotionAnalysis = {
      type: emotionType,
      distance: totalDistance,
      speed: speed,
      duration: totalTime
    };
    
    envConfig.log('情绪分析结果:', this.emotionAnalysis);
  },

  /**
   * 清空墨迹
   */
  clearInk() {
    const ctx = wx.createCanvasContext('emotionCanvas');
    ctx.clearRect(0, 0, 400, 300);
    ctx.draw();
    
    this.emotionPath = null;
    this.emotionAnalysis = null;
  },

  /**
   * 生成今日卡片
   */
  async generateDailyCard() {
    if (!this.emotionPath || this.emotionPath.length < 5) {
      wx.showModal({
        title: '提示',
        content: '请先画下你的情绪墨迹，让我感知你的今天',
        showCancel: false
      });
      return;
    }

    // 检查环境信息是否已获取完成
    if (!this.data.environmentReady) {
      // 显示等待提示
      wx.showLoading({
        title: '正在获取环境信息...',
        mask: true
      });
      
      try {
        // 等待环境信息获取完成，最多等待55秒（与后端/网关超时策略匹配）
        const maxWaitTime = 55000; // 55秒
        const checkInterval = 500;  // 500毫秒检查一次
        const startTime = Date.now();
        
        while (!this.data.environmentReady && (Date.now() - startTime) < maxWaitTime) {
          await new Promise(resolve => setTimeout(resolve, checkInterval));
        }
        
        wx.hideLoading();
        
        if (!this.data.environmentReady) {
          // 超时仍未获取到环境信息，询问用户是否继续
          const shouldContinue = await new Promise(resolve => {
            wx.showModal({
              title: '环境信息获取中',
              content: '位置和天气信息正在获取中，是否使用基础信息继续生成？',
              confirmText: '继续生成',
              cancelText: '等待完成',
              success: (res) => resolve(res.confirm),
              fail: () => resolve(false)
            });
          });
          
          if (!shouldContinue) {
            return; // 用户选择等待，退出生成
          }
        }
      } catch (error) {
        wx.hideLoading();
        envConfig.error('等待环境信息时出错:', error);
        // 发生错误时也询问用户是否继续
        const shouldContinue = await new Promise(resolve => {
          wx.showModal({
            title: '提示',
            content: '环境信息获取遇到问题，是否使用基础信息生成卡片？',
            success: (res) => resolve(res.confirm),
            fail: () => resolve(false)
          });
        });
        
        if (!shouldContinue) {
          return;
        }
      }
    }

    try {
      this.setData({ 
        isGenerating: true,
        currentStep: 0,
        loadingText: '正在感知你的情绪...'
      });

      // 模拟生成步骤
      setTimeout(() => {
        this.setData({ 
          currentStep: 1,
          loadingText: '分析环境与热点...'
        });
      }, 1000);

      setTimeout(() => {
        this.setData({ 
          currentStep: 2,
          loadingText: '创意构思中...'
        });
      }, 2000);

      setTimeout(() => {
        this.setData({ 
          currentStep: 3,
          loadingText: '魔法生成中...'
        });
      }, 3000);

      // 构建请求数据 - 智能环境感知与情绪分析
      // 获取热点话题用于AI创意生成
      let trendingTopics = '';
      try {
        const { envAPI } = require('../../utils/request.js');
        const cityName = this.data.cityName || '本地';
        const trendingRes = await envAPI.getTrending(cityName);
        const items = (trendingRes && trendingRes.items) || [];
        if (items.length > 0) {
          trendingTopics = items.slice(0, 3).map(item => item.title).join('、');
        }
      } catch (e) {
        // 热点获取失败，静默降级
        envConfig.log('热点获取失败，使用基础信息', e);
      }
      
      // 增强的环境感知信息
      const locationInfo = {
        city: this.data.cityName || '本地',
        weather: this.data.weatherInfo || '温和',
        coordinates: this.data.userLocation ? `${this.data.userLocation.latitude.toFixed(3)}, ${this.data.userLocation.longitude.toFixed(3)}` : '当前位置'
      };
      
      // 深度情绪分析
      const emotionAnalysis = this.emotionAnalysis || {};
      const emotionInfo = {
        type: emotionAnalysis.type || 'calm', // 情绪类型：energetic/calm/thoughtful
        intensity: this.getEmotionIntensity(emotionAnalysis), // 情绪强度：low/medium/high
        pattern: this.getEmotionPattern(emotionAnalysis), // 情绪模式：flowing/jagged/circular
        duration: emotionAnalysis.duration || 0, // 绘制时长
        complexity: this.getEmotionComplexity(emotionAnalysis) // 复杂度：simple/moderate/complex
      };
      
      // 时间上下文
      const now = new Date();
      const timeContext = {
        period: this.getTimePeriod(now.getHours()), // 时段：dawn/morning/afternoon/evening/night
        weekday: now.toLocaleDateString('zh-CN', { weekday: 'long' }),
        season: this.getSeason(now.getMonth() + 1)
      };
      
      // 构建丰富的AI提示
      const userInput = this.buildEnhancedPrompt(locationInfo, emotionInfo, timeContext, trendingTopics);

      const requestData = {
        user_input: userInput,
        user_id: this.data.userInfo.id,
        // 增强的主题信息，便于后端AI理解
        theme: emotionInfo.type,
        style: `emotion-compass-${emotionInfo.intensity}-${timeContext.period}`
      };

      // 发送生成请求
      const result = await postcardAPI.create(requestData);
      const { task_id } = result;
      
      // 保存任务ID以便错误处理时清理
      this.currentTaskId = task_id;
      envConfig.log('开始明信片生成任务:', task_id);

      // 开始轮询任务状态 - 使用AI生成专用配置，支持长时间任务
      const finalResult = await startPolling(task_id, {
        ...POLLING_CONFIGS.AI_GENERATION,
        onProgress: (progress) => {
          this.setData({
            loadingText: `生成进度: ${progress}%`
          });
        }
      });
      
      // 任务完成，清理任务ID
      this.currentTaskId = null;

      // 生成成功
      this.setData({
        isGenerating: false,
        needEmotionInput: false,
        todayCard: this.formatCardData(finalResult)
      });

      // 清空画布
      this.clearInk();

      // 刷新历史卡片
      this.loadUserCards();

      const app = getApp();
      app.utils.showSuccess('今日卡片生成完成！');

    } catch (error) {
      envConfig.error('生成卡片失败:', error);
      
      // 清理当前任务
      if (this.currentTaskId) {
        const { stopPolling } = require('../../utils/task-polling.js');
        stopPolling(this.currentTaskId);
        this.currentTaskId = null;
        envConfig.log('已清理失败的任务轮询');
      }
      
      this.setData({
        isGenerating: false
      });

      const app = getApp();
      app.utils.showError('生成失败，请重试');
    }
  },

  /**
   * 翻转卡片
   */
  flipCard() {
    this.setData({
      cardFlipped: !this.data.cardFlipped
    });
  },

  /**
   * 播放音乐
   */
  playMusic(e) {
    const { url } = e.currentTarget.dataset;
    if (url) {
      // 这里可以集成音乐播放功能
      wx.showToast({
        title: '播放音乐功能开发中',
        icon: 'none'
      });
    }
  },

  /**
   * 加载用户历史卡片
   */
  async loadUserCards() {
    if (!this.data.hasUserInfo) return;

    try {
      const response = await postcardAPI.getUserPostcards(this.data.userInfo.id, 1, 10);
      const cards = response.postcards || [];
      
      const formattedCards = cards.map(card => ({
        id: card.id,
        date: new Date(card.created_at).toLocaleDateString('zh-CN', {
          month: 'short',
          day: 'numeric'
        }),
        keyword: card.concept || '回忆',
        moodColor: this.getMoodColor(card.emotion_type)
      }));

      this.setData({
        userCards: formattedCards
      });

    } catch (error) {
      envConfig.error('加载历史卡片失败:', error);
    }
  },

  /**
   * 根据情绪类型获取颜色
   */
  getMoodColor(emotionType) {
    const colors = {
      'energetic': '#ff6b6b',
      'calm': '#4ecdc4',
      'thoughtful': '#45b7d1',
      'happy': '#feca57',
      'peaceful': '#a55eea'
    };
    return colors[emotionType] || '#74b9ff';
  },

  /**
   * 查看历史卡片
   */
  viewCard(e) {
    const { cardId } = e.currentTarget.dataset;
    wx.navigateTo({
      url: `/pages/postcard/postcard?id=${cardId}`
    });
  },

  /**
   * 处理分享参数
   */
  handleShareOptions(options) {
    const app = getApp();
    if (app.globalData.sharedPostcardId) {
      // 处理分享进入的情况
      wx.showModal({
        title: '分享卡片',
        content: '您通过分享链接进入，是否查看该卡片？',
        success: (res) => {
          if (res.confirm) {
            wx.navigateTo({
              url: `/pages/postcard/postcard?id=${app.globalData.sharedPostcardId}`
            });
          }
        }
      });
    }
  },

  /**
   * 分享功能
   */
  onShareAppMessage() {
    if (this.data.todayCard) {
      return {
        title: `我在情绪罗盘记录了今天的心情：${this.data.todayCard.keyword}`,
        path: `/pages/postcard/postcard?id=${this.data.todayCard.id}`,
        imageUrl: this.data.todayCard.image || ''
      };
    }
    
    return {
      title: '情绪罗盘 - 每一天，都值得被温柔记录',
      path: '/pages/index/index'
    };
  },

  /**
   * 分享到朋友圈
   */
  onShareTimeline() {
    return {
      title: '情绪罗盘 - 每一天，都值得被温柔记录',
      imageUrl: this.data.todayCard?.image || ''
    };
  },

  // ==================== 增强情绪分析工具方法 ====================

  /**
   * 获取情绪强度
   */
  getEmotionIntensity(analysis) {
    if (!analysis || !analysis.speed || !analysis.distance) return 'low';
    
    const speed = analysis.speed;
    const distance = analysis.distance;
    
    // 综合考虑速度和距离
    if (speed > 0.8 || distance > 500) return 'high';
    if (speed > 0.3 || distance > 150) return 'medium'; 
    return 'low';
  },

  /**
   * 获取情绪模式
   */
  getEmotionPattern(analysis) {
    if (!analysis || !analysis.distance || !analysis.duration) return 'flowing';
    
    const speed = analysis.speed || 0;
    const distance = analysis.distance || 0;
    const duration = analysis.duration || 1000;
    
    // 基于速度变化和轨迹特征判断模式
    const averageSpeed = distance / duration * 1000; // 像素/秒
    
    if (averageSpeed > 100) return 'jagged'; // 急促、锯齿状
    if (distance > 300 && duration > 3000) return 'circular'; // 长时间画圆
    return 'flowing'; // 流畅平滑
  },

  /**
   * 获取情绪复杂度
   */
  getEmotionComplexity(analysis) {
    if (!analysis || !analysis.distance) return 'simple';
    
    const distance = analysis.distance;
    const duration = analysis.duration || 1000;
    
    // 基于轨迹复杂度判断
    if (distance > 400 && duration > 4000) return 'complex';
    if (distance > 150 && duration > 2000) return 'moderate';
    return 'simple';
  },

  /**
   * 获取时段
   */
  getTimePeriod(hour) {
    if (hour < 6) return 'dawn'; // 凌晨
    if (hour < 12) return 'morning'; // 上午
    if (hour < 18) return 'afternoon'; // 下午
    if (hour < 22) return 'evening'; // 傍晚
    return 'night'; // 夜晚
  },

  /**
   * 获取季节
   */
  getSeason(month) {
    if (month >= 3 && month <= 5) return 'spring'; // 春天
    if (month >= 6 && month <= 8) return 'summer'; // 夏天
    if (month >= 9 && month <= 11) return 'autumn'; // 秋天
    return 'winter'; // 冬天
  },

  /**
   * 构建增强AI提示
   */
  buildEnhancedPrompt(locationInfo, emotionInfo, timeContext, trendingTopics) {
    const prompt = `心绪花开 - 智能情绪明信片生成

环境感知：
• 地理位置：${locationInfo.city}（${locationInfo.coordinates}）
• 天气状况：${locationInfo.weather}
• 时间背景：${timeContext.weekday} ${timeContext.period} (${timeContext.season})
${trendingTopics ? `• 当地热点：${trendingTopics}` : ''}

情绪分析：
• 情绪类型：${emotionInfo.type}（${this.getEmotionDescription(emotionInfo.type)}）
• 情绪强度：${emotionInfo.intensity}
• 表达模式：${emotionInfo.pattern}
• 情感复杂度：${emotionInfo.complexity}
• 表达时长：${Math.round(emotionInfo.duration / 1000)}秒

请基于以上信息生成一张个性化的动态明信片，要求：
1. 深度融合地理环境、天气状况和当地热点话题
2. 准确反映用户的情绪状态和表达方式
3. 结合时间背景营造恰当的氛围
4. 生成有趣、温暖、具有个人意义的内容
5. 包含互动元素和动画效果，适合微信小程序展示`;

    return prompt;
  },

  /**
   * 获取情绪类型描述
   */
  getEmotionDescription(emotionType) {
    const descriptions = {
      'energetic': '活跃充满活力',
      'calm': '平静内敛',
      'thoughtful': '深思熟虑',
      'happy': '愉悦开心',
      'peaceful': '宁静安详'
    };
    return descriptions[emotionType] || '独特的情绪状态';
  },

  /**
   * 手动重新获取环境信息
   */
  retryEnvironmentInfo() {
    envConfig.log('用户手动重试获取环境信息');
    
    // 重置环境状态
    this.setData({
      environmentReady: false,
      weatherInfo: '获取中...'
    });
    
    // 重新获取位置和天气
    this.getLocationAndWeather();
  },

  /**
   * 检查环境信息获取状态
   */
  checkEnvironmentStatus() {
    return {
      ready: this.data.environmentReady,
      hasLocation: this.data.locationPermissionGranted,
      city: this.data.cityName || '未知',
      weather: this.data.weatherInfo || '未知'
    };
  }
});
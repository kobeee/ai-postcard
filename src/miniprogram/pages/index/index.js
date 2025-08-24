// pages/index/index.js - 情绪罗盘首页
const { postcardAPI, authAPI } = require('../../utils/request.js');
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
      // 获取Canvas上下文
      const ctx = wx.createCanvasContext('emotionCanvas');
      
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
      const location = await new Promise((resolve, reject) => {
        wx.getLocation({
          type: 'gcj02',
          success: resolve,
          fail: reject
        });
      });

      envConfig.log('获取位置成功:', location);
      
      // 这里可以调用天气API获取天气信息
      // 模拟天气数据
      const weatherConditions = ['晴朗', '多云', '微风', '细雨', '暖阳', '清风'];
      const randomWeather = weatherConditions[Math.floor(Math.random() * weatherConditions.length)];
      
      this.setData({
        weatherInfo: randomWeather,
        userLocation: {
          latitude: location.latitude,
          longitude: location.longitude
        }
      });

    } catch (error) {
      envConfig.error('获取位置失败:', error);
      this.setDefaultWeather();
    }
  },

  /**
   * 设置默认天气信息
   */
  setDefaultWeather() {
    const defaultWeatherConditions = ['微风', '晴朗', '温和'];
    const randomWeather = defaultWeatherConditions[Math.floor(Math.random() * defaultWeatherConditions.length)];
    
    this.setData({
      weatherInfo: randomWeather + '（基于默认设置）'
    });
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
    
    const ctx = wx.createCanvasContext('emotionCanvas');
    const point = e.touches[0];
    
    ctx.setStrokeStyle('#667eea');
    ctx.setLineWidth(4);
    ctx.setLineCap('round');
    ctx.setLineJoin('round');
    
    ctx.beginPath();
    ctx.moveTo(point.x, point.y);
    
    this.emotionPath = [{
      x: point.x,
      y: point.y,
      time: Date.now()
    }];
    
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
    
    const ctx = wx.createCanvasContext('emotionCanvas');
    const point = e.touches[0];
    
    ctx.lineTo(point.x, point.y);
    ctx.stroke();
    ctx.draw(true);
    
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
    
    this.setData({ isDrawing: false });
    
    // 分析情绪墨迹
    this.analyzeEmotion();
    
    envConfig.log('结束绘制情绪墨迹');
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

      // 构建请求数据
      const requestData = {
        content: '今日情绪卡片生成',
        user_id: this.data.userInfo.id,
        emotion_analysis: this.emotionAnalysis,
        location: this.data.userLocation,
        weather: this.data.weatherInfo,
        timestamp: Date.now()
      };

      // 发送生成请求
      const result = await postcardAPI.create(requestData);
      const { task_id } = result;

      // 开始轮询任务状态
      const finalResult = await startPolling(task_id, {
        ...POLLING_CONFIGS.NORMAL,
        onProgress: (progress) => {
          this.setData({
            loadingText: `生成进度: ${progress}%`
          });
        }
      });

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
  }
});
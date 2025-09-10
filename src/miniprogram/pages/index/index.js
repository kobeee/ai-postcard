// pages/index/index.js - 情绪罗盘首页
const { postcardAPI, authAPI, envAPI } = require('../../utils/enhanced-request.js');
const { enhancedAuthManager: authUtil } = require('../../utils/enhanced-auth.js');
const { startPolling, POLLING_CONFIGS } = require('../../utils/task-polling.js');
const { parseCardData } = require('../../utils/data-parser.js');
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
    userCards: [],
    // 调试浮层受控开关（默认关闭）
    envDebug: false,
    showDebug: false,
    
    // 用户信息设置UI已移除，改为直接微信授权
    showProfileSetup: false,
    tempAvatarUrl: '',
    tempNickname: '',
    canCompleteSetup: false
  },

  onLoad(options) {
    envConfig.log('情绪罗盘启动', options);
    // 初始化调试标志（仅开发环境可开启）
    this.setData({ envDebug: !!envConfig.debug, showDebug: false });
    
    // 处理分享进入
    this.handleShareOptions(options);
    
    // 初始化页面
    this.initPage();
  },

  onShow() {
    // 刷新用户状态
    this.refreshUserStatus();
    
    // 若从删除返回并被标记为重置，则清理今日卡片并回到画布
    try {
      const app = getApp();
      if (app.globalData && app.globalData.resetToCanvas) {
        app.globalData.resetToCanvas = false;
        // 清空今日卡片并重新初始化画布
        this.setData({ todayCard: null, needEmotionInput: true, cardFlipped: false });
        this.clearInk();
        this.initCanvas();
        // 刷新记忆画廊
        this.loadUserCards();
        // 跳过本次配额检查，直接展示画布
        return;
      }
    } catch (_) {}
    
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
      greeting = '夜深了，记录今天的心情。';
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
      const { envAPI } = require('../../utils/enhanced-request.js');
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
      // 增强用户信息处理逻辑
      const enhancedUserInfo = this.processUserInfo(userInfo);
      
      this.setData({
        userInfo: enhancedUserInfo,
        hasUserInfo: true
      });
      
      // 设置个性化问候语 - 优化昵称获取逻辑
      const nickname = this.getUserNickname(enhancedUserInfo);
      if (nickname && nickname !== '微信用户') {
        const baseGreeting = this.data.greetingText.replace(/^.*，/, ''); // 移除现有昵称
        this.setData({
          greetingText: `${nickname}，${baseGreeting}`
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
   * 处理用户信息，确保包含必要字段
   */
  processUserInfo(userInfo) {
    if (!userInfo) return null;
    
    // 确保头像URL字段统一，提供默认头像
    const avatarUrl = userInfo.avatarUrl || userInfo.avatar_url || userInfo.headimgurl || this.getDefaultAvatarUrl();
    
    // 确保昵称字段统一
    const nickName = userInfo.nickName || userInfo.nickname || userInfo.nick_name || '';
    
    return {
      ...userInfo,
      avatarUrl: avatarUrl,
      nickName: nickName,
      // 兼容性字段
      avatar_url: avatarUrl,
      nickname: nickName
    };
  },

  /**
   * 获取用户昵称
   */
  getUserNickname(userInfo) {
    if (!userInfo) return '';
    
    // 按优先级尝试不同的昵称字段
    const possibleNicknames = [
      userInfo.nickName,      // 微信小程序标准字段
      userInfo.nickname,      // 后端可能转换的字段
      userInfo.nick_name,     // 下划线格式
      userInfo.name,          // 通用name字段
      userInfo.displayName,   // 显示名称
      userInfo.userName       // 用户名
    ];
    
    for (const name of possibleNicknames) {
      if (name && typeof name === 'string' && name.trim() !== '' && name !== '微信用户') {
        return name.trim();
      }
    }
    
    return ''; // 如果都没有有效昵称，返回空字符串
  },

  /**
   * 获取默认头像 URL
   */
  getDefaultAvatarUrl() {
    // 返回一个默认头像或者使用 base64 编码的默认头像
    return 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjQiIGhlaWdodD0iNjQiIHZpZXdCb3g9IjAgMCA2NCA2NCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGNpcmNsZSBjeD0iMzIiIGN5PSIzMiIgcj0iMzIiIGZpbGw9IiNGNUY1RjUiLz4KPGNpcmNsZSBjeD0iMzIiIGN5PSIyNCIgcj0iMTAiIGZpbGw9IiNEOUQ5RDkiLz4KPHBhdGggZD0iTTEyIDUyQzEyIDQ0IDIwIDM4IDMyIDM4UzUyIDQ0IDUyIDUyIiBzdHJva2U9IiNEOUQ5RDkiIHN0cm9rZS13aWR0aD0iNCIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIi8+Cjwvc3ZnPgo=';
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
   * 检查今日卡片状态 - 基于配额系统
   */
  async checkTodayCard() {
    try {
      // 确保用户已登录且有有效的用户信息
      if (!this.data.userInfo || !this.data.userInfo.id) {
        envConfig.warn('用户未登录，跳过配额检查');
        this.setData({
          needEmotionInput: false,  // 未登录时不显示画布，引导登录
          todayCard: null
        });
        return;
      }
      
      // 🔥 检查token是否存在，避免401错误
      const token = wx.getStorageSync('userToken');
      if (!token) {
        envConfig.warn('用户token不存在，跳过配额检查');
        this.setData({
          needEmotionInput: false,  // 无token时不显示画布，引导重新登录
          todayCard: null
        });
        return;
      }
      
      const userId = this.data.userInfo.id;
      
      // 🔥 使用配额API检查状态
      const quotaInfo = await postcardAPI.getUserQuota(userId);
      
      if (quotaInfo.current_card_exists) {
        // 当前有今日卡片，获取并显示
        const response = await postcardAPI.getUserPostcards(userId, 1, 1);
        const cards = response.postcards || [];
        
        if (cards.length > 0) {
          const latestCard = cards[0];
          this.setData({
            todayCard: this.formatCardData(latestCard),
            needEmotionInput: false  // 不显示画布
          });
        } else {
          // 配额显示有卡片但实际没有，可能数据不一致，显示画布
          this.setData({
            needEmotionInput: quotaInfo.should_show_canvas
          });
        }
      } else {
        // 当前没有今日卡片，根据should_show_canvas决定显示
        this.setData({
          needEmotionInput: quotaInfo.should_show_canvas,
          todayCard: null
        });
      }
      
      envConfig.log('今日卡片状态检查:', {
        current_card_exists: quotaInfo.current_card_exists,
        should_show_canvas: quotaInfo.should_show_canvas,
        generated_count: quotaInfo.generated_count,
        remaining_quota: quotaInfo.remaining_quota
      });
      
    } catch (error) {
      envConfig.error('检查今日卡片失败:', error);
      
      // 🔥 如果是401错误，清理过期token并引导重新登录
      if (error.statusCode === 401 || error.code === 401) {
        envConfig.warn('Token已过期，清理认证信息');
        wx.removeStorageSync('userToken');
        wx.removeStorageSync('refreshToken');
        wx.removeStorageSync('userInfo');
        
        // 🔥 同步清理enhancedAuthManager状态
        try {
          const { enhancedAuthManager } = require('../../utils/enhanced-auth.js');
          await enhancedAuthManager.clearAuth();
          envConfig.log('✅ 已同步清理enhancedAuthManager状态');
        } catch (error) {
          envConfig.error('同步清理认证状态失败:', error);
        }
        
        this.setData({
          userInfo: null,
          hasUserInfo: false,
          needEmotionInput: false,  // 不显示画布，引导重新登录
          todayCard: null
        });
        return;
      }
      
      // 其他错误时默认显示画布
      this.setData({
        needEmotionInput: true,
        todayCard: null
      });
    }
  },

  /**
   * 格式化卡片数据 - 使用统一的数据解析逻辑
   */
  formatCardData(cardData) {
    try {
      envConfig.log('开始格式化卡片数据:', cardData);
      
      // 确保cardData是对象而不是字符串
      if (typeof cardData === 'string') {
        try {
          cardData = JSON.parse(cardData);
        } catch (parseError) {
          envConfig.error('cardData是无效的JSON字符串:', parseError);
          return this.getDefaultCardData();
        }
      }
      
      if (!cardData || typeof cardData !== 'object') {
        envConfig.error('cardData格式无效:', cardData);
        return this.getDefaultCardData();
      }
      
      // 🔧 使用统一的数据解析逻辑
      const parseResult = parseCardData(cardData);
      const structuredData = parseResult.structuredData;
      
      // 初始化基础数据，从解析结果中提取
      let mainText = '每一天都值得被温柔记录';
      let englishQuote = 'Every day deserves to be gently remembered';
      let keyword = '今日心境';
      let recommendations = {};
      
      // 如果有结构化数据，使用结构化数据
      if (structuredData) {
        // 提取主要内容
        if (structuredData.content) {
          if (structuredData.content.main_text) {
            mainText = structuredData.content.main_text;
          }
          // 提取英文引用
          if (structuredData.content.quote && structuredData.content.quote.text) {
            englishQuote = structuredData.content.quote.text;
          }
        }
        
        // 提取标题
        if (structuredData.title) {
          keyword = structuredData.title;
        }
        
        // 提取推荐内容
        if (structuredData.recommendations) {
          recommendations = structuredData.recommendations;
        }
        
        // 更新原始数据
        cardData.structured_data = structuredData;
      } else {
        // 降级处理：从原始字段提取
        if (cardData.content && typeof cardData.content === 'string') {
          mainText = cardData.content;
        }
        if (cardData.concept && typeof cardData.concept === 'string') {
          keyword = cardData.concept;
        }
      }
      
      // 构建最终数据 - 只包含模板实际使用的字段，提升性能
      const result = {
        id: cardData.id || Date.now().toString(),
        date: new Date().toLocaleDateString('zh-CN', {
          month: 'long',
          day: 'numeric',  
          weekday: 'long'
        }),
        keyword: keyword,
        quote: mainText,
        english: englishQuote,
        // 只保留模板中实际使用的图片字段
        image: cardData.card_image_url || cardData.image_url || '',
        // 结构化数据用于组件判断
        structured_data: cardData.structured_data || null,
        // 预处理推荐内容显示状态
        hasRecommendations: !!(
          (recommendations.music && recommendations.music.length > 0) ||
          (recommendations.book && recommendations.book.length > 0) ||
          (recommendations.movie && recommendations.movie.length > 0)
        ),
        // 动态布局/动效：从结构化里读取提示或根据情绪强度推断
        layout_mode: (cardData.structured_data && cardData.structured_data.visual && cardData.structured_data.visual.style_hints && (
          cardData.structured_data.visual.style_hints.layout_style === 'minimal' ? 'layout-compact' : (
          cardData.structured_data.visual.style_hints.layout_style === 'rich' ? 'layout-rich' : 'layout-standard'
        ))) || 'layout-standard',
        motion: (cardData.structured_data && cardData.structured_data.visual && cardData.structured_data.visual.style_hints && cardData.structured_data.visual.style_hints.animation_type) || 'float',
        
        // 推荐内容 - 只在有数据时创建对象，减少内存占用
        music: recommendations.music ? {
          title: recommendations.music.title || '轻松愉快的音乐',
          artist: recommendations.music.artist || '推荐歌手'
        } : null,
        book: recommendations.book ? {
          title: recommendations.book.title || '温暖的书籍', 
          author: recommendations.book.author || '推荐作者'
        } : null,
        movie: recommendations.movie ? {
          title: recommendations.movie.title || '治愈系电影',
          director: recommendations.movie.director || '推荐导演'
        } : null
      };
      
      envConfig.log('格式化完成的卡片数据:', result);
      return result;
      
    } catch (error) {
      envConfig.error('格式化卡片数据时发生错误:', error);
      return this.getDefaultCardData();
    }
  },

  /**
   * 从混合文本中提取 JSON 对象（支持 ```json 包裹或带前后缀的情况）
   */
  extractJsonFromText(text) {
    if (!text || typeof text !== 'string') return null;
    try {
      // 1) 优先解析 ```json ... ``` 代码块
      const block = text.match(/```json\s*([\s\S]*?)\s*```/i);
      if (block && block[1]) {
        return JSON.parse(block[1]);
      }

      // 2) 退化：在整段文本中寻找首个完整的花括号JSON对象
      const cleaned = text.replace(/```/g, '');
      const firstBrace = cleaned.indexOf('{');
      if (firstBrace !== -1) {
        // 使用栈匹配，找到与首个 { 对应的 }
        let depth = 0;
        for (let i = firstBrace; i < cleaned.length; i++) {
          const ch = cleaned[i];
          if (ch === '{') depth++;
          else if (ch === '}') {
            depth--;
            if (depth === 0) {
              const jsonStr = cleaned.substring(firstBrace, i + 1);
              return JSON.parse(jsonStr);
            }
          }
        }
      }
      return null;
    } catch (e) {
      return null;
    }
  },

  /**
   * 将解析出的对象映射为组件可用的结构化数据
   */
  buildStructuredFromParsed(parsed) {
    if (!parsed || typeof parsed !== 'object') return null;
    const title = parsed['主标题'] || parsed['标题'] || parsed.title || '今日心境';
    const subtitle = parsed['副标题'] || parsed.subtitle || '';
    const main = parsed['正文内容'] || parsed['正文'] || parsed.content || '';
    const english = parsed['英文'] || parsed['英文引用'] || parsed.english || '';

    const structured = {
      title,
      content: {
        main_text: main,
        subtitle: subtitle || undefined,
        quote: english ? { text: english } : undefined
      },
      visual: {
        style_hints: {
          color_scheme: ['#6366f1', '#8b5cf6'],
          layout_style: 'artistic',
          animation_type: 'float'
        }
      },
      context: {
        location: this.data.cityName || '当前位置',
        weather: this.data.weatherInfo || ''
      }
    };
    return structured;
  },
  
  /**
   * 获取默认卡片数据 - 性能优化版本
   */
  getDefaultCardData() {
    return {
      id: Date.now().toString(),
      date: new Date().toLocaleDateString('zh-CN', {
        month: 'long',
        day: 'numeric',
        weekday: 'long'
      }),
      keyword: '今日心境',
      quote: '每一天都值得被温柔记录',
      english: 'Every day deserves to be gently remembered',
      image: '',
      structured_data: null,
      // 新增动态布局与动效配置（默认）
      layout_mode: 'layout-standard', // layout-standard | layout-compact | layout-rich
      motion: 'float', // float | pulse | gradient
      // 默认推荐内容设为null，减少不必要的对象创建
      music: null,
      book: null,
      movie: null
    };
  },


  /**
   * 快速登录 - 使用openid登录，不获取用户信息
   */
  async handleQuickLogin() {
    try {
      wx.showLoading({ title: '登录中...', mask: true });

      // 1. 获取微信登录code
      const loginResult = await new Promise((resolve, reject) => {
        wx.login({ success: resolve, fail: reject });
      });

      // 2. 发送到后端进行认证（不传真实用户信息，只传基础信息）
      const basicUserInfo = {
        nickName: '微信用户',
        avatarUrl: '',
        // 标记这是快速登录
        _isQuickLogin: true
      };
      const authResult = await authAPI.login(loginResult.code, basicUserInfo);

      // 3. 保存认证信息
      wx.setStorageSync('userToken', authResult.token);
      wx.setStorageSync('userInfo', authResult.userInfo);
      if (authResult.refreshToken) {
        wx.setStorageSync('refreshToken', authResult.refreshToken);
      }
      
      // 🔥 关键修复：更新enhancedAuthManager的token状态
      try {
        const { enhancedAuthManager } = require('../../utils/enhanced-auth.js');
        await enhancedAuthManager.restoreAuthState();
        envConfig.log('✅ 已同步认证状态到enhancedAuthManager');
      } catch (error) {
        envConfig.error('同步认证状态失败:', error);
      }

      // 直接设置用户信息（不再引导完善资料）
      const enhancedUserInfo = this.processUserInfo(authResult.userInfo);
      this.setData({
        userInfo: enhancedUserInfo,
        hasUserInfo: true,
        showProfileSetup: false
      });
      this.checkUserStatus();

      wx.hideLoading();

    } catch (error) {
      wx.hideLoading();
      wx.showToast({
        title: error.message || '登录失败，请重试',
        icon: 'none',
        duration: 2000
      });
      envConfig.error('快速登录失败:', error);
    }
  },

  /**
   * 点击头像更换 - 简化版
   */
  async onChooseAvatar(e) {
    const { avatarUrl } = e.detail || {};
    if (!avatarUrl) return;
    
    envConfig.log('用户选择新头像:', avatarUrl);
    
    try {
      // 直接更新用户信息中的头像
      const updatedUserInfo = {
        ...this.data.userInfo,
        avatarUrl: avatarUrl,
        avatar_url: avatarUrl
      };
      
      // 更新页面显示
      this.setData({
        userInfo: updatedUserInfo
      });
      
      // 保存到本地存储
      wx.setStorageSync('userInfo', updatedUserInfo);
      
      wx.showToast({
        title: '头像更新成功',
        icon: 'success',
        duration: 1500
      });
      
    } catch (error) {
      envConfig.error('更新头像失败:', error);
      wx.showToast({
        title: '头像更新失败',
        icon: 'none'
      });
    }
  },

  /**
   * 昵称输入回调 - 保留但不使用
   */
  onNicknameInput(e) {
    // 保留方法，但不再使用
    envConfig.log('昵称输入事件(已禁用):', e.detail?.value);
  },

  /**
   * 简化版完成设置 - 不再使用
   */
  async completeProfileSetup() {
    // 保留方法，但不再使用
    wx.showToast({ title: '请使用快速登录', icon: 'none' });
  },

  /**
   * 旧版登录方法 - 已废弃，保留仅供兼容
   */
  async handleLogin(e) {
    // 提示用户使用新版登录方式
    wx.showModal({
      title: '登录方式已更新',
      content: '请使用“设置头像昵称”按钮进行完整登录，或点击“快速体验”直接开始使用。',
      confirmText: '知道了',
      showCancel: false
    });
  },

  /**
   * 情绪墨迹 - 开始绘制
   */
  onInkStart(e) {
    // 防止事件穿透
    e.preventDefault && e.preventDefault();
    
    if (!e.touches || e.touches.length === 0) {
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
    this.emotionImagePath = null;
  },
  
  /**
   * 获取canvas的base64数据
   */
  async getCanvasBase64Data() {
    try {
      envConfig.log('开始获取canvas的base64数据...');
      
      return new Promise((resolve, reject) => {
        wx.canvasToTempFilePath({
          canvasId: 'emotionCanvas',
          success: (res) => {
            const tempFilePath = res.tempFilePath;
            envConfig.log('Canvas转临时文件成功:', tempFilePath);
            
            // 读取文件并转换为base64
            const fs = wx.getFileSystemManager();
            fs.readFile({
              filePath: tempFilePath,
              encoding: 'base64',
              success: (readResult) => {
                const base64Data = readResult.data;
                envConfig.log('Canvas转base64成功，数据长度:', base64Data.length);
                resolve({
                  base64: base64Data,
                  format: 'png',
                  size: base64Data.length * 3 / 4 // 估算文件大小
                });
              },
              fail: (readError) => {
                envConfig.error('读取临时文件失败:', readError);
                reject(new Error('读取canvas图片数据失败'));
              }
            });
          },
          fail: (error) => {
            envConfig.error('Canvas转临时文件失败:', error);
            reject(new Error(`Canvas转图片失败: ${error.errMsg || error.message || '未知错误'}`));
          }
        });
      });
      
    } catch (error) {
      envConfig.error('获取canvas base64数据过程中出错:', error);
      throw error;
    }
  },
  
  /**
   * 上传base64图片数据到服务器
   */
  async uploadEmotionImageBase64(imageData) {
    try {
      envConfig.log('开始上传情绪图片base64数据到服务器，数据大小:', imageData.size);
      
      // 获取用户token
      const userToken = wx.getStorageSync('userToken');
      if (!userToken) {
        throw new Error('用户未登录');
      }
      
      return new Promise((resolve, reject) => {
        wx.request({
          url: envConfig.getApiUrl('/upload/emotion-image-base64'),
          method: 'POST',
          header: {
            'Authorization': `Bearer ${userToken}`,
            'Content-Type': 'application/json'
          },
          data: {
            image_base64: imageData.base64,
            format: imageData.format,
            size: imageData.size
          },
          success: (res) => {
            try {
              envConfig.log('上传响应状态码:', res.statusCode);
              envConfig.log('上传响应数据:', res.data);
              
              if (res.statusCode !== 200) {
                reject(new Error(`HTTP ${res.statusCode}: ${JSON.stringify(res.data) || '服务器错误'}`));
                return;
              }
              
              const data = res.data;
              if (data.success) {
                envConfig.log('情绪图片base64上传成功:', data.data);
                resolve(data.data);
              } else {
                envConfig.error('情绪图片上传失败:', data.message);
                reject(new Error(data.message || '上传失败'));
              }
            } catch (e) {
              envConfig.error('解析上传响应失败:', e, res);
              reject(new Error(`服务器响应异常: ${JSON.stringify(res.data)}`));
            }
          },
          fail: (error) => {
            envConfig.error('情绪图片上传网络失败:', error);
            reject(new Error(`网络请求失败: ${error.errMsg || error.message || '未知错误'}`));
          }
        });
      });
      
    } catch (error) {
      envConfig.error('上传情绪图片过程中出错:', error);
      throw error;
    }
  },

  /**
   * 分析绘画轨迹数据，提供详细的绘制特征分析
   */
  analyzeDrawingTrajectory() {
    if (!this.emotionPath || this.emotionPath.length < 2) {
      return {
        stroke_count: 0,
        drawing_time: 0,
        average_speed: 0,
        complexity: 'none',
        direction_changes: 0,
        pressure_variation: 'steady',
        pattern_type: 'undefined',
        emotion_indicators: []
      };
    }

    const path = this.emotionPath;
    const totalPoints = path.length;
    const totalTime = path[totalPoints - 1].time - path[0].time;
    
    // 计算总路径长度
    let totalDistance = 0;
    let directionChanges = 0;
    let speeds = [];
    
    for (let i = 1; i < totalPoints; i++) {
      const prev = path[i - 1];
      const curr = path[i];
      const distance = Math.sqrt(Math.pow(curr.x - prev.x, 2) + Math.pow(curr.y - prev.y, 2));
      const timeInterval = curr.time - prev.time;
      
      totalDistance += distance;
      
      if (timeInterval > 0) {
        speeds.push(distance / timeInterval);
      }
      
      // 检测方向变化
      if (i > 1) {
        const prevPrev = path[i - 2];
        const angle1 = Math.atan2(prev.y - prevPrev.y, prev.x - prevPrev.x);
        const angle2 = Math.atan2(curr.y - prev.y, curr.x - prev.x);
        const angleDiff = Math.abs(angle2 - angle1);
        
        if (angleDiff > Math.PI / 4) { // 45度以上的方向变化
          directionChanges++;
        }
      }
    }
    
    const averageSpeed = speeds.length > 0 ? speeds.reduce((a, b) => a + b, 0) / speeds.length : 0;
    const speedVariance = speeds.length > 0 ? speeds.reduce((acc, speed) => acc + Math.pow(speed - averageSpeed, 2), 0) / speeds.length : 0;
    
    // 分析绘制模式
    let patternType = 'undefined';
    let complexity = 'simple';
    let emotionIndicators = [];
    
    // 根据统计数据推断绘制模式和情绪
    const normalizedDistance = totalDistance / 100; // 标准化距离
    const normalizedTime = totalTime / 1000; // 转换为秒
    
    // 模式分析
    if (directionChanges < totalPoints * 0.1) {
      patternType = 'smooth_flow';  // 平滑流畅
    } else if (directionChanges > totalPoints * 0.3) {
      patternType = 'chaotic';      // 混乱多变
    } else {
      patternType = 'moderate';     // 适中
    }
    
    // 复杂度分析
    if (totalPoints > 50 && directionChanges > 10) {
      complexity = 'complex';
    } else if (totalPoints > 20 || directionChanges > 5) {
      complexity = 'moderate';
    }
    
    // 情绪指标分析
    if (averageSpeed > 2) {
      emotionIndicators.push('energetic');
    }
    if (speedVariance > 1) {
      emotionIndicators.push('unstable_pace');
    }
    if (totalTime > 10000) { // 超过10秒
      emotionIndicators.push('contemplative');
    }
    if (directionChanges / totalPoints > 0.3) {
      emotionIndicators.push('restless');
    }
    if (normalizedDistance < 2) {
      emotionIndicators.push('concentrated');
    }
    
    return {
      stroke_count: 1, // 当前实现为单笔画
      drawing_time: totalTime,
      total_distance: totalDistance,
      average_speed: averageSpeed,
      speed_variance: speedVariance,
      complexity: complexity,
      direction_changes: directionChanges,
      direction_change_rate: directionChanges / totalPoints,
      pressure_variation: speedVariance > 1 ? 'varied' : 'steady',
      pattern_type: patternType,
      emotion_indicators: emotionIndicators,
      point_count: totalPoints,
      // 提供给AI的文本描述
      drawing_description: this.generateDrawingDescription(
        patternType, complexity, averageSpeed, totalTime, emotionIndicators
      )
    };
  },

  /**
   * 生成绘画描述供AI理解
   */
  generateDrawingDescription(patternType, complexity, averageSpeed, totalTime, emotionIndicators) {
    let description = [];
    
    // 绘制风格描述
    const patternMap = {
      'smooth_flow': '绘制流畅平滑，笔触连贯',
      'chaotic': '绘制多变混乱，频繁转向',
      'moderate': '绘制节奏适中，有张有弛'
    };
    description.push(patternMap[patternType] || '绘制风格未明');
    
    // 复杂度描述
    const complexityMap = {
      'simple': '线条简单',
      'moderate': '线条中等复杂',
      'complex': '线条复杂多变'
    };
    description.push(complexityMap[complexity]);
    
    // 速度描述
    if (averageSpeed > 3) {
      description.push('绘制速度很快');
    } else if (averageSpeed > 1) {
      description.push('绘制速度适中');
    } else {
      description.push('绘制速度缓慢');
    }
    
    // 时长描述
    if (totalTime > 15000) {
      description.push('绘制时间很长，显示深思');
    } else if (totalTime > 5000) {
      description.push('绘制时间适中');
    } else {
      description.push('绘制时间较短');
    }
    
    // 情绪指标描述
    if (emotionIndicators.includes('energetic')) {
      description.push('显示精力充沛');
    }
    if (emotionIndicators.includes('contemplative')) {
      description.push('体现深思状态');
    }
    if (emotionIndicators.includes('restless')) {
      description.push('表现内心不安');
    }
    if (emotionIndicators.includes('concentrated')) {
      description.push('显示专注集中');
    }
    
    return description.join('，');
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

    // 🔥 检查用户生成配额
    try {
      const app = getApp();
      const userId = this.data.userInfo && this.data.userInfo.id;
      if (!userId) {
        wx.showModal({
          title: '需要登录',
          content: '请先登录以便检查生成配额',
          showCancel: false
        });
        return;
      }
      
      // 🔥 检查token是否存在
      const token = wx.getStorageSync('userToken');
      if (!token) {
        wx.showModal({
          title: '需要重新登录',
          content: '请先重新登录以便检查生成配额',
          showCancel: false
        });
        return;
      }
      
      wx.showLoading({
        title: '检查生成次数...',
        mask: true
      });
      
      const quotaInfo = await postcardAPI.getUserQuota(userId);
      wx.hideLoading();
      
      if (!quotaInfo.can_generate) {
        wx.showModal({
          title: '生成次数已用完',
          content: quotaInfo.message,
          confirmText: '我知道了',
          showCancel: false
        });
        return;
      }
      
      // 显示配额提示
      if (quotaInfo.remaining_quota <= 1) {
        const shouldContinue = await new Promise(resolve => {
          wx.showModal({
            title: '生成提醒',
            content: `${quotaInfo.message}，确定要生成吗？`,
            confirmText: '确定生成',
            cancelText: '暂不生成',
            success: (res) => resolve(res.confirm),
            fail: () => resolve(false)
          });
        });
        
        if (!shouldContinue) {
          return;
        }
      }
      
    } catch (error) {
      wx.hideLoading();
      envConfig.error('检查配额失败:', error);
      
      // 🔥 如果是401错误，清理过期token并引导重新登录
      if (error.statusCode === 401 || error.code === 401) {
        envConfig.warn('Token已过期，清理认证信息');
        wx.removeStorageSync('userToken');
        wx.removeStorageSync('refreshToken');
        wx.removeStorageSync('userInfo');
        
        // 🔥 同步清理enhancedAuthManager状态
        try {
          const { enhancedAuthManager } = require('../../utils/enhanced-auth.js');
          await enhancedAuthManager.clearAuth();
          envConfig.log('✅ 已同步清理enhancedAuthManager状态');
        } catch (error) {
          envConfig.error('同步清理认证状态失败:', error);
        }
        
        this.setData({
          userInfo: null,
          hasUserInfo: false
        });
        
        wx.showModal({
          title: '需要重新登录',
          content: '登录状态已过期，请重新登录后再生成卡片',
          showCancel: false,
          confirmText: '我知道了'
        });
        return;
      }
      
      // 其他配额检查失败时不阻断用户操作，显示警告即可
      wx.showToast({
        title: '配额检查失败，将继续生成',
        icon: 'none',
        duration: 2000
      });
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
      // Step 1: 获取情绪墨迹的base64数据（直接传给生成接口）
      // 注意：为避免原生 canvas 层级遮挡加载层，先完成截图再进入生成状态
      let emotionImageBase64 = null;
      try {
        // 检查是否有绘制内容
        if (!this.emotionPath || this.emotionPath.length < 5) {
          envConfig.log('没有足够的绘制内容，跳过图片处理');
        } else {
          // 先行截图，完成后再显示加载遮罩
          const imageData = await this.getCanvasBase64Data();
          const fmt = (imageData && imageData.format) ? imageData.format : 'png';
          emotionImageBase64 = `data:image/${fmt};base64,${imageData.base64}`;
          envConfig.log('情绪墨迹base64数据提取成功，数据长度:', emotionImageBase64.length);
        }
      } catch (imageError) {
        envConfig.warn('情绪图片数据提取失败，继续使用轨迹分析:', imageError);
        // 图片处理失败不影响卡片生成，继续使用传统的轨迹分析
      }

      // 开始显示生成遮罩（此时画布已完成截图且会被隐藏，不会遮挡）
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
        const { envAPI } = require('../../utils/enhanced-request.js');
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
      
      // 分析绘画轨迹数据
      const drawingAnalysis = this.analyzeDrawingTrajectory();

      const requestData = {
        user_input: userInput,
        user_id: this.data.userInfo.id,
        // 增强的主题信息，便于后端AI理解
        theme: emotionInfo.type,
        style: `emotion-compass-${emotionInfo.intensity}-${timeContext.period}`,
        // 添加绘画轨迹分析数据
        drawing_data: {
          trajectory: this.emotionPath || [],
          analysis: drawingAnalysis
        },
        // 🆕 直接传递base64编码的情绪图片数据
        emotion_image_base64: emotionImageBase64
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

      // 生成成功 - 添加详细的调试信息
      envConfig.log('任务完成，原始结果:', finalResult);
      const formattedCard = this.formatCardData(finalResult);
      envConfig.log('格式化后的卡片数据:', formattedCard);
      
      this.setData({
        isGenerating: false,
        needEmotionInput: false,
        todayCard: formattedCard
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
      const errMsg = (error && error.message) || '';
      const quotaKeywords = ['超出', '次数', '配额', 'quota', 'limit'];
      const isQuotaExceeded = quotaKeywords.some(k => errMsg.includes(k));
      
      if (isQuotaExceeded) {
        wx.showToast({
          title: '今日生成次数已用完',
          icon: 'none',
          duration: 3000
        });
      } else {
        app.utils.showError('生成失败，请重试');
      }
    }
  },

  /**
   * 翻转卡片
   */
  flipCard() {
    // 若使用结构化组件，则由子组件自行处理翻转，这里不再切换父容器
    if (this.data.todayCard && this.data.todayCard.structured_data) {
      return;
    }
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
      
      const formattedCards = cards.map(card => {
        // 解析结构化数据，提取预览内容
        let previewData = {
          title: card.concept || '回忆',
          mainText: '',
          mood: '',
          backgroundImage: ''
        };
        
        if (card.structured_data) {
          try {
            const structured = typeof card.structured_data === 'string' 
              ? JSON.parse(card.structured_data) 
              : card.structured_data;
            
            previewData = {
              title: structured.title || card.concept || '回忆',
              mainText: structured.content?.main_text || card.quote || '',
              mood: structured.mood?.primary || '',
              backgroundImage: structured.visual?.background_image_url || card.image || ''
            };
          } catch (e) {
            envConfig.warn('解析结构化数据失败:', e);
          }
        } else {
          // 降级处理
          previewData = {
            title: card.concept || '回忆',
            mainText: card.quote || '',
            mood: card.emotion_type || '',
            backgroundImage: card.image || ''
          };
        }
        
        return {
          id: card.id,
          date: new Date(card.created_at).toLocaleDateString('zh-CN', {
            month: 'short',
            day: 'numeric'
          }),
          keyword: previewData.title,
          mainText: previewData.mainText.substring(0, 20) + (previewData.mainText.length > 20 ? '...' : ''),
          mood: previewData.mood,
          backgroundImage: previewData.backgroundImage,
          moodColor: this.getMoodColor(card.emotion_type)
        };
      });

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
    
    envConfig.log('点击查看卡片, cardId:', cardId);
    
    if (!cardId) {
      envConfig.error('卡片ID缺失');
      const app = getApp();
      app.utils?.showError('卡片信息异常，请重试');
      return;
    }
    
    wx.navigateTo({
      url: `/pages/postcard/postcard?id=${cardId}`,
      fail: (error) => {
        envConfig.error('页面跳转失败:', error);
        const app = getApp();
        app.utils?.showError('页面跳转失败，请重试');
      }
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
      const card = this.data.todayCard;
      let shareTitle = '我在AI明信片记录了今天的心情';
      
      // 使用更丰富的分享标题
      if (card.keyword && card.keyword !== '今日心境') {
        shareTitle = `${card.keyword} | 我的AI明信片`;
      } else if (card.quote && card.quote.length > 0) {
        const shortQuote = card.quote.length > 20 ? card.quote.substring(0, 20) + '...' : card.quote;
        shareTitle = `"${shortQuote}" | 我的AI明信片`;
      }
      
      return {
        title: shareTitle,
        path: `/pages/postcard/postcard?id=${card.id}`,
        imageUrl: card.image || ''
      };
    }
    
    return {
      title: 'AI明信片 - 每一天，都值得被温柔记录',
      path: '/pages/index/index'
    };
  },

  /**
   * 分享到朋友圈
   */
  onShareTimeline() {
    const cityName = this.data.cityName;
    const weatherInfo = this.data.weatherInfo;
    
    let timelineTitle = 'AI明信片 - 每一天，都值得被温柔记录';
    
    // 结合环境信息的朋友圈标题
    if (this.data.todayCard) {
      const card = this.data.todayCard;
      if (card.keyword && cityName) {
        timelineTitle = `${card.keyword} | ${cityName}的AI明信片`;
      } else if (cityName && weatherInfo) {
        timelineTitle = `${cityName}，${weatherInfo} | AI明信片记录`;
      } else if (card.keyword) {
        timelineTitle = `${card.keyword} | AI明信片`;
      }
    } else if (cityName && weatherInfo) {
      timelineTitle = `${cityName}，${weatherInfo} | AI明信片创作`;
    }
    
    return {
      title: timelineTitle,
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
  },

  // ==================== 结构化卡片事件处理 ====================

  /**
   * 结构化卡片点击事件
   */
  onStructuredCardTap(e) {
    const { structuredData } = e.detail;
    envConfig.log('结构化卡片被点击:', structuredData);
    
    // 可以在这里添加卡片点击的交互逻辑
    // 比如展示详细信息、播放动画等
  },

  /**
   * 推荐内容点击事件
   */
  onRecommendationTap(e) {
    const { type, item } = e.detail;
    envConfig.log('推荐内容被点击:', type, item);
    
    // 根据推荐类型执行不同操作
    switch (type) {
      case 'music':
        this.handleMusicRecommendation(item);
        break;
      case 'book':
        this.handleBookRecommendation(item);
        break;
      case 'movie':
        this.handleMovieRecommendation(item);
        break;
    }
  },

  /**
   * 结构化卡片分享事件
   */
  onStructuredCardShare(e) {
    const { structuredData } = e.detail;
    envConfig.log('分享结构化卡片:', structuredData);
    
    // 触发小程序分享
    wx.showShareMenu({
      withShareTicket: true
    });
  },

  /**
   * 处理音乐推荐
   */
  handleMusicRecommendation(musicItem) {
    wx.showModal({
      title: `🎵 ${musicItem.title}`,
      content: `演唱者：${musicItem.artist}\n\n推荐理由：${musicItem.reason}`,
      confirmText: '搜索音乐',
      cancelText: '关闭',
      success: (res) => {
        if (res.confirm) {
          // 这里可以集成音乐搜索功能
          wx.showToast({
            title: '音乐搜索功能开发中',
            icon: 'none'
          });
        }
      }
    });
  },

  /**
   * 处理书籍推荐
   */
  handleBookRecommendation(bookItem) {
    wx.showModal({
      title: `📚 ${bookItem.title}`,
      content: `作者：${bookItem.author}\n\n推荐理由：${bookItem.reason}`,
      confirmText: '了解更多',
      cancelText: '关闭',
      success: (res) => {
        if (res.confirm) {
          // 这里可以集成图书搜索功能
          wx.showToast({
            title: '图书搜索功能开发中',
            icon: 'none'
          });
        }
      }
    });
  },

  /**
   * 处理电影推荐
   */
  handleMovieRecommendation(movieItem) {
    wx.showModal({
      title: `🎬 ${movieItem.title}`,
      content: `导演：${movieItem.director}\n\n推荐理由：${movieItem.reason}`,
      confirmText: '查看详情',
      cancelText: '关闭',
      success: (res) => {
        if (res.confirm) {
          // 这里可以集成电影信息查询功能
          wx.showToast({
            title: '电影信息功能开发中',
            icon: 'none'
          });
        }
      }
    });
  },

  /**
   * 跳转到测试页面
   */
  goToTestPage() {
    wx.navigateTo({
      url: '/pages/flip-test/flip-test'
    });
  }
});

// hanging-charm.js - 🔮 挂件式心象签组件
const { resourceCache } = require('../../utils/resource-cache.js');

Component({
  /**
   * 组件配置选项 - 避免样式冲突
   */
  options: {
    addGlobalClass: false,  // 禁用全局样式类，避免页面样式冲突
    styleIsolation: 'isolated'  // 完全隔离样式，避免外部样式侵入
  },

  /**
   * 组件的属性列表
   */
  properties: {
    // 心象签数据（支持新的扁平化结构）
    oracleData: {
      type: Object,
      value: {},
      observer: 'onOracleDataChange'
    },
    // 挂件类型ID (如 'bagua-jinnang', 'lianhua-yuanpai' 等)
    charmType: {
      type: String,
      value: 'lianhua-yuanpai',
      observer: 'onCharmTypeChange'
    },
    // 背景图片URL
    backgroundImage: {
      type: String,
      value: ''
    },
    // 是否显示动画
    showAnimation: {
      type: Boolean,
      value: true
    },
    // 尺寸模式 (small, standard, large)
    sizeMode: {
      type: String,
      value: 'standard'
    }
  },

  /**
   * 组件的初始数据
   */
  data: {
    // 翻面状态
    isFlipped: false,
    // 当前charm配置
    charmConfig: null,
    // 动画数据
    animationData: {},
    // 是否正在动画中
    isAnimating: false,
    // 挂件图片路径
    charmImagePath: '',
    // 背景光圈样式
    glowStyle: '',
    // 标题样式
    titleStyle: '',
    // 副标题样式
    subtitleStyle: '',
    // 解签笺动画状态
    showInterpretation: false,
    // 动态颜色
    charmMainColor: '#8B7355',
    charmAccentColor: '#D4AF37',
    // 正面签名拆分字符，避免依赖writing-mode
    charmNameChars: [],
    // 解签内容拆分字符，确保竖排显示
    insightChars: [],
    impressionChars: [],
    // 统一竖排数据预处理结果
    verticalData: {
      hexagramNameChars: [],
      strokeImpressionChars: [],
      dailyGuidesColumns: [],
      blessingStreamChars: [],
      extrasReflectionsChars: [],
      extrasMicroActionsChars: [],
      extrasGratitudeChars: [],
      extrasMoodTipsChars: [],
      extrasLifeInsightsChars: [],
      extrasCreativeSparkChars: [],
      extrasMindfulnessChars: [],
      extrasFutureVisionChars: [],
      oracleAffirmationChars: [],
      culturalNoteChars: [],
      fengShuiFocusChars: [],
      ritualHintChars: [],
      seasonTimeChars: [],
      elementBalanceData: [],
      symbolicKeywordsChars: []
    },
  },

  /**
   * 组件生命周期
   */
  lifetimes: {
    attached() {
      this.loadCharmConfig();
      this.setupStyles();
    },
    
    ready() {
      // 初始化动态样式和数据预处理
      if (this.data.oracleData && Object.keys(this.data.oracleData).length > 0) {
        // 🔧 只调用 updateDynamicStyles，它会内部处理 charm_name
        this.updateDynamicStyles(this.data.oracleData);
        this.updateInterpretationChars(this.data.oracleData);
        // 统一竖排数据预处理
        this._preprocessVerticalData(this.data.oracleData);
      }
      this.triggerEntryAnimation();
    }
  },

  /**
   * 组件方法
   */
  methods: {
    /**
     * 🔮 加载挂件配置（支持缓存的远程资源）
     */
    async loadCharmConfig() {
      try {
        // 获取当前挂件类型对应的配置
        const charmConfig = await this.getCharmConfigById(this.data.charmType);
        
        if (charmConfig) {
          
          // 🔮 构建资源URL并获取缓存路径
          let originalUrl = '';
          if (charmConfig.imageUrl) {
            // 已有完整URL，直接使用
            originalUrl = charmConfig.imageUrl;
          } else if (charmConfig.image && this.isBuiltinConfig(charmConfig)) {
            // 内置配置需要构建完整URL
            originalUrl = this.buildImageUrl(charmConfig.image);
          } else if (charmConfig.image) {
            // 其他情况直接使用image字段
            originalUrl = charmConfig.image;
          }
          
          // 通过缓存管理器获取资源（自动下载并缓存）
          if (originalUrl) {
            try {
              const cachedImagePath = await resourceCache.getCachedResourceUrl(originalUrl);
              
              this.setData({
                charmConfig: charmConfig,
                charmImagePath: cachedImagePath
              });
              this.setupDynamicStyles();
              
            } catch (error) {
              console.warn('资源缓存获取失败，使用默认形状:', error);
              this.setData({
                charmConfig: charmConfig,
                charmImagePath: '' // 清空路径，使用默认形状
              });
              this.setupDynamicStyles();
            }
          } else {
            this.setData({
              charmConfig: charmConfig,
              charmImagePath: ''
            });
            this.setupDynamicStyles();
          }
        } else {
          console.warn('未找到挂件配置，使用默认配置');
          this.useDefaultCharmConfig();
        }
        
      } catch (error) {
        console.error('加载挂件配置失败:', error);
        this.useDefaultCharmConfig();
      }
    },

    /**
     * 根据ID获取挂件配置
     */
    async getCharmConfigById(charmId) {
      try {
        // 🔮 优先从父组件的全局挂件配置中查找
        const pages = typeof getCurrentPages === 'function' ? getCurrentPages() : [];
        const currentPage = pages.length > 0 ? pages[pages.length - 1] : null;
        
        if (currentPage && currentPage.data && currentPage.data.charmConfigs && currentPage.data.charmConfigs.length > 0) {
          const config = currentPage.data.charmConfigs.find(config => config.id === charmId);
          if (config) {
            return config;
          }
        }
        
        // 回退到内置配置
        const charmConfigs = this.getBuiltinCharmConfigs();
        return charmConfigs.find(config => config.id === charmId);
        
      } catch (error) {
        console.error('获取挂件配置失败:', error);
        const charmConfigs = this.getBuiltinCharmConfigs();
        return charmConfigs.find(config => config.id === charmId);
      }
    },

    /**
     * 获取内置挂件配置 - 完整的18种签体配置作为降级方案
     */
    getBuiltinCharmConfigs() {
      return [
        {
          "id": "bagua-jinnang",
          "name": "八角锦囊 (神秘守护)",
          "image": "八角锦囊 (神秘守护).png",
          "title": {
            "type": "vertical",
            "position": { "x": 512, "y": 520 },
            "maxChars": 4,
            "lineHeight": 72,
            "fontSize": 68,
            "fontWeight": 600
          },
          "subtitle": {
            "visible": true,
            "position": { "x": 512, "y": 660 },
            "maxChars": 10,
            "fontSize": 30,
            "color": "#2E3A4A"
          },
          "glow": {
            "shape": "octagon",
            "radius": [380, 380],
            "opacity": 0.4,
            "blendMode": "screen"
          },
          "suggestedPalette": ["#5DA9E9", "#F2D7EE"],
          "note": "八角造型较稳重，竖排签名置中效果最佳。"
        },
        {
          "id": "liujiao-denglong",
          "name": "六角灯笼面 (光明指引)",
          "image": "六角灯笼面 (光明指引).png",
          "title": {
            "type": "vertical",
            "position": { "x": 512, "y": 530 },
            "maxChars": 4,
            "lineHeight": 68,
            "fontSize": 64,
            "fontWeight": 600
          },
          "subtitle": {
            "visible": true,
            "position": { "x": 512, "y": 660 },
            "maxChars": 10,
            "fontSize": 28,
            "color": "#2C3E50"
          },
          "glow": {
            "shape": "hexagon",
            "radius": [360, 360],
            "opacity": 0.35,
            "blendMode": "screen"
          },
          "suggestedPalette": ["#FFD166", "#F6E7CD"],
          "note": "灯笼顶部空间收紧，适合竖排签名。"
        },
        {
          "id": "juanzhou-huakuang",
          "name": "卷轴画框 (徐徐展开)",
          "image": "卷轴画框 (徐徐展开).png",
          "title": {
            "type": "horizontal",
            "position": { "x": 512, "y": 520 },
            "maxChars": 6,
            "lineHeight": 56,
            "fontSize": 56,
            "fontWeight": 600
          },
          "subtitle": {
            "visible": true,
            "position": { "x": 512, "y": 600 },
            "maxChars": 16,
            "fontSize": 30,
            "color": "#4A3728"
          },
          "glow": {
            "shape": "rectangle",
            "radius": [420, 320],
            "opacity": 0.35,
            "blendMode": "screen"
          },
          "suggestedPalette": ["#E9C46A", "#F4A261"],
          "note": "卷轴横向空间充足，支持横排签名。"
        },
        {
          "id": "shuangyu-jinnang",
          "name": "双鱼锦囊 (年年有余)",
          "image": "双鱼锦囊 (年年有余).png",
          "title": {
            "type": "vertical",
            "position": { "x": 512, "y": 525 },
            "maxChars": 4,
            "lineHeight": 70,
            "fontSize": 66,
            "fontWeight": 600
          },
          "subtitle": {
            "visible": true,
            "position": { "x": 512, "y": 655 },
            "maxChars": 10,
            "fontSize": 28,
            "color": "#274060"
          },
          "glow": {
            "shape": "ellipse",
            "radius": [360, 420],
            "opacity": 0.42,
            "blendMode": "screen"
          },
          "suggestedPalette": ["#94D1BE", "#F9C74F"],
          "note": "双鱼造型优雅，适合竖排签名。"
        },
        {
          "id": "siyue-jinjie",
          "name": "四叶锦结 (幸运相伴)",
          "image": "四叶锦结 (幸运相伴).png",
          "title": {
            "type": "vertical",
            "position": { "x": 512, "y": 500 },
            "maxChars": 4,
            "lineHeight": 72,
            "fontSize": 68,
            "fontWeight": 600
          },
          "subtitle": {
            "visible": false
          },
          "glow": {
            "shape": "clover",
            "radius": [360, 360],
            "opacity": 0.4,
            "blendMode": "screen"
          },
          "suggestedPalette": ["#52B788", "#D8F3DC"],
          "note": "四叶形中心紧凑，建议只显示主签名。"
        },
        {
          "id": "ruyi-jie",
          "name": "如意结 (万事如意)",
          "image": "如意结 (万事如意).png",
          "title": {
            "type": "vertical",
            "position": { "x": 512, "y": 520 },
            "maxChars": 4,
            "lineHeight": 70,
            "fontSize": 66,
            "fontWeight": 600
          },
          "subtitle": {
            "visible": true,
            "position": { "x": 512, "y": 660 },
            "maxChars": 10,
            "fontSize": 28,
            "color": "#432C7A"
          },
          "glow": {
            "shape": "loop",
            "radius": [360, 400],
            "opacity": 0.4,
            "blendMode": "screen"
          },
          "suggestedPalette": ["#7D5BA6", "#FFE5F1"],
          "note": "如意结造型经典，适合竖排签名。"
        },
        {
          "id": "fangsheng-jie",
          "name": "方胜结 (同心永结)",
          "image": "方胜结 (同心永结).png",
          "title": {
            "type": "vertical",
            "position": { "x": 512, "y": 520 },
            "maxChars": 4,
            "lineHeight": 68,
            "fontSize": 64,
            "fontWeight": 600
          },
          "subtitle": {
            "visible": false
          },
          "glow": {
            "shape": "diamond",
            "radius": [360, 360],
            "opacity": 0.38,
            "blendMode": "screen"
          },
          "suggestedPalette": ["#48B8D0", "#E8F6FD"],
          "note": "菱形内部空间较小，适合竖排签名。"
        },
        {
          "id": "zhuchi-changpai",
          "name": "朱漆长牌 (言简意赅)",
          "image": "朱漆长牌 (言简意赅).png",
          "title": {
            "type": "vertical",
            "position": { "x": 512, "y": 540 },
            "maxChars": 3,
            "lineHeight": 80,
            "fontSize": 70,
            "fontWeight": 600
          },
          "subtitle": {
            "visible": true,
            "position": { "x": 512, "y": 700 },
            "maxChars": 8,
            "fontSize": 28,
            "color": "#4F1D1D"
          },
          "glow": {
            "shape": "rectangle",
            "radius": [320, 440],
            "opacity": 0.32,
            "blendMode": "screen"
          },
          "suggestedPalette": ["#D62828", "#F77F00"],
          "note": "牌身狭长，签名控制在3个字以内。"
        },
        {
          "id": "haitang-muchuang",
          "name": "海棠木窗 (古典窗格)",
          "image": "海棠木窗 (古典窗格).png",
          "title": {
            "type": "vertical",
            "position": { "x": 512, "y": 530 },
            "maxChars": 4,
            "lineHeight": 70,
            "fontSize": 64,
            "fontWeight": 600
          },
          "subtitle": {
            "visible": true,
            "position": { "x": 512, "y": 660 },
            "maxChars": 12,
            "fontSize": 30,
            "color": "#362C2A"
          },
          "glow": {
            "shape": "rounded-square",
            "radius": [380, 380],
            "opacity": 0.38,
            "blendMode": "screen"
          },
          "suggestedPalette": ["#A47148", "#F4E6D4"],
          "note": "窗格花纹细密，适合竖排签名。"
        },
        {
          "id": "xiangyun-liucai",
          "name": "祥云流彩 (梦幻意境)",
          "image": "祥云流彩 (梦幻意境).png",
          "title": {
            "type": "horizontal",
            "position": { "x": 512, "y": 540 },
            "maxChars": 6,
            "lineHeight": 54,
            "fontSize": 52,
            "fontWeight": 600
          },
          "subtitle": {
            "visible": true,
            "position": { "x": 512, "y": 620 },
            "maxChars": 12,
            "fontSize": 28,
            "color": "#2B3A55"
          },
          "glow": {
            "shape": "ellipse",
            "radius": [420, 320],
            "opacity": 0.4,
            "blendMode": "screen"
          },
          "suggestedPalette": ["#5F0A87", "#B5A0FF"],
          "note": "云纹延展，适合横排签名。"
        },
        {
          "id": "xiangyun-hulu",
          "name": "祥云葫芦 (福禄绵延)",
          "image": "祥云葫芦 (福禄绵延).png",
          "title": {
            "type": "vertical",
            "position": { "x": 512, "y": 560 },
            "maxChars": 3,
            "lineHeight": 78,
            "fontSize": 70,
            "fontWeight": 600
          },
          "subtitle": {
            "visible": true,
            "position": { "x": 512, "y": 700 },
            "maxChars": 8,
            "fontSize": 30,
            "color": "#3E2723"
          },
          "glow": {
            "shape": "gourd",
            "radius": [320, 420],
            "opacity": 0.36,
            "blendMode": "screen"
          },
          "suggestedPalette": ["#FFB703", "#FB8500"],
          "note": "葫芦造型独特，适合3字签名。"
        },
        {
          "id": "zhujie-changtiao",
          "name": "竹节长条 (虚心有节)",
          "image": "竹节长条 (虚心有节).png",
          "title": {
            "type": "vertical",
            "position": { "x": 512, "y": 540 },
            "maxChars": 3,
            "lineHeight": 78,
            "fontSize": 68,
            "fontWeight": 600
          },
          "subtitle": {
            "visible": true,
            "position": { "x": 512, "y": 700 },
            "maxChars": 8,
            "fontSize": 28,
            "color": "#1B4332"
          },
          "glow": {
            "shape": "rectangle",
            "radius": [300, 440],
            "opacity": 0.3,
            "blendMode": "screen"
          },
          "suggestedPalette": ["#40916C", "#95D5B2"],
          "note": "竹节笔直，适合3字签名。"
        },
        {
          "id": "lianhua-yuanpai",
          "name": "莲花圆牌 (平和雅致)",
          "image": "莲花圆牌 (平和雅致).png",
          "title": {
            "type": "vertical",
            "position": { "x": 512, "y": 520 },
            "maxChars": 4,
            "lineHeight": 72,
            "fontSize": 68,
            "fontWeight": 600
          },
          "subtitle": {
            "visible": true,
            "position": { "x": 512, "y": 645 },
            "maxChars": 10,
            "fontSize": 30,
            "color": "#2F3E46"
          },
          "glow": {
            "shape": "circle",
            "radius": [380, 380],
            "opacity": 0.38,
            "blendMode": "screen"
          },
          "suggestedPalette": ["#6BC9B0", "#FFE5D9"],
          "note": "圆牌留白充足，可保留副标题。"
        },
        {
          "id": "jinbian-moyu",
          "name": "金边墨玉璧 (沉稳庄重)",
          "image": "金边墨玉璧 (沉稳庄重).png",
          "title": {
            "type": "vertical",
            "position": { "x": 512, "y": 520 },
            "maxChars": 3,
            "lineHeight": 74,
            "fontSize": 66,
            "fontWeight": 600
          },
          "subtitle": {
            "visible": true,
            "position": { "x": 512, "y": 650 },
            "maxChars": 8,
            "fontSize": 28,
            "color": "#1D3557"
          },
          "glow": {
            "shape": "circle",
            "radius": [360, 360],
            "opacity": 0.32,
            "blendMode": "screen"
          },
          "suggestedPalette": ["#264653", "#E9C46A"],
          "note": "墨玉色调沉稳，适合3字签名。"
        },
        {
          "id": "yinxing-ye",
          "name": "银杏叶 (坚韧与永恒)",
          "image": "银杏叶 (坚韧与永恒).png",
          "title": {
            "type": "horizontal",
            "position": { "x": 512, "y": 520 },
            "maxChars": 6,
            "lineHeight": 52,
            "fontSize": 52,
            "fontWeight": 600
          },
          "subtitle": {
            "visible": true,
            "position": { "x": 512, "y": 600 },
            "maxChars": 14,
            "fontSize": 28,
            "color": "#3F3B2C"
          },
          "glow": {
            "shape": "leaf",
            "radius": [460, 340],
            "opacity": 0.36,
            "blendMode": "screen"
          },
          "suggestedPalette": ["#E4CFA3", "#6D9773"],
          "note": "银杏叶横幅较宽，适合横排签名。"
        },
        {
          "id": "zhangming-suo",
          "name": "长命锁 (富贵安康)",
          "image": "长命锁 (富贵安康).png",
          "title": {
            "type": "vertical",
            "position": { "x": 512, "y": 540 },
            "maxChars": 3,
            "lineHeight": 78,
            "fontSize": 70,
            "fontWeight": 600
          },
          "subtitle": {
            "visible": true,
            "position": { "x": 512, "y": 690 },
            "maxChars": 10,
            "fontSize": 28,
            "color": "#623412"
          },
          "glow": {
            "shape": "cloud",
            "radius": [360, 360],
            "opacity": 0.34,
            "blendMode": "screen"
          },
          "suggestedPalette": ["#F4A261", "#FEF3C7"],
          "note": "锁体呈祥云形，适合3字签名。"
        },
        {
          "id": "qingyu-tuanshan",
          "name": "青玉团扇 (清风徐来)",
          "image": "青玉团扇 (清风徐来).png",
          "title": {
            "type": "horizontal",
            "position": { "x": 512, "y": 530 },
            "maxChars": 6,
            "lineHeight": 52,
            "fontSize": 52,
            "fontWeight": 600
          },
          "subtitle": {
            "visible": true,
            "position": { "x": 512, "y": 610 },
            "maxChars": 14,
            "fontSize": 28,
            "color": "#1E3A34"
          },
          "glow": {
            "shape": "fan",
            "radius": [420, 340],
            "opacity": 0.34,
            "blendMode": "screen"
          },
          "suggestedPalette": ["#6ABEA7", "#B7E4C7"],
          "note": "团扇上半部较宽，适合横排签名。"
        },
        {
          "id": "qinghua-cishan",
          "name": "青花瓷扇 (文化底蕴)",
          "image": "青花瓷扇 (文化底蕴).png",
          "title": {
            "type": "horizontal",
            "position": { "x": 512, "y": 520 },
            "maxChars": 6,
            "lineHeight": 50,
            "fontSize": 50,
            "fontWeight": 600
          },
          "subtitle": {
            "visible": true,
            "position": { "x": 512, "y": 600 },
            "maxChars": 14,
            "fontSize": 28,
            "color": "#1F3C88"
          },
          "glow": {
            "shape": "fan",
            "radius": [440, 340],
            "opacity": 0.34,
            "blendMode": "screen"
          },
          "suggestedPalette": ["#1F3C88", "#A8C5F0"],
          "note": "青花纹路典雅，适合横排签名。"
        }
      ];
    },

    /**
     * 判断是否为内置配置
     */
    isBuiltinConfig(config) {
      const builtinIds = [
        'bagua-jinnang', 'liujiao-denglong', 'juanzhou-huakuang', 'shuangyu-jinnang',
        'siyue-jinjie', 'ruyi-jie', 'fangsheng-jie', 'zhuchi-changpai',
        'haitang-muchuang', 'xiangyun-liucai', 'xiangyun-hulu', 'zhujie-changtiao',
        'lianhua-yuanpai', 'jinbian-moyu', 'yinxing-ye', 'zhangming-suo',
        'qingyu-tuanshan', 'qinghua-cishan'
      ];
      return builtinIds.includes(config.id);
    },

    /**
     * 构建图片完整URL
     */
    buildImageUrl(imageName) {
      // 尝试获取环境配置
      try {
        const envConfig = require('../../config/env.js');
        const baseUrl = envConfig.AI_AGENT_PUBLIC_URL || 'http://localhost:8080';
        return `${baseUrl}/resources/签体/${encodeURIComponent(imageName)}`;
      } catch (error) {
        console.warn('无法获取环境配置，使用默认URL构建:', error);
        return `http://localhost:8080/resources/签体/${encodeURIComponent(imageName)}`;
      }
    },


    /**
     * 使用默认挂件配置
     */
    useDefaultCharmConfig() {
      const defaultConfig = {
        "id": "default",
        "name": "默认圆形",
        "image": "",
        "title": {
          "type": "horizontal",
          "position": { "x": 512, "y": 420 },
          "maxChars": 6,
          "fontSize": 56,
          "fontWeight": 500
        },
        "subtitle": {
          "visible": true,
          "position": { "x": 512, "y": 520 },
          "maxChars": 10,
          "fontSize": 28,
          "color": "#2E3A4A"
        },
        "glow": {
          "shape": "circle",
          "radius": [350, 350],
          "opacity": 0.35,
          "blendMode": "multiply"
        },
        "suggestedPalette": ["#E8F4FD", "#B2BEC3"]
      };
      
      this.setData({
        charmConfig: defaultConfig,
        charmImagePath: '' // 默认配置不使用图片
      });
      
      this.setupDynamicStyles();
    },

    /**
     * 设置基础样式
     */
    setupStyles() {
      const sizeMap = {
        small: { width: '200rpx', height: '200rpx' },
        standard: { width: '350rpx', height: '350rpx' },
        large: { width: '950rpx', height: '950rpx' }
      };
      
      const size = sizeMap[this.data.sizeMode] || sizeMap.standard;
      
      // 基础容器样式 - 使用视窗单位
      const containerStyle = `
        width: ${size.width};
        height: ${size.height};
        ${size.maxWidth ? `max-width: ${size.maxWidth};` : ''}
        ${size.maxHeight ? `max-height: ${size.maxHeight};` : ''}
        ${size.minWidth ? `min-width: ${size.minWidth};` : ''}
        ${size.minHeight ? `min-height: ${size.minHeight};` : ''}
        perspective: 1000rpx;
      `;
      
      this.setData({
        containerStyle: containerStyle
      });
    },

    /**
     * 设置动态样式
     */
    setupDynamicStyles() {
      const config = this.data.charmConfig;
      if (!config) return;
      
      // 设置背景光圈样式
      this.setupGlowStyle();
      
      // 设置标题样式
      this.setupTitleStyle();
      
      // 设置副标题样式
      this.setupSubtitleStyle();
    },

    /**
     * 设置背景光圈样式
     */
    setupGlowStyle() {
      const { charmConfig, backgroundImage } = this.data;
      if (!charmConfig || !backgroundImage) return;
      
      const glow = charmConfig.glow;
      const [radiusX, radiusY] = glow.radius;
      
      let clipPath = '';
      switch (glow.shape) {
        case 'circle':
          clipPath = `circle(${radiusX / 2}rpx at center)`;
          break;
        case 'ellipse':
          clipPath = `ellipse(${radiusX / 2}rpx ${radiusY / 2}rpx at center)`;
          break;
        case 'octagon':
          clipPath = `polygon(30% 0%, 70% 0%, 100% 30%, 100% 70%, 70% 100%, 30% 100%, 0% 70%, 0% 30%)`;
          break;
        default:
          clipPath = `circle(${radiusX / 2}rpx at center)`;
      }
      
      const glowStyle = `
        background-image: url('${backgroundImage}');
        background-size: cover;
        background-position: center;
        filter: blur(40rpx);
        opacity: ${glow.opacity};
        clip-path: ${clipPath};
        mix-blend-mode: ${glow.blendMode};
        width: ${radiusX * 1.2}rpx;
        height: ${radiusY * 1.2}rpx;
      `;
      
      this.setData({
        glowStyle: glowStyle
      });
    },

    /**
     * 设置标题样式
     */
    setupTitleStyle() {
      const { charmConfig } = this.data;
      if (!charmConfig) return;
      
      const title = charmConfig.title;
      
      let titleStyle = `
        font-size: ${title.fontSize}rpx;
        font-weight: ${title.fontWeight};
        color: ${title.color || '#1F2937'};
      `;
      
      // 根据类型设置不同的排列方式
      if (title.type === 'vertical') {
        titleStyle += `
          writing-mode: vertical-rl;
          line-height: ${title.lineHeight || title.fontSize}rpx;
        `;
      } else if (title.type === 'arc') {
        // 弧形文字需要特殊处理，这里先用普通水平排列
        titleStyle += `
          text-align: center;
        `;
      } else {
        titleStyle += `
          text-align: center;
        `;
      }
      
      this.setData({
        titleStyle: titleStyle
      });
    },

    /**
     * 设置副标题样式
     */
    setupSubtitleStyle() {
      const { charmConfig } = this.data;
      if (!charmConfig || !charmConfig.subtitle.visible) return;
      
      const subtitle = charmConfig.subtitle;
      
      const subtitleStyle = `
        font-size: ${subtitle.fontSize}rpx;
        color: ${subtitle.color};
        text-align: center;
        opacity: 0.8;
      `;
      
      this.setData({
        subtitleStyle: subtitleStyle
      });
    },

    /**
     * 触发入场动画
     */
    triggerEntryAnimation() {
      if (!this.data.showAnimation) return;
      
      const animation = wx.createAnimation({
        duration: 600,
        timingFunction: 'cubic-bezier(0.175, 0.885, 0.32, 1.275)'
      });
      
      // 从上方飘入的效果
      animation.translateY(0).opacity(1).scale(1).step();
      
      this.setData({
        animationData: animation.export(),
        isAnimating: true
      });
      
      // 动画结束后重置状态
      setTimeout(() => {
        this.setData({
          isAnimating: false
        });
      }, 600);
    },

    /**
     * 点击挂件触发翻面
     */
    onCharmTap() {
      this.flipCharm();
    },

    /**
     * 翻面动画
     */
    flipCharm() {
      if (this.data.isAnimating) return;
      
      this.setData({
        isAnimating: true
      });
      
      const animation = wx.createAnimation({
        duration: 500,
        timingFunction: 'ease-in-out'
      });
      
      // 翻转180度
      const newFlipped = !this.data.isFlipped;
      animation.rotateY(newFlipped ? 180 : 0).step();
      
      this.setData({
        isFlipped: newFlipped,
        animationData: animation.export()
      });
      
      // 如果翻到背面，延迟显示解签笺
      if (newFlipped) {
        setTimeout(() => {
          this.setData({
            showInterpretation: true
          });
        }, 250); // 翻面动画的一半时间
      } else {
        this.setData({
          showInterpretation: false
        });
      }
      
      // 动画结束
      setTimeout(() => {
        this.setData({
          isAnimating: false
        });
      }, 500);
      
      // 触发事件
      this.triggerEvent('flip', { 
        isFlipped: newFlipped 
      });
    },

    /**
     * 分享挂件
     */
    onShareCharm() {
      this.triggerEvent('share', {
        oracleData: this.data.oracleData,
        charmType: this.data.charmType
      });
    },

    /**
     * 监听oracle数据变化
     */
    onOracleDataChange(newData) {
      if (newData && Object.keys(newData).length > 0) {
        this.updateDynamicStyles(newData);
        this.updateInterpretationChars(newData);
        this._preprocessVerticalData(newData);
      }
    },

    /**
     * 监听挂件类型变化
     */
    onCharmTypeChange(newType, oldType) {
      if (newType && newType !== oldType) {
        // 重新加载挂件配置
        this.loadCharmConfig();
      }
    },

    /**
     * 🔮 根据心象签数据更新动态样式
     */
    updateDynamicStyles(oracleData) {
      
      // 🔧 修复颜色提取 - 支持多级fallback
      const mainColor = oracleData.charm_main_color || 
                       (oracleData.structured_data && oracleData.structured_data.charm_main_color) ||
                       oracleData.oracle_color_1 || 
                       this.data.charmConfig?.suggestedPalette?.[0] || 
                       '#2D3748';
      
      const accentColor = oracleData.charm_accent_color || 
                         (oracleData.structured_data && oracleData.structured_data.charm_accent_color) ||
                         oracleData.oracle_color_2 || 
                         this.data.charmConfig?.suggestedPalette?.[1] || 
                         '#D4AF37';

      this.setData({
        charmMainColor: mainColor,
        charmAccentColor: accentColor
      });

      // 🔮 更新签名文字 - 修复多层级数据提取
      const charmName = oracleData.charm_name || 
                       oracleData.oracle_title || 
                       oracleData.title ||
                       oracleData.ai_selected_charm_name ||
                       oracleData.oracle_hexagram_name ||
                       // 🔧 修复：charm_name 在 structured_data 顶层
                       (oracleData.structured_data && oracleData.structured_data.charm_name) ||
                       (oracleData.structured_data && oracleData.structured_data.charm_identity && oracleData.structured_data.charm_identity.charm_name) ||
                       (oracleData.structured_data && oracleData.structured_data.oracle_theme && oracleData.structured_data.oracle_theme.title) ||
                       '心象签';
      
      
      this.updateCharmNameChars(charmName);

      // 更新背景图片
      const backgroundImg = oracleData.visual_background_image || 
                           oracleData.background_image_url ||
                           oracleData.image_url ||
                           this.data.backgroundImage;
      
      if (backgroundImg && backgroundImg !== this.data.backgroundImage) {
        this.setData({
          backgroundImage: backgroundImg
        });
        this.setupGlowStyle();
      }
    },

    /**
     * 🔮 将签名拆解为字符数组，兼容小程序竖排限制
     */
    updateCharmNameChars(charmName = '') {
      if (typeof charmName !== 'string' || !charmName || charmName.trim() === '') {
        this.setData({ charmNameChars: ['心', '象', '签'] });
        return;
      }

      // 清理文字：移除空格、标点符号、"签"字后缀
      let cleaned = charmName.replace(/[\s\.\,\!\?\;\:\"\'，。！？；：""'']/g, '').trim();
      
      // 如果以"签"结尾，移除它（因为我们会自动添加）
      if (cleaned.endsWith('签')) {
        cleaned = cleaned.slice(0, -1);
      }
      
      // 限制长度为3个字符（加上"签"字就是4个）
      const maxLength = 3;
      const truncated = cleaned.length > maxLength ? cleaned.substring(0, maxLength) : cleaned;
      
      // 如果有内容，添加"签"字
      const finalChars = truncated ? Array.from(truncated + '签') : ['心', '象', '签'];
      
      this.setData({ 
        charmNameChars: finalChars
      });
    },

    /**
     * 将解签内容拆解为字符数组，确保竖排显示
     */
    updateInterpretationChars(oracleData) {
      // 简化版 - 不处理背面内容
      this.setData({
        insightChars: [],
        impressionChars: []
      });
    },

    /**
     * 🎯 统一竖排数据预处理核心方法 - 增强版
     * 将所有需要竖排显示的字段进行统一处理，支持自动换列和密度控制
     */
    _preprocessVerticalData(oracleData) {
      // 智能提取数据 - 支持多层级fallback
      const getFieldValue = (field) => {
        // 优先从顶层获取
        if (oracleData[field]) return oracleData[field];
        
        // 从structured_data获取
        if (oracleData.structured_data && oracleData.structured_data[field]) {
          return oracleData.structured_data[field];
        }
        
        // 从嵌套结构获取
        if (oracleData.structured_data) {
          const sd = oracleData.structured_data;
          
          // oracle_manifest相关字段
          if (field.startsWith('oracle_hexagram_') && sd.oracle_manifest && sd.oracle_manifest.hexagram) {
            if (field === 'oracle_hexagram_name') return sd.oracle_manifest.hexagram.name;
            if (field === 'oracle_hexagram_insight') return sd.oracle_manifest.hexagram.insight;
          }
          
          // daily_guide字段
          if (field === 'oracle_daily_guides' && sd.oracle_manifest && sd.oracle_manifest.daily_guide) {
            return sd.oracle_manifest.daily_guide;
          }
          
          // fengshui和ritual字段
          if (field === 'oracle_fengshui_focus' && sd.oracle_manifest && sd.oracle_manifest.fengshui_focus) {
            return sd.oracle_manifest.fengshui_focus;
          }
          if (field === 'oracle_ritual_hint' && sd.oracle_manifest && sd.oracle_manifest.ritual_hint) {
            return sd.oracle_manifest.ritual_hint;
          }
          
          // ink_reading相关字段
          if (field === 'oracle_stroke_impression' && sd.ink_reading && sd.ink_reading.stroke_impression) {
            return sd.ink_reading.stroke_impression;
          }
          if (field === 'oracle_symbolic_keywords' && sd.ink_reading && sd.ink_reading.symbolic_keywords) {
            return sd.ink_reading.symbolic_keywords;
          }
          
          // blessing_stream
          if (field === 'oracle_blessing_stream' && sd.blessing_stream) {
            return sd.blessing_stream;
          }
          
          // affirmation
          if (field === 'oracle_affirmation' && sd.affirmation) {
            return sd.affirmation;
          }
          
          // culture_note
          if (field === 'oracle_culture_note' && sd.culture_note) {
            return sd.culture_note;
          }
        }
        
        return undefined;
      };

      // 准备WXML可直接使用的数据
      const extractedOracleData = {
        oracle_hexagram_name: getFieldValue('oracle_hexagram_name'),
        oracle_hexagram_insight: getFieldValue('oracle_hexagram_insight'),
        oracle_daily_guides: getFieldValue('oracle_daily_guides'),
        oracle_fengshui_focus: getFieldValue('oracle_fengshui_focus'),
        oracle_ritual_hint: getFieldValue('oracle_ritual_hint'),
        oracle_blessing_stream: getFieldValue('oracle_blessing_stream'),
        oracle_stroke_impression: getFieldValue('oracle_stroke_impression'),
        oracle_affirmation: getFieldValue('oracle_affirmation'),
        oracle_culture_note: getFieldValue('oracle_culture_note')
      };
      
      this.setData({ 
        extractedOracleData
      });
    },


    /**
     * 🎯 将文本拆分为字符数组 - 增强版
     * @param {string} text - 输入文本
     * @param {number} maxLength - 最大长度限制
     */
    _splitTextToChars(text, maxLength = 100) {
      if (!text || typeof text !== 'string') {
        return [];
      }
      
      // 清理文本：移除多余空格和换行
      const cleaned = text.replace(/\s+/g, '').trim();
      
      if (cleaned.length === 0) {
        return [];
      }
      
      // 按最大长度截断
      const truncated = cleaned.length > maxLength ? cleaned.substring(0, maxLength) + '…' : cleaned;
      const chars = Array.from(truncated);
      
      return chars;
    },
    
    /**
     * 🆕 组合季节和时段信息
     */
    _combineSeasonTimeInfo(oracleData) {
      const season = oracleData.oracle_season_hint || '';
      const sessionTime = oracleData.oracle_session_time || '';
      
      if (season && sessionTime) {
        return season + sessionTime + '时光';
      } else if (season) {
        return season + '时节';
      } else if (sessionTime) {
        return sessionTime + '时分';
      }
      return '';
    },
    
    /**
     * 🆕 处理五行元素平衡数据
     */
    _processElementBalance(wood, fire, earth, metal, water) {
      const elements = [
        { name: '木', value: wood, symbol: '🌳' },
        { name: '火', value: fire, symbol: '🔥' },
        { name: '土', value: earth, symbol: '🌍' },
        { name: '金', value: metal, symbol: '⚱️' },
        { name: '水', value: water, symbol: '💧' }
      ];
      
      return elements.filter(el => typeof el.value === 'number' && el.value > 0)
                    .sort((a, b) => b.value - a.value) // 按强度排序
                    .slice(0, 3); // 只显示前3个
    },

    /**
     * 🎯 将数组内容按换行拆分，保持原始结构
     */
    _splitWithLineBreaks(arrayData) {
      if (!Array.isArray(arrayData)) return [];
      return arrayData.filter(item => item && typeof item === 'string');
    },

    /**
     * 🎯 将列表数据分配到指定列数的分栏中 - 增强版
     * @param {Array} listData - 输入数组
     * @param {number} columnCount - 列数
     * @param {number} maxItemsPerColumn - 每列最大项目数
     */
    _splitListToColumns(listData, columnCount = 2, maxItemsPerColumn = 8) {
      if (!Array.isArray(listData) || listData.length === 0) {
        return Array(columnCount).fill().map(() => []);
      }
      
      // 过滤有效数据
      const validItems = listData.filter(item => item && typeof item === 'string' && item.trim().length > 0);
      
      if (validItems.length === 0) {
        return Array(columnCount).fill().map(() => []);
      }
      
      const columns = Array(columnCount).fill().map(() => []);
      
      // 智能分配：优先填满第一列，再填第二列，依此类推
      validItems.forEach((item, index) => {
        const columnIndex = Math.floor(index / maxItemsPerColumn) % columnCount;
        if (columns[columnIndex].length < maxItemsPerColumn) {
          columns[columnIndex].push(item);
        }
      });
      
      return columns;
    },

    /**
     * 阻止事件冒泡
     */
    stopPropagation() {
      // 阻止事件向上传播
    }
  }
});

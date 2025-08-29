Component({
  /**
   * 结构化明信片组件 - 基于结构化数据的固定模板
   */
  properties: {
    // 结构化数据
    structuredData: {
      type: Object,
      value: {}
    },
    
    // 🔧 分别传递的字段，作为备用数据源
    cardMood: {
      type: Object,
      value: null
    },
    cardTitle: {
      type: String,
      value: ''
    },
    cardVisual: {
      type: Object,
      value: null
    },
    cardContent: {
      type: Object,
      value: null
    },
    cardContext: {
      type: Object,
      value: null
    },
    cardRecommendations: {
      type: Object,
      value: null
    },
    // 背景图片URL（Gemini生成）
    backgroundImage: {
      type: String,
      value: ''
    },
    // 兜底英文（当 structuredData 未提供 quote/english 时由父组件传入）
    fallbackEnglish: {
      type: String,
      value: ''
    },
    // 是否显示动画
    showAnimation: {
      type: Boolean,
      value: true
    },
    // 卡片尺寸模式
    sizeMode: {
      type: String,
      value: 'standard' // standard, compact, large
    }
  },

  data: {
    // 动态样式
    dynamicCardStyle: '',
    dynamicContentStyle: '',
    
    // 动画状态
    animationData: {},
    isAnimating: false,
    
    // 推荐内容展开状态
    recommendationsExpanded: false,
    // 预处理动画显示状态
    showGradientAnimation: false,
    // 规范化后的推荐首项
    recMusic: null,
    recBook: null,
    recMovie: null,
    hasMusic: false,
    hasBook: false,
    hasMovie: false,
    // 引用/英文规范化
    hasQuote: false,
    quoteText: '',
    quoteAuthor: '',
    quoteTranslation: ''
  },

  lifetimes: {
    attached() {
      this.initCard();
    },
    
    ready() {
      this.setupAnimations();
    }
  },

  observers: {
    'structuredData': function(newData) {
      if (newData && Object.keys(newData).length > 0) {
        this.updateDynamicStyles(newData);
        this.normalizeRecommendations(newData);
        this.normalizeQuote(newData);
        this.updateAnimationStates(newData);
      }
    }
  },

  methods: {
    /**
     * 初始化卡片
     */
    initCard() {
      const { structuredData } = this.data;
      if (structuredData && Object.keys(structuredData).length > 0) {
        this.updateDynamicStyles();
        this.setupAnimations();
      }
    },

    /**
     * 更新动态样式
     */
    updateDynamicStyles(data) {
      // 使用传入的数据或组件的数据
      const structuredData = data || this.data.structuredData;
      const { sizeMode } = this.data;
      
      if (!structuredData || !structuredData.visual) {
        return;
      }

      const styleHints = structuredData.visual.style_hints || {};
      const mood = structuredData.mood || {};
      
      // 基础尺寸
      const sizeConfig = {
        standard: { width: '690rpx', height: '1100rpx' },
        compact: { width: '600rpx', height: '960rpx' },
        large: { width: '750rpx', height: '1200rpx' }
      };
      
      const size = sizeConfig[sizeMode] || sizeConfig.standard;
      
      // 动态卡片样式
      let cardStyle = `width: ${size.width}; height: ${size.height};`;
      
      // 主题色彩
      if (mood.color_theme) {
        cardStyle += `border: 3rpx solid ${mood.color_theme};`;
      }
      
      // 渐变背景叠加
      if (styleHints.color_scheme && Array.isArray(styleHints.color_scheme)) {
        const [color1, color2] = styleHints.color_scheme;
        cardStyle += `background: linear-gradient(135deg, ${color1}20, ${color2}20);`;
      }
      
      // 紧凑的布局样式调整，减少padding以容纳更多内容
      let contentStyle = '';
      if (styleHints.layout_style === 'minimal') {
        contentStyle = 'padding: 35rpx 25rpx;';
      } else if (styleHints.layout_style === 'rich') {
        contentStyle = 'padding: 40rpx 30rpx;';
      } else if (styleHints.layout_style === 'artistic') {
        contentStyle = 'padding: 45rpx 35rpx; text-align: center;';
      } else {
        // 默认紧凑布局
        contentStyle = 'padding: 30rpx 25rpx;';
      }
      
      this.setData({
        dynamicCardStyle: cardStyle,
        dynamicContentStyle: contentStyle
      });
    },

    /**
     * 规范化推荐数据，兼容对象/数组
     */
    normalizeRecommendations(data) {
      try {
        const rec = (data && data.recommendations) || {};
        const pickFirst = (value) => {
          if (!value) return null;
          return Array.isArray(value) ? (value[0] || null) : value;
        };
        const recMusic = pickFirst(rec.music);
        const recBook = pickFirst(rec.book);
        const recMovie = pickFirst(rec.movie);
        this.setData({
          recMusic,
          recBook,
          recMovie,
          hasMusic: !!(recMusic && recMusic.title),
          hasBook: !!(recBook && recBook.title),
          hasMovie: !!(recMovie && recMovie.title)
        });
      } catch (e) {
        // ignore
      }
    },

    /**
     * 规范化引用/英文字段
     */
    normalizeQuote(data) {
      try {
        const content = (data && data.content) || {};
        let text = '';
        let author = '';
        let translation = '';
        // 1) 标准结构
        if (content.quote) {
          if (typeof content.quote === 'string') {
            text = content.quote;
          } else {
            text = content.quote.text || '';
            author = content.quote.author || '';
            translation = content.quote.translation || '';
          }
        }
        // 2) 兼容 content.english 为字符串
        if (!text && typeof content.english === 'string') {
          text = content.english;
        }
        // 3) 兼容根级 english
        if (!text && data.english) {
          if (typeof data.english === 'string') text = data.english;
          else text = data.english.text || '';
        }
        // 4) 父组件传入的兜底英文
        if (!text && this.data.fallbackEnglish) {
          text = this.data.fallbackEnglish;
        }
        this.setData({
          hasQuote: !!text,
          quoteText: text,
          quoteAuthor: author,
          quoteTranslation: translation
        });
      } catch (e) {
        // ignore
      }
    },

    /**
     * 设置动画效果
     */
    setupAnimations() {
      const { structuredData, showAnimation } = this.data;
      
      if (!showAnimation || !structuredData || !structuredData.visual) {
        return;
      }

      const animationType = structuredData.visual.style_hints?.animation_type || 'float';
      
      // 创建动画
      const animation = wx.createAnimation({
        duration: 2000,
        timingFunction: 'ease-in-out',
        delay: 0
      });

      switch (animationType) {
        case 'float':
          this.startFloatAnimation(animation);
          break;
        case 'pulse':
          this.startPulseAnimation(animation);
          break;
        case 'gradient':
          this.startGradientAnimation();
          break;
        default:
          this.startFloatAnimation(animation);
      }
    },

    /**
     * 浮动动画
     */
    startFloatAnimation(animation) {
      const animate = () => {
        animation.translateY(-10).step({ duration: 2000 });
        animation.translateY(0).step({ duration: 2000 });
        
        this.setData({
          animationData: animation.export(),
          isAnimating: true
        });
        
        setTimeout(() => {
          if (this.data.showAnimation) {
            animate();
          }
        }, 4000);
      };
      
      animate();
    },

    /**
     * 脉冲动画
     */
    startPulseAnimation(animation) {
      const animate = () => {
        animation.scale(1.05).step({ duration: 1000 });
        animation.scale(1).step({ duration: 1000 });
        
        this.setData({
          animationData: animation.export(),
          isAnimating: true
        });
        
        setTimeout(() => {
          if (this.data.showAnimation) {
            animate();
          }
        }, 2000);
      };
      
      animate();
    },

    /**
     * 渐变动画（通过样式变化实现）
     */
    startGradientAnimation() {
      // 渐变动画通过CSS实现，这里只是触发状态
      this.setData({
        isAnimating: true
      });
    },

    /**
     * 切换推荐内容展开状态
     */
    toggleRecommendations() {
      this.setData({
        recommendationsExpanded: !this.data.recommendationsExpanded
      });
    },

    /**
     * 处理卡片点击
     */
    onCardTap() {
      // 触发父组件事件
      this.triggerEvent('cardtap', {
        structuredData: this.data.structuredData
      });
    },

    /**
     * 处理推荐项点击
     */
    onRecommendationTap(e) {
      const { type, item } = e.currentTarget.dataset;
      
      // 触发推荐点击事件
      this.triggerEvent('recommendationtap', {
        type,
        item,
        structuredData: this.data.structuredData
      });
    },

    /**
     * 分享卡片
     */
    shareCard() {
      this.triggerEvent('share', {
        structuredData: this.data.structuredData
      });
    },

    /**
     * 更新动画状态（预处理复杂表达式）
     */
    updateAnimationStates(data) {
      const showGradientAnimation = !!(
        this.data.isAnimating && 
        data.visual && 
        data.visual.style_hints && 
        data.visual.style_hints.animation_type === 'gradient'
      );
      
      this.setData({ showGradientAnimation });
    },

    /**
     * 获取格式化的情绪强度
     */
    getMoodIntensityStars(intensity) {
      const stars = Math.min(Math.max(Math.floor(intensity / 2), 1), 5);
      return '★'.repeat(stars) + '☆'.repeat(5 - stars);
    }
  }
});

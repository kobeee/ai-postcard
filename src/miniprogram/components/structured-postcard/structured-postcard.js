Component({
  /**
   * 结构化明信片组件 - 基于结构化数据的固定模板
   */
  properties: {
    // 结构化数据
    structuredData: {
      type: Object,
      value: {},
    },

    // 🔧 分别传递的字段，作为备用数据源
    cardMood: {
      type: Object,
      value: null,
    },
    cardTitle: {
      type: String,
      value: "",
    },
    cardVisual: {
      type: Object,
      value: null,
    },
    cardContent: {
      type: Object,
      value: null,
    },
    cardContext: {
      type: Object,
      value: null,
    },
    cardRecommendations: {
      type: Object,
      value: null,
    },
    // 背景图片URL（Gemini生成）
    backgroundImage: {
      type: String,
      value: "",
    },
    // 兜底英文（当 structuredData 未提供 quote/english 时由父组件传入）
    fallbackEnglish: {
      type: String,
      value: "",
    },
    // 是否显示动画
    showAnimation: {
      type: Boolean,
      value: true,
    },
    // 卡片尺寸模式
    sizeMode: {
      type: String,
      value: "standard", // standard, compact, large
    },
  },

  data: {
    // 动态样式
    dynamicCardStyle: "",
    dynamicContentStyle: "",
    containerStyle: "",

    // 动画状态
    animationData: {},
    isAnimating: false,

    // 翻转状态
    isFlipped: false,
    isFlipping: false,

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
    quoteText: "",
    quoteAuthor: "",
    quoteTranslation: "",
    // 背面扩展内容（当后端未返回 extras 时，本地兜底）
    extras: null,
  },

  lifetimes: {
    attached() {
      this.initCard()
    },

    ready() {
      this.setupAnimations()
      this.normalizeExtras()
    },
  },

  observers: {
    structuredData: function (newData) {
      if (newData && Object.keys(newData).length > 0) {
        this.updateDynamicStyles(newData)
        this.normalizeRecommendations(newData)
        this.normalizeQuote(newData)
        this.updateAnimationStates(newData)
        this.normalizeExtras(newData)
      }
    },
  },

  methods: {
    /**
     * 初始化卡片
     */
    initCard() {
      const { structuredData } = this.data
      if (structuredData && Object.keys(structuredData).length > 0) {
        this.updateDynamicStyles()
        this.setupAnimations()
        this.normalizeExtras()
      }
    },

    /**
     * 更新动态样式 - 适配新的5层架构
     */
    updateDynamicStyles(data) {
      // 使用传入的数据或组件的数据
      const structuredData = data || this.data.structuredData
      const { sizeMode } = this.data

      if (!structuredData || !structuredData.visual) {
        return
      }

      const styleHints = structuredData.visual.style_hints || {}
      const mood = structuredData.mood || {}

      // 基础尺寸
      const sizeConfig = {
        standard: { width: "690rpx", height: "1100rpx" },
        compact: { width: "690rpx", height: "960rpx" },
        large: { width: "750rpx", height: "1200rpx" },
      }

      const size = sizeConfig[sizeMode] || sizeConfig.standard

      // 容器样式（第1层：card-scene）
      const containerStyle = `width: ${size.width}; height: ${size.height};`

      // 视觉外壳样式（第4层：postcard-shell）- 只负责视觉效果
      let shellStyle = ""
      
      // 主题色彩边框
      if (mood.color_theme) {
        shellStyle += `border: 3rpx solid ${mood.color_theme};`
      }

      // 渐变背景叠加
      if (styleHints.color_scheme && Array.isArray(styleHints.color_scheme)) {
        const [color1, color2] = styleHints.color_scheme
        shellStyle += `background: linear-gradient(135deg, ${color1}20, ${color2}20);`
      }

      // 内容层样式（第5层：postcard-content）- 负责内容布局
      let contentStyle = ""
      if (styleHints.layout_style === "minimal") {
        contentStyle = "padding: 35rpx 25rpx;"
      } else if (styleHints.layout_style === "rich") {
        contentStyle = "padding: 40rpx 30rpx;"
      } else if (styleHints.layout_style === "artistic") {
        contentStyle = "padding: 45rpx 35rpx; text-align: center;"
      } else {
        // 默认紧凑布局
        contentStyle = "padding: 30rpx 25rpx;"
      }

      this.setData({
        containerStyle,           // 用于 card-scene
        dynamicCardStyle: shellStyle,  // 用于 postcard-shell
        dynamicContentStyle: contentStyle, // 用于 postcard-content
      })
    },

    /**
     * 规范化推荐数据，兼容对象/数组
     */
    normalizeRecommendations(data) {
      try {
        const rec = (data && data.recommendations) || {}
        const pickFirst = (value) => {
          if (!value) return null
          return Array.isArray(value) ? value[0] || null : value
        }
        const recMusic = pickFirst(rec.music)
        const recBook = pickFirst(rec.book)
        const recMovie = pickFirst(rec.movie)
        this.setData({
          recMusic,
          recBook,
          recMovie,
          hasMusic: !!(recMusic && recMusic.title),
          hasBook: !!(recBook && recBook.title),
          hasMovie: !!(recMovie && recMovie.title),
        })
      } catch (e) {
        // ignore
      }
    },

    /**
     * 规范化引用/英文字段
     */
    normalizeQuote(data) {
      try {
        const content = (data && data.content) || {}
        let text = ""
        let author = ""
        let translation = ""
        // 1) 标准结构
        if (content.quote) {
          if (typeof content.quote === "string") {
            text = content.quote
          } else {
            text = content.quote.text || ""
            author = content.quote.author || ""
            translation = content.quote.translation || ""
          }
        }
        // 2) 兼容 content.english 为字符串
        if (!text && typeof content.english === "string") {
          text = content.english
        }
        // 3) 兼容根级 english
        if (!text && data.english) {
          if (typeof data.english === "string") text = data.english
          else text = data.english.text || ""
        }
        // 4) 父组件传入的兜底英文
        if (!text && this.data.fallbackEnglish) {
          text = this.data.fallbackEnglish
        }
        this.setData({
          hasQuote: !!text,
          quoteText: text,
          quoteAuthor: author,
          quoteTranslation: translation,
        })
      } catch (e) {
        // ignore
      }
    },

    /**
     * 兜底生成背面扩展内容（extras），避免背面与推荐内容重复且过于单调
     */
    normalizeExtras(raw) {
      try {
        const data = raw || this.data.structuredData || {}
        if (data.extras && Object.keys(data.extras).length > 0) {
          this.setData({ extras: data.extras })
          return
        }

        const content = data.content || {}
        const mood = data.mood || {}

        const reflections = []
        if (content.sub_text && typeof content.sub_text === "string") {
          reflections.push(content.sub_text.slice(0, 14))
        } else if (content.main_text) {
          reflections.push(String(content.main_text).slice(0, 14))
        }

        const gratitude = []
        if (content.hot_topics) {
          const ht = content.hot_topics
          const pick = [ht.xiaohongshu, ht.douyin].filter(Boolean)[0]
          if (pick) gratitude.push(String(pick).slice(0, 12))
        }
        if (gratitude.length === 0 && mood.primary) {
          gratitude.push(`感谢当下的${mood.primary}`.slice(0, 12))
        }

        const microActions = []
        microActions.push("深呼吸3次")
        microActions.push("步行10分钟")

        const moodTips = []
        if (this.data.quoteTranslation) {
          moodTips.push(String(this.data.quoteTranslation).slice(0, 14))
        } else if (this.data.quoteText) {
          moodTips.push(String(this.data.quoteText).slice(0, 16))
        } else if (mood.primary) {
          moodTips.push(`${mood.primary}的好方式：写下一句`.slice(0, 16))
        }

        const extras = {
          reflections,
          gratitude,
          micro_actions: microActions,
          mood_tips: moodTips,
        }
        this.setData({ extras })
      } catch (e) {
        // ignore
      }
    },

    /**
     * 设置动画效果
     */
    setupAnimations() {
      const { structuredData, showAnimation } = this.data

      if (!showAnimation || !structuredData || !structuredData.visual) {
        return
      }

      const animationType = structuredData.visual.style_hints?.animation_type || "float"

      const animation = wx.createAnimation({
        duration: 3000,
        timingFunction: "cubic-bezier(0.25, 0.46, 0.45, 0.94)",
        delay: 0,
      })

      switch (animationType) {
        case "float":
          this.startFloatAnimation(animation)
          break
        case "pulse":
          this.startPulseAnimation(animation)
          break
        case "gradient":
          this.startGradientAnimation()
          break
        default:
          this.startFloatAnimation(animation)
      }
    },

    /**
     * 浮动动画
     */
    startFloatAnimation(animation) {
      const animate = () => {
        animation.translateY(-6).step({ duration: 2500 })
        animation.translateY(0).step({ duration: 2500 })

        this.setData({
          animationData: animation.export(),
          isAnimating: true,
        })

        setTimeout(() => {
          if (this.data.showAnimation) {
            animate()
          }
        }, 5000)
      }

      animate()
    },

    /**
     * 脉冲动画
     */
    startPulseAnimation(animation) {
      const animate = () => {
        animation.scale(1.02).step({ duration: 1500 })
        animation.scale(1).step({ duration: 1500 })

        this.setData({
          animationData: animation.export(),
          isAnimating: true,
        })

        setTimeout(() => {
          if (this.data.showAnimation) {
            animate()
          }
        }, 3000)
      }

      animate()
    },

    /**
     * 渐变动画（通过样式变化实现）
     */
    startGradientAnimation() {
      // 渐变动画通过CSS实现，这里只是触发状态
      this.setData({
        isAnimating: true,
      })
    },

    /**
     * 切换推荐内容展开状态
     */
    toggleRecommendations(e) {
      e && e.stopPropagation && e.stopPropagation()

      // 添加触觉反馈
      wx.vibrateShort &&
        wx.vibrateShort({
          type: "light",
        })

      const newState = !this.data.recommendationsExpanded
      this.setData({
        recommendationsExpanded: newState,
      })

      // 显示状态提示
      wx.showToast({
        title: newState ? "展开推荐" : "收起推荐",
        icon: "none",
        duration: 800,
      })
    },

    /**
     * 处理卡片点击
     */
    onCardTap() {
      if (this.data.isFlipping) {
        return
      }

      this.setData({ isFlipping: true })

      // 添加触觉反馈
      wx.vibrateShort &&
        wx.vibrateShort({
          type: "light",
        })

      // 翻转卡片
      this.setData({
        isFlipped: !this.data.isFlipped,
      })

      setTimeout(() => {
        this.setData({ isFlipping: false })
      }, 800) // 对应CSS动画0.8s

      // 触发父组件事件
      this.triggerEvent("cardtap", {
        structuredData: this.data.structuredData,
        isFlipped: this.data.isFlipped,
      })

      wx.showToast({
        title: this.data.isFlipped ? "查看详情" : "返回正面",
        icon: "none",
        duration: 1000,
      })
    },

    /**
     * 处理推荐项点击
     */
    onRecommendationTap(e) {
      e.stopPropagation()

      // 添加触觉反馈
      wx.vibrateShort &&
        wx.vibrateShort({
          type: "light",
        })

      const { type, item } = e.currentTarget.dataset

      // 触发推荐点击事件
      this.triggerEvent("recommendationtap", {
        type,
        item,
        structuredData: this.data.structuredData,
      })
    },

    /**
     * 分享卡片
     */
    shareCard(e) {
      e && e.stopPropagation && e.stopPropagation()

      // 添加触觉反馈
      wx.vibrateShort &&
        wx.vibrateShort({
          type: "medium",
        })

      this.triggerEvent("share", {
        structuredData: this.data.structuredData,
      })
    },

    /**
     * 更新动画状态（预处理复杂表达式）
     */
    updateAnimationStates(data) {
      const showGradientAnimation = !!(
        this.data.isAnimating &&
        data.visual &&
        data.visual.style_hints &&
        data.visual.style_hints.animation_type === "gradient"
      )

      this.setData({ showGradientAnimation })
    },

    /**
     * 获取格式化的情绪强度
     */
    getMoodIntensityStars(intensity) {
      const stars = Math.min(Math.max(Math.floor(intensity / 2), 1), 5)
      return "★".repeat(stars) + "☆".repeat(5 - stars)
    },

    /**
     * 生成卡片截图 - 当前正面展开推荐状态
     */
    async generateScreenshot() {
      try {
        // 确保推荐内容展开以捕获完整卡片
        const originalExpanded = this.data.recommendationsExpanded
        if (!originalExpanded) {
          this.setData({ recommendationsExpanded: true })
          // 等待界面更新完成
          await new Promise(resolve => setTimeout(resolve, 300))
        }

        // 使用微信小程序的 canvasToTempFilePath API 生成截图
        const result = await new Promise((resolve, reject) => {
          const query = wx.createSelectorQuery().in(this)
          query.select('.card-scene').boundingClientRect()
          query.exec((res) => {
            if (!res[0]) {
              reject(new Error('无法获取卡片元素'))
              return
            }

            const rect = res[0]
            
            // 创建临时 canvas
            const ctx = wx.createCanvasContext('screenshot-canvas', this)
            
            // 设置canvas尺寸
            const pixelRatio = wx.getSystemInfoSync().pixelRatio || 2
            const canvasWidth = rect.width * pixelRatio
            const canvasHeight = rect.height * pixelRatio

            // 由于小程序限制，我们无法直接截图DOM
            // 使用 canvasToTempFilePath 需要先在 canvas 上绘制内容
            // 这里使用替代方案：返回当前卡片的背景图片
            
            const { backgroundImage } = this.data
            const { structuredData } = this.data
            
            if (backgroundImage) {
              resolve(backgroundImage)
            } else if (structuredData && structuredData.visual && structuredData.visual.background_image_url) {
              resolve(structuredData.visual.background_image_url)
            } else {
              reject(new Error('无可用的卡片图片'))
            }
          })
        })

        // 恢复原始展开状态
        if (!originalExpanded) {
          this.setData({ recommendationsExpanded: originalExpanded })
        }

        return result
      } catch (error) {
        console.error('生成卡片截图失败:', error)
        throw error
      }
    },

    /**
     * 高级DOM截图方案 - 使用Canvas绘制
     */
    async generateCanvasScreenshot() {
      try {
        const { structuredData, backgroundImage, isFlipped } = this.data
        
        if (!structuredData) {
          throw new Error('缺少卡片数据')
        }

        // 确保显示正面且推荐展开
        const originalFlipped = isFlipped
        const originalExpanded = this.data.recommendationsExpanded
        
        if (originalFlipped) {
          this.setData({ isFlipped: false })
        }
        if (!originalExpanded) {
          this.setData({ recommendationsExpanded: true })
        }
        
        // 等待界面更新
        await new Promise(resolve => setTimeout(resolve, 500))

        // 先处理异步的背景图片下载
        let backgroundImagePath = null
        if (backgroundImage) {
          try {
            console.log('开始下载Gemini背景图片:', backgroundImage)
            const res = await new Promise((resolve, reject) => {
              wx.downloadFile({
                url: backgroundImage,
                success: resolve,
                fail: reject
              })
            })
            backgroundImagePath = res.tempFilePath
            console.log('Gemini背景图片下载成功:', backgroundImagePath)
          } catch (error) {
            console.warn('背景图片下载失败，跳过:', error)
          }
        } else {
          console.log('没有backgroundImage，使用渐变背景')
        }

        return new Promise((resolve, reject) => {
          const canvasId = 'screenshot-canvas'
          const ctx = wx.createCanvasContext(canvasId, this)
          
          // Canvas尺寸 (按实际卡片比例)
          const canvasWidth = 375 // 逻辑像素
          const canvasHeight = 500
          
          // 1. 首先绘制Gemini背景图片（如果有的话）
          if (backgroundImagePath) {
            console.log('在Canvas中绘制Gemini背景图片:', backgroundImagePath)
            // 绘制Gemini生成的背景图片，填满整个Canvas
            ctx.drawImage(backgroundImagePath, 0, 0, canvasWidth, canvasHeight)
            
            // 在背景图片上添加轻微的渐变遮罩以确保文字可读
            const overlayGradient = ctx.createLinearGradient(0, 0, 0, canvasHeight)
            overlayGradient.addColorStop(0, 'rgba(103, 126, 234, 0.2)')
            overlayGradient.addColorStop(1, 'rgba(118, 75, 162, 0.3)')
            ctx.fillStyle = overlayGradient
            ctx.fillRect(0, 0, canvasWidth, canvasHeight)
            console.log('Gemini背景图片和遮罩绘制完成')
          } else {
            console.log('使用渐变背景作为降级方案')
            // 如果没有背景图片，使用渐变背景作为降级方案
            const gradient = ctx.createLinearGradient(0, 0, 0, canvasHeight)
            gradient.addColorStop(0, '#667eea')
            gradient.addColorStop(1, '#764ba2')
            ctx.fillStyle = gradient
            ctx.fillRect(0, 0, canvasWidth, canvasHeight)
          }
          
          // 2. 添加内容区域的半透明背景（提升文字可读性）
          ctx.fillStyle = 'rgba(255, 255, 255, 0.15)'
          ctx.fillRect(20, 20, canvasWidth - 40, canvasHeight - 40)
          
          // 添加文字阴影效果以提升可读性
          ctx.shadowColor = 'rgba(0, 0, 0, 0.8)'
          ctx.shadowBlur = 4
          ctx.shadowOffsetX = 1
          ctx.shadowOffsetY = 1
          
          // 绘制卡片标题
          const title = structuredData.title || structuredData.content?.main_text || '今日心情'
          ctx.fillStyle = '#ffffff'
          ctx.font = 'bold 24px sans-serif'
          ctx.textAlign = 'center'
          ctx.fillText(title, canvasWidth / 2, 80)
          
          // 绘制心情
          const mood = structuredData.mood?.primary || 'calm'
          ctx.font = '18px sans-serif'
          ctx.fillStyle = 'rgba(255, 255, 255, 0.95)'
          ctx.fillText(`心情：${mood}`, canvasWidth / 2, 120)
          
          // 绘制位置信息
          const location = structuredData.context?.location || '未知位置'
          ctx.fillText(`位置：${location}`, canvasWidth / 2, 150)
          
          // 绘制推荐内容标题
          ctx.font = 'bold 20px sans-serif'
          ctx.fillStyle = '#ffffff'
          ctx.textAlign = 'center'
          ctx.fillText('今日推荐', canvasWidth / 2, 200)
          
          // 为推荐内容创建半透明背景区域
          ctx.shadowColor = 'transparent' // 暂时关闭阴影
          ctx.fillStyle = 'rgba(255, 255, 255, 0.1)'
          ctx.fillRect(30, 220, canvasWidth - 60, 120)
          
          // 恢复阴影设置
          ctx.shadowColor = 'rgba(0, 0, 0, 0.8)'
          ctx.shadowBlur = 3
          ctx.shadowOffsetX = 1
          ctx.shadowOffsetY = 1
          
          // 绘制音乐推荐
          const music = this.data.recMusic
          if (music && music.title) {
            ctx.font = '16px sans-serif'
            ctx.fillStyle = 'rgba(255, 255, 255, 0.95)'
            ctx.textAlign = 'left'
            ctx.fillText(`🎵 ${music.title}`, 40, 240)
            if (music.artist) {
              ctx.font = '14px sans-serif'
              ctx.fillStyle = 'rgba(255, 255, 255, 0.8)'
              ctx.fillText(`   by ${music.artist}`, 40, 260)
            }
          }
          
          // 绘制书籍推荐
          const book = this.data.recBook
          if (book && book.title) {
            ctx.font = '16px sans-serif'
            ctx.fillStyle = 'rgba(255, 255, 255, 0.95)'
            ctx.fillText(`📚 ${book.title}`, 40, 290)
            if (book.author) {
              ctx.font = '14px sans-serif'
              ctx.fillStyle = 'rgba(255, 255, 255, 0.8)'
              ctx.fillText(`   by ${book.author}`, 40, 310)
            }
          }
          
          // 绘制电影推荐
          const movie = this.data.recMovie
          if (movie && movie.title) {
            ctx.font = '16px sans-serif'
            ctx.fillStyle = 'rgba(255, 255, 255, 0.95)'
            ctx.fillText(`🎬 ${movie.title}`, 40, 330)
          }
          
          // 绘制英文引用（底部区域）
          if (this.data.hasQuote && this.data.quoteText) {
            // 为引用创建单独的背景区域
            ctx.shadowColor = 'transparent'
            ctx.fillStyle = 'rgba(0, 0, 0, 0.2)'
            ctx.fillRect(20, 380, canvasWidth - 40, 80)
            
            // 恢复阴影
            ctx.shadowColor = 'rgba(0, 0, 0, 0.8)'
            ctx.shadowBlur = 2
            
            ctx.font = 'italic 14px serif'
            ctx.fillStyle = 'rgba(255, 255, 255, 0.9)'
            ctx.textAlign = 'center'
            
            // 处理长文本换行
            const quoteText = this.data.quoteText
            if (quoteText.length > 40) {
              const firstLine = quoteText.substring(0, 40)
              const secondLine = quoteText.substring(40)
              ctx.fillText(`"${firstLine}"`, canvasWidth / 2, 410)
              ctx.fillText(`"${secondLine}"`, canvasWidth / 2, 430)
            } else {
              ctx.fillText(`"${quoteText}"`, canvasWidth / 2, 420)
            }
            
            if (this.data.quoteTranslation) {
              ctx.font = '12px sans-serif'
              ctx.fillStyle = 'rgba(255, 255, 255, 0.7)'
              ctx.fillText(`"${this.data.quoteTranslation}"`, canvasWidth / 2, 450)
            }
          }
          
          // 绘制完成，导出图片
          ctx.draw(false, () => {
            wx.canvasToTempFilePath({
              canvasId,
              success: (res) => {
                // 恢复原始状态
                this.setData({ 
                  isFlipped: originalFlipped,
                  recommendationsExpanded: originalExpanded 
                })
                resolve(res.tempFilePath)
              },
              fail: (err) => {
                // 恢复原始状态
                this.setData({ 
                  isFlipped: originalFlipped,
                  recommendationsExpanded: originalExpanded 
                })
                reject(err)
              }
            }, this)
          })
        })
      } catch (error) {
        console.error('Canvas截图失败:', error)
        throw error
      }
    },
  },
})

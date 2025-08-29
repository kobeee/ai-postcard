// components/dynamic-postcard/dynamic-postcard.js
Component({
  properties: {
    // 明信片数据
    postcardData: {
      type: Object,
      value: {},
      observer: 'onPostcardDataChange'
    },
    
    // 小程序组件代码
    miniprogramComponent: {
      type: Object,
      value: null,
      observer: 'onComponentChange'
    },
    
    // 是否包含动画
    hasAnimation: {
      type: Boolean,
      value: false
    },
    
    // 是否包含交互
    hasInteractive: {
      type: Boolean,
      value: false
    }
  },

  data: {
    // 动态样式
    dynamicStyle: '',
    
    // 是否有富文本内容
    hasRichContent: false,
    
    // 富文本节点
    richNodes: [],
    
    // 动画数据
    animationData: null,
    
    // 组件状态
    componentReady: false
  },

  lifetimes: {
    attached() {
      this.initializeComponent();
    },

    ready() {
      this.setData({ componentReady: true });
      this.applyDynamicStyles();
    }
  },

  methods: {
    /**
     * 初始化组件
     */
    initializeComponent() {
      if (this.data.miniprogramComponent) {
        this.renderDynamicComponent();
      } else {
        this.renderFallbackContent();
      }
      
      if (this.data.hasAnimation) {
        this.initializeAnimations();
      }
    },

    /**
     * 明信片数据变化处理
     */
    onPostcardDataChange(newData) {
      if (this.data.componentReady) {
        this.initializeComponent();
      }
    },

    /**
     * 组件代码变化处理
     */
    onComponentChange(newComponent) {
      if (this.data.componentReady && newComponent) {
        this.renderDynamicComponent();
      }
    },

    /**
     * 渲染动态组件
     */
    renderDynamicComponent() {
      const component = this.data.miniprogramComponent;
      if (!component) return;

      try {
        // 解析WXML内容转换为rich-text节点
        if (component.wxml) {
          const richNodes = this.parseWxmlToRichText(component.wxml);
          this.setData({
            richNodes,
            hasRichContent: richNodes.length > 0
          });
        }

        // 应用WXSS样式
        if (component.wxss) {
          this.applyDynamicStyles(component.wxss);
        }

        // 执行JS逻辑（简化版本，主要处理数据和事件）
        if (component.js) {
          this.executeDynamicLogic(component.js);
        }

      } catch (error) {
        this.renderFallbackContent();
      }
    },

    /**
     * 渲染兜底内容
     */
    renderFallbackContent() {
      this.setData({
        hasRichContent: false,
        richNodes: []
      });
    },

    /**
     * 解析WXML为rich-text节点（简化版本）
     */
    parseWxmlToRichText(wxml) {
      try {
        // 简单的WXML到HTML转换
        let html = wxml
          .replace(/<view/g, '<div')
          .replace(/<\/view>/g, '</div>')
          .replace(/<text/g, '<span')
          .replace(/<\/text>/g, '</span>')
          .replace(/\{\{([^}]+)\}\}/g, (match, expression) => {
            // 处理数据绑定，这里简化处理
            return this.evaluateExpression(expression);
          });

        // 转换为rich-text支持的节点格式
        return [{
          name: 'div',
          attrs: {
            class: 'dynamic-content'
          },
          children: [{
            type: 'text',
            text: html
          }]
        }];
      } catch (error) {
        return [];
      }
    },

    /**
     * 应用动态样式
     */
    applyDynamicStyles(wxss) {
      if (!wxss) return;

      try {
        // 提取样式规则并转换为内联样式
        const styleRules = this.extractStyleRules(wxss);
        const dynamicStyle = this.convertToInlineStyle(styleRules);
        
        this.setData({ dynamicStyle });
      } catch (error) {
      }
    },

    /**
     * 提取CSS样式规则
     */
    extractStyleRules(wxss) {
      const rules = {};
      
      // 简单的CSS解析（生产环境需要更完善的解析器）
      const matches = wxss.match(/\.([^{]+)\s*\{([^}]+)\}/g);
      if (matches) {
        matches.forEach(rule => {
          const [, selector, styles] = rule.match(/\.([^{]+)\s*\{([^}]+)\}/);
          if (selector && styles) {
            rules[selector.trim()] = styles.trim();
          }
        });
      }

      return rules;
    },

    /**
     * 转换为内联样式
     */
    convertToInlineStyle(rules) {
      // 提取主要容器样式
      const containerStyle = rules['postcard-container'] || rules['container'] || '';
      
      // 转换rpx单位
      return containerStyle.replace(/(\d+)rpx/g, (match, num) => {
        const px = Math.round(num / 2); // rpx to px conversion
        return `${px}px`;
      });
    },

    /**
     * 执行动态逻辑（简化版本）
     */
    executeDynamicLogic(jsCode) {
      try {
        // 提取数据定义
        const dataMatch = jsCode.match(/data\s*:\s*\{([^}]+)\}/);
        if (dataMatch) {
        }

        // 提取方法定义
        const methodsMatch = jsCode.match(/methods\s*:\s*\{([\s\S]*)\}/);
        if (methodsMatch) {
        }
      } catch (error) {
      }
    },

    /**
     * 计算表达式值（简化版本）
     */
    evaluateExpression(expression) {
      // 这里需要根据实际的数据上下文来计算
      // 简化处理：直接返回表达式或默认值
      const data = this.data.postcardData;
      
      if (expression === 'content') {
        return data.content || '';
      } else if (expression === 'concept') {
        return data.concept || '';
      }
      
      return expression;
    },

    /**
     * 初始化动画
     */
    initializeAnimations() {
      // 创建基础动画
      const animation = wx.createAnimation({
        duration: 1000,
        timingFunction: 'ease',
        delay: 0
      });

      // 执行入场动画
      animation.opacity(1).scale(1).rotate(0).step();
      
      this.setData({
        animationData: animation.export()
      });

      // 循环动画（如果需要）
      this.startLoopAnimation();
    },

    /**
     * 开始循环动画
     */
    startLoopAnimation() {
      if (!this.data.hasAnimation) return;

      const animation = wx.createAnimation({
        duration: 2000,
        timingFunction: 'ease-in-out'
      });

      // 创建呼吸效果
      animation.scale(1.02).step({ duration: 1000 });
      animation.scale(1.0).step({ duration: 1000 });

      this.setData({
        animationData: animation.export()
      });

      // 继续循环
      setTimeout(() => {
        if (this.data.hasAnimation) {
          this.startLoopAnimation();
        }
      }, 2000);
    },

    /**
     * 处理点击事件
     */
    onPostcardTap() {
      if (this.data.hasInteractive) {
        // 触发交互动画
        this.triggerInteractiveAnimation();
      }
      
      // 触发自定义事件
      this.triggerEvent('postcardtap', {
        postcardData: this.data.postcardData
      });
    },

    /**
     * 触发交互动画
     */
    triggerInteractiveAnimation() {
      const animation = wx.createAnimation({
        duration: 300,
        timingFunction: 'ease-out'
      });

      // 点击反馈动画
      animation.scale(0.95).step({ duration: 150 });
      animation.scale(1.0).step({ duration: 150 });

      this.setData({
        animationData: animation.export()
      });
    }
  }
});
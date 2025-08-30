// utils/data-parser.js - 统一的数据解析工具

/**
 * 智能提取文本中的JSON数据
 * @param {string} text - 包含JSON的文本
 * @returns {Object|null} - 解析后的JSON对象或null
 */
function extractJsonFromText(text) {
  if (!text || typeof text !== 'string') return null;
  
  // 移除markdown代码块包装
  const cleanText = text.replace(/```json\s*([\s\S]*?)\s*```/g, '$1').trim();
  
  // 尝试直接解析
  try {
    return JSON.parse(cleanText);
  } catch (e) {
    // 尝试提取第一个JSON对象
    const jsonMatch = cleanText.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      try {
        return JSON.parse(jsonMatch[0]);
      } catch (e2) {
        return null;
      }
    }
    return null;
  }
}

/**
 * 构建标准结构化数据格式
 * @param {Object} rawData - 解析出的原始数据
 * @returns {Object} - 标准化的结构化数据
 */
function buildStructuredFromParsed(rawData) {
  // 处理中文键名的数据
  if (rawData['主题概念'] || rawData['文案方向']) {
    return {
      title: rawData['主标题'] || rawData['主题概念'] || '今日心情',
      content: {
        main_text: rawData['正文内容'] || rawData['主题概念'] || '暂无内容',
        quote: {
          text: 'Every day deserves to be gently remembered',
          translation: '每一天都值得被温柔记录'
        }
      },
      visual: {
        style_hints: {
          color_scheme: ['#6366f1', '#8b5cf6'],
          layout_style: 'artistic',
          animation_type: 'float'
        }
      },
      mood: {
        primary: '宁静',
        intensity: 7,
        color_theme: '#6366f1'
      },
      context: {
        location: '当前位置',
        weather: '舒适'
      },
      recommendations: generateDefaultRecommendations(rawData)
    };
  }
  
  // 如果已经是标准格式
  if (rawData.title || rawData.content) {
    return rawData;
  }
  
  // 默认格式
  return {
    title: 'AI明信片',
    content: {
      main_text: typeof rawData === 'string' ? rawData : JSON.stringify(rawData, null, 2),
      quote: {
        text: 'Every moment is worth remembering',
        translation: '每一刻都值得记住'
      }
    },
    visual: {
      style_hints: {
        color_scheme: ['#3b82f6', '#1e40af'],
        layout_style: 'minimal',
        animation_type: 'pulse'
      }
    }
  };
}

/**
 * 生成默认推荐内容
 * @param {Object} rawData - 原始数据
 * @returns {Object} - 推荐内容对象
 */
function generateDefaultRecommendations(rawData) {
  return {
    music: [{
      title: '轻音乐推荐',
      artist: '放松音乐',
      reason: '适合当前心境'
    }],
    book: [{
      title: '心灵读物',
      author: '推荐作者',
      reason: '陶冶情操'
    }]
  };
}

/**
 * 标准数据解析函数 - 必须在所有页面统一使用
 * @param {Object} cardData - 后端返回的原始卡片数据
 * @returns {Object} - 解析结果对象
 */
function parseCardData(cardData) {
  let structuredData = null;
  let hasStructuredData = false;
  let debugInfo = {
    originalContent: cardData.content ? cardData.content.substring(0, 200) + '...' : 'null',
    contentType: typeof cardData.content,
    hasStructuredDataField: !!cardData.structured_data,
    hasMiniprogramComponent: !!cardData.miniprogram_component,
    hasFrontendCode: !!cardData.frontend_code
  };

  try {
    // 🆕 优先使用后端扁平化字段（字段名与后端API协议一致）
    if (cardData.mood_primary || cardData.card_title || cardData.content_main_text) {
      
      structuredData = {};
      
      // 只添加非空字段
      if (cardData.card_title) {
        structuredData.title = cardData.card_title;
      }
      
      // 情绪数据 - 只在有数据时创建
      const mood = {};
      if (cardData.mood_primary) mood.primary = cardData.mood_primary;
      if (cardData.mood_intensity) mood.intensity = cardData.mood_intensity;
      if (cardData.mood_secondary) mood.secondary = cardData.mood_secondary;
      if (cardData.mood_color_theme) mood.color_theme = cardData.mood_color_theme;
      if (Object.keys(mood).length > 0) {
        structuredData.mood = mood;
      }
      
      // 视觉样式 - 只在有数据时创建
      const visual = { style_hints: {} };
      if (cardData.visual_color_scheme) visual.style_hints.color_scheme = cardData.visual_color_scheme;
      if (cardData.visual_layout_style) visual.style_hints.layout_style = cardData.visual_layout_style;
      if (cardData.visual_animation_type) visual.style_hints.animation_type = cardData.visual_animation_type;
      if (cardData.visual_background_image || cardData.image_url) {
        visual.background_image_url = cardData.visual_background_image || cardData.image_url;
      }
      if (Object.keys(visual.style_hints).length > 0 || visual.background_image_url) {
        structuredData.visual = visual;
      }
      
      // 内容数据 - 只在有数据时创建
      const content = {};
      if (cardData.content_main_text) content.main_text = cardData.content_main_text;
      
      // 引用 - 只在有数据时创建
      const quote = {};
      if (cardData.content_quote_text) quote.text = cardData.content_quote_text;
      if (cardData.content_quote_author) quote.author = cardData.content_quote_author;
      if (cardData.content_quote_translation) quote.translation = cardData.content_quote_translation;
      if (Object.keys(quote).length > 0) {
        content.quote = quote;
      }
      
      // 热点话题 - 只在有数据时创建
      const hot_topics = {};
      if (cardData.content_hot_topics_douyin) hot_topics.douyin = cardData.content_hot_topics_douyin;
      if (cardData.content_hot_topics_xiaohongshu) hot_topics.xiaohongshu = cardData.content_hot_topics_xiaohongshu;
      if (Object.keys(hot_topics).length > 0) {
        content.hot_topics = hot_topics;
      }
      
      if (Object.keys(content).length > 0) {
        structuredData.content = content;
      }
      
      // 上下文 - 只在有数据时创建
      const context = {};
      if (cardData.context_weather) context.weather = cardData.context_weather;
      if (cardData.context_location) context.location = cardData.context_location;
      if (cardData.context_time) context.time_context = cardData.context_time;
      if (Object.keys(context).length > 0) {
        structuredData.context = context;
      }
      
      // 推荐内容 - 只在有数据时创建
      const recommendations = {};
      if (cardData.recommendations_music_title) {
        recommendations.music = [{
          title: cardData.recommendations_music_title,
          artist: cardData.recommendations_music_artist,
          reason: cardData.recommendations_music_reason
        }];
      }
      if (cardData.recommendations_book_title) {
        recommendations.book = [{
          title: cardData.recommendations_book_title,
          author: cardData.recommendations_book_author,
          reason: cardData.recommendations_book_reason
        }];
      }
      if (cardData.recommendations_movie_title) {
        recommendations.movie = [{
          title: cardData.recommendations_movie_title,
          director: cardData.recommendations_movie_director,
          reason: cardData.recommendations_movie_reason
        }];
      }
      if (Object.keys(recommendations).length > 0) {
        structuredData.recommendations = recommendations;
      }
      
      // 🆕 扩展字段处理 - 8个extras字段，支持卡片背面丰富内容
      const extras = {};
      
      // reflections - 深度思考与反思
      if (cardData.extras_reflections) {
        try {
          extras.reflections = Array.isArray(cardData.extras_reflections) 
            ? cardData.extras_reflections 
            : JSON.parse(cardData.extras_reflections);
        } catch (e) {
          if (typeof cardData.extras_reflections === 'string') {
            extras.reflections = [cardData.extras_reflections];
          }
        }
      }
      
      // gratitude - 感恩内容
      if (cardData.extras_gratitude) {
        try {
          extras.gratitude = Array.isArray(cardData.extras_gratitude) 
            ? cardData.extras_gratitude 
            : JSON.parse(cardData.extras_gratitude);
        } catch (e) {
          if (typeof cardData.extras_gratitude === 'string') {
            extras.gratitude = [cardData.extras_gratitude];
          }
        }
      }
      
      // micro_actions - 微行动建议
      if (cardData.extras_micro_actions) {
        try {
          extras.micro_actions = Array.isArray(cardData.extras_micro_actions) 
            ? cardData.extras_micro_actions 
            : JSON.parse(cardData.extras_micro_actions);
        } catch (e) {
          if (typeof cardData.extras_micro_actions === 'string') {
            extras.micro_actions = [cardData.extras_micro_actions];
          }
        }
      }
      
      // mood_tips - 情绪管理建议
      if (cardData.extras_mood_tips) {
        try {
          extras.mood_tips = Array.isArray(cardData.extras_mood_tips) 
            ? cardData.extras_mood_tips 
            : JSON.parse(cardData.extras_mood_tips);
        } catch (e) {
          if (typeof cardData.extras_mood_tips === 'string') {
            extras.mood_tips = [cardData.extras_mood_tips];
          }
        }
      }
      
      // life_insights - 人生感悟
      if (cardData.extras_life_insights) {
        try {
          extras.life_insights = Array.isArray(cardData.extras_life_insights) 
            ? cardData.extras_life_insights 
            : JSON.parse(cardData.extras_life_insights);
        } catch (e) {
          if (typeof cardData.extras_life_insights === 'string') {
            extras.life_insights = [cardData.extras_life_insights];
          }
        }
      }
      
      // creative_spark - 创意火花
      if (cardData.extras_creative_spark) {
        try {
          extras.creative_spark = Array.isArray(cardData.extras_creative_spark) 
            ? cardData.extras_creative_spark 
            : JSON.parse(cardData.extras_creative_spark);
        } catch (e) {
          if (typeof cardData.extras_creative_spark === 'string') {
            extras.creative_spark = [cardData.extras_creative_spark];
          }
        }
      }
      
      // mindfulness - 正念练习
      if (cardData.extras_mindfulness) {
        try {
          extras.mindfulness = Array.isArray(cardData.extras_mindfulness) 
            ? cardData.extras_mindfulness 
            : JSON.parse(cardData.extras_mindfulness);
        } catch (e) {
          if (typeof cardData.extras_mindfulness === 'string') {
            extras.mindfulness = [cardData.extras_mindfulness];
          }
        }
      }
      
      // future_vision - 未来愿景
      if (cardData.extras_future_vision) {
        try {
          extras.future_vision = Array.isArray(cardData.extras_future_vision) 
            ? cardData.extras_future_vision 
            : JSON.parse(cardData.extras_future_vision);
        } catch (e) {
          if (typeof cardData.extras_future_vision === 'string') {
            extras.future_vision = [cardData.extras_future_vision];
          }
        }
      }
      
      // 只在有内容时添加extras字段
      if (Object.keys(extras).length > 0) {
        structuredData.extras = extras;
      }
      
      hasStructuredData = true;
      debugInfo.parseSuccess = true;
      debugInfo.dataSource = 'backend_flattened';
      debugInfo.parsedKeys = Object.keys(structuredData);
      
      return { structuredData, hasStructuredData, debugInfo };
    }
    
    // 1. 降级：使用structured_data字段 - 这是最重要的数据源
    if (cardData.structured_data) {
      let parsedStructuredData = cardData.structured_data;
      
      // 处理字符串格式的structured_data
      if (typeof parsedStructuredData === 'string') {
        try {
          // 智能提取JSON（处理markdown包裹等情况）
          parsedStructuredData = extractJsonFromText(parsedStructuredData) || JSON.parse(parsedStructuredData);
        } catch (e) {
          parsedStructuredData = null;
        }
      }
      
      if (parsedStructuredData && typeof parsedStructuredData === 'object') {
        structuredData = parsedStructuredData;
        hasStructuredData = true;
        debugInfo.parseSuccess = true;
        debugInfo.dataSource = 'structured_data';
        debugInfo.parsedKeys = Object.keys(parsedStructuredData);
        
        // 确保背景图片URL存在
        if (!structuredData.visual) structuredData.visual = {};
        if (!structuredData.visual.background_image_url && cardData.image_url) {
          structuredData.visual.background_image_url = cardData.image_url;
        }
        
        return { structuredData, hasStructuredData, debugInfo };
      }
    }
    
    // 2. 降级：解析content字段中的JSON
    if (cardData.content && typeof cardData.content === 'string') {
      const parsed = extractJsonFromText(cardData.content);
      if (parsed) {
        structuredData = buildStructuredFromParsed(parsed);
        hasStructuredData = true;
        debugInfo.parseSuccess = true;
        debugInfo.dataSource = 'content_json';
        debugInfo.parsedKeys = Object.keys(parsed);
        
        // 附加背景图片
        if (cardData.image_url) {
          if (!structuredData.visual) structuredData.visual = {};
          structuredData.visual.background_image_url = cardData.image_url;
        }
        
        return { structuredData, hasStructuredData, debugInfo };
      }
    }
    
    // 3. 最终降级：使用概念字段或创建默认格式
    let title = 'AI明信片';
    let mainText = '每一天都值得被温柔记录';
    
    if (cardData.concept) {
      try {
        const conceptData = extractJsonFromText(cardData.concept);
        if (conceptData && conceptData['主题概念']) {
          title = conceptData['主题概念'];
        }
      } catch (e) {
        // 如果concept不是JSON，直接作为标题使用
        title = cardData.concept;
      }
    }
    
    if (cardData.content && typeof cardData.content === 'string' && !cardData.content.includes('{')) {
      // 如果content是纯文本（不包含JSON）
      mainText = cardData.content;
    }
    
    structuredData = {
      title,
      content: {
        main_text: mainText,
        quote: {
          text: 'Every day deserves to be gently remembered',
          translation: '每一天都值得被温柔记录'
        }
      },
      visual: {
        style_hints: {
          color_scheme: ['#3b82f6', '#1e40af'],
          layout_style: 'minimal',
          animation_type: 'pulse'
        },
        background_image_url: cardData.image_url
      },
      mood: {
        primary: '平静',
        intensity: 5,
        color_theme: '#3b82f6'
      },
      context: {
        location: '当前位置',
        weather: '舒适'
      }
    };
    
    hasStructuredData = true;
    debugInfo.parseSuccess = true;
    debugInfo.dataSource = 'default_fallback';
    
  } catch (error) {
    debugInfo.parseError = error.message;
    debugInfo.parseSuccess = false;
  }

  // 最终验证和修复机制
  if (structuredData) {
    // 验证关键字段
    const requiredFields = ['mood', 'title', 'visual', 'content', 'context'];
    const missingFields = [];
    
    requiredFields.forEach(field => {
      if (!structuredData[field]) {
        missingFields.push(field);
      }
    });
    
    if (missingFields.length > 0) {
      // 尝试从原始数据补充
      if (!structuredData.title && (cardData.concept || cardData.content)) {
        try {
          const conceptData = extractJsonFromText(cardData.concept) || {};
          structuredData.title = conceptData['主题概念'] || conceptData['主标题'] || '明信片';
        } catch (e) {
          structuredData.title = '明信片';
        }
      }
    }
  }

  return { structuredData, hasStructuredData, debugInfo };
}

/**
 * 获取背景图片URL（按优先级）
 * @param {Object} cardData - 卡片数据
 * @returns {string} - 背景图片URL
 */
function getBackgroundImageUrl(cardData) {
  return (cardData.structured_data?.visual?.background_image_url ||
          cardData.card_image_url ||
          cardData.image_url ||
          '');
}

module.exports = {
  parseCardData,
  extractJsonFromText,
  buildStructuredFromParsed,
  getBackgroundImageUrl
};
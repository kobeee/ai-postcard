// utils/card-data-manager.js - 卡片数据管理和缓存工具

const { parseCardData } = require('./data-parser.js');
const { TimeFormatter } = require('./time-formatter.js');
const envConfig = require('../config/env.js');

/**
 * 卡片数据缓存管理器
 */
class CardDataManager {
  
  /**
   * 构建卡片缓存键名
   */
  static getCacheKey(cardId) {
    return `postcard_${cardId}`;
  }
  
  /**
   * 构建用户卡片列表缓存键名
   */
  static getUserCardsKey(userId) {
    return `user_cards_${userId}`;
  }
  
  /**
   * 处理原始卡片数据为可用格式
   * 从首页逻辑提取，确保一致性
   */
  static processCardData(rawCardData) {
    try {
      // 使用统一的数据解析逻辑
      const parseResult = parseCardData(rawCardData);
      
      // 格式化创建时间 - 使用统一的时间处理工具
      // 保存原始UTC时间用于业务逻辑，同时提供格式化时间用于显示
      const formattedCard = {
        ...rawCardData,
        // 保存原始UTC时间（用于逻辑判断）
        created_at_utc: rawCardData.created_at,
        // 格式化后的时间（用于显示）
        created_at: rawCardData.created_at ? 
          TimeFormatter.formatToChineseLocal(rawCardData.created_at) : rawCardData.created_at
      };
      
      // 构建完整的卡片数据对象
      const processedData = {
        // 原始数据
        originalCard: formattedCard,
        // 解析后的结构化数据
        structuredData: parseResult.structuredData,
        // 是否有有效的结构化数据
        hasStructuredData: parseResult.hasStructuredData,
        // 调试信息
        debugInfo: parseResult.debugInfo,
        // 缓存时间戳
        cachedAt: Date.now(),
        // 卡片ID
        cardId: rawCardData.id
      };
      
      envConfig.log('卡片数据处理完成:', {
        cardId: rawCardData.id,
        hasStructuredData: parseResult.hasStructuredData,
        structuredKeys: parseResult.structuredData ? Object.keys(parseResult.structuredData) : []
      });
      
      return processedData;
      
    } catch (error) {
      envConfig.error('处理卡片数据失败:', error);
      return {
        originalCard: rawCardData,
        structuredData: null,
        hasStructuredData: false,
        debugInfo: { error: error.message },
        cachedAt: Date.now(),
        cardId: rawCardData.id
      };
    }
  }
  
  /**
   * 缓存卡片数据
   */
  static cacheCard(cardId, processedData) {
    try {
      const cacheKey = this.getCacheKey(cardId);
      wx.setStorageSync(cacheKey, processedData);
      envConfig.log('卡片数据已缓存:', cacheKey);
      return true;
    } catch (error) {
      envConfig.error('缓存卡片数据失败:', error);
      return false;
    }
  }
  
  /**
   * 获取缓存的卡片数据
   */
  static getCachedCard(cardId) {
    try {
      const cacheKey = this.getCacheKey(cardId);
      const cachedData = wx.getStorageSync(cacheKey);
      
      if (cachedData && cachedData.cardId === cardId) {
        // 检查缓存是否过期（24小时）
        const cacheAge = Date.now() - (cachedData.cachedAt || 0);
        const maxAge = 24 * 60 * 60 * 1000; // 24小时
        
        if (cacheAge < maxAge) {
          envConfig.log('从缓存获取卡片数据:', cardId);
          return cachedData;
        } else {
          envConfig.log('缓存已过期，清理:', cardId);
          this.clearCard(cardId);
        }
      }
      
      return null;
    } catch (error) {
      envConfig.error('获取缓存卡片数据失败:', error);
      return null;
    }
  }
  
  /**
   * 清理指定卡片的缓存
   */
  static clearCard(cardId) {
    try {
      const cacheKey = this.getCacheKey(cardId);
      wx.removeStorageSync(cacheKey);
      envConfig.log('已清理卡片缓存:', cardId);
      return true;
    } catch (error) {
      envConfig.error('清理卡片缓存失败:', error);
      return false;
    }
  }
  
  /**
   * 批量清理用户的所有卡片缓存
   */
  static clearUserCards(userId) {
    try {
      // 获取所有存储的键
      const info = wx.getStorageInfoSync();
      const keys = info.keys || [];
      
      // 查找并清理该用户相关的缓存
      keys.forEach(key => {
        if (key.startsWith('postcard_')) {
          try {
            const data = wx.getStorageSync(key);
            if (data && data.originalCard && data.originalCard.user_id === userId) {
              wx.removeStorageSync(key);
              envConfig.log('清理用户卡片缓存:', key);
            }
          } catch (e) {
            // 忽略单个键的错误
          }
        }
      });
      
      // 清理用户卡片列表缓存
      const userCardsKey = this.getUserCardsKey(userId);
      wx.removeStorageSync(userCardsKey);
      
      return true;
    } catch (error) {
      envConfig.error('批量清理用户卡片缓存失败:', error);
      return false;
    }
  }
  
  /**
   * 从候选列表中挑选首个可用资源URL
   */
  static pickAssetUrl(candidates) {
    if (!candidates || !candidates.length) {
      return '';
    }
    for (let i = 0; i < candidates.length; i++) {
      const value = candidates[i];
      if (value) {
        return value;
      }
    }
    return '';
  }

  /**
   * 将来源中存在的资源字段补回到目标对象
   */
  static mergeAssetFields(target, source, fields) {
    if (!target || !source || !fields) {
      return;
    }
    fields.forEach((field) => {
      if (!target[field] && source[field]) {
        target[field] = source[field];
      }
    });
  }

  /**
   * 统一原始卡片上的资源字段，确保别名一致
   */
  static normalizeOriginalCardAssets(card) {
    if (!card) {
      return;
    }
    const primary = this.pickAssetUrl([
      card.card_image_url,
      card.image_url,
      card.image,
      card.visual_background_image
    ]);

    if (primary) {
      if (!card.card_image_url) card.card_image_url = primary;
      if (!card.image_url) card.image_url = primary;
      if (!card.image) card.image = primary;
      if (!card.visual_background_image) card.visual_background_image = primary;
    }
  }

  /**
   * 统一结构化数据中的背景资源字段
   */
  static normalizeStructuredAssets(structured, fallback) {
    if (!structured || typeof structured !== 'object') {
      return;
    }

    if (!structured.visual) {
      structured.visual = {};
    }

    const visual = structured.visual;
    const primary = this.pickAssetUrl([
      visual.background_image_url,
      structured.visual_background_image,
      structured.image_url,
      fallback
    ]);

    if (primary) {
      if (!visual.background_image_url) {
        visual.background_image_url = primary;
      }
      if (!structured.visual_background_image) {
        structured.visual_background_image = primary;
      }
    }
  }

  /**
   * 在缓存前补齐缺失的资源字段，避免覆盖已有图片
   */
  static preserveExistingAssets(processedData, existingData) {
    if (!processedData) {
      return;
    }

    const originalCard = processedData.originalCard || {};
    const existingOriginal = existingData && existingData.originalCard ? existingData.originalCard : null;

    if (existingOriginal) {
      this.mergeAssetFields(originalCard, existingOriginal, [
        'card_image_url',
        'image_url',
        'image',
        'visual_background_image'
      ]);
    }

    let structured = processedData.structuredData;
    let structuredIsObject = structured && typeof structured === 'object';

    if (structuredIsObject) {
      if (existingData && existingData.structuredData) {
        const existingStructured = existingData.structuredData;
        const existingStructuredIsObject = existingStructured && typeof existingStructured === 'object';
        const existingBackground = this.pickAssetUrl([
          existingStructuredIsObject && existingStructured.visual ? existingStructured.visual.background_image_url : '',
          existingStructuredIsObject ? existingStructured.visual_background_image : '',
          existingOriginal ? existingOriginal.card_image_url : '',
          existingOriginal ? existingOriginal.image_url : ''
        ]);

        if (existingBackground) {
          if (!structured.visual) {
            structured.visual = {};
          }
          if (!structured.visual.background_image_url) {
            structured.visual.background_image_url = existingBackground;
          }
          if (!structured.visual_background_image) {
            structured.visual_background_image = existingBackground;
          }
        }
      }

      const fallbackBackground = this.pickAssetUrl([
        structured.visual ? structured.visual.background_image_url : '',
        structured.visual_background_image,
        originalCard.card_image_url,
        originalCard.image_url,
        originalCard.image,
        originalCard.visual_background_image
      ]);

      this.normalizeStructuredAssets(structured, fallbackBackground);

      const syncedBackground = this.pickAssetUrl([
        structured.visual ? structured.visual.background_image_url : '',
        structured.visual_background_image,
        fallbackBackground
      ]);

      if (syncedBackground) {
        if (!originalCard.card_image_url) originalCard.card_image_url = syncedBackground;
        if (!originalCard.image_url) originalCard.image_url = syncedBackground;
        if (!originalCard.image) originalCard.image = syncedBackground;
        if (!originalCard.visual_background_image) originalCard.visual_background_image = syncedBackground;
      }
    } else if (existingData && existingData.structuredData && typeof existingData.structuredData === 'object') {
      processedData.structuredData = existingData.structuredData;
      processedData.hasStructuredData = processedData.hasStructuredData || existingData.hasStructuredData;
      structured = processedData.structuredData;
      structuredIsObject = structured && typeof structured === 'object';

      if (structuredIsObject) {
        const fallback = this.pickAssetUrl([
          structured.visual ? structured.visual.background_image_url : '',
          structured.visual_background_image,
          existingOriginal ? existingOriginal.card_image_url : '',
          existingOriginal ? existingOriginal.image_url : ''
        ]);

        this.normalizeStructuredAssets(structured, fallback);
      }
    }

    this.normalizeOriginalCardAssets(originalCard);
    processedData.originalCard = originalCard;
  }

  /**
   * 处理并缓存卡片数据（一站式服务）
   */
  static processAndCacheCard(rawCardData) {
    if (!rawCardData || !rawCardData.id) {
      envConfig.error('无效的卡片数据');
      return null;
    }
    
    // 处理数据
    const existingData = this.getCachedCard(rawCardData.id);
    const processedData = this.processCardData(rawCardData);

    // 在写入前保留已有资源，避免覆盖已生成的图片
    this.preserveExistingAssets(processedData, existingData);
    
    // 缓存数据
    this.cacheCard(rawCardData.id, processedData);
    
    return processedData;
  }
  
  /**
   * 获取或创建卡片数据（先查缓存，再处理）
   */
  static getOrCreateCardData(cardId, rawCardData = null) {
    // 先尝试从缓存获取
    let cachedData = this.getCachedCard(cardId);
    
    if (cachedData) {
      return cachedData;
    }
    
    // 缓存不存在，需要原始数据进行处理
    if (!rawCardData) {
      envConfig.warn('缓存不存在且未提供原始数据:', cardId);
      return null;
    }
    
    // 处理并缓存新数据
    return this.processAndCacheCard(rawCardData);
  }
  
  /**
   * 更新卡片的页面标题
   */
  static updatePageTitle(processedData) {
    if (!processedData) return;
    
    try {
      const title = processedData.structuredData?.oracle_card_title || 
                   processedData.structuredData?.title || 
                   processedData.structuredData?.ai_selected_charm_name || 
                   processedData.originalCard?.keyword ||
                   '心象签详情';
      
      wx.setNavigationBarTitle({ title });
    } catch (error) {
      envConfig.error('设置页面标题失败:', error);
    }
  }

  /**
   * 检查卡片是否为今日创建
   * @param {Object} cardData - 卡片数据 
   * @returns {boolean} 是否为今日创建
   */
  static isCardToday(cardData) {
    if (!cardData || !cardData.created_at) {
      return false;
    }
    
    try {
      // 优先使用原始UTC时间数据
      let timeToCheck = cardData.created_at_utc || cardData.created_at;
      
      // 如果是已经格式化的时间（包含中文），则无法准确判断
      if (typeof timeToCheck === 'string' && timeToCheck.includes('年')) {
        envConfig.warn('仅有格式化的时间数据，无法准确进行今日判断:', timeToCheck);
        return false;
      }
      
      return TimeFormatter.isToday(timeToCheck);
    } catch (error) {
      envConfig.error('判断是否为今日卡片失败:', error);
      return false;
    }
  }
}

module.exports = {
  CardDataManager
};

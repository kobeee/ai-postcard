// utils/card-data-manager.js - 卡片数据管理和缓存工具

const { parseCardData } = require('./data-parser.js');
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
      
      // 格式化创建时间
      const formattedCard = {
        ...rawCardData,
        created_at: rawCardData.created_at ? 
          new Date(rawCardData.created_at).toLocaleString('zh-CN', {
            year: 'numeric',
            month: 'long', 
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
          }) : rawCardData.created_at
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
   * 处理并缓存卡片数据（一站式服务）
   */
  static processAndCacheCard(rawCardData) {
    if (!rawCardData || !rawCardData.id) {
      envConfig.error('无效的卡片数据');
      return null;
    }
    
    // 处理数据
    const processedData = this.processCardData(rawCardData);
    
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
}

module.exports = {
  CardDataManager
};
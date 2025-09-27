// utils/resource-cache.js - 资源缓存管理器
const envConfig = require('../config/env.js');

/**
 * 资源缓存管理器
 * 负责下载、缓存和管理小程序资源文件
 */
class ResourceCacheManager {
  constructor() {
    this.cachePrefix = 'resource_cache_';
    this.maxCacheSize = 50 * 1024 * 1024; // 50MB缓存上限
    this.cacheExpiry = 7 * 24 * 60 * 60 * 1000; // 7天过期时间
  }

  /**
   * 获取缓存的资源URL
   * @param {string} resourceUrl - 远程资源URL
   * @returns {Promise<string>} 本地缓存路径或原URL
   */
  async getCachedResourceUrl(resourceUrl) {
    if (!resourceUrl) return '';

    try {
      // 生成缓存key
      const cacheKey = this.generateCacheKey(resourceUrl);
      
      // 检查缓存是否存在且未过期
      const cachedResource = await this.getCachedResource(cacheKey);
      if (cachedResource && await this.isFileExists(cachedResource.localPath)) {
        envConfig.log('🔄 使用缓存资源:', cachedResource.localPath);
        return cachedResource.localPath;
      }

      // 缓存不存在或已过期，下载新资源
      envConfig.log('📥 下载新资源:', resourceUrl);
      const localPath = await this.downloadAndCacheResource(resourceUrl, cacheKey);
      return localPath;

    } catch (error) {
      envConfig.error('资源缓存获取失败:', error);
      return resourceUrl; // 降级返回原URL
    }
  }

  /**
   * 下载并缓存资源
   * @param {string} resourceUrl - 远程资源URL
   * @param {string} cacheKey - 缓存键
   * @returns {Promise<string>} 本地文件路径
   */
  downloadAndCacheResource(resourceUrl, cacheKey) {
    return new Promise((resolve, reject) => {
      wx.downloadFile({
        url: resourceUrl,
        timeout: 15000, // 15秒超时
        success: async (res) => {
          if (res.statusCode === 200) {
            try {
              // 保存到缓存记录
              const cacheData = {
                originalUrl: resourceUrl,
                localPath: res.tempFilePath,
                downloadTime: Date.now(),
                fileSize: await this.getFileSize(res.tempFilePath)
              };

              await this.saveCachedResource(cacheKey, cacheData);
              
              // 检查缓存大小，必要时清理
              this.cleanupCacheIfNeeded();

              envConfig.log('✅ 资源下载缓存成功:', res.tempFilePath);
              resolve(res.tempFilePath);

            } catch (error) {
              envConfig.error('保存缓存失败:', error);
              resolve(res.tempFilePath); // 即使缓存失败，也返回临时文件
            }
          } else {
            reject(new Error(`下载失败: HTTP ${res.statusCode}`));
          }
        },
        fail: (error) => {
          envConfig.error('资源下载失败:', error);
          reject(error);
        }
      });
    });
  }

  /**
   * 批量预下载资源
   * @param {Array<string>} resourceUrls - 资源URL数组
   * @returns {Promise<Object>} 下载结果映射
   */
  async preloadResources(resourceUrls) {
    if (!Array.isArray(resourceUrls) || resourceUrls.length === 0) {
      return {};
    }

    envConfig.log('🚀 开始批量预下载资源:', resourceUrls.length);
    
    const results = {};
    const downloadPromises = resourceUrls.map(async (url) => {
      try {
        const localPath = await this.getCachedResourceUrl(url);
        results[url] = { success: true, localPath };
      } catch (error) {
        results[url] = { success: false, error: error.message };
      }
    });

    await Promise.allSettled(downloadPromises);
    
    const successCount = Object.values(results).filter(r => r.success).length;
    envConfig.log('✅ 批量预下载完成:', `${successCount}/${resourceUrls.length}`);
    
    return results;
  }

  /**
   * 生成缓存键
   * @param {string} url - 原始URL
   * @returns {string} 缓存键
   */
  generateCacheKey(url) {
    // 使用URL的hash作为缓存键，确保唯一性
    let hash = 0;
    for (let i = 0; i < url.length; i++) {
      const char = url.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // 转换为32位整数
    }
    return `${this.cachePrefix}${Math.abs(hash).toString(36)}`;
  }

  /**
   * 获取缓存的资源信息
   * @param {string} cacheKey - 缓存键
   * @returns {Promise<Object|null>} 缓存资源信息
   */
  async getCachedResource(cacheKey) {
    try {
      const cachedData = wx.getStorageSync(cacheKey);
      if (!cachedData) return null;

      // 检查是否过期
      const now = Date.now();
      if (now - cachedData.downloadTime > this.cacheExpiry) {
        // 过期，删除缓存
        wx.removeStorageSync(cacheKey);
        return null;
      }

      return cachedData;
    } catch (error) {
      envConfig.error('获取缓存资源失败:', error);
      return null;
    }
  }

  /**
   * 保存缓存资源信息
   * @param {string} cacheKey - 缓存键
   * @param {Object} cacheData - 缓存数据
   */
  async saveCachedResource(cacheKey, cacheData) {
    try {
      wx.setStorageSync(cacheKey, cacheData);
    } catch (error) {
      envConfig.error('保存缓存资源失败:', error);
      throw error;
    }
  }

  /**
   * 检查文件是否存在
   * @param {string} filePath - 文件路径
   * @returns {Promise<boolean>} 文件是否存在
   */
  isFileExists(filePath) {
    return new Promise((resolve) => {
      wx.getFileInfo({
        filePath,
        success: () => resolve(true),
        fail: () => resolve(false)
      });
    });
  }

  /**
   * 获取文件大小
   * @param {string} filePath - 文件路径
   * @returns {Promise<number>} 文件大小（字节）
   */
  getFileSize(filePath) {
    return new Promise((resolve) => {
      wx.getFileInfo({
        filePath,
        success: (res) => resolve(res.size || 0),
        fail: () => resolve(0)
      });
    });
  }

  /**
   * 必要时清理缓存
   */
  async cleanupCacheIfNeeded() {
    try {
      const storageInfo = wx.getStorageInfoSync();
      const currentSize = storageInfo.currentSize * 1024; // 转换为字节
      
      if (currentSize > this.maxCacheSize * 0.8) {
        envConfig.log('🧹 开始清理资源缓存');
        await this.cleanupOldCache();
      }
    } catch (error) {
      envConfig.error('缓存清理检查失败:', error);
    }
  }

  /**
   * 清理过期缓存
   */
  async cleanupOldCache() {
    try {
      const storageInfo = wx.getStorageInfoSync();
      const allKeys = storageInfo.keys.filter(key => key.startsWith(this.cachePrefix));
      
      const now = Date.now();
      let cleanedCount = 0;

      for (const key of allKeys) {
        try {
          const cachedData = wx.getStorageSync(key);
          if (cachedData && (now - cachedData.downloadTime > this.cacheExpiry)) {
            wx.removeStorageSync(key);
            cleanedCount++;
          }
        } catch (error) {
          // 删除损坏的缓存记录
          wx.removeStorageSync(key);
          cleanedCount++;
        }
      }

      envConfig.log('🧹 缓存清理完成:', `清理了${cleanedCount}个过期资源`);
    } catch (error) {
      envConfig.error('缓存清理失败:', error);
    }
  }

  /**
   * 手动清除所有缓存
   */
  async clearAllCache() {
    try {
      const storageInfo = wx.getStorageInfoSync();
      const cacheKeys = storageInfo.keys.filter(key => key.startsWith(this.cachePrefix));
      
      for (const key of cacheKeys) {
        wx.removeStorageSync(key);
      }

      envConfig.log('🧹 已清除所有资源缓存:', `${cacheKeys.length}个`);
      
    } catch (error) {
      envConfig.error('清除缓存失败:', error);
    }
  }

  /**
   * 获取缓存统计信息
   * @returns {Object} 缓存统计
   */
  getCacheStats() {
    try {
      const storageInfo = wx.getStorageInfoSync();
      const cacheKeys = storageInfo.keys.filter(key => key.startsWith(this.cachePrefix));
      
      let totalSize = 0;
      let validCount = 0;
      const now = Date.now();

      for (const key of cacheKeys) {
        try {
          const cachedData = wx.getStorageSync(key);
          if (cachedData && (now - cachedData.downloadTime <= this.cacheExpiry)) {
            totalSize += cachedData.fileSize || 0;
            validCount++;
          }
        } catch (error) {
          // 忽略损坏的缓存记录
        }
      }

      return {
        totalCacheKeys: cacheKeys.length,
        validResources: validCount,
        totalSize: totalSize,
        maxSize: this.maxCacheSize,
        usagePercent: Math.round((totalSize / this.maxCacheSize) * 100)
      };
    } catch (error) {
      envConfig.error('获取缓存统计失败:', error);
      return {
        totalCacheKeys: 0,
        validResources: 0,
        totalSize: 0,
        maxSize: this.maxCacheSize,
        usagePercent: 0
      };
    }
  }
}

// 单例实例
const resourceCache = new ResourceCacheManager();

module.exports = {
  resourceCache,
  ResourceCacheManager
};
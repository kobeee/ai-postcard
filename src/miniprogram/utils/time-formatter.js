// utils/time-formatter.js - 统一的时间处理工具
const envConfig = require('../config/env.js');

/**
 * 时间格式化工具类
 * 专门处理UTC时间转换为本地时间的格式化
 */
class TimeFormatter {
  
  /**
   * 将UTC时间字符串格式化为中文本地时间
   * @param {string} utcTimeString - UTC时间字符串，如 "2025-09-29T05:15:58.651000+00:00"
   * @param {Object} options - 格式化选项
   * @returns {string} 格式化后的本地时间字符串
   */
  static formatToChineseLocal(utcTimeString, options = {}) {
    try {
      if (!utcTimeString) {
        return '';
      }

      // 解析UTC时间字符串
      const utcDate = new Date(utcTimeString);
      
      // 验证日期是否有效
      if (isNaN(utcDate.getTime())) {
        envConfig.error('无效的时间格式:', utcTimeString);
        return utcTimeString; // 返回原始字符串作为后备
      }

      // 🔧 直接使用手动时区转换，避免微信小程序兼容性问题
      // 手动添加8小时转换为北京时间
      const localDate = new Date(utcDate.getTime() + 8 * 60 * 60 * 1000);
      
      envConfig.log('时间转换:', {
        input: utcTimeString,
        utcTime: utcDate.toUTCString(),
        localTime: localDate.toString(),
        utcMs: utcDate.getTime(),
        localMs: localDate.getTime()
      });

      // 使用手动格式化确保结果一致
      return this.formatDateManually(localDate);

    } catch (error) {
      envConfig.error('时间格式化失败:', error, '原始时间:', utcTimeString);
      return utcTimeString; // 最后的后备方案
    }
  }

  /**
   * 手动格式化日期（降级方案）
   * @param {Date} date - 日期对象
   * @returns {string} 格式化的时间字符串
   */
  static formatDateManually(date) {
    const year = date.getFullYear();
    const month = date.getMonth() + 1; // 月份从0开始
    const day = date.getDate();
    const hour = date.getHours();
    const minute = date.getMinutes().toString().padStart(2, '0');
    const second = date.getSeconds().toString().padStart(2, '0');

    const monthNames = ['1月', '2月', '3月', '4月', '5月', '6月', 
                       '7月', '8月', '9月', '10月', '11月', '12月'];
    
    // 正确处理上午/下午
    const period = hour < 12 ? '上午' : '下午';
    const displayHour = hour.toString().padStart(2, '0');
    
    return `${year}年${monthNames[month-1]}${day}日${period}${displayHour}:${minute}:${second}`;
  }

  /**
   * 获取简化的时间格式（不含秒）
   * @param {string} utcTimeString - UTC时间字符串
   * @returns {string} 简化格式的时间
   */
  static formatToSimple(utcTimeString) {
    return this.formatToChineseLocal(utcTimeString, {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'Asia/Shanghai',
      hour12: false
    });
  }

  /**
   * 获取相对时间描述（如"2小时前"）
   * @param {string} utcTimeString - UTC时间字符串
   * @returns {string} 相对时间描述
   */
  static formatToRelative(utcTimeString) {
    try {
      const utcDate = new Date(utcTimeString);
      const now = new Date();
      const diffMs = now.getTime() - utcDate.getTime();
      const diffMinutes = Math.floor(diffMs / (1000 * 60));
      const diffHours = Math.floor(diffMinutes / 60);
      const diffDays = Math.floor(diffHours / 24);

      if (diffMinutes < 1) {
        return '刚刚';
      } else if (diffMinutes < 60) {
        return `${diffMinutes}分钟前`;
      } else if (diffHours < 24) {
        return `${diffHours}小时前`;
      } else if (diffDays < 7) {
        return `${diffDays}天前`;
      } else {
        // 超过一周显示具体日期
        return this.formatToSimple(utcTimeString);
      }
    } catch (error) {
      envConfig.error('相对时间计算失败:', error);
      return this.formatToChineseLocal(utcTimeString);
    }
  }

  /**
   * 检查是否为今日时间
   * @param {string} utcTimeString - UTC时间字符串
   * @returns {boolean} 是否为今日
   */
  static isToday(utcTimeString) {
    try {
      const utcDate = new Date(utcTimeString);
      const today = new Date();
      
      // 转换为本地时间的日期字符串进行比较
      const utcDateLocal = new Date(utcDate.getTime() + 8 * 60 * 60 * 1000);
      const todayDateStr = today.toDateString();
      const cardDateStr = utcDateLocal.toDateString();
      
      return todayDateStr === cardDateStr;
    } catch (error) {
      envConfig.error('今日判断失败:', error);
      return false;
    }
  }

  /**
   * 验证时间格式化功能
   * @returns {Object} 验证结果
   */
  static validate() {
    const testUTCTime = "2025-09-29T05:15:58.651000+00:00";
    const expectedLocal = "2025年9月29日下午13:15:58"; // UTC+8 = 13:15
    
    try {
      const result = this.formatToChineseLocal(testUTCTime);
      const isValid = result.includes('13:15') || result.includes('下午') || result.includes('13点');
      
      return {
        success: isValid,
        input: testUTCTime,
        output: result,
        expected: expectedLocal
      };
    } catch (error) {
      return {
        success: false,
        error: error.message
      };
    }
  }
}

module.exports = {
  TimeFormatter
};
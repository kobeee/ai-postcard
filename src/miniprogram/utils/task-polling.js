// utils/task-polling.js - 异步任务轮询工具
const { postcardAPI } = require('./request.js');
const envConfig = require('../config/env.js');

/**
 * 任务轮询管理器
 */
class TaskPollingManager {
  constructor() {
    this.pollingTasks = new Map(); // 存储正在轮询的任务
    this.defaultInterval = 2000; // 默认轮询间隔2秒
    this.maxRetries = 60; // 最大重试次数（2分钟）
  }
  
  /**
   * 开始轮询任务状态
   * @param {string} taskId 任务ID
   * @param {Object} options 轮询选项
   * @returns {Promise} 返回最终结果的Promise
   */
  startPolling(taskId, options = {}) {
    const {
      interval = this.defaultInterval,
      maxRetries = this.maxRetries,
      onProgress = null,
      onStatusChange = null
    } = options;
    
    // 如果任务已在轮询中，返回现有Promise
    if (this.pollingTasks.has(taskId)) {
      envConfig.log(`任务 ${taskId} 已在轮询中`);
      return this.pollingTasks.get(taskId).promise;
    }
    
    envConfig.log(`开始轮询任务: ${taskId}`);
    
    // 创建轮询Promise
    const pollingPromise = new Promise((resolve, reject) => {
      let retryCount = 0;
      let lastStatus = null;
      
      const poll = async () => {
        try {
          // 检查是否已取消轮询
          if (!this.pollingTasks.has(taskId)) {
            envConfig.log(`任务 ${taskId} 轮询已取消`);
            reject(new Error('轮询已取消'));
            return;
          }
          
          // 查询任务状态
          const result = await postcardAPI.getStatus(taskId);
          const { status, progress, error } = result;
          
          envConfig.log(`任务 ${taskId} 状态:`, { status, progress });
          
          // 状态变化回调
          if (status !== lastStatus && onStatusChange) {
            onStatusChange(status, progress);
          }
          lastStatus = status;
          
          // 进度回调
          if (onProgress && progress) {
            onProgress(progress);
          }
          
          // 检查任务状态
          switch (status) {
            case 'completed':
              // 任务完成，获取最终结果
              try {
                const finalResult = await postcardAPI.getResult(taskId);
                this.stopPolling(taskId);
                resolve(finalResult);
              } catch (resultError) {
                envConfig.error(`获取任务结果失败: ${taskId}`, resultError);
                this.stopPolling(taskId);
                reject(resultError);
              }
              break;
              
            case 'failed':
              // 任务失败
              this.stopPolling(taskId);
              reject(new Error(error || '任务处理失败'));
              break;
              
            case 'pending':
            case 'processing':
              // 任务进行中，继续轮询
              retryCount++;
              if (retryCount >= maxRetries) {
                this.stopPolling(taskId);
                reject(new Error('任务处理超时'));
              } else {
                setTimeout(poll, interval);
              }
              break;
              
            default:
              // 未知状态
              envConfig.error(`未知任务状态: ${status}`);
              retryCount++;
              if (retryCount >= maxRetries) {
                this.stopPolling(taskId);
                reject(new Error(`未知任务状态: ${status}`));
              } else {
                setTimeout(poll, interval);
              }
          }
          
        } catch (error) {
          envConfig.error(`轮询任务状态失败: ${taskId}`, error);
          
          retryCount++;
          if (retryCount >= maxRetries) {
            this.stopPolling(taskId);
            reject(error);
          } else {
            // 网络错误等，延长间隔后重试
            setTimeout(poll, interval * 2);
          }
        }
      };
      
      // 开始首次轮询
      poll();
    });
    
    // 存储轮询任务信息
    this.pollingTasks.set(taskId, {
      promise: pollingPromise,
      startTime: Date.now(),
      interval,
      maxRetries
    });
    
    // Promise完成后清理
    pollingPromise.finally(() => {
      this.pollingTasks.delete(taskId);
    });
    
    return pollingPromise;
  }
  
  /**
   * 停止轮询指定任务
   * @param {string} taskId 任务ID
   */
  stopPolling(taskId) {
    if (this.pollingTasks.has(taskId)) {
      envConfig.log(`停止轮询任务: ${taskId}`);
      this.pollingTasks.delete(taskId);
    }
  }
  
  /**
   * 停止所有轮询任务
   */
  stopAllPolling() {
    envConfig.log('停止所有轮询任务');
    this.pollingTasks.clear();
  }
  
  /**
   * 获取当前轮询任务列表
   */
  getPollingTasks() {
    return Array.from(this.pollingTasks.keys());
  }
  
  /**
   * 检查任务是否在轮询中
   * @param {string} taskId 任务ID
   */
  isPolling(taskId) {
    return this.pollingTasks.has(taskId);
  }
  
  /**
   * 获取任务轮询信息
   * @param {string} taskId 任务ID
   */
  getPollingInfo(taskId) {
    const taskInfo = this.pollingTasks.get(taskId);
    if (!taskInfo) return null;
    
    return {
      taskId,
      startTime: taskInfo.startTime,
      duration: Date.now() - taskInfo.startTime,
      interval: taskInfo.interval,
      maxRetries: taskInfo.maxRetries
    };
  }
}

// 创建全局轮询管理器实例
const taskPollingManager = new TaskPollingManager();

// 页面隐藏时停止轮询，页面显示时恢复轮询的工具函数
function setupPagePollingLifecycle(page, taskId) {
  const originalOnHide = page.onHide || function() {};
  const originalOnShow = page.onShow || function() {};
  
  page.onHide = function() {
    envConfig.log('页面隐藏，暂停轮询');
    // 注意：这里不直接停止，而是让轮询自然完成或超时
    originalOnHide.call(this);
  };
  
  page.onShow = function() {
    envConfig.log('页面显示');
    originalOnShow.call(this);
  };
}

module.exports = {
  taskPollingManager,
  
  // 导出常用方法
  startPolling: (taskId, options) => taskPollingManager.startPolling(taskId, options),
  stopPolling: (taskId) => taskPollingManager.stopPolling(taskId),
  stopAllPolling: () => taskPollingManager.stopAllPolling(),
  isPolling: (taskId) => taskPollingManager.isPolling(taskId),
  getPollingInfo: (taskId) => taskPollingManager.getPollingInfo(taskId),
  getPollingTasks: () => taskPollingManager.getPollingTasks(),
  
  // 页面生命周期集成
  setupPagePollingLifecycle,
  
  // 预定义的轮询配置
  POLLING_CONFIGS: {
    // 快速轮询（用于短任务）
    FAST: {
      interval: 1000,
      maxRetries: 30
    },
    
    // 正常轮询（默认）
    NORMAL: {
      interval: 2000,
      maxRetries: 60
    },
    
    // 慢速轮询（用于长任务）
    SLOW: {
      interval: 5000,
      maxRetries: 120
    }
  }
};
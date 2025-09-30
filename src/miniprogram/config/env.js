// config/env.js - 环境配置管理
const ENV_CONFIG = {
  // 开发环境配置
  development: {
    baseURL: 'https://ai.elvis1949.cloudns.pro/postcard', // 网关服务端口
    // baseURL: 'http://localhost:8083', // 网关服务端口
    apiPrefix: '/api/v1',
    timeout: 60000, // 延长到60秒，支持大模型调用和准确性优先
    debug: true,
    // AI Agent服务的公共资源URL（用于动态资源加载）
    AI_AGENT_PUBLIC_URL: 'https://ai.elvis1949.cloudns.pro/postcard-public'
    // AI_AGENT_PUBLIC_URL: 'http://localhost:8080'
  },
  
  // 测试环境配置
  testing: {
    baseURL: 'https://test-api.your-domain.com', // 测试服务器
    apiPrefix: '/api/v1', 
    timeout: 45000, // 测试环境也延长到45秒
    debug: true,
    AI_AGENT_PUBLIC_URL: 'https://test-ai-agent.your-domain.com'
  },
  
  // 生产环境配置
  production: {
    baseURL: 'https://api.your-domain.com', // 生产服务器
    apiPrefix: '/api/v1',
    timeout: 30000, // 生产环境延长到30秒，平衡体验和准确性
    debug: false,
    AI_AGENT_PUBLIC_URL: 'https://ai-agent.your-domain.com'
  }
};

// 获取当前环境
function getCurrentEnv() {
  // 可以通过编译条件或者其他方式判断环境
  // 开发阶段默认使用development
  return 'development';
}

// 导出当前环境配置
const currentEnv = getCurrentEnv();
const config = ENV_CONFIG[currentEnv];

module.exports = {
  ...config,
  currentEnv,
  
  // 获取完整的API URL
  getApiUrl: (path) => {
    return `${config.baseURL}${config.apiPrefix}${path}`;
  },
  
  // 日志输出控制
  log: (...args) => {
    if (config.debug) {
      console.log('[AI明信片]', ...args);
    }
  },
  
  // 错误日志
  error: (...args) => {
    if (config.debug) {
      console.error('[AI明信片错误]', ...args);
    }
  },
  
  // 警告日志
  warn: (...args) => {
    if (config.debug) {
      console.warn('[AI明信片警告]', ...args);
    }
  }
};
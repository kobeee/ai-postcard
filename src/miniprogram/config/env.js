// config/env.js - 环境配置管理
const ENV_CONFIG = {
  // 开发环境配置
  development: {
    baseURL: 'http://localhost:8083', // 网关服务端口
    apiPrefix: '/api/v1',
    timeout: 10000,
    debug: true
  },
  
  // 测试环境配置
  testing: {
    baseURL: 'https://test-api.your-domain.com', // 测试服务器
    apiPrefix: '/api/v1', 
    timeout: 10000,
    debug: true
  },
  
  // 生产环境配置
  production: {
    baseURL: 'https://api.your-domain.com', // 生产服务器
    apiPrefix: '/api/v1',
    timeout: 8000,
    debug: false
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
  }
};
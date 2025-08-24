// utils/network-test.js - 网络连通性测试工具
const envConfig = require('../config/env.js');

/**
 * 网络连通性测试工具
 * 可在微信开发者工具控制台中使用
 */
class NetworkTester {
  constructor() {
    this.results = [];
  }

  /**
   * 测试基础连通性
   */
  async testBasicConnectivity() {
    console.log('🔍 开始基础连通性测试...');
    
    const tests = [
      {
        name: '网关健康检查',
        url: 'http://localhost:8083/health',
        method: 'GET'
      },
      {
        name: '小程序API健康检查',
        url: 'http://localhost:8083/api/v1/miniprogram/health',
        method: 'GET'
      },
      {
        name: '用户服务健康检查',
        url: 'http://localhost:8081/health',
        method: 'GET'
      },
      {
        name: 'PostCard服务健康检查',
        url: 'http://localhost:8082/health',
        method: 'GET'
      }
    ];

    for (const test of tests) {
      await this.runSingleTest(test);
    }

    this.printResults();
  }

  /**
   * 测试API端点
   */
  async testAPIEndpoints() {
    console.log('🔍 开始API端点测试...');
    
    const tests = [
      {
        name: '登录API测试',
        url: 'http://localhost:8083/api/v1/miniprogram/auth/login',
        method: 'POST',
        data: {
          code: 'test_code',
          userInfo: {
            nickName: 'Test User',
            avatarUrl: ''
          }
        }
      },
      {
        name: '获取用户作品API测试',
        url: 'http://localhost:8083/api/v1/miniprogram/postcards/user?user_id=test-user-id&page=1&limit=10',
        method: 'GET'
      }
    ];

    for (const test of tests) {
      await this.runSingleTest(test);
    }

    this.printResults();
  }

  /**
   * 执行单个测试
   */
  async runSingleTest(test) {
    try {
      console.log(`📡 测试: ${test.name}`);
      
      const startTime = Date.now();
      
      const response = await new Promise((resolve, reject) => {
        wx.request({
          url: test.url,
          method: test.method || 'GET',
          data: test.data || {},
          header: {
            'Content-Type': 'application/json'
          },
          timeout: 10000,
          success: resolve,
          fail: reject
        });
      });

      const endTime = Date.now();
      const duration = endTime - startTime;

      const result = {
        name: test.name,
        status: 'SUCCESS',
        statusCode: response.statusCode,
        duration: `${duration}ms`,
        data: response.data,
        url: test.url
      };

      this.results.push(result);
      
      console.log(`✅ ${test.name} - 成功 (${duration}ms)`);
      console.log('响应数据:', response.data);

    } catch (error) {
      const result = {
        name: test.name,
        status: 'FAILED',
        error: error.errMsg || error.message || '未知错误',
        url: test.url
      };

      this.results.push(result);
      
      console.log(`❌ ${test.name} - 失败`);
      console.log('错误信息:', error);
    }
    
    console.log('---');
  }

  /**
   * 打印测试结果汇总
   */
  printResults() {
    console.log('\n📊 测试结果汇总:');
    console.log('=====================================');
    
    const successCount = this.results.filter(r => r.status === 'SUCCESS').length;
    const failCount = this.results.filter(r => r.status === 'FAILED').length;
    
    console.log(`总测试数: ${this.results.length}`);
    console.log(`成功: ${successCount} ✅`);
    console.log(`失败: ${failCount} ❌`);
    console.log('=====================================');
    
    this.results.forEach((result, index) => {
      console.log(`${index + 1}. ${result.name}`);
      console.log(`   状态: ${result.status}`);
      console.log(`   URL: ${result.url}`);
      
      if (result.status === 'SUCCESS') {
        console.log(`   状态码: ${result.statusCode}`);
        console.log(`   耗时: ${result.duration}`);
      } else {
        console.log(`   错误: ${result.error}`);
      }
      console.log('');
    });
    
    // 清空结果，准备下次测试
    this.results = [];
  }

  /**
   * 快速测试当前环境配置
   */
  async quickTest() {
    console.log('⚡ 快速环境测试');
    console.log('当前环境配置:');
    console.log('baseURL:', envConfig.baseURL);
    console.log('apiPrefix:', envConfig.apiPrefix);
    console.log('timeout:', envConfig.timeout);
    console.log('debug:', envConfig.debug);
    console.log('---');
    
    // 测试最关键的端点
    await this.runSingleTest({
      name: '小程序API健康检查',
      url: envConfig.baseURL + '/api/v1/miniprogram/health',
      method: 'GET'
    });
  }

  /**
   * 测试特定URL
   */
  async testURL(url, method = 'GET', data = null) {
    console.log(`🎯 测试指定URL: ${url}`);
    
    await this.runSingleTest({
      name: '自定义URL测试',
      url: url,
      method: method,
      data: data
    });
  }
}

// 创建全局测试实例
const networkTester = new NetworkTester();

// 导出测试工具
module.exports = {
  NetworkTester,
  
  // 快捷方法，可直接在控制台调用
  test: networkTester,
  
  // 快速测试函数
  quickTest: () => networkTester.quickTest(),
  testBasic: () => networkTester.testBasicConnectivity(),
  testAPI: () => networkTester.testAPIEndpoints(),
  testURL: (url, method, data) => networkTester.testURL(url, method, data)
};

// 如果是在控制台环境中，直接挂载到全局
if (typeof global !== 'undefined') {
  global.networkTest = {
    quick: () => networkTester.quickTest(),
    basic: () => networkTester.testBasicConnectivity(),
    api: () => networkTester.testAPIEndpoints(),
    url: (url, method, data) => networkTester.testURL(url, method, data)
  };
}
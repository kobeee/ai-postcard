/**
 * Gateway Service - 最小化 Express 应用
 * 用于环境验证和基础服务测试
 */
const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
require('dotenv').config();

const app = express();
const port = process.env.GATEWAY_PORT || 8080;

// 中间件
app.use(helmet()); // 安全头
app.use(cors()); // 跨域支持
app.use(morgan('combined')); // 请求日志
app.use(express.json()); // JSON 解析
app.use(express.urlencoded({ extended: true })); // URL 编码解析

// 根路径 - 基础健康检查
app.get('/', (req, res) => {
    res.json({
        message: 'Gateway Service is running',
        service: 'gateway-service',
        status: 'healthy',
        timestamp: new Date().toISOString()
    });
});

// 详细健康检查
app.get('/health', (req, res) => {
    res.json({
        status: 'healthy',
        service: 'gateway-service',
        environment: process.env.NODE_ENV || 'development',
        version: '1.0.0',
        uptime: process.uptime(),
        timestamp: new Date().toISOString()
    });
});

// 服务信息
app.get('/info', (req, res) => {
    res.json({
        service: 'gateway-service',
        version: '1.0.0',
        description: 'AI 明信片项目 API 网关',
        environment: process.env.NODE_ENV || 'development',
        endpoints: [
            '/',
            '/health',
            '/info',
            '/api/v1/*'  // 未来的 API 路由
        ],
        upstreamServices: {
            'user-service': process.env.USER_SERVICE_URL || 'http://user-service:8080',
            'postcard-service': process.env.POSTCARD_SERVICE_URL || 'http://postcard-service:8080',
            'ai-agent-service': process.env.AI_AGENT_SERVICE_URL || 'http://ai-agent-service:8000'
        }
    });
});

// API 路由占位符
app.use('/api/v1', (req, res) => {
    res.json({
        message: 'API Gateway - Route not implemented yet',
        path: req.path,
        method: req.method,
        timestamp: new Date().toISOString()
    });
});

// 404 处理
app.use('*', (req, res) => {
    res.status(404).json({
        error: 'Not Found',
        message: `Route ${req.method} ${req.originalUrl} not found`,
        service: 'gateway-service',
        timestamp: new Date().toISOString()
    });
});

// 错误处理中间件
app.use((err, req, res, next) => {
    console.error('Gateway Service Error:', err);
    res.status(err.status || 500).json({
        error: 'Internal Server Error',
        message: process.env.NODE_ENV === 'development' ? err.message : 'Something went wrong',
        service: 'gateway-service',
        timestamp: new Date().toISOString()
    });
});

// 启动服务器
app.listen(port, '0.0.0.0', () => {
    console.log(`Gateway Service running on port ${port}`);
    console.log(`Environment: ${process.env.NODE_ENV || 'development'}`);
    console.log(`Health check: http://localhost:${port}/health`);
});

module.exports = app;

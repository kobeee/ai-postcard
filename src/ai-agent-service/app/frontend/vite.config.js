import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  build: {
    outDir: '../static', // 构建到上级static目录，供FastAPI静态文件服务
    emptyOutDir: true,
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000', // ai-agent-service后端API
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000', // WebSocket代理
        ws: true,
        changeOrigin: true,
      },
    },
  },
})

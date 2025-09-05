import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  build: {
    outDir: 'dist', // 构建到dist目录，供Docker多阶段构建使用
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

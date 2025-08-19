<template>
  <div class="container">
    <!-- 左侧对话区 -->
    <div class="sidebar">
      <div class="header">
        <h2>Lovart.ai 模拟器</h2>
        <div class="status" :class="{ connected: wsConnected, generating: generating }">
          {{ wsConnected ? (generating ? '生成中...' : '已连接') : '未连接' }}
        </div>
      </div>
      
      <div class="chat-list" ref="chatListRef">
        <div v-for="(msg, idx) in chatMessages" :key="idx" :class="['chat-msg', msg.type]">
          <template v-if="msg.type === 'markdown'">
            <MarkdownView :content="msg.content" />
          </template>
          <template v-else-if="msg.type === 'error'">
            <div class="error-msg">❌ {{ msg.content }}</div>
          </template>
          <template v-else-if="msg.type === 'status'">
            <div class="status-msg">🔄 {{ msg.content }}</div>
          </template>
          <template v-else>
            <div>{{ msg.content }}</div>
          </template>
        </div>
      </div>
      
      <div class="input-bar">
        <input 
          v-model="input" 
          :disabled="generating" 
          @keyup.enter="onSend" 
          placeholder="请输入你的需求，例如：创建一个贪吃蛇游戏..."
          class="input-field"
        />
        <button @click="onSend" :disabled="generating || !input.trim()" class="send-btn">
          {{ generating ? '生成中' : '生成' }}
        </button>
      </div>
    </div>

    <!-- 右侧预览区 -->
    <div class="main-panel">
      <div class="tabs">
        <span :class="{active: tab==='preview'}" @click="tab='preview'">网页预览</span>
        <span :class="{active: tab==='code'}" @click="tab='code'">代码预览</span>
      </div>
      
      <div class="preview-area" v-if="tab==='preview'">
        <iframe 
          v-if="hasMainHtmlFile()" 
          :src="getPreviewUrl()" 
          class="preview-frame"
          sandbox="allow-scripts"
        ></iframe>
        <div v-else class="placeholder">
          <div class="placeholder-icon">🎨</div>
          <div>请输入需求开始生成代码</div>
        </div>
      </div>
      
      <!-- 代码预览区域 - 支持多文件 -->
      <div class="code-area" v-else>
        <div class="file-explorer" v-if="projectFiles.length > 0">
          <div class="explorer-header">
            <span class="icon">📁</span>
            <span>项目文件 ({{ projectFiles.length }})</span>
          </div>
          <div class="file-list">
            <div 
              v-for="file in projectFiles" 
              :key="file.name"
              :class="['file-item', { active: selectedFile === file.name }]"
              @click="selectedFile = file.name"
            >
              <span class="file-icon">{{ getFileIcon(file.name) }}</span>
              <span class="file-name">{{ file.name }}</span>
              <span v-if="file.generating" class="generating-indicator">⚡</span>
              <span class="file-size">{{ formatFileSize(file.content?.length || 0) }}</span>
            </div>
          </div>
        </div>
        
        <div class="code-content">
          <div v-if="getSelectedFileContent()" class="code-header">
            <span class="file-path">{{ selectedFile }}</span>
            <span class="file-info">{{ getSelectedFileContent().length }} 字符</span>
          </div>
          <CodeView 
            v-if="getSelectedFileContent()" 
            :code="getSelectedFileContent()" 
            :lang="getFileLanguage(selectedFile)"
            :enableTyping="true"
            :autoStart="false"
          />
          <div v-else class="placeholder">
            <div class="placeholder-icon">📝</div>
            <div>还没有生成代码，请在左侧输入需求开始生成</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, nextTick, onUnmounted, computed } from 'vue'
import MarkdownView from './components/MarkdownView.vue'
import CodeView from './components/CodeView.vue'

// 状态管理
const chatMessages = reactive([])
const input = ref('')
const generating = ref(false)
const projectFiles = reactive([])
const selectedFile = ref('')
const tab = ref('preview')
const chatListRef = ref(null)
const wsConnected = ref(false)
let currentWs = null

// 检查是否有主HTML文件
const hasMainHtmlFile = () => {
  if (!projectFiles || projectFiles.length === 0) return false
  
  return projectFiles.some(f => 
    f && f.name && (
      f.name.toLowerCase().includes('index.html') || 
      f.name.toLowerCase().includes('main.html') ||
      f.name.endsWith('.html')
    )
  )
}

// 获取预览URL - 直接使用后端生成的文件
const getPreviewUrl = () => {
  const mainFile = projectFiles.find(f => 
    f && f.name && (
      f.name.toLowerCase().includes('index.html') || 
      f.name.toLowerCase().includes('main.html') ||
      f.name.endsWith('.html')
    )
  )
  
  if (!mainFile?.name) return ''
  
  // 使用后端的generated目录直接访问文件
  return `/generated/${mainFile.name}?t=${Date.now()}`
}

// 获取选中文件内容
const getSelectedFileContent = () => {
  if (!projectFiles || projectFiles.length === 0 || !selectedFile.value) return ''
  
  const file = projectFiles.find(f => f && f.name === selectedFile.value)
  return file?.content || ''
}

// 获取文件图标
const getFileIcon = (filename) => {
  if (!filename || typeof filename !== 'string') return '📄'
  
  const parts = filename.split('.')
  if (parts.length < 2) return '📄'
  
  const ext = parts.pop().toLowerCase()
  const iconMap = {
    'html': '🌐',
    'css': '🎨', 
    'js': '⚡',
    'json': '📋',
    'md': '📝',
    'txt': '📄',
    'png': '🖼️',
    'jpg': '🖼️',
    'jpeg': '🖼️',
    'gif': '🖼️',
    'svg': '🎯'
  }
  return iconMap[ext] || '📄'
}

// 获取文件语言类型
const getFileLanguage = (filename) => {
  if (!filename || typeof filename !== 'string') return 'text'
  
  const parts = filename.split('.')
  if (parts.length < 2) return 'text'
  
  const ext = parts.pop().toLowerCase()
  const langMap = {
    'html': 'html',
    'css': 'css',
    'js': 'javascript',
    'json': 'json',
    'md': 'markdown'
  }
  return langMap[ext] || 'text'
}

// 格式化文件大小
const formatFileSize = (size) => {
  if (!size || isNaN(size) || size < 0) return '0B'
  if (size < 1024) return `${size}B`
  if (size < 1024 * 1024) return `${Math.round(size / 1024)}KB`
  return `${Math.round(size / (1024 * 1024))}MB`
}

// 添加或更新项目文件
const updateProjectFile = (filename, content, generating = false) => {
  if (!filename || typeof filename !== 'string') return
  
  const existingIndex = projectFiles.findIndex(f => f && f.name === filename)
  const isNewFile = existingIndex < 0
  
  if (existingIndex >= 0) {
    projectFiles[existingIndex].content = content || ''
    projectFiles[existingIndex].generating = generating
  } else {
    projectFiles.push({
      name: filename,
      content: content || '',
      generating: generating
    })
  }
  
  // 🎯 智能文件自动选择逻辑
  if (isNewFile && !generating) {
    // 新文件且生成完成时，自动跳转
    selectedFile.value = filename
    console.log(`🎯 自动切换到新文件: ${filename}`)
    
    // 如果在预览模式且是HTML文件，自动刷新预览
    if (tab.value === 'preview' && filename.toLowerCase().includes('.html')) {
      nextTick(() => {
        console.log('🔄 检测到新HTML文件，准备刷新预览')
      })
    }
  } else if (!selectedFile.value) {
    // 如果没有选中文件，选择第一个
    selectedFile.value = filename
  }
}

// 从服务器获取生成的文件内容
const fetchGeneratedFile = async (filename) => {
  try {
    const response = await fetch(`/generated/${filename}`)
    if (response.ok) {
      const content = await response.text()
      updateProjectFile(filename, content, false)
      console.log(`✅ 成功获取文件: ${filename}, 内容长度: ${content.length}`)
    } else {
      console.warn(`⚠️ 获取文件失败: ${filename}, 状态: ${response.status}`)
    }
  } catch (error) {
    console.error(`❌ 获取文件异常: ${filename}`, error)
  }
}

// 解析代码块，提取多个文件
const parseCodeContent = (content) => {
  if (!content || typeof content !== 'string') return []
  
  // 匹配文件块模式：```filename\ncode\n```
  const fileBlockRegex = /```(\w+\.[\w.]+)\n([\s\S]*?)\n```/g
  const matches = []
  let match
  
  try {
    while ((match = fileBlockRegex.exec(content)) !== null) {
      if (match[1] && match[2]) {
        matches.push({
          filename: match[1],
          content: match[2]
        })
      }
    }
    
    // 如果没有找到文件块，但内容包含HTML，作为index.html处理
    if (matches.length === 0 && (content.includes('<!DOCTYPE') || content.includes('<html'))) {
      matches.push({
        filename: 'index.html',
        content: content
      })
    }
  } catch (error) {
    console.error('解析代码内容时出错:', error)
    // 出错时返回原始内容作为HTML文件
    return [{
      filename: 'index.html',
      content: content
    }]
  }
  
  return matches
}

// 自动滚动到底部
const scrollToBottom = () => {
  nextTick(() => {
    if (chatListRef.value) {
      chatListRef.value.scrollTop = chatListRef.value.scrollHeight
    }
  })
}

// 添加消息
const addMessage = (type, content) => {
  chatMessages.push({ type, content })
  scrollToBottom()
}

// 发送请求
const onSend = async () => {
  if (!input.value.trim() || generating.value) return
  
  const userInput = input.value.trim()
  addMessage('markdown', `**你：** ${userInput}`)
  
  generating.value = true
  projectFiles.length = 0  // 清空项目文件
  selectedFile.value = ''
  tab.value = 'preview'
  input.value = ''

  try {
    // 1. 创建任务
    const resp = await fetch('/api/v1/coding/generate-code', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt: userInput })
    })
    
    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}: ${resp.statusText}`)
    }
    
    const { task_id } = await resp.json()
    addMessage('status', `任务已创建: ${task_id}`)
    
    // 2. 建立 WebSocket 连接
    const wsProto = location.protocol === 'https:' ? 'wss' : 'ws'
    const wsUrl = `${wsProto}://${location.host}/api/v1/coding/status/${task_id}`
    
    currentWs = new WebSocket(wsUrl)
    
    currentWs.onopen = () => {
      wsConnected.value = true
      addMessage('status', 'WebSocket连接已建立')
    }
    
    currentWs.onmessage = (event) => {
      let data
      try {
        data = JSON.parse(event.data)
      } catch (e) {
        console.error('解析WebSocket消息失败:', e)
        return
      }
      
      // 处理不同类型的消息
      if (data.type === 'markdown') {
        addMessage('markdown', data.content)
      } else if (data.type === 'markdown_stream') {
        // 流式markdown内容
        addMessage('markdown', data.content)
      } else if (data.type === 'code' || data.type === 'code_chunk') {
        // 流式代码内容，尝试解析多文件
        const files = parseCodeContent(data.content || '')
        files.forEach(file => {
          updateProjectFile(file.filename, file.content, true)
        })
      } else if (data.type === 'code_stream') {
        // 实时流式代码生成
        addMessage('markdown', `💻 ${data.content}`)
        
        // 自动切换到代码预览
        if (tab.value !== 'code') {
          tab.value = 'code'
        }
        
        // 处理实时文件更新
        if (data.partial_files && Object.keys(data.partial_files).length > 0) {
          Object.entries(data.partial_files).forEach(([filename, content]) => {
            updateProjectFile(filename, content, true)
          })
        } else {
          // fallback: 解析代码内容
          const files = parseCodeContent(data.content || '')
          files.forEach(file => {
            updateProjectFile(file.filename, file.content, true)
          })
        }
      } else if (data.type === 'tool_result') {
        // 处理工具执行结果
        if (data.file_name) {
          addMessage('status', `📁 ${data.content}`)
          // 尝试从服务器读取文件内容
          fetchGeneratedFile(data.file_name)
        }
      } else if (data.type === 'file_created') {
        // 处理文件创建完成事件，直接使用文件内容
        if (data.file_name && data.file_content) {
          addMessage('status', `📁 ${data.content}`)
          updateProjectFile(data.file_name, data.file_content, false)
          
          // 暂时不自动切换tab，等代码生成完成后再切换
          // 只在代码预览模式下显示文件
          if (tab.value !== 'code') {
            tab.value = 'code'
            console.log(`🎯 检测到新文件，切换到代码模式: ${data.file_name}`)
          }
        }
      } else if (data.type === 'error') {
        addMessage('error', data.content)
        generating.value = false
        wsConnected.value = false
        currentWs?.close()
      } else if (data.type === 'complete') {
        // 🔥 处理文件信息 - 优先使用后端提取的文件信息
        if (data.files && Object.keys(data.files).length > 0) {
          // 使用后端提取的文件信息
          Object.entries(data.files).forEach(([filename, content]) => {
            updateProjectFile(filename, content, false)
          })
        } else if (data.final_code) {
          // 后备方案：前端解析
          const files = parseCodeContent(data.final_code)
          files.forEach(file => {
            updateProjectFile(file.filename, file.content, false)
          })
        }
        addMessage('status', '✅ 代码生成完成！')
        
        // 🎯 所有代码完成后才自动跳转到网页预览
        const hasHtmlFile = projectFiles.some(file => 
          file && file.name && file.name.toLowerCase().includes('.html')
        )
        if (hasHtmlFile && tab.value !== 'preview') {
          tab.value = 'preview'
          console.log('🎯 代码生成完成，自动切换到网页预览')
        }
        
        if (data.metadata) {
          const meta = data.metadata
          addMessage('markdown', `**生成统计：**\n- 模型: ${meta.model_used}\n- 耗时: ${meta.duration_ms}ms\n- 总Token: ${meta.total_tokens}\n- 成本: $${meta.cost_usd}`)
        }
        generating.value = false
        wsConnected.value = false
        currentWs?.close()
      } else if (data.type === 'status') {
        addMessage('status', data.content)
      }
    }
    
    currentWs.onerror = (error) => {
      console.error('WebSocket错误:', error)
      addMessage('error', 'WebSocket连接异常')
      generating.value = false
      wsConnected.value = false
    }
    
    currentWs.onclose = () => {
      wsConnected.value = false
      if (generating.value) {
        generating.value = false
        addMessage('status', 'WebSocket连接已关闭')
      }
    }
    
  } catch (error) {
    console.error('请求失败:', error)
    addMessage('error', `请求失败: ${error.message}`)
    generating.value = false
  }
}

// 组件卸载时清理WebSocket连接
onUnmounted(() => {
  if (currentWs) {
    currentWs.close()
  }
})

// 初始化欢迎消息
addMessage('markdown', '**欢迎使用 Lovart.ai 模拟器！**\n\n请输入你的需求，我会帮你生成相应的前端代码。\n\n例如：\n- 创建一个贪吃蛇游戏\n- 制作一个简单的计算器\n- 设计一个登录表单')
</script>

<style scoped>
.container {
  display: flex;
  height: 100vh;
  background: #f4f6fa;
}

.sidebar {
  width: 420px;
  background: #fff;
  border-right: 1px solid #e1e5e9;
  display: flex;
  flex-direction: column;
  box-shadow: 2px 0 8px rgba(0,0,0,0.04);
}

.header {
  padding: 20px;
  border-bottom: 1px solid #e1e5e9;
  background: #fafbfc;
}

.header h2 {
  font-size: 20px;
  color: #1a1a1a;
  margin-bottom: 8px;
}

.status {
  font-size: 13px;
  color: #666;
  padding: 4px 8px;
  border-radius: 12px;
  background: #f0f0f0;
  display: inline-block;
}

.status.connected {
  background: #e8f5e8;
  color: #2e7d32;
}

.status.generating {
  background: #fff3cd;
  color: #856404;
}

.chat-list {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.chat-msg {
  margin-bottom: 16px;
}

.chat-msg.error .error-msg {
  color: #d32f2f;
  background: #ffebee;
  border-left: 4px solid #d32f2f;
  padding: 12px 16px;
  border-radius: 4px;
  font-size: 14px;
}

.chat-msg.status .status-msg {
  color: #1976d2;
  background: #e3f2fd;
  border-left: 4px solid #1976d2;
  padding: 12px 16px;
  border-radius: 4px;
  font-size: 14px;
}

.input-bar {
  display: flex;
  padding: 20px;
  border-top: 1px solid #e1e5e9;
  background: #fafbfc;
  gap: 12px;
}

.input-field {
  flex: 1;
  padding: 12px 16px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 15px;
  background: #fff;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.input-field:focus {
  outline: none;
  border-color: #1976d2;
  box-shadow: 0 0 0 3px rgba(25, 118, 210, 0.1);
}

.input-field:disabled {
  background: #f5f5f5;
  color: #999;
}

.send-btn {
  padding: 12px 24px;
  background: #1976d2;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s, transform 0.1s;
  min-width: 80px;
}

.send-btn:hover:not(:disabled) {
  background: #1565c0;
  transform: translateY(-1px);
}

.send-btn:disabled {
  background: #b0bec5;
  cursor: not-allowed;
  transform: none;
}

.main-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #f4f6fa;
}

.tabs {
  display: flex;
  border-bottom: 1px solid #e1e5e9;
  background: #fff;
}

.tabs span {
  padding: 16px 32px;
  cursor: pointer;
  font-size: 16px;
  font-weight: 500;
  color: #666;
  border-bottom: 3px solid transparent;
  transition: all 0.2s;
}

.tabs span:hover {
  background: #f8f9fa;
  color: #333;
}

.tabs .active {
  color: #1976d2;
  border-bottom: 3px solid #1976d2;
  background: #f4f6fa;
}

.preview-area {
  flex: 1;
  background: #f4f6fa;
  display: flex;
  flex-direction: column;
}

.code-area {
  flex: 1;
  display: flex;
  background: #f4f6fa;
}

.file-explorer {
  width: 280px;
  background: #fff;
  border-right: 1px solid #e1e5e9;
  display: flex;
  flex-direction: column;
}

.explorer-header {
  padding: 16px;
  border-bottom: 1px solid #e1e5e9;
  background: #fafbfc;
  font-weight: 600;
  font-size: 14px;
  color: #333;
}

.explorer-header .icon {
  margin-right: 8px;
}

.file-list {
  flex: 1;
  overflow-y: auto;
}

.file-item {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  cursor: pointer;
  border-bottom: 1px solid #f0f0f0;
  transition: background 0.2s;
}

.file-item:hover {
  background: #f8f9fa;
}

.file-item.active {
  background: #e3f2fd;
  border-right: 3px solid #1976d2;
}

.file-icon {
  margin-right: 8px;
  font-size: 16px;
}

.file-name {
  flex: 1;
  font-size: 14px;
  color: #333;
}

.generating-indicator {
  color: #ff9800;
  font-size: 12px;
  margin-left: 4px;
}

.file-size {
  font-size: 12px;
  color: #999;
  margin-left: 8px;
}

.code-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #fff;
}

.code-header {
  padding: 16px;
  border-bottom: 1px solid #e1e5e9;
  background: #fafbfc;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.file-path {
  font-weight: 600;
  font-size: 14px;
  color: #333;
}

.file-info {
  font-size: 12px;
  color: #999;
}

.preview-frame {
  width: 100%;
  height: 100%;
  border: none;
  background: #fff;
  border-radius: 8px;
  margin: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #999;
  font-size: 18px;
}

.placeholder-icon {
  font-size: 48px;
  margin-bottom: 16px;
}
</style>

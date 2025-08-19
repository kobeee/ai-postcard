<template>
  <div class="code-view-container">
    <!-- 代码显示区域 -->
    <pre class="code-view"><code ref="codeBlock" :class="langClass">{{ displayCode }}</code></pre>
    
    <!-- 打字光标 -->
    <span v-if="enableTyping && isTyping && !typingComplete" class="typing-cursor">|</span>
  </div>
</template>

<script setup>
import { onMounted, watch, ref, computed, nextTick, onUnmounted } from 'vue'
import hljs from 'highlight.js/lib/core'
import javascript from 'highlight.js/lib/languages/javascript'
import xml from 'highlight.js/lib/languages/xml'
import css from 'highlight.js/lib/languages/css'
import 'highlight.js/styles/github-dark.css'

// 注册语言
hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('html', xml)
hljs.registerLanguage('css', css)

const props = defineProps({
  code: {
    type: String,
    required: true
  },
  lang: {
    type: String,
    default: 'html'
  },
  enableTyping: {
    type: Boolean,
    default: true
  },
  autoStart: {
    type: Boolean,
    default: true
  }
})

// 打字动画状态
const codeBlock = ref(null)
const targetCode = ref('')
const displayedCode = ref('')
const isTyping = ref(false)
const typingComplete = ref(false)
const typingSpeed = ref(1) // 打字速度（毫秒）- 最快速度
const currentIndex = ref(0)
let typingTimer = null

// 计算属性
const langClass = computed(() => `language-${props.lang}`)
const displayCode = computed(() => {
  return props.enableTyping ? displayedCode.value : props.code
})
const displayedLength = computed(() => displayedCode.value.length)
const progressPercent = computed(() => {
  if (!targetCode.value.length) return 0
  return Math.round((displayedLength.value / targetCode.value.length) * 100)
})

// 代码高亮
const highlight = async () => {
  await nextTick()
  if (codeBlock.value) {
    hljs.highlightElement(codeBlock.value)
  }
}

// 开始打字动画
const startTyping = () => {
  if (typingComplete.value) {
    // 重新开始
    resetTyping()
  }
  
  isTyping.value = true
  typeNextCharacter()
}

// 停止打字动画
const stopTyping = () => {
  isTyping.value = false
  if (typingTimer) {
    clearTimeout(typingTimer)
    typingTimer = null
  }
}

// 重置打字状态
const resetTyping = () => {
  stopTyping()
  displayedCode.value = ''
  currentIndex.value = 0
  typingComplete.value = false
}

// 打字下一个字符
const typeNextCharacter = () => {
  if (!isTyping.value || currentIndex.value >= targetCode.value.length) {
    // 打字完成
    isTyping.value = false
    typingComplete.value = true
    highlight()
    return
  }
  
  // 添加下一个字符
  displayedCode.value = targetCode.value.substring(0, currentIndex.value + 1)
  currentIndex.value++
  
  // 实时高亮（频率较低以避免性能问题）
  if (currentIndex.value % 10 === 0) {
    highlight()
  }
  
  // 调度下一个字符
  typingTimer = setTimeout(typeNextCharacter, typingSpeed.value)
}

// 切换打字状态
const toggleTyping = () => {
  if (typingComplete.value) {
    // 重新开始
    resetTyping()
    startTyping()
  } else if (isTyping.value) {
    // 暂停
    stopTyping()
  } else {
    // 开始/继续
    startTyping()
  }
}

// 监听代码变化
watch(() => props.code, (newCode) => {
  targetCode.value = newCode || ''
  
  if (props.enableTyping) {
    resetTyping()
    if (props.autoStart && newCode) {
      // 自动开始打字动画，使用最快速度
      setTimeout(() => {
        startTyping()
      }, 100)
    }
  } else {
    // 非打字模式，直接显示并高亮
    highlight()
  }
}, { immediate: true })

// 监听打字速度变化
watch(typingSpeed, (newSpeed) => {
  // 如果正在打字，应用新速度
  if (isTyping.value && typingTimer) {
    stopTyping()
    startTyping()
  }
})

// 组件挂载
onMounted(() => {
  if (!props.enableTyping) {
    highlight()
  }
})

// 组件卸载时清理定时器
onUnmounted(() => {
  if (typingTimer) {
    clearTimeout(typingTimer)
  }
})
</script>

<style scoped>
.code-view-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #22272e;
}

/* 打字动画控制栏 */
.typing-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #2d333b;
  border-bottom: 1px solid #444c56;
  flex-shrink: 0;
}

.typing-controls-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.control-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #21262d;
  color: #f0f6fc;
  border: 1px solid #30363d;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}

.control-btn:hover {
  background: #30363d;
  border-color: #8b949e;
}

.speed-control {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #f0f6fc;
  font-size: 12px;
}

.speed-slider {
  width: 80px;
  height: 4px;
  background: #21262d;
  border-radius: 2px;
  outline: none;
  cursor: pointer;
}

.speed-slider::-webkit-slider-thumb {
  appearance: none;
  width: 12px;
  height: 12px;
  background: #58a6ff;
  border-radius: 50%;
  cursor: pointer;
}

.speed-value {
  min-width: 35px;
  text-align: right;
  color: #8b949e;
}

.typing-progress {
  display: flex;
  align-items: center;
  gap: 12px;
}

.progress-bar {
  width: 120px;
  height: 6px;
  background: #21262d;
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #58a6ff, #1f6feb);
  border-radius: 3px;
  transition: width 0.1s ease;
}

.progress-text {
  font-size: 11px;
  color: #8b949e;
  min-width: 60px;
  text-align: right;
}

/* 代码显示区域 */
.code-view {
  background: #22272e;
  color: #fff;
  border-radius: 0;
  padding: 16px;
  font-family: 'Monaco', 'Menlo', 'Consolas', 'Liberation Mono', monospace;
  font-size: 14px;
  overflow-x: auto;
  margin: 0;
  flex: 1;
  white-space: pre-wrap;
  word-wrap: break-word;
  line-height: 1.5;
}

/* 打字光标动画 */
.typing-cursor {
  position: absolute;
  color: #58a6ff;
  font-weight: bold;
  animation: blink 1s infinite;
  margin-left: 2px;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .typing-controls {
    flex-direction: column;
    gap: 12px;
    align-items: stretch;
  }
  
  .typing-controls-left {
    justify-content: space-between;
  }
  
  .typing-progress {
    justify-content: space-between;
  }
  
  .progress-bar {
    flex: 1;
    max-width: 150px;
  }
}
</style>

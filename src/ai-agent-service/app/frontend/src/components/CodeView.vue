<template>
  <div class="code-view-container">
    <pre class="code-view"><code ref="codeBlock" :class="langClass">{{ code }}</code></pre>
  </div>
</template>

<script setup>
import { onMounted, watch, ref, computed } from 'vue'
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
  }
})

const codeBlock = ref(null)
const langClass = computed(() => `language-${props.lang}`)

const highlight = () => {
  if (codeBlock.value && props.code) {
    hljs.highlightElement(codeBlock.value)
  }
}

onMounted(highlight)
watch(() => props.code, highlight)
</script>

<style scoped>
.code-view-container {
  height: 100%;
  overflow: auto;
  background: #22272e;
}

.code-view {
  background: #22272e;
  color: #fff;
  border-radius: 0;
  padding: 16px;
  font-family: 'Monaco', 'Menlo', 'Consolas', 'Liberation Mono', monospace;
  font-size: 14px;
  overflow-x: auto;
  margin: 0;
  min-height: 100%;
  white-space: pre-wrap;
  word-wrap: break-word;
}
</style>

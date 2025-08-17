<template>
  <div class="markdown-view" v-html="renderedMarkdown"></div>
</template>

<script setup>
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps({
  content: {
    type: String,
    required: true
  }
})

const renderedMarkdown = computed(() => {
  if (!props.content) return ''
  return marked.parse(props.content)
})
</script>

<style scoped>
.markdown-view {
  font-size: 15px;
  line-height: 1.7;
  color: #222;
  background: #fff;
  padding: 12px 0;
  word-break: break-all;
}

.markdown-view :deep(h1), 
.markdown-view :deep(h2), 
.markdown-view :deep(h3) {
  margin: 12px 0 6px;
  color: #333;
}

.markdown-view :deep(code) {
  background: #f5f5f5;
  padding: 2px 4px;
  border-radius: 3px;
  font-size: 90%;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
}

.markdown-view :deep(pre) {
  background: #f5f5f5;
  padding: 8px;
  border-radius: 4px;
  overflow-x: auto;
  margin: 8px 0;
}

.markdown-view :deep(ul), 
.markdown-view :deep(ol) {
  margin: 8px 0;
  padding-left: 24px;
}

.markdown-view :deep(blockquote) {
  border-left: 4px solid #ddd;
  padding-left: 12px;
  margin: 8px 0;
  color: #666;
}
</style>

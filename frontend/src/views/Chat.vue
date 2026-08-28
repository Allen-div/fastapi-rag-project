<template>
  <div class="chat-layout">
    <!-- 左侧对话列表 -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <h3>对话列表</h3>
        <button class="btn-new" @click="startNewChat">+ 新对话</button>
      </div>
      <div class="conv-list">
        <div
          v-for="conv in conversations"
          :key="conv.thread_id"
          class="conv-item"
          :class="{ active: conv.thread_id === activeThreadId }"
          @click="switchConversation(conv)"
        >
          <div class="conv-title">{{ conv.title }}</div>
          <div class="conv-time">{{ formatTime(conv.updated_at || conv.created_at) }}</div>
        </div>
        <div v-if="conversations.length === 0" class="empty-list">暂无对话</div>
      </div>
    </aside>

    <!-- 右侧聊天区 -->
    <section class="chat-main">
      <div class="messages-area">
        <div v-if="loadingMessages" class="chat-loading">
          <div class="spinner"></div>
          <p>加载历史消息...</p>
        </div>
        <div v-else-if="messages.length === 0" class="chat-empty">
          <div class="empty-icon">💬</div>
          <h2>开始新对话</h2>
          <p>在下方输入你的问题，AI 将基于你上传的文档进行回答</p>
        </div>
        <div v-else class="messages" ref="messagesContainer">
          <div
            v-for="(msg, i) in messages"
            :key="i"
            class="message"
            :class="msg.role"
          >
            <div class="msg-avatar">{{ msg.role === 'user' ? '👤' : '🤖' }}</div>
            <div class="msg-content">
              <div class="msg-text">
                {{ msg.content }}<span v-if="msg.role === 'assistant' && msg.streaming" class="typing-cursor">|</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="input-area">
        <textarea
          v-model="inputQuery"
          @keydown.enter.exact.prevent="sendMessage"
          placeholder="输入你的问题，Enter 发送..."
          rows="2"
          :disabled="streaming"
        ></textarea>
        <button
          class="btn-send"
          :disabled="!inputQuery.trim() || streaming"
          @click="sendMessage"
        >
          {{ streaming ? '思考中...' : '发送' }}
        </button>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, reactive, nextTick, onMounted } from 'vue'
import api from '../utils/api'

const conversations = ref([])
const activeThreadId = ref(null)
const messages = ref([])
const loadingMessages = ref(false)
const inputQuery = ref('')
const streaming = ref(false)
const messagesContainer = ref(null)

onMounted(async () => {
  await loadConversations()
})

async function loadConversations() {
  try {
    const res = await api.get('/chat/conversation', { params: { page: 1, page_size: 50 } })
    conversations.value = res.data.conversations || []
  } catch (e) {
    console.error('加载对话列表失败:', e)
  }
}

function startNewChat() {
  // 仅展开新的聊天框，不调用后端创建对话
  // 后端会在发送第一条消息时（thread_id 为空）自动创建对话
  activeThreadId.value = null
  messages.value = []
}

async function switchConversation(conv) {
  activeThreadId.value = conv.thread_id
  messages.value = []
  loadingMessages.value = true
  try {
    const res = await api.get('/chat/messages', { params: { conversion_id: conv.id } })
    const msgs = res.data.messages || []
    messages.value = msgs.map(m => ({
      role: m.role === 'user' ? 'user' : 'assistant',
      content: m.content
    }))
  } catch (e) {
    console.error('加载历史消息失败:', e)
  } finally {
    loadingMessages.value = false
    await scrollToBottom()
  }
}

async function sendMessage() {
  const query = inputQuery.value.trim()
  if (!query || streaming.value) return

  messages.value.push({ role: 'user', content: query })
  inputQuery.value = ''
  streaming.value = true

  // 添加占位 AI 消息（用 reactive，保证流式内容逐字更新能触发 Vue 响应式渲染）
  const aiMsg = reactive({ role: 'assistant', content: '', streaming: true })
  messages.value.push(aiMsg)
  await scrollToBottom()

  const token = localStorage.getItem('token')
  try {
    const response = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        query,
        thread_id: activeThreadId.value || null,
        top_k: 5
      })
    })

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            if (data.type === 'ai_content') {
              aiMsg.content += data.content
              await scrollToBottom()
            } else if (data.type === 'done') {
              if (!activeThreadId.value) {
                activeThreadId.value = data.thread_id
              }
              // 刷新列表（标题可能已被后端更新）
              await loadConversations()
            }
          } catch (e) { /* ignore parse errors */ }
        }
      }
    }
  } catch (e) {
    aiMsg.content = '请求失败，请重试'
    console.error('SSE error:', e)
  } finally {
    aiMsg.streaming = false
    streaming.value = false
    await scrollToBottom()
  }
}

async function scrollToBottom() {
  await nextTick()
  const el = messagesContainer.value
  if (el) el.scrollTop = el.scrollHeight
}

function formatTime(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const now = new Date()
  const diff = now - d
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  return d.toLocaleDateString('zh-CN')
}
</script>

<style scoped>
.chat-layout {
  display: flex;
  height: calc(100vh - 52px);
}

/* 侧边栏 */
.sidebar {
  width: 280px;
  background: var(--bg-white);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sidebar-header h3 {
  font-size: 15px;
  font-weight: 600;
}

.btn-new {
  font-size: 13px;
  color: var(--primary);
  background: var(--primary-bg);
  padding: 4px 12px;
  border-radius: 16px;
  font-weight: 500;
  transition: background 0.15s;
}
.btn-new:hover { background: #dde4ff; }

.conv-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.conv-item {
  padding: 12px 14px;
  border-radius: var(--radius);
  cursor: pointer;
  transition: background 0.1s;
  margin-bottom: 2px;
}
.conv-item:hover { background: var(--border-light); }
.conv-item.active { background: var(--primary-bg); }

.conv-title {
  font-size: 14px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conv-time {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
}

.empty-list {
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
  padding: 40px 0;
}

/* 聊天主区域 */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.messages-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.chat-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
}

.empty-icon { font-size: 48px; margin-bottom: 16px; }
.chat-empty h2 { font-size: 20px; font-weight: 600; color: var(--text); margin-bottom: 8px; }
.chat-empty p { font-size: 14px; max-width: 360px; text-align: center; }

.chat-loading {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  font-size: 14px;
  gap: 12px;
}

.chat-loading .spinner {
  width: 28px;
  height: 28px;
  border: 3px solid var(--border);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.message {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
  max-width: 720px;
}

/* 用户消息：靠右 + 头像在右 */
.message.user {
  flex-direction: row-reverse;
  align-self: flex-end;
}

.msg-avatar { font-size: 20px; flex-shrink: 0; margin-top: 2px; }

.msg-content {
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.msg-text {
  font-size: 14px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
  padding: 10px 16px;
  width: fit-content;
  max-width: 100%;
}

/* 用户气泡：主色实心 */
.message.user .msg-text {
  background: var(--primary);
  color: #fff;
  border-radius: 12px 4px 12px 12px;
}

/* 机器人气泡：白底描边 */
.message.assistant .msg-text {
  background: var(--bg-white);
  border: 1px solid var(--border-light);
  border-radius: 4px 12px 12px 12px;
}

.typing-cursor {
  display: inline;
  animation: blink 1s steps(1) infinite;
  color: var(--primary);
}

@keyframes blink {
  50% { opacity: 0; }
}

/* 输入区 */
.input-area {
  padding: 16px 24px;
  border-top: 1px solid var(--border);
  display: flex;
  gap: 12px;
  align-items: flex-end;
  background: var(--bg-white);
}

.input-area textarea {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: 14px;
  resize: none;
  max-height: 120px;
  transition: border-color 0.15s;
}
.input-area textarea:focus { border-color: var(--primary); }

.btn-send {
  padding: 10px 20px;
  background: var(--primary);
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  border-radius: var(--radius);
  white-space: nowrap;
  transition: background 0.15s;
}
.btn-send:hover { background: var(--primary-light); }
.btn-send:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
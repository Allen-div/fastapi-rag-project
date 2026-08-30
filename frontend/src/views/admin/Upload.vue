<template>
  <div class="admin-page">
    <div class="admin-header">
      <h2>上传文档</h2>
      <p>上传文档后，系统将保存到服务器，并由后台异步解析入库，用于 RAG 对话检索</p>
    </div>

    <div class="upload-zone" :class="{ dragging }" @dragover.prevent="dragging = true" @dragleave="dragging = false" @drop.prevent="handleDrop">
      <div class="upload-icon">📄</div>
      <p class="upload-text">拖拽文件到此处，或点击选择文件</p>
      <p class="upload-hint">支持 .txt、.pdf、.doc、.docx、.csv、.json，最大 100MB</p>
      <input ref="fileInput" type="file" @change="handleFileChange" accept=".txt,.pdf,.doc,.docx,.csv,.json" hidden />
      <button class="btn-select" @click="$refs.fileInput.click()">选择文件</button>
    </div>

    <div v-if="uploading" class="upload-status">
      <div class="status-bar">
        <div class="status-fill" :style="{ width: progress + '%' }"></div>
      </div>
      <p class="status-text">{{ statusText }}</p>
    </div>

    <div v-if="result" class="upload-result">
      <div class="result-left">
        <div class="result-icon">✅</div>
        <div class="result-info">
          <p><strong>{{ result.file_name }}</strong> 上传成功</p>
          <p class="result-detail">{{ result.message }}</p>
          <p class="result-detail">文档 ID: {{ result.doc_id }} · 任务 ID: {{ result.task_id }}</p>
        </div>
      </div>
      <router-link to="/admin/documents" class="btn-goto">查看进度</router-link>
    </div>

    <div v-if="error" class="upload-error">{{ error }}</div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import api from '../../utils/api'

const fileInput = ref(null)
const dragging = ref(false)
const uploading = ref(false)
const progress = ref(0)
const statusText = ref('')
const result = ref(null)
const error = ref('')

function handleDrop(e) {
  dragging.value = false
  const file = e.dataTransfer.files[0]
  if (file) uploadFile(file)
}

function handleFileChange(e) {
  const file = e.target.files[0]
  if (file) uploadFile(file)
}

async function uploadFile(file) {
  error.value = ''
  result.value = null
  uploading.value = true
  progress.value = 0
  statusText.value = '正在上传...'

  const formData = new FormData()
  formData.append('file', file)

  try {
    const res = await api.post('/document/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (e.total) {
          progress.value = Math.round((e.loaded / e.total) * 100)
        }
      }
    })
    progress.value = 100
    statusText.value = '上传完成，后台处理中...'
    result.value = res.data
  } catch (e) {
    error.value = e.response?.data?.detail || '上传失败，请重试'
  } finally {
    uploading.value = false
    if (fileInput.value) fileInput.value.value = ''
  }
}
</script>

<style scoped>
.admin-page {
  max-width: 640px;
  margin: 0 auto;
  padding: 40px 24px;
}

.admin-header {
  margin-bottom: 32px;
}

.admin-header h2 {
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 6px;
}

.admin-header p {
  font-size: 14px;
  color: var(--text-secondary);
}

.upload-zone {
  border: 2px dashed var(--border);
  border-radius: var(--radius-lg);
  padding: 48px 24px;
  text-align: center;
  transition: border-color 0.15s, background 0.15s;
  cursor: pointer;
}
.upload-zone:hover,
.upload-zone.dragging {
  border-color: var(--primary);
  background: var(--primary-bg);
}

.upload-icon { font-size: 40px; margin-bottom: 12px; }
.upload-text { font-size: 15px; font-weight: 500; margin-bottom: 6px; }
.upload-hint { font-size: 13px; color: var(--text-muted); margin-bottom: 20px; }

.btn-select {
  padding: 8px 24px;
  background: var(--primary);
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  border-radius: var(--radius);
  transition: background 0.15s;
}
.btn-select:hover { background: var(--primary-light); }

/* 上传状态 */
.upload-status {
  margin-top: 24px;
}

.status-bar {
  height: 4px;
  background: var(--border-light);
  border-radius: 2px;
  overflow: hidden;
}

.status-fill {
  height: 100%;
  background: var(--primary);
  border-radius: 2px;
  transition: width 0.3s ease;
}

.status-text {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 8px;
}

/* 结果 */
.upload-result {
  margin-top: 24px;
  padding: 16px 20px;
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  border-radius: var(--radius);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.result-left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.result-icon { font-size: 24px; }
.result-info p { font-size: 14px; }
.result-detail { font-size: 13px; color: var(--text-secondary); margin-top: 2px; }

.btn-goto {
  font-size: 13px;
  color: var(--primary);
  background: var(--primary-bg);
  padding: 6px 14px;
  border-radius: var(--radius);
  font-weight: 500;
  flex-shrink: 0;
  transition: background 0.15s;
}
.btn-goto:hover { background: #dde4ff; }

.upload-error {
  margin-top: 24px;
  padding: 14px 18px;
  background: var(--danger-bg);
  color: var(--danger);
  border-radius: var(--radius);
  font-size: 14px;
}
</style>
<template>
  <div class="admin-page">
    <div class="admin-header">
      <div>
        <h2>文档管理</h2>
        <p>管理已上传的文档，查看解析进度，删除不需要的文档</p>
      </div>
      <button class="btn-refresh" @click="refresh" :disabled="refreshing">刷新</button>
    </div>

    <div class="table-wrap">
      <table class="doc-table">
        <thead>
          <tr>
            <th>文件名</th>
            <th>类型</th>
            <th>大小</th>
            <th>状态</th>
            <th>分块数</th>
            <th>上传时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="doc in documents" :key="doc.id">
            <td class="doc-name" :title="doc.error_message || doc.file_name">{{ doc.file_name }}</td>
            <td class="doc-type">{{ doc.file_type || '-' }}</td>
            <td>{{ formatSize(doc.file_size) }}</td>
            <td>
              <span class="status-badge" :class="statusClass(doc.status)">
                <span v-if="doc.status === 'processing'" class="dot-spinner"></span>
                {{ statusText(doc.status) }}
              </span>
            </td>
            <td>{{ doc.chunk_count || '-' }}</td>
            <td>{{ formatTime(doc.created_at) }}</td>
            <td>
              <button class="btn-delete" @click="handleDelete(doc)">删除</button>
            </td>
          </tr>
          <tr v-if="documents.length === 0">
            <td colspan="7" class="empty-row">暂无文档，请先上传</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="pagination" v-if="total > pageSize">
      <button :disabled="page <= 1" @click="changePage(page - 1)">上一页</button>
      <span class="page-info">第 {{ page }} 页 / 共 {{ totalPages }} 页</span>
      <button :disabled="page >= totalPages" @click="changePage(page + 1)">下一页</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import api from '../../utils/api'

const documents = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const refreshing = ref(false)

let pollTimer = null

const totalPages = computed(() => Math.ceil(total.value / pageSize.value) || 1)

const STATUS_MAP = {
  pending: '等待处理',
  processing: '处理中',
  completed: '已完成',
  failed: '失败'
}

onMounted(() => loadDocuments())
onUnmounted(() => stopPolling())

async function loadDocuments() {
  try {
    const res = await api.get('/document/documents', {
      params: { page: page.value, page_size: pageSize.value }
    })
    documents.value = res.data.documents || []
    total.value = res.data.total || 0
    updatePolling()
  } catch (e) {
    console.error('加载文档列表失败:', e)
  } finally {
    refreshing.value = false
  }
}

async function refresh() {
  refreshing.value = true
  await loadDocuments()
}

// 只要存在未完成（pending/processing）的文档，就每 3 秒自动刷新一次
function updatePolling() {
  const hasProcessing = documents.value.some(d => d.status === 'pending' || d.status === 'processing')
  if (hasProcessing && !pollTimer) {
    pollTimer = setInterval(loadDocuments, 3000)
  } else if (!hasProcessing && pollTimer) {
    stopPolling()
  }
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function changePage(p) {
  page.value = p
  loadDocuments()
}

async function handleDelete(doc) {
  if (!confirm(`确定要删除 "${doc.file_name}" 吗？`)) return
  try {
    await api.delete(`/document/documents/${doc.id}`)
    await loadDocuments()
  } catch (e) {
    alert('删除失败: ' + (e.response?.data?.detail || '未知错误'))
  }
}

function statusText(status) {
  return STATUS_MAP[status] || status || '-'
}

function statusClass(status) {
  return 'status-' + status
}

function formatSize(bytes) {
  if (!bytes) return '-'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function formatTime(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}
</script>

<style scoped>
.admin-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 40px 24px;
}

.admin-header {
  margin-bottom: 32px;
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
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

.btn-refresh {
  font-size: 13px;
  color: var(--text-secondary);
  background: var(--bg-white);
  border: 1px solid var(--border);
  padding: 6px 16px;
  border-radius: var(--radius);
  transition: background 0.15s;
}
.btn-refresh:hover:not(:disabled) { background: var(--border-light); }
.btn-refresh:disabled { opacity: 0.5; cursor: not-allowed; }

.table-wrap {
  background: var(--bg-white);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border);
  overflow: hidden;
}

.doc-table {
  width: 100%;
  border-collapse: collapse;
}

.doc-table th {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 14px 16px;
  text-align: left;
  background: var(--border-light);
  border-bottom: 1px solid var(--border);
}

.doc-table td {
  padding: 14px 16px;
  font-size: 14px;
  border-bottom: 1px solid var(--border-light);
}

.doc-table tr:last-child td { border-bottom: none; }

.doc-name {
  font-weight: 500;
  max-width: 240px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.doc-type { color: var(--text-secondary); font-size: 13px; }

/* 状态徽章 */
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 500;
  padding: 3px 10px;
  border-radius: 12px;
  white-space: nowrap;
}
.status-pending { background: #fef3c7; color: #92400e; }
.status-processing { background: #dbeafe; color: #1e40af; }
.status-completed { background: #d1fae5; color: #065f46; }
.status-failed { background: #fee2e2; color: #991b1b; }

.dot-spinner {
  width: 10px;
  height: 10px;
  border: 2px solid rgba(30, 64, 175, 0.3);
  border-top-color: #1e40af;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.btn-delete {
  font-size: 13px;
  color: var(--danger);
  background: none;
  padding: 4px 10px;
  border-radius: 4px;
  transition: background 0.15s;
}
.btn-delete:hover { background: var(--danger-bg); }

.empty-row {
  text-align: center;
  color: var(--text-muted);
  padding: 48px 16px !important;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  margin-top: 24px;
}

.pagination button {
  padding: 6px 16px;
  background: var(--bg-white);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: 13px;
  color: var(--text);
  transition: background 0.15s;
}
.pagination button:hover:not(:disabled) { background: var(--border-light); }
.pagination button:disabled { opacity: 0.4; cursor: not-allowed; }

.page-info { font-size: 13px; color: var(--text-secondary); }
</style>
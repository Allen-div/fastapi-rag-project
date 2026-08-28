<template>
  <div class="auth-page">
    <div class="auth-card">
      <h1 class="auth-title">注册</h1>
      <p class="auth-sub">创建你的 RAG 对话系统账号</p>
      <form @submit.prevent="handleRegister" class="auth-form">
        <div class="field">
          <label>用户名</label>
          <input v-model="form.username" type="text" placeholder="请输入用户名" required />
        </div>
        <div class="field">
          <label>邮箱</label>
          <input v-model="form.email" type="email" placeholder="请输入邮箱" required />
        </div>
        <div class="field">
          <label>全名</label>
          <input v-model="form.full_name" type="text" placeholder="请输入姓名（选填）" />
        </div>
        <div class="field">
          <label>密码</label>
          <input v-model="form.password" type="password" placeholder="请输入密码" required />
        </div>
        <p v-if="error" class="error-msg">{{ error }}</p>
        <button type="submit" class="btn-primary" :disabled="loading">
          {{ loading ? '注册中...' : '注册' }}
        </button>
      </form>
      <p class="auth-footer">
        已有账号？<router-link to="/login">立即登录</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const form = reactive({ username: '', email: '', password: '', full_name: '' })
const loading = ref(false)
const error = ref('')

async function handleRegister() {
  error.value = ''
  loading.value = true
  try {
    await authStore.register(form)
    await authStore.login(form.username, form.password)
    router.push('/chat')
  } catch (e) {
    const detail = e.response?.data?.detail
    error.value = typeof detail === 'string' ? detail : '注册失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.auth-card {
  width: 400px;
  background: var(--bg-white);
  border-radius: var(--radius-lg);
  padding: 40px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
}

.auth-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 4px;
}

.auth-sub {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 32px;
}

.auth-form { display: flex; flex-direction: column; gap: 20px; }

.field { display: flex; flex-direction: column; gap: 6px; }

.field label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
}

.field input {
  padding: 10px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: 14px;
  transition: border-color 0.15s;
}
.field input:focus { border-color: var(--primary); box-shadow: 0 0 0 3px var(--primary-bg); }

.error-msg {
  font-size: 13px;
  color: var(--danger);
  background: var(--danger-bg);
  padding: 10px 14px;
  border-radius: var(--radius);
}

.btn-primary {
  padding: 12px;
  background: var(--primary);
  color: #fff;
  font-size: 15px;
  font-weight: 500;
  border-radius: var(--radius);
  transition: background 0.15s;
}
.btn-primary:hover { background: var(--primary-light); }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }

.auth-footer {
  text-align: center;
  font-size: 13px;
  color: var(--text-muted);
  margin-top: 24px;
}
</style>
<template>
  <div id="app-root">
    <nav v-if="isLoggedIn" class="navbar">
      <div class="nav-left">
        <span class="logo">RAG</span>
        <router-link to="/chat" class="nav-link" :class="{ active: $route.path.startsWith('/chat') }">对话</router-link>
        <router-link to="/admin/upload" class="nav-link" :class="{ active: isAdmin }">管理</router-link>
      </div>
      <div class="nav-right">
        <div v-if="authStore.user" class="user-info">
          <div class="avatar">{{ avatarText }}</div>
          <span class="username">{{ displayName }}</span>
        </div>
        <button class="btn-logout" @click="handleLogout">退出登录</button>
      </div>
    </nav>

    <!-- 管理子导航 -->
    <div v-if="isAdmin && isLoggedIn" class="admin-subnav">
      <router-link to="/admin/upload" class="sub-link" :class="{ active: $route.path === '/admin/upload' }">上传文档</router-link>
      <router-link to="/admin/documents" class="sub-link" :class="{ active: $route.path === '/admin/documents' }">文档列表</router-link>
    </div>

    <main :class="mainClass">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const isLoggedIn = computed(() => authStore.isLoggedIn)
const isAdmin = computed(() => router.currentRoute.value.path.startsWith('/admin'))
const mainClass = computed(() => ({
  'has-nav': isLoggedIn.value,
  'has-subnav': isLoggedIn.value && isAdmin.value
}))

const displayName = computed(() => authStore.user?.full_name || authStore.user?.username || '')
const avatarText = computed(() => displayName.value.charAt(0).toUpperCase() || '?')

onMounted(async () => {
  // 刷新页面时 token 存在但 user 为空，则拉取用户信息
  if (authStore.isLoggedIn && !authStore.user) {
    await authStore.fetchUserInfo()
  }
})

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.navbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 52px;
  background: var(--bg-white);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  z-index: 100;
}

.nav-left {
  display: flex;
  align-items: center;
  gap: 32px;
}

.logo {
  font-weight: 700;
  font-size: 18px;
  color: var(--primary);
  letter-spacing: -0.5px;
}

.nav-link {
  font-size: 14px;
  color: var(--text-secondary);
  padding: 4px 0;
  border-bottom: 2px solid transparent;
  transition: color 0.15s, border-color 0.15s;
}

.nav-link:hover { color: var(--text); }
.nav-link.active {
  color: var(--primary);
  border-bottom-color: var(--primary);
}

.btn-logout {
  font-size: 13px;
  color: var(--text-secondary);
  background: none;
  padding: 6px 12px;
  border-radius: var(--radius);
  transition: background 0.15s;
}
.btn-logout:hover { background: var(--border-light); }

.nav-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--primary);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  user-select: none;
}

.username {
  font-size: 13px;
  color: var(--text);
  font-weight: 500;
}

/* 管理子导航 */
.admin-subnav {
  position: fixed;
  top: 52px;
  left: 0;
  right: 0;
  height: 44px;
  background: var(--bg);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 24px;
  z-index: 90;
}

.sub-link {
  font-size: 13px;
  color: var(--text-secondary);
  padding: 6px 16px;
  border-radius: 16px;
  transition: background 0.15s, color 0.15s;
}
.sub-link:hover { background: var(--border-light); color: var(--text); }
.sub-link.active {
  background: var(--primary-bg);
  color: var(--primary);
  font-weight: 500;
}

.has-nav { padding-top: 52px; }
.has-subnav { padding-top: 96px; }
main { min-height: 100vh; }
</style>
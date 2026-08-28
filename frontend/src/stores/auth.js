import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../utils/api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))

  const isLoggedIn = computed(() => !!token.value)

  async function login(username, password) {
    const formData = new URLSearchParams()
    formData.append('username', username)
    formData.append('password', password)

    const res = await api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })
    token.value = res.data.access_token
    localStorage.setItem('token', token.value)
    await fetchUserInfo()
    return res.data
  }

  async function fetchUserInfo() {
    if (!token.value) return null
    try {
      const res = await api.get('/user/userinfo')
      user.value = res.data
      localStorage.setItem('user', JSON.stringify(res.data))
      return res.data
    } catch (e) {
      console.error('获取用户信息失败:', e)
      return null
    }
  }

  async function register(data) {
    const res = await api.post('/auth/register', data)
    return res.data
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  return { token, user, isLoggedIn, login, register, fetchUserInfo, logout }
})
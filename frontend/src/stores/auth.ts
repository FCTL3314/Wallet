import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, type UserResponse } from '../api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref<UserResponse | null>(null)

  const isAuthenticated = computed(() => !!token.value)

  function _saveTokens(accessToken: string, refreshToken: string) {
    token.value = accessToken
    localStorage.setItem('token', accessToken)
    localStorage.setItem('refresh_token', refreshToken)
  }

  async function login(email: string, password: string) {
    const { data } = await authApi.login(email, password)
    _saveTokens(data.access_token, data.refresh_token)
    await fetchUser()
  }

  async function register(email: string, password: string) {
    const { data } = await authApi.register(email, password)
    _saveTokens(data.access_token, data.refresh_token)
    await fetchUser()
  }

  async function fetchUser() {
    try {
      const { data } = await authApi.me()
      user.value = data
    } catch {
      logout()
    }
  }

  async function logout() {
    const refreshToken = localStorage.getItem('refresh_token')
    if (refreshToken) {
      authApi.logout(refreshToken).catch(() => {})
    }
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('refresh_token')
  }

  return { token, user, isAuthenticated, login, register, fetchUser, logout }
})

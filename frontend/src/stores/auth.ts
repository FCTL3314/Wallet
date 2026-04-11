import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, type UserResponse } from '../api/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<UserResponse | null>(null)

  const isAuthenticated = computed(() => !!user.value)

  async function login(email: string, password: string) {
    const { data } = await authApi.login(email, password)
    user.value = data
  }

  async function register(email: string, password: string) {
    const { data } = await authApi.register(email, password)
    user.value = data
  }

  async function fetchUser() {
    try {
      const { data } = await authApi.me()
      user.value = data
    } catch {
      user.value = null
    }
  }

  async function updateBaseCurrency(code: string | null) {
    const { data } = await authApi.updatePreferences(code)
    user.value = data
  }

  async function logout() {
    authApi.logout().catch(() => {})
    user.value = null
  }

  return { user, isAuthenticated, login, register, fetchUser, logout, updateBaseCurrency }
})

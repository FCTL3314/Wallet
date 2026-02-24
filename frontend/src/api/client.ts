import axios from 'axios'
import type { App } from 'vue'
import { getErrorMessage } from './errors'

let toastService: { add: (options: object) => void } | null = null

export function initApiClient(app: App) {
  toastService = app.config.globalProperties.$toast
}

const api = axios.create({
  baseURL: '/api',
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status
    const code = error.response?.data?.code

    // Auth errors handled inline by views, not via redirect
    const isAuthError = code?.startsWith('auth/')

    if (status === 401 && !isAuthError) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    } else if (toastService && !isAuthError) {
      toastService.add({
        severity: 'error',
        summary: 'Error',
        detail: getErrorMessage(error),
        life: 5000,
      })
    }
    return Promise.reject(error)
  }
)

export default api

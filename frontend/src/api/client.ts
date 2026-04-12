import axios from 'axios'
import type { App } from 'vue'
import { getErrorMessage } from './errors'

let toastService: { add: (options: object) => void } | null = null

export function initApiClient(app: App) {
  toastService = app.config.globalProperties.$toast
}

const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
})

let isRefreshing = false
let failedQueue: Array<{ resolve: () => void; reject: (error: unknown) => void }> = []

function processQueue(error: unknown) {
  failedQueue.forEach((p) => (error ? p.reject(error) : p.resolve()))
  failedQueue = []
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    const status = error.response?.status
    const isAuthEndpoint = ['/auth/login', '/auth/register', '/auth/refresh', '/auth/me'].some(
      (path) => originalRequest.url?.includes(path),
    )

    if (status === 401 && !isAuthEndpoint && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise<void>((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then(() => api(originalRequest))
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        await axios.post('/api/auth/refresh', null, { withCredentials: true })
        processQueue(null)
        return api(originalRequest)
      } catch (refreshError) {
        processQueue(refreshError)
        if (window.location.pathname !== '/login') {
          window.location.href = '/login'
        }
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    if (toastService && !isAuthEndpoint) {
      toastService.add({
        severity: 'error',
        summary: 'Error',
        detail: getErrorMessage(error),
        life: 5000,
      })
    }

    return Promise.reject(error)
  },
)

export default api

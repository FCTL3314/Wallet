import axios from 'axios'
import type { AxiosError, InternalAxiosRequestConfig } from 'axios'
import { getErrorMessage } from './errors'
import { coerceMoney } from './_money'
import { useLoadingStore } from '../stores/loading'
import { useNotificationsStore } from '../stores/notifications'

const AUTH_PATH_PREFIX = '/auth/'
const NO_REFRESH_PATHS = ['/auth/login', '/auth/register', '/auth/refresh'] as const

type RetriableRequest = InternalAxiosRequestConfig & { _retry?: boolean }

let onSessionExpired: (() => void) | null = null

export function initApiClient(sessionExpiredHandler: () => void) {
  onSessionExpired = sessionExpiredHandler
}

const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
})

api.interceptors.request.use((config) => {
  useLoadingStore().start()
  return config
})

let isRefreshing = false
let failedQueue: Array<{ resolve: () => void; reject: (error: unknown) => void }> = []

function processQueue(error: unknown) {
  failedQueue.forEach((p) => (error ? p.reject(error) : p.resolve()))
  failedQueue = []
}

api.interceptors.response.use(
  (response) => {
    useLoadingStore().done()
    if (response.data) coerceMoney(response.data)
    return response
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as RetriableRequest | undefined
    const requestUrl = originalRequest?.url ?? ''
    const status = error.response?.status
    useLoadingStore().done()

    const isAuthRequest = requestUrl.includes(AUTH_PATH_PREFIX)
    const skipsRefresh = NO_REFRESH_PATHS.some((path) => requestUrl.includes(path))

    if (status === 401 && originalRequest && !skipsRefresh && !originalRequest._retry) {
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
        onSessionExpired?.()
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    if (!isAuthRequest) {
      useNotificationsStore().add({
        type: 'error',
        title: 'Request failed',
        message: getErrorMessage(error),
      })
    }

    return Promise.reject(error)
  },
)

export default api

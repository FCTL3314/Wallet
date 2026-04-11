import api from './client'

export interface UserResponse {
  id: number
  email: string
  created_at: string
  onboarding_completed: boolean
  base_currency_code: string | null
}

export const authApi = {
  register(email: string, password: string) {
    return api.post<UserResponse>('/auth/register', { email, password })
  },
  login(email: string, password: string) {
    return api.post<UserResponse>('/auth/login', { email, password })
  },
  refresh() {
    return api.post<void>('/auth/refresh')
  },
  logout() {
    return api.post<void>('/auth/logout')
  },
  me() {
    return api.get<UserResponse>('/auth/me')
  },
  changeEmail(current_password: string, new_email: string) {
    return api.patch<UserResponse>('/auth/me/email', { current_password, new_email })
  },
  changePassword(current_password: string, new_password: string) {
    return api.patch<void>('/auth/me/password', { current_password, new_password })
  },
  completeOnboarding() {
    return api.post<UserResponse>('/auth/me/complete-onboarding')
  },
  updatePreferences(base_currency_code: string | null) {
    return api.patch<UserResponse>('/auth/me/preferences', { base_currency_code })
  },
}

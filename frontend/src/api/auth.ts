import api from './client'

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface UserResponse {
  id: number
  email: string
}

export const authApi = {
  register(email: string, password: string) {
    return api.post<TokenResponse>('/auth/register', { email, password })
  },
  login(email: string, password: string) {
    return api.post<TokenResponse>('/auth/login', { email, password })
  },
  refresh(refresh_token: string) {
    return api.post<TokenResponse>('/auth/refresh', { refresh_token })
  },
  logout(refresh_token: string) {
    return api.post('/auth/logout', { refresh_token })
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
}

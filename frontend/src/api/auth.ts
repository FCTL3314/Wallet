import api from './client'

export interface TokenResponse {
  access_token: string
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
  me() {
    return api.get<UserResponse>('/auth/me')
  },
}

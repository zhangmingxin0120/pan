import request from '@/api/request'
import type { AuthResponse, PublicSystemConfig, User } from '@/types'

export const login = (email: string, password: string) =>
  request.post<AuthResponse>('/auth/login', { email, password }).then((response) => response.data)

export const adminLogin = (username: string, password: string) =>
  request.post<AuthResponse>('/admin/login', { username, password }).then((response) => response.data)

export const register = (email: string, name: string, password: string) =>
  request
    .post<AuthResponse>('/auth/register', { email, name, password })
    .then((response) => response.data)

export const getMe = () => request.get<User>('/auth/me').then((response) => response.data)

export const changePassword = (currentPassword: string, newPassword: string) =>
  request
    .post<AuthResponse>('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    })
    .then((response) => response.data)

export const logout = () => request.post<void>('/auth/logout')

export const getPublicSystemConfig = () =>
  request.get<PublicSystemConfig>('/system/config').then((response) => response.data)

import request from '@/api/request'
import type {
  AdminOverview,
  AdminSettings,
  AdminUser,
  AdminUserCreateResult,
  AdminUserList,
  TemporaryPasswordResult,
} from '@/types'

export const getOverview = () =>
  request.get<AdminOverview>('/admin/overview').then((response) => response.data)

export const getUsers = (search?: string) =>
  request.get<AdminUserList>('/admin/users', { params: { search } }).then((response) => response.data)

export const updateUser = (id: string, payload: { is_active?: boolean; quota_bytes?: number }) =>
  request.patch<AdminUser>(`/admin/users/${id}`, payload).then((response) => response.data)

export const getSettings = () =>
  request.get<AdminSettings>('/admin/settings').then((response) => response.data)

export const updateSettings = (registrationEnabled: boolean) =>
  request
    .patch<AdminSettings>('/admin/settings', { registration_enabled: registrationEnabled })
    .then((response) => response.data)

export const createUser = (payload: { email: string; name: string; quota_bytes?: number }) =>
  request.post<AdminUserCreateResult>('/admin/users', payload).then((response) => response.data)

export const resetUserPassword = (id: string, password: string) =>
  request
    .post<TemporaryPasswordResult>(`/admin/users/${id}/reset-password`, { password })
    .then((response) => response.data)

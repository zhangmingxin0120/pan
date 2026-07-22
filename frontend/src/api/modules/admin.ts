import request from '@/api/request'
import type { AdminOverview, AdminUser, AdminUserList } from '@/types'

export const getOverview = () =>
  request.get<AdminOverview>('/admin/overview').then((response) => response.data)

export const getUsers = (search?: string) =>
  request.get<AdminUserList>('/admin/users', { params: { search } }).then((response) => response.data)

export const updateUser = (id: string, payload: { is_active?: boolean; quota_bytes?: number }) =>
  request.patch<AdminUser>(`/admin/users/${id}`, payload).then((response) => response.data)

import request from '@/api/request'
import type {
  AdminOverview,
  AdminSettings,
  AdminUser,
  AdminUserCreateResult,
  AdminUserList,
  ApiApplication,
  ApiApplicationList,
  ApiApplicationSecret,
  IntegrationFolder,
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

export const getIntegrationFolders = (userId: string) =>
  request
    .get<IntegrationFolder[]>(`/admin/integrations/users/${userId}/folders`)
    .then((response) => response.data)

export const getApiApplications = () =>
  request
    .get<ApiApplicationList>('/admin/integrations')
    .then((response) => response.data)

export const createApiApplication = (payload: {
  name: string
  user_id: string
  root_node_id: string
  can_read: boolean
  can_write: boolean
  can_delete: boolean
}) =>
  request
    .post<ApiApplicationSecret>('/admin/integrations', payload)
    .then((response) => response.data)

export const updateApiApplication = (id: string, isActive: boolean) =>
  request
    .patch<ApiApplication>(`/admin/integrations/${id}`, { is_active: isActive })
    .then((response) => response.data)

export const rotateApiApplicationKey = (id: string) =>
  request
    .post<{ api_key: string }>(`/admin/integrations/${id}/rotate-key`)
    .then((response) => response.data)

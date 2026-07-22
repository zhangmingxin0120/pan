export type NodeKind = 'file' | 'folder'

export interface User {
  id: string
  email: string
  username: string | null
  name: string
  quota_bytes: number
  is_admin: boolean
  must_change_password: boolean
  is_active: boolean
}

export interface AdminOverview {
  user_count: number
  active_user_count: number
  file_count: number
  storage_bytes: number
}

export interface AdminUser {
  id: string
  email: string
  name: string
  is_active: boolean
  quota_bytes: number
  used_bytes: number
  created_at: string
}

export interface AdminUserList {
  items: AdminUser[]
  total: number
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}

export interface DriveNode {
  id: string
  parent_id: string | null
  kind: NodeKind
  name: string
  is_root: boolean
  size_bytes: number
  content_type: string | null
  created_at: string
  updated_at: string
  trashed_at: string | null
}

export interface Breadcrumb {
  id: string
  name: string
}

export interface NodeListResponse {
  items: DriveNode[]
  total: number
  page: number
  page_size: number
  breadcrumbs: Breadcrumb[]
  current_folder: DriveNode
}

export interface StorageUsage {
  used_bytes: number
  quota_bytes: number
}

export interface Share {
  id: string
  token: string
  node: DriveNode
  expires_at: string
  revoked_at: string | null
  created_at: string
  is_active: boolean
}

export interface ShareListResponse {
  items: Share[]
  total: number
  page: number
  page_size: number
}

export interface PublicShare {
  token: string
  root: DriveNode
  current_folder: DriveNode | null
  breadcrumbs: Breadcrumb[]
  items: DriveNode[]
  expires_at: string
  owner_name: string
}

export interface ApiError {
  code: string
  message: string
  details?: unknown
}

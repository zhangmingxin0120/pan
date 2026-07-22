import request from '@/api/request'
import type { DriveNode, NodeListResponse, StorageUsage } from '@/types'

export interface NodeQuery {
  parent_id?: string
  search?: string
  sort_by?: 'name' | 'size' | 'updated_at'
  sort_order?: 'asc' | 'desc'
  page?: number
  page_size?: number
}

export const getNodes = (params: NodeQuery) =>
  request.get<NodeListResponse>('/nodes', { params }).then((response) => response.data)

export const getFolders = () => request.get<DriveNode[]>('/nodes/folders').then((response) => response.data)

export const createFolder = (parentId: string | undefined, name: string) =>
  request
    .post<DriveNode>('/nodes/folders', { parent_id: parentId || null, name })
    .then((response) => response.data)

export const uploadFile = (
  parentId: string | undefined,
  file: File,
  onProgress: (percent: number) => void,
) => {
  const form = new FormData()
  if (parentId) form.append('parent_id', parentId)
  form.append('file', file)
  return request
    .post<DriveNode>('/nodes/upload', form, {
      timeout: 0,
      onUploadProgress: (event) => {
        if (event.total) onProgress(Math.round((event.loaded / event.total) * 100))
      },
    })
    .then((response) => response.data)
}

export const renameNode = (nodeId: string, name: string) =>
  request.patch<DriveNode>(`/nodes/${nodeId}/name`, { name }).then((response) => response.data)

export const moveNode = (nodeId: string, targetParentId?: string) =>
  request
    .post<DriveNode>(`/nodes/${nodeId}/move`, { target_parent_id: targetParentId || null })
    .then((response) => response.data)

export const copyNode = (nodeId: string, targetParentId?: string) =>
  request
    .post<DriveNode>(`/nodes/${nodeId}/copy`, { target_parent_id: targetParentId || null })
    .then((response) => response.data)

export const deleteNode = (nodeId: string) => request.delete(`/nodes/${nodeId}`)
export const getStorageUsage = () =>
  request.get<StorageUsage>('/storage/usage').then((response) => response.data)

export const downloadUrl = (nodeId: string, preview = false) =>
  `${request.defaults.baseURL}/nodes/${nodeId}/${preview ? 'preview' : 'download'}`

export const fetchPrivateBlob = async (nodeId: string, preview = false) => {
  const response = await request.get<Blob>(`/nodes/${nodeId}/${preview ? 'preview' : 'download'}`, {
    responseType: 'blob',
    timeout: 0,
  })
  return response.data
}

export const getTrash = () => request.get<DriveNode[]>('/trash').then((response) => response.data)
export const restoreNode = (nodeId: string) =>
  request.post<DriveNode>(`/trash/${nodeId}/restore`).then((response) => response.data)
export const permanentlyDeleteNode = (nodeId: string) => request.delete(`/trash/${nodeId}`)
export const emptyTrash = () => request.delete('/trash')

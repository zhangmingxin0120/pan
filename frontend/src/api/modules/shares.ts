import request from '@/api/request'
import type { PublicShare, Share, ShareListResponse } from '@/types'

export const createShare = (nodeId: string, expiresInDays = 7) =>
  request
    .post<Share>('/shares', { node_id: nodeId, expires_in_days: expiresInDays })
    .then((response) => response.data)

export const getShares = () =>
  request.get<ShareListResponse>('/shares').then((response) => response.data)

export const revokeShare = (shareId: string) => request.delete(`/shares/${shareId}`)

export const getPublicShare = (token: string, parentId?: string) =>
  request
    .get<PublicShare>(`/public/shares/${token}`, { params: { parent_id: parentId } })
    .then((response) => response.data)

export const publicFileUrl = (token: string, nodeId: string, preview = false) =>
  `${request.defaults.baseURL}/public/shares/${token}/nodes/${nodeId}/${preview ? 'preview' : 'download'}`


import axios from 'axios'
import type { ApiError } from '@/types'

const CSRF_COOKIE_NAME = 'pan_csrf'
const SAFE_METHODS = new Set(['get', 'head', 'options'])

try {
  window.sessionStorage.removeItem('pan_access_token')
  window.localStorage.removeItem('pan_access_token')
} catch {
  // 旧版浏览器 Token 仅做迁移清理，不影响 Cookie 会话。
}

const getCookie = (name: string) => {
  const prefix = `${encodeURIComponent(name)}=`
  const item = document.cookie.split('; ').find((value) => value.startsWith(prefix))
  return item ? decodeURIComponent(item.slice(prefix.length)) : null
}

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 30_000,
  withCredentials: true,
})

request.interceptors.request.use((config) => {
  const method = config.method?.toLowerCase() || 'get'
  if (!SAFE_METHODS.has(method)) {
    const csrfToken = getCookie(CSRF_COOKIE_NAME)
    if (csrfToken) config.headers['X-CSRF-Token'] = csrfToken
  }
  return config
})

request.interceptors.response.use(
  (response) => response,
  (error) => {
    const requestUrl = String(error.config?.url || '')
    const isLoginRequest = requestUrl.endsWith('/auth/login') || requestUrl.endsWith('/admin/login')
    if (error.response?.status === 401 && getCookie(CSRF_COOKIE_NAME) && !isLoginRequest) {
      document.cookie = `${CSRF_COOKIE_NAME}=; Max-Age=0; Path=/; SameSite=Lax`
      window.dispatchEvent(new Event('pan:auth-expired'))
    }
    const apiError = error.response?.data as ApiError | undefined
    error.userMessage = apiError?.message || (error.code === 'ECONNABORTED' ? '请求超时，请重试' : '网络异常，请重试')
    return Promise.reject(error)
  },
)

export default request

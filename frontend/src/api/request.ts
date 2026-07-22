import axios from 'axios'
import type { ApiError } from '@/types'

const TOKEN_KEY = 'pan_access_token'

export const getToken = () => sessionStorage.getItem(TOKEN_KEY)
export const setToken = (token: string) => sessionStorage.setItem(TOKEN_KEY, token)
export const clearToken = () => sessionStorage.removeItem(TOKEN_KEY)

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 30_000,
})

request.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

request.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && getToken()) {
      clearToken()
      window.dispatchEvent(new Event('pan:auth-expired'))
    }
    const apiError = error.response?.data as ApiError | undefined
    error.userMessage = apiError?.message || (error.code === 'ECONNABORTED' ? '请求超时，请重试' : '网络异常，请重试')
    return Promise.reject(error)
  },
)

export default request


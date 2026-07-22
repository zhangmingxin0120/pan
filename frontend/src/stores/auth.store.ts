import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import * as authApi from '@/api/modules/auth'
import { clearToken, getToken, setToken } from '@/api/request'
import type { User } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const initialized = ref(false)
  const isAuthenticated = computed(() => Boolean(user.value && getToken()))

  async function initialize() {
    if (initialized.value) return
    if (getToken()) {
      try {
        user.value = await authApi.getMe()
      } catch {
        clearToken()
      }
    }
    initialized.value = true
  }

  async function login(email: string, password: string) {
    const result = await authApi.login(email, password)
    setToken(result.access_token)
    user.value = result.user
  }

  async function adminLogin(username: string, password: string) {
    const result = await authApi.adminLogin(username, password)
    setToken(result.access_token)
    user.value = result.user
  }

  async function register(email: string, name: string, password: string) {
    const result = await authApi.register(email, name, password)
    setToken(result.access_token)
    user.value = result.user
  }

  async function changePassword(currentPassword: string, newPassword: string) {
    const result = await authApi.changePassword(currentPassword, newPassword)
    setToken(result.access_token)
    user.value = result.user
  }

  function logout() {
    clearToken()
    user.value = null
  }

  return { user, initialized, isAuthenticated, initialize, login, adminLogin, register, changePassword, logout }
})

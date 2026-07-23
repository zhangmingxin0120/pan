import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import * as authApi from '@/api/modules/auth'
import type { User } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const initialized = ref(false)
  const isAuthenticated = computed(() => Boolean(user.value))

  async function initialize() {
    if (initialized.value) return
    try {
      user.value = await authApi.getMe()
    } catch {
      user.value = null
    }
    initialized.value = true
  }

  async function login(email: string, password: string) {
    const result = await authApi.login(email, password)
    user.value = result.user
  }

  async function adminLogin(username: string, password: string) {
    const result = await authApi.adminLogin(username, password)
    user.value = result.user
  }

  async function register(email: string, name: string, password: string) {
    const result = await authApi.register(email, name, password)
    user.value = result.user
  }

  async function changePassword(currentPassword: string, newPassword: string) {
    const result = await authApi.changePassword(currentPassword, newPassword)
    user.value = result.user
  }

  function clearSession() {
    user.value = null
  }

  async function logout() {
    try {
      await authApi.logout()
    } finally {
      clearSession()
    }
  }

  return { user, initialized, isAuthenticated, initialize, login, adminLogin, register, changePassword, logout, clearSession }
})

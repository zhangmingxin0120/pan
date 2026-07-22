<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Files, Key, Link, Logout, Menu2, Trash } from '@vicons/tabler'
import {
  NButton,
  NDrawer,
  NDrawerContent,
  NDropdown,
  NInput,
  NModal,
  NProgress,
  useMessage,
} from 'naive-ui'
import AppIcon from '@/components/base/AppIcon.vue'
import { getStorageUsage } from '@/api/modules/nodes'
import { useAuthStore } from '@/stores/auth.store'
import type { StorageUsage } from '@/types'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const message = useMessage()
const mobileOpen = ref(false)
const usage = ref<StorageUsage | null>(null)
const passwordDialog = ref(false)
const passwordLoading = ref(false)
const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')

const navItems = [
  { name: 'files', label: '我的文件', icon: Files, to: '/files' },
  { name: 'shares', label: '我的分享', icon: Link, to: '/shares' },
  { name: 'trash', label: '回收站', icon: Trash, to: '/trash' },
]

const usagePercent = computed(() =>
  usage.value ? Math.min(100, Math.round((usage.value.used_bytes / usage.value.quota_bytes) * 100)) : 0,
)

const formatSize = (bytes: number) => {
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let value = bytes
  let index = 0
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024
    index += 1
  }
  return `${value >= 10 || index === 0 ? value.toFixed(0) : value.toFixed(1)} ${units[index]}`
}

const go = (to: string) => {
  mobileOpen.value = false
  void router.push(to)
}

const logout = () => {
  authStore.logout()
  void router.push('/login')
}

function handleAccountAction(key: string | number) {
  if (key === 'password') {
    currentPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
    passwordDialog.value = true
  } else if (key === 'logout') {
    logout()
  }
}

async function submitPassword() {
  if (!currentPassword.value) return message.warning('请输入当前密码')
  if (newPassword.value.length < 8) return message.warning('新密码至少 8 位')
  if (newPassword.value !== confirmPassword.value) return message.warning('两次输入的新密码不一致')
  passwordLoading.value = true
  try {
    await authStore.changePassword(currentPassword.value, newPassword.value)
    passwordDialog.value = false
    message.success('密码已修改，其他设备需要重新登录')
  } catch (error) {
    message.error((error as { userMessage?: string }).userMessage || '修改密码失败，请重试')
  } finally {
    passwordLoading.value = false
  }
}

async function refreshUsage() {
  try {
    usage.value = await getStorageUsage()
  } catch {
    // 容量失败不阻塞主要文件操作。
  }
}

onMounted(() => {
  void refreshUsage()
  window.addEventListener('pan:storage-changed', refreshUsage)
})
onBeforeUnmount(() => window.removeEventListener('pan:storage-changed', refreshUsage))
</script>

<template>
  <div class="app-layout">
    <aside class="sidebar">
      <div class="brand" @click="go('/files')">
        <span class="brand-mark">P</span>
        <span>Pan</span>
      </div>
      <nav class="nav" aria-label="主要导航">
        <button
          v-for="item in navItems"
          :key="item.name"
          class="nav-item"
          :class="{ 'nav-item--active': route.name === item.name }"
          type="button"
          @click="go(item.to)"
        >
          <AppIcon :icon="item.icon" :size="20" />
          <span>{{ item.label }}</span>
        </button>
      </nav>
      <div class="sidebar-footer">
        <div v-if="usage" class="usage-card">
          <div class="usage-label"><span>存储空间</span><span>{{ usagePercent }}%</span></div>
          <NProgress type="line" :percentage="usagePercent" :show-indicator="false" :height="6" />
          <div class="usage-value">
            已使用 {{ formatSize(usage.used_bytes) }} / {{ formatSize(usage.quota_bytes) }}
          </div>
        </div>
        <NDropdown
          :options="[
            { label: '修改密码', key: 'password' },
            { type: 'divider', key: 'divider' },
            { label: '退出登录', key: 'logout' },
          ]"
          trigger="click"
          @select="handleAccountAction"
        >
          <button class="account-button" type="button">
            <span class="avatar">{{ authStore.user?.name.slice(0, 1).toUpperCase() || 'P' }}</span>
            <span class="account-copy">
              <strong>{{ authStore.user?.name || '用户' }}</strong>
              <small>{{ authStore.user?.email }}</small>
            </span>
          </button>
        </NDropdown>
      </div>
    </aside>

    <header class="mobile-header">
      <NButton quaternary circle aria-label="打开导航" @click="mobileOpen = true">
        <template #icon><AppIcon :icon="Menu2" :size="22" /></template>
      </NButton>
      <div class="brand brand--mobile"><span class="brand-mark">P</span><span>Pan</span></div>
      <NButton quaternary circle aria-label="退出登录" @click="logout">
        <template #icon><AppIcon :icon="Logout" :size="20" /></template>
      </NButton>
    </header>

    <main class="main-content"><RouterView /></main>

    <NDrawer v-model:show="mobileOpen" placement="left" :width="280">
      <NDrawerContent closable title="Pan">
        <nav class="nav nav--drawer">
          <button
            v-for="item in navItems"
            :key="item.name"
            class="nav-item"
            :class="{ 'nav-item--active': route.name === item.name }"
            type="button"
            @click="go(item.to)"
          >
            <AppIcon :icon="item.icon" :size="20" />
            <span>{{ item.label }}</span>
          </button>
          <button
            class="nav-item"
            type="button"
            @click="mobileOpen = false; handleAccountAction('password')"
          >
            <AppIcon :icon="Key" :size="20" />
            <span>修改密码</span>
          </button>
        </nav>
      </NDrawerContent>
    </NDrawer>

    <NModal
      v-model:show="passwordDialog"
      preset="dialog"
      title="修改密码"
      positive-text="确认修改"
      negative-text="取消"
      :loading="passwordLoading"
      :mask-closable="false"
      @positive-click="submitPassword"
    >
      <div class="password-form">
        <label>
          <span>当前密码</span>
          <NInput
            v-model:value="currentPassword"
            type="password"
            show-password-on="click"
            autocomplete="current-password"
            placeholder="输入当前密码"
          />
        </label>
        <label>
          <span>新密码</span>
          <NInput
            v-model:value="newPassword"
            type="password"
            show-password-on="click"
            autocomplete="new-password"
            placeholder="至少 8 位"
          />
        </label>
        <label>
          <span>确认新密码</span>
          <NInput
            v-model:value="confirmPassword"
            type="password"
            show-password-on="click"
            autocomplete="new-password"
            placeholder="再次输入新密码"
            @keyup.enter="submitPassword"
          />
        </label>
      </div>
    </NModal>
  </div>
</template>

<style scoped lang="scss">
@use '@/assets/styles/variables' as *;

.app-layout {
  min-height: 100vh;
}

.sidebar {
  position: fixed;
  inset: 0 auto 0 0;
  width: 232px;
  display: flex;
  flex-direction: column;
  padding: 24px 16px 16px;
  background: $surface;
  border-right: 1px solid $border;
  z-index: 10;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 44px;
  padding: 0 10px;
  font-size: 20px;
  font-weight: 650;
  letter-spacing: -0.03em;
  cursor: pointer;
}

.brand-mark {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 9px;
  color: white;
  background: $primary;
  font-size: 17px;
  font-weight: 650;
}

.nav {
  display: grid;
  gap: 4px;
  margin-top: 28px;
}

.nav-item {
  width: 100%;
  height: 44px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 12px;
  border: 0;
  border-radius: $radius-md;
  background: transparent;
  color: $text-secondary;
  cursor: pointer;
  text-align: left;
  transition: color 120ms ease, background 120ms ease;
}

.nav-item:hover {
  background: $surface-muted;
  color: $text;
}

.nav-item--active {
  color: $primary;
  background: $primary-soft;
  font-weight: 550;
}

.sidebar-footer {
  margin-top: auto;
}

.usage-card {
  padding: 12px;
  margin-bottom: 10px;
  border-top: 1px solid $border;
}

.usage-label {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  color: $text-secondary;
  font-size: 12px;
}

.usage-value {
  margin-top: 7px;
  color: $text-muted;
  font-size: 11px;
  font-variant-numeric: tabular-nums;
}

.account-button {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border: 0;
  border-radius: $radius-md;
  background: transparent;
  cursor: pointer;
  text-align: left;
}

.account-button:hover {
  background: $surface-muted;
}

.avatar {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: $primary-soft;
  color: $primary;
  font-weight: 600;
}

.account-copy {
  min-width: 0;
  display: grid;
}

.account-copy strong,
.account-copy small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.account-copy strong {
  font-size: 13px;
  font-weight: 550;
}

.account-copy small {
  color: $text-muted;
  font-size: 11px;
}

.main-content {
  min-height: 100vh;
  margin-left: 232px;
}

.mobile-header {
  display: none;
}

.nav--drawer {
  margin-top: 0;
}

.password-form {
  display: grid;
  gap: 14px;
  padding-top: 4px;
}

.password-form label {
  display: grid;
  gap: 6px;
  color: $text-secondary;
  font-size: 13px;
}

@media (max-width: 900px) {
  .sidebar {
    display: none;
  }

  .mobile-header {
    position: sticky;
    top: 0;
    z-index: 9;
    height: 60px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 16px;
    background: rgba(255, 255, 255, 0.94);
    border-bottom: 1px solid $border;
    backdrop-filter: blur(12px);
  }

  .brand--mobile {
    height: auto;
    padding: 0;
    font-size: 18px;
    cursor: default;
  }

  .brand--mobile .brand-mark {
    width: 27px;
    height: 27px;
    font-size: 15px;
  }

  .main-content {
    margin-left: 0;
  }
}
</style>

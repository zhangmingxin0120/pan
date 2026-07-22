<script setup lang="ts">
import { computed, h, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Database, File, Key, Logout, Search, Users } from '@vicons/tabler'
import { NButton, NDataTable, NInput, NInputNumber, NModal, NSwitch, NTag, useMessage, type DataTableColumns } from 'naive-ui'
import AppIcon from '@/components/base/AppIcon.vue'
import { getOverview, getUsers, updateUser } from '@/api/modules/admin'
import { useAuthStore } from '@/stores/auth.store'
import type { AdminOverview, AdminUser } from '@/types'

const router = useRouter()
const authStore = useAuthStore()
const message = useMessage()
const overview = ref<AdminOverview | null>(null)
const users = ref<AdminUser[]>([])
const search = ref('')
const loading = ref(true)
const quotaDialog = ref(false)
const quotaUser = ref<AdminUser | null>(null)
const quotaGb = ref<number | null>(null)
const quotaLoading = ref(false)

const formatSize = (bytes: number) => {
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let value = bytes
  let index = 0
  while (value >= 1024 && index < units.length - 1) { value /= 1024; index += 1 }
  return `${value >= 10 || index === 0 ? value.toFixed(0) : value.toFixed(1)} ${units[index]}`
}
const formatDate = (value: string) => new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium' }).format(new Date(value))

async function load() {
  loading.value = true
  try {
    const [summary, result] = await Promise.all([getOverview(), getUsers(search.value || undefined)])
    overview.value = summary
    users.value = result.items
  } catch (error) {
    message.error((error as { userMessage?: string }).userMessage || '管理数据加载失败')
  } finally { loading.value = false }
}

async function toggleUser(user: AdminUser, active: boolean) {
  try {
    const updated = await updateUser(user.id, { is_active: active })
    Object.assign(user, updated)
    if (overview.value) overview.value.active_user_count += active ? 1 : -1
    message.success(active ? '用户已启用' : '用户已停用，现有登录已失效')
  } catch (error) { message.error((error as { userMessage?: string }).userMessage || '操作失败') }
}

function editQuota(user: AdminUser) {
  quotaUser.value = user
  quotaGb.value = user.quota_bytes / 1024 / 1024 / 1024
  quotaDialog.value = true
}

async function saveQuota() {
  if (!quotaUser.value || quotaGb.value === null) return false
  quotaLoading.value = true
  try {
    const updated = await updateUser(quotaUser.value.id, { quota_bytes: Math.round(quotaGb.value * 1024 ** 3) })
    Object.assign(quotaUser.value, updated)
    quotaDialog.value = false
    message.success('容量配额已更新')
  } catch (error) { message.error((error as { userMessage?: string }).userMessage || '更新失败') }
  finally { quotaLoading.value = false }
  return false
}

const columns = computed<DataTableColumns<AdminUser>>(() => [
  { title: '用户', key: 'name', render: (row) => h('div', { class: 'user-cell' }, [h('strong', row.name), h('small', row.email)]) },
  { title: '存储使用', key: 'used_bytes', render: (row) => `${formatSize(row.used_bytes)} / ${formatSize(row.quota_bytes)}` },
  { title: '注册时间', key: 'created_at', render: (row) => formatDate(row.created_at) },
  { title: '状态', key: 'is_active', render: (row) => h(NTag, { type: row.is_active ? 'success' : 'default', size: 'small' }, { default: () => row.is_active ? '正常' : '已停用' }) },
  { title: '启用', key: 'toggle', width: 80, render: (row) => h(NSwitch, { value: row.is_active, 'onUpdate:value': (value: boolean) => void toggleUser(row, value) }) },
  { title: '', key: 'actions', width: 100, render: (row) => h(NButton, { size: 'small', onClick: () => editQuota(row) }, { default: () => '调整配额' }) },
])

function logout() { authStore.logout(); void router.replace('/admin/login') }
onMounted(() => void load())
</script>

<template>
  <main class="admin-page">
    <header class="admin-header">
      <div class="brand"><span class="brand-mark">P</span><span><strong>Pan</strong><small>系统管理</small></span></div>
      <div class="account-actions">
        <span>administrator</span>
        <NButton quaternary @click="router.push('/change-password')"><template #icon><AppIcon :icon="Key" /></template>修改密码</NButton>
        <NButton quaternary @click="logout"><template #icon><AppIcon :icon="Logout" /></template>退出</NButton>
      </div>
    </header>
    <section class="content">
      <div><h1>系统概览</h1><p>查看网盘运行数据并管理普通用户</p></div>
      <div class="stats">
        <div class="stat"><AppIcon :icon="Users" /><span><small>用户总数</small><strong>{{ overview?.user_count ?? '—' }}</strong></span></div>
        <div class="stat"><AppIcon :icon="Database" /><span><small>正常用户</small><strong>{{ overview?.active_user_count ?? '—' }}</strong></span></div>
        <div class="stat"><AppIcon :icon="File" /><span><small>文件总数</small><strong>{{ overview?.file_count ?? '—' }}</strong></span></div>
        <div class="stat"><AppIcon :icon="Database" /><span><small>存储占用</small><strong>{{ overview ? formatSize(overview.storage_bytes) : '—' }}</strong></span></div>
      </div>
      <section class="users-panel">
        <div class="panel-head"><div><h2>用户管理</h2><span>不包含唯一管理员账号</span></div><NInput v-model:value="search" clearable placeholder="搜索姓名或邮箱" @keyup.enter="load"><template #prefix><AppIcon :icon="Search" /></template></NInput></div>
        <NDataTable :columns="columns" :data="users" :loading="loading" :row-key="(row: AdminUser) => row.id" :scroll-x="860" />
      </section>
    </section>
    <NModal v-model:show="quotaDialog" preset="dialog" title="调整容量配额" positive-text="保存" negative-text="取消" :loading="quotaLoading" @positive-click="saveQuota">
      <div class="quota-form"><span>{{ quotaUser?.name }}（GB）</span><NInputNumber v-model:value="quotaGb" :min="0" :precision="1" style="width: 100%" /></div>
    </NModal>
  </main>
</template>

<style scoped lang="scss">
@use '@/assets/styles/variables' as *;
.admin-page { min-height: 100vh; background: $background; }
.admin-header { height: 68px; display: flex; align-items: center; justify-content: space-between; padding: 0 32px; border-bottom: 1px solid $border; background: $surface; }
.brand { display: flex; align-items: center; gap: 10px; }.brand-mark { width: 32px; height: 32px; display: grid; place-items: center; border-radius: 9px; color: white; background: $primary; font-weight: 650; }.brand > span:last-child { display: grid; }.brand small { color: $text-muted; font-size: 10px; }
.account-actions { display: flex; align-items: center; gap: 8px; color: $text-secondary; font-size: 13px; }
.content { width: min(1180px, calc(100% - 40px)); margin: 0 auto; padding: 34px 0 60px; }.content h1 { margin: 0; font-size: 27px; }.content > div > p { margin: 6px 0 0; color: $text-secondary; }
.stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin: 26px 0; }.stat { display: flex; align-items: center; gap: 14px; padding: 20px; border: 1px solid $border; border-radius: $radius-lg; background: $surface; color: $primary; }.stat > span { display: grid; }.stat small { color: $text-muted; }.stat strong { margin-top: 3px; color: $text; font-size: 23px; }
.users-panel { overflow: hidden; border: 1px solid $border; border-radius: $radius-lg; background: $surface; }.panel-head { display: flex; align-items: center; justify-content: space-between; padding: 18px 20px; border-bottom: 1px solid $border; }.panel-head h2 { margin: 0; font-size: 17px; }.panel-head span { color: $text-muted; font-size: 12px; }.panel-head :deep(.n-input) { width: 260px; }
:deep(.user-cell) { display: grid; }:deep(.user-cell small) { color: $text-muted; }.quota-form { display: grid; gap: 8px; padding-top: 8px; }
@media (max-width: 800px) { .admin-header { padding: 0 16px; }.account-actions > span { display: none; }.stats { grid-template-columns: repeat(2, 1fr); }.panel-head { align-items: stretch; flex-direction: column; gap: 12px; }.panel-head :deep(.n-input) { width: 100%; } }
@media (max-width: 480px) { .account-actions .n-button:first-of-type { display: none; }.stats { grid-template-columns: 1fr; } }
</style>

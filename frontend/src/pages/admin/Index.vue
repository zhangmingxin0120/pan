<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Api, Database, File, Key, LayoutBoard, Logout, Search, Users } from '@vicons/tabler'
import {
  NButton,
  NDataTable,
  NInput,
  NInputNumber,
  NModal,
  NSwitch,
  NTag,
  useMessage,
  type DataTableColumns,
} from 'naive-ui'
import AppIcon from '@/components/base/AppIcon.vue'
import IntegrationPanel from '@/components/admin/IntegrationPanel.vue'
import {
  createUser,
  getOverview,
  getSettings,
  getUsers,
  resetUserPassword,
  updateSettings,
  updateUser,
} from '@/api/modules/admin'
import { useAuthStore } from '@/stores/auth.store'
import type { AdminOverview, AdminSettings, AdminUser } from '@/types'

const router = useRouter()
const authStore = useAuthStore()
const message = useMessage()
const overview = ref<AdminOverview | null>(null)
const settings = ref<AdminSettings | null>(null)
const users = ref<AdminUser[]>([])
const search = ref('')
const loading = ref(true)
const settingsLoading = ref(false)

const currentSection = computed(() => {
  if (router.currentRoute.value.name === 'admin-users') return 'users'
  if (router.currentRoute.value.name === 'admin-api') return 'api'
  return 'overview'
})

const quotaDialog = reactive({ show: false, user: null as AdminUser | null, gb: null as number | null, loading: false })
const createDialog = reactive({ show: false, email: '', name: '', quotaGb: 5, loading: false })
const resetDialog = reactive({ show: false, user: null as AdminUser | null, password: '123456', loading: false })
const credentialDialog = reactive({ show: false, title: '', email: '', password: '' })

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

const formatDate = (value: string) =>
  new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium' }).format(new Date(value))

const diskFreePercent = computed(() => {
  if (!overview.value?.disk_total_bytes) return 0
  return (overview.value.disk_free_bytes / overview.value.disk_total_bytes) * 100
})

const diskHealth = computed(() => {
  if (diskFreePercent.value <= 5) return { label: '即将用满', type: 'error' as const }
  if (diskFreePercent.value <= 15) return { label: '空间偏低', type: 'warning' as const }
  return { label: '空间充足', type: 'success' as const }
})

const errorText = (error: unknown) =>
  (error as { userMessage?: string }).userMessage || '操作失败，请重试'

async function load() {
  loading.value = true
  try {
    const [summary, result, systemSettings] = await Promise.all([
      getOverview(),
      getUsers(search.value || undefined),
      getSettings(),
    ])
    overview.value = summary
    users.value = result.items
    settings.value = systemSettings
  } catch (error) {
    message.error(errorText(error))
  } finally {
    loading.value = false
  }
}

async function toggleRegistration(enabled: boolean) {
  settingsLoading.value = true
  try {
    settings.value = await updateSettings(enabled)
    message.success(enabled ? '公开注册已开启' : '公开注册已关闭，已有用户仍可登录')
  } catch (error) {
    message.error(errorText(error))
  } finally {
    settingsLoading.value = false
  }
}

async function toggleUser(user: AdminUser, active: boolean) {
  try {
    const updated = await updateUser(user.id, { is_active: active })
    Object.assign(user, updated)
    if (overview.value) overview.value.active_user_count += active ? 1 : -1
    message.success(active ? '用户已启用' : '用户已停用，现有登录已失效')
  } catch (error) {
    message.error(errorText(error))
  }
}

function editQuota(user: AdminUser) {
  quotaDialog.user = user
  quotaDialog.gb = user.quota_bytes / 1024 ** 3
  quotaDialog.show = true
}

async function saveQuota() {
  if (!quotaDialog.user || quotaDialog.gb === null) return false
  quotaDialog.loading = true
  try {
    const updated = await updateUser(quotaDialog.user.id, {
      quota_bytes: Math.round(quotaDialog.gb * 1024 ** 3),
    })
    Object.assign(quotaDialog.user, updated)
    quotaDialog.show = false
    message.success('容量配额已更新')
  } catch (error) {
    message.error(errorText(error))
  } finally {
    quotaDialog.loading = false
  }
  return false
}

function openCreateUser() {
  createDialog.email = ''
  createDialog.name = ''
  createDialog.quotaGb = 5
  createDialog.show = true
}

async function submitCreateUser() {
  if (!createDialog.name.trim()) return message.warning('请输入显示名称'), false
  if (!/^\S+@\S+\.\S+$/.test(createDialog.email)) return message.warning('请输入有效邮箱'), false
  createDialog.loading = true
  try {
    const result = await createUser({
      email: createDialog.email,
      name: createDialog.name,
      quota_bytes: Math.round(createDialog.quotaGb * 1024 ** 3),
    })
    createDialog.show = false
    credentialDialog.title = '账号已创建'
    credentialDialog.email = result.user.email
    credentialDialog.password = result.temporary_password
    credentialDialog.show = true
    await load()
  } catch (error) {
    message.error(errorText(error))
  } finally {
    createDialog.loading = false
  }
  return false
}

function resetPassword(user: AdminUser) {
  resetDialog.user = user
  resetDialog.password = '123456'
  resetDialog.show = true
}

async function submitResetPassword() {
  if (!resetDialog.user) return false
  if (resetDialog.password.length < 6) return message.warning('重置密码至少需要 6 位'), false
  resetDialog.loading = true
  try {
    const result = await resetUserPassword(resetDialog.user.id, resetDialog.password)
    resetDialog.show = false
    credentialDialog.title = '密码已重置'
    credentialDialog.email = resetDialog.user.email
    credentialDialog.password = result.temporary_password
    credentialDialog.show = true
  } catch (error) {
    message.error(errorText(error))
  } finally {
    resetDialog.loading = false
  }
  return false
}

async function copyCredentials() {
  await navigator.clipboard.writeText(
    `登录邮箱：${credentialDialog.email}\n临时密码：${credentialDialog.password}\n首次登录后请立即修改密码。`,
  )
  message.success('登录信息已复制')
  return false
}

const columns = computed<DataTableColumns<AdminUser>>(() => [
  {
    title: '用户',
    key: 'name',
    render: (row) =>
      h('div', { class: 'user-cell' }, [h('strong', row.name), h('small', row.email)]),
  },
  {
    title: '存储使用',
    key: 'used_bytes',
    render: (row) => `${formatSize(row.used_bytes)} / ${formatSize(row.quota_bytes)}`,
  },
  { title: '注册时间', key: 'created_at', render: (row) => formatDate(row.created_at) },
  {
    title: '状态',
    key: 'is_active',
    render: (row) =>
      h(
        NTag,
        { type: row.is_active ? 'success' : 'default', size: 'small' },
        { default: () => (row.is_active ? '正常' : '已停用') },
      ),
  },
  {
    title: '启用',
    key: 'toggle',
    width: 80,
    render: (row) =>
      h(NSwitch, {
        value: row.is_active,
        'onUpdate:value': (value: boolean) => void toggleUser(row, value),
      }),
  },
  {
    title: '操作',
    key: 'actions',
    width: 190,
    render: (row) =>
      h('div', { class: 'table-actions' }, [
        h(NButton, { size: 'small', onClick: () => editQuota(row) }, { default: () => '调整配额' }),
        h(
          NButton,
          { size: 'small', quaternary: true, onClick: () => resetPassword(row) },
          { default: () => '重置密码' },
        ),
      ]),
  },
])

function logout() {
  authStore.logout()
  void router.replace('/admin/login')
}

function navigate(section: 'overview' | 'users' | 'api') {
  const targets = { overview: '/admin', users: '/admin/users', api: '/admin/api' }
  void router.push(targets[section])
}

onMounted(() => void load())
</script>

<template>
  <main class="admin-page">
    <aside class="admin-sidebar">
      <div class="brand"><span class="brand-mark">P</span><span><strong>Pan</strong><small>系统管理</small></span></div>
      <nav class="admin-nav" aria-label="管理菜单">
        <button :class="{ active: currentSection === 'overview' }" @click="navigate('overview')"><AppIcon :icon="LayoutBoard" />概览</button>
        <button :class="{ active: currentSection === 'users' }" @click="navigate('users')"><AppIcon :icon="Users" />用户管理</button>
        <button :class="{ active: currentSection === 'api' }" @click="navigate('api')"><AppIcon :icon="Api" />开放 API</button>
      </nav>
      <div class="sidebar-foot">Pan 私人云盘</div>
    </aside>

    <div class="admin-workspace">
      <header class="admin-header">
        <span class="workspace-label">管理后台</span>
        <div class="account-actions">
          <span>administrator</span>
          <NButton quaternary @click="router.push('/change-password')"><template #icon><AppIcon :icon="Key" /></template>修改密码</NButton>
          <NButton quaternary @click="logout"><template #icon><AppIcon :icon="Logout" /></template>退出</NButton>
        </div>
      </header>

      <div class="admin-layout">
        <section class="content" :class="currentSection === 'overview' ? 'content--wide' : 'content--fluid'">
      <div class="page-header" v-if="currentSection === 'overview'"><h1>系统概览</h1><p>查看网盘运行数据与存储状态</p></div>
      <div class="page-header" v-else-if="currentSection === 'users'"><h1>用户管理</h1><p>创建内部账号、调整容量和重置用户密码</p></div>
      <div class="page-header" v-else><h1>开放 API</h1><p>为指定账号创建 API，并精确控制接口权限</p></div>
      <div v-if="currentSection === 'overview'" class="stats">
        <div class="stat"><AppIcon :icon="Users" /><span><small>用户总数</small><strong>{{ overview?.user_count ?? '—' }}</strong></span></div>
        <div class="stat"><AppIcon :icon="Database" /><span><small>正常用户</small><strong>{{ overview?.active_user_count ?? '—' }}</strong></span></div>
        <div class="stat"><AppIcon :icon="File" /><span><small>文件总数</small><strong>{{ overview?.file_count ?? '—' }}</strong></span></div>
        <div class="stat storage-stat">
          <AppIcon :icon="Database" />
          <span>
            <small>全站文件总量</small>
            <strong>{{ overview ? formatSize(overview.storage_bytes) : '—' }}</strong>
            <span v-if="overview" class="stat-detail">磁盘剩余 {{ formatSize(overview.disk_free_bytes) }} / {{ formatSize(overview.disk_total_bytes) }}（{{ diskFreePercent.toFixed(1) }}%）</span>
          </span>
          <NTag v-if="overview" :type="diskHealth.type" size="small" round>{{ diskHealth.label }}</NTag>
        </div>
      </div>

      <section v-if="currentSection === 'overview'" class="registration-setting">
        <div><strong>允许公开注册</strong><span>关闭后注册入口隐藏，已有用户、管理员和公开分享不受影响。</span></div>
        <NSwitch :value="settings?.registration_enabled || false" :loading="settingsLoading" @update:value="toggleRegistration" />
      </section>

      <section v-if="currentSection === 'users'" class="users-panel">
        <div class="panel-head">
          <div><h2>账号列表</h2><span>查看账号状态与存储使用情况</span></div>
          <div class="panel-actions">
            <NInput v-model:value="search" clearable placeholder="搜索姓名或邮箱" @keyup.enter="load"><template #prefix><AppIcon :icon="Search" /></template></NInput>
            <NButton type="primary" @click="openCreateUser">创建账号</NButton>
          </div>
        </div>
        <NDataTable :columns="columns" :data="users" :loading="loading" :row-key="(row: AdminUser) => row.id" :scroll-x="960" />
      </section>

      <IntegrationPanel v-if="currentSection === 'api'" :users="users" />
        </section>
      </div>
    </div>

    <NModal v-model:show="quotaDialog.show" preset="dialog" title="调整容量配额" positive-text="保存" negative-text="取消" :loading="quotaDialog.loading" @positive-click="saveQuota">
      <div class="form-stack"><span>{{ quotaDialog.user?.name }}（GiB）</span><NInputNumber v-model:value="quotaDialog.gb" :min="0" :precision="1" style="width: 100%" /></div>
    </NModal>

    <NModal v-model:show="createDialog.show" preset="dialog" title="创建内部账号" positive-text="创建账号" negative-text="取消" :loading="createDialog.loading" :mask-closable="false" @positive-click="submitCreateUser">
      <div class="form-stack">
        <label><span>显示名称</span><NInput v-model:value="createDialog.name" maxlength="80" placeholder="例如：小潘" /></label>
        <label><span>登录邮箱</span><NInput v-model:value="createDialog.email" placeholder="name@example.com" autocomplete="off" /></label>
        <label><span>容量配额（GiB）</span><NInputNumber v-model:value="createDialog.quotaGb" :min="0" :precision="1" style="width: 100%" /></label>
      </div>
    </NModal>

    <NModal v-model:show="resetDialog.show" preset="dialog" :title="`重置 ${resetDialog.user?.name || ''} 的密码`" positive-text="确认重置" negative-text="取消" :loading="resetDialog.loading" :mask-closable="false" @positive-click="submitResetPassword">
      <div class="form-stack">
        <p class="reset-warning">重置后，该用户的现有登录立即失效，并且下次登录后必须修改密码。</p>
        <label><span>设置新密码</span><NInput v-model:value="resetDialog.password" maxlength="128" placeholder="请输入至少 6 位密码" /></label>
      </div>
    </NModal>

    <NModal v-model:show="credentialDialog.show" preset="dialog" :title="credentialDialog.title" positive-text="复制登录信息" negative-text="关闭" :mask-closable="false" @positive-click="copyCredentials">
      <div class="credential-box">
        <p>临时密码只显示这一次，请复制后安全地交给用户。</p>
        <label><span>登录邮箱</span><NInput :value="credentialDialog.email" readonly /></label>
        <label><span>临时密码</span><NInput :value="credentialDialog.password" readonly /></label>
        <small>用户首次登录后必须修改密码，完成前不能使用网盘。</small>
      </div>
    </NModal>
  </main>
</template>

<style scoped lang="scss">
@use '@/assets/styles/variables' as *;
.admin-page { min-height: 100vh; background: $background; }
.admin-sidebar { position: fixed; z-index: 20; inset: 0 auto 0 0; width: 216px; display: flex; flex-direction: column; border-right: 1px solid $border; background: $surface; }
.brand { height: 56px; display: flex; align-items: center; gap: 10px; padding: 0 20px; border-bottom: 1px solid $border; }
.brand-mark { width: 30px; height: 30px; display: grid; place-items: center; flex: 0 0 auto; border-radius: $radius-md; color: white; background: $primary; font-weight: 650; }
.brand > span:last-child { display: grid; min-width: 0; }.brand strong { line-height: 1.1; }.brand small { margin-top: 2px; color: $text-muted; font-size: 10px; }
.admin-nav { display: grid; gap: 4px; padding: 18px 12px; }
.admin-nav button { min-height: 40px; display: flex; align-items: center; gap: 11px; padding: 0 12px; border: 0; border-radius: $radius-md; color: $text-secondary; background: transparent; font: inherit; font-size: 14px; text-align: left; cursor: pointer; transition: color .16s ease, background-color .16s ease; }
.admin-nav button:hover { color: $text; background: $surface-muted; }.admin-nav button:focus-visible { outline: 2px solid $primary; outline-offset: 2px; }.admin-nav button.active { color: $primary; background: $primary-soft; font-weight: 600; }
.sidebar-foot { margin-top: auto; padding: 16px 24px; border-top: 1px solid $border; color: $text-muted; font-size: 11px; }
.admin-workspace { min-height: 100vh; margin-left: 216px; }
.admin-header { position: sticky; z-index: 15; top: 0; height: 56px; display: flex; align-items: center; justify-content: space-between; gap: 24px; padding: 0 24px; border-bottom: 1px solid $border; background: rgba(255, 255, 255, .96); backdrop-filter: blur(10px); }
.workspace-label { color: $text-secondary; font-size: 13px; font-weight: 500; }.account-actions { display: flex; align-items: center; gap: 4px; flex: 0 0 auto; color: $text-secondary; font-size: 13px; }
.admin-layout { width: 100%; padding: 24px; }.content { width: 100%; min-width: 0; margin: 0 auto; }.content--wide { max-width: 1440px; }.content--fluid { max-width: none; }
.page-header { margin-bottom: 18px; }.page-header h1 { margin: 0; color: $text; font-size: 20px; font-weight: 600; line-height: 28px; }.page-header p { margin: 3px 0 0; color: $text-secondary; font-size: 13px; line-height: 20px; }
.stats { display: grid; grid-template-columns: repeat(3, minmax(160px, 1fr)) minmax(300px, 1.6fr); gap: 12px; margin-bottom: 16px; }.stat { min-width: 0; min-height: 104px; display: flex; align-items: center; gap: 13px; padding: 18px; border: 1px solid $border; border-radius: $radius-md; background: $surface; color: $primary; }.stat > span { display: grid; min-width: 0; }.stat small { color: $text-muted; font-size: 12px; }.stat strong { margin-top: 3px; color: $text; font-size: 22px; font-variant-numeric: tabular-nums; }
.storage-stat { position: relative; }.storage-stat .stat-detail { margin-top: 4px; overflow: hidden; color: $text-muted; font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }.storage-stat > .n-tag { position: absolute; top: 14px; right: 14px; }
.registration-setting { display: flex; align-items: center; justify-content: space-between; gap: 20px; padding: 16px 18px; border: 1px solid $border; border-radius: $radius-md; background: $surface; }.registration-setting > div { display: grid; gap: 2px; }.registration-setting strong { font-size: 14px; }.registration-setting span { color: $text-muted; font-size: 12px; }
.users-panel { overflow: hidden; border: 1px solid $border; border-radius: $radius-md; background: $surface; }.panel-head { min-height: 64px; display: flex; align-items: center; justify-content: space-between; gap: 20px; padding: 12px 16px; border-bottom: 1px solid $border; }.panel-head h2 { margin: 0; font-size: 16px; }.panel-head span { color: $text-muted; font-size: 12px; }.panel-actions, :deep(.table-actions) { display: flex; align-items: center; gap: 8px; }.panel-actions :deep(.n-input) { width: 260px; }
:deep(.user-cell) { display: grid; min-width: 0; }:deep(.user-cell small) { overflow: hidden; color: $text-muted; text-overflow: ellipsis; }.form-stack, .credential-box { display: grid; gap: 14px; padding-top: 6px; }.form-stack label, .credential-box label { display: grid; gap: 6px; color: $text-secondary; font-size: 13px; }.credential-box p { margin: 0; padding: 10px 12px; color: $warning; background: #fff7ea; border-radius: $radius-md; }.credential-box small { color: $text-muted; }
.reset-warning { margin: 0; padding: 10px 12px; color: $warning; background: #fff7ea; border-radius: $radius-md; font-size: 13px; }
@media (max-width: 1180px) { .stats { grid-template-columns: repeat(3, 1fr); }.storage-stat { grid-column: 1 / -1; }.account-actions > span { display: none; } }
@media (max-width: 900px) { .admin-sidebar { width: 64px; }.brand { justify-content: center; padding: 0; }.brand > span:last-child, .sidebar-foot { display: none; }.admin-nav { padding: 14px 8px; }.admin-nav button { justify-content: center; padding: 0; font-size: 0; }.admin-workspace { margin-left: 64px; }.admin-layout { padding: 16px; }.admin-header { padding: 0 16px; }.stats { grid-template-columns: repeat(2, 1fr); }.storage-stat { grid-column: 1 / -1; }.panel-head { align-items: stretch; flex-direction: column; }.panel-actions :deep(.n-input) { width: 100%; }.panel-actions { align-items: stretch; } }
@media (max-width: 640px) { .admin-sidebar { position: static; width: 100%; height: auto; border-right: 0; }.brand { display: none; }.admin-nav { display: flex; padding: 6px 8px; border-bottom: 1px solid $border; }.admin-nav button { flex: 1; gap: 6px; padding: 0 8px; font-size: 12px; }.admin-workspace { margin-left: 0; }.admin-header { position: static; }.workspace-label { display: none; }.account-actions { margin-left: auto; }.account-actions .n-button:first-of-type { display: none; }.stats { grid-template-columns: 1fr; }.storage-stat { grid-column: auto; }.registration-setting { align-items: flex-start; }.panel-actions { flex-direction: column; } }
</style>

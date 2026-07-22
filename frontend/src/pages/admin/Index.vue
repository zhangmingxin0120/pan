<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Database, File, Key, Logout, Search, Users } from '@vicons/tabler'
import {
  NButton,
  NDataTable,
  NInput,
  NInputNumber,
  NModal,
  NSwitch,
  NTag,
  useDialog,
  useMessage,
  type DataTableColumns,
} from 'naive-ui'
import AppIcon from '@/components/base/AppIcon.vue'
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
const dialog = useDialog()
const overview = ref<AdminOverview | null>(null)
const settings = ref<AdminSettings | null>(null)
const users = ref<AdminUser[]>([])
const search = ref('')
const loading = ref(true)
const settingsLoading = ref(false)

const quotaDialog = reactive({ show: false, user: null as AdminUser | null, gb: null as number | null, loading: false })
const createDialog = reactive({ show: false, email: '', name: '', quotaGb: 5, loading: false })
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
  dialog.warning({
    title: `重置 ${user.name} 的密码？`,
    content: '重置后该用户的所有现有登录立即失效，并需要使用新临时密码登录。',
    positiveText: '确认重置',
    negativeText: '取消',
    async onPositiveClick() {
      try {
        const result = await resetUserPassword(user.id)
        credentialDialog.title = '密码已重置'
        credentialDialog.email = user.email
        credentialDialog.password = result.temporary_password
        credentialDialog.show = true
      } catch (error) {
        message.error(errorText(error))
      }
    },
  })
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

      <section class="registration-setting">
        <div><strong>允许公开注册</strong><span>关闭后注册入口隐藏，已有用户、管理员和公开分享不受影响。</span></div>
        <NSwitch :value="settings?.registration_enabled || false" :loading="settingsLoading" @update:value="toggleRegistration" />
      </section>

      <section class="users-panel">
        <div class="panel-head">
          <div><h2>用户管理</h2><span>创建内部账号、调整容量或重置密码</span></div>
          <div class="panel-actions">
            <NInput v-model:value="search" clearable placeholder="搜索姓名或邮箱" @keyup.enter="load"><template #prefix><AppIcon :icon="Search" /></template></NInput>
            <NButton type="primary" @click="openCreateUser">创建账号</NButton>
          </div>
        </div>
        <NDataTable :columns="columns" :data="users" :loading="loading" :row-key="(row: AdminUser) => row.id" :scroll-x="960" />
      </section>
    </section>

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
.admin-header { height: 68px; display: flex; align-items: center; justify-content: space-between; padding: 0 32px; border-bottom: 1px solid $border; background: $surface; }
.brand { display: flex; align-items: center; gap: 10px; }.brand-mark { width: 32px; height: 32px; display: grid; place-items: center; border-radius: 9px; color: white; background: $primary; font-weight: 650; }.brand > span:last-child { display: grid; }.brand small { color: $text-muted; font-size: 10px; }
.account-actions { display: flex; align-items: center; gap: 8px; color: $text-secondary; font-size: 13px; }
.content { width: min(1180px, calc(100% - 40px)); margin: 0 auto; padding: 34px 0 60px; }.content h1 { margin: 0; font-size: 27px; }.content > div > p { margin: 6px 0 0; color: $text-secondary; }
.stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin: 26px 0 16px; }.stat { display: flex; align-items: center; gap: 14px; padding: 20px; border: 1px solid $border; border-radius: $radius-lg; background: $surface; color: $primary; }.stat > span { display: grid; }.stat small { color: $text-muted; }.stat strong { margin-top: 3px; color: $text; font-size: 23px; }
.registration-setting { display: flex; align-items: center; justify-content: space-between; gap: 20px; padding: 17px 20px; margin-bottom: 16px; border: 1px solid $border; border-radius: $radius-lg; background: $surface; }.registration-setting > div { display: grid; gap: 3px; }.registration-setting span { color: $text-muted; font-size: 12px; }
.users-panel { overflow: hidden; border: 1px solid $border; border-radius: $radius-lg; background: $surface; }.panel-head { display: flex; align-items: center; justify-content: space-between; gap: 20px; padding: 18px 20px; border-bottom: 1px solid $border; }.panel-head h2 { margin: 0; font-size: 17px; }.panel-head span { color: $text-muted; font-size: 12px; }.panel-actions, :deep(.table-actions) { display: flex; align-items: center; gap: 8px; }.panel-actions :deep(.n-input) { width: 260px; }
:deep(.user-cell) { display: grid; }:deep(.user-cell small) { color: $text-muted; }.form-stack, .credential-box { display: grid; gap: 14px; padding-top: 6px; }.form-stack label, .credential-box label { display: grid; gap: 6px; color: $text-secondary; font-size: 13px; }.credential-box p { margin: 0; padding: 10px 12px; color: $warning; background: #fff7ea; border-radius: $radius-md; }.credential-box small { color: $text-muted; }
@media (max-width: 800px) { .admin-header { padding: 0 16px; }.account-actions > span { display: none; }.stats { grid-template-columns: repeat(2, 1fr); }.panel-head { align-items: stretch; flex-direction: column; }.panel-actions :deep(.n-input) { width: 100%; }.panel-actions { align-items: stretch; } }
@media (max-width: 480px) { .account-actions .n-button:first-of-type { display: none; }.stats { grid-template-columns: 1fr; }.registration-setting { align-items: flex-start; }.panel-actions { flex-direction: column; } }
</style>

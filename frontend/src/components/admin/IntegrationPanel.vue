<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue'
import {
  NButton,
  NDataTable,
  NInput,
  NModal,
  NSelect,
  NSwitch,
  NTag,
  useDialog,
  useMessage,
  type DataTableColumns,
} from 'naive-ui'
import {
  createApiApplication,
  getApiApplications,
  getIntegrationFolders,
  rotateApiApplicationKey,
  updateApiApplication,
} from '@/api/modules/admin'
import type { AdminUser, ApiApplication, IntegrationFolder } from '@/types'

const props = defineProps<{ users: AdminUser[] }>()
const message = useMessage()
const dialog = useDialog()
const applications = ref<ApiApplication[]>([])
const loading = ref(true)
const folders = ref<IntegrationFolder[]>([])
const folderLoading = ref(false)

const createDialog = reactive({
  show: false,
  loading: false,
  name: '',
  userId: null as string | null,
  rootNodeId: null as string | null,
  canRead: true,
  canWrite: true,
  canDelete: false,
})
const secretDialog = reactive({ show: false, title: '', apiKey: '' })

const userOptions = computed(() =>
  props.users
    .filter((user) => user.is_active)
    .map((user) => ({ label: `${user.name}（${user.email}）`, value: user.id })),
)
const folderOptions = computed(() =>
  folders.value.map((folder) => ({ label: folder.path, value: folder.id })),
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

const formatDateTime = (value: string | null) =>
  value
    ? new Intl.DateTimeFormat('zh-CN', { dateStyle: 'short', timeStyle: 'short' }).format(
        new Date(value),
      )
    : '尚未调用'

const errorText = (error: unknown) =>
  (error as { userMessage?: string }).userMessage || '操作失败，请重试'

async function loadApplications() {
  loading.value = true
  try {
    applications.value = (await getApiApplications()).items
  } catch (error) {
    message.error(errorText(error))
  } finally {
    loading.value = false
  }
}

function openCreate() {
  Object.assign(createDialog, {
    show: true,
    name: '',
    userId: null,
    rootNodeId: null,
    canRead: true,
    canWrite: true,
    canDelete: false,
  })
  folders.value = []
}

async function selectUser(userId: string | null) {
  createDialog.userId = userId
  createDialog.rootNodeId = null
  folders.value = []
  if (!userId) return
  folderLoading.value = true
  try {
    folders.value = await getIntegrationFolders(userId)
    const root = folders.value.find((folder) => folder.path === '/')
    createDialog.rootNodeId = root?.id || folders.value[0]?.id || null
  } catch (error) {
    message.error(errorText(error))
  } finally {
    folderLoading.value = false
  }
}

async function submitCreate() {
  if (!createDialog.name.trim()) return message.warning('请输入应用名称'), false
  if (!createDialog.userId) return message.warning('请选择关联账号'), false
  if (!createDialog.rootNodeId) return message.warning('请选择授权目录'), false
  if (!createDialog.canRead && !createDialog.canWrite && !createDialog.canDelete) {
    return message.warning('至少选择一项权限'), false
  }
  createDialog.loading = true
  try {
    const result = await createApiApplication({
      name: createDialog.name,
      user_id: createDialog.userId,
      root_node_id: createDialog.rootNodeId,
      can_read: createDialog.canRead,
      can_write: createDialog.canWrite,
      can_delete: createDialog.canDelete,
    })
    createDialog.show = false
    secretDialog.title = 'API 应用已创建'
    secretDialog.apiKey = result.api_key
    secretDialog.show = true
    await loadApplications()
  } catch (error) {
    message.error(errorText(error))
  } finally {
    createDialog.loading = false
  }
  return false
}

async function toggleApplication(application: ApiApplication, active: boolean) {
  try {
    Object.assign(application, await updateApiApplication(application.id, active))
    message.success(active ? 'API 应用已启用' : 'API 应用已停用，密钥立即失效')
  } catch (error) {
    message.error(errorText(error))
  }
}

function rotateKey(application: ApiApplication) {
  dialog.warning({
    title: `轮换 ${application.name} 的密钥？`,
    content: '轮换后旧密钥立即失效，外部系统必须改用新密钥。',
    positiveText: '确认轮换',
    negativeText: '取消',
    async onPositiveClick() {
      try {
        const result = await rotateApiApplicationKey(application.id)
        secretDialog.title = 'API Key 已轮换'
        secretDialog.apiKey = result.api_key
        secretDialog.show = true
        await loadApplications()
      } catch (error) {
        message.error(errorText(error))
      }
    },
  })
}

async function copyApiKey() {
  await navigator.clipboard.writeText(secretDialog.apiKey)
  message.success('API Key 已复制')
  return false
}

const columns: DataTableColumns<ApiApplication> = [
  {
    title: '应用',
    key: 'name',
    render: (row) => h('div', { class: 'stack-cell' }, [h('strong', row.name), h('small', row.key_prefix)]),
  },
  {
    title: '账号与目录',
    key: 'scope',
    render: (row) => h('div', { class: 'stack-cell' }, [h('span', row.user_email), h('small', row.root_path)]),
  },
  {
    title: '权限',
    key: 'permissions',
    render: (row) =>
      h('div', { class: 'permission-tags' }, [
        row.can_read ? h(NTag, { size: 'small' }, { default: () => '读取' }) : null,
        row.can_write ? h(NTag, { size: 'small' }, { default: () => '写入' }) : null,
        row.can_delete ? h(NTag, { size: 'small', type: 'warning' }, { default: () => '删除' }) : null,
      ]),
  },
  {
    title: '接口使用',
    key: 'usage',
    render: (row) =>
      h('div', { class: 'stack-cell' }, [
        h('span', `${row.request_count} 次调用 · ${row.failed_request_count} 次失败`),
        h('small', `上传 ${formatSize(row.upload_bytes)} · 下载 ${formatSize(row.download_bytes)}`),
      ]),
  },
  { title: '最近调用', key: 'last_used_at', render: (row) => formatDateTime(row.last_used_at) },
  {
    title: '状态',
    key: 'is_active',
    width: 76,
    render: (row) =>
      h(NSwitch, {
        value: row.is_active,
        'onUpdate:value': (value: boolean) => void toggleApplication(row, value),
      }),
  },
  {
    title: '操作',
    key: 'actions',
    width: 92,
    render: (row) =>
      h(NButton, { size: 'small', quaternary: true, onClick: () => rotateKey(row) }, { default: () => '轮换密钥' }),
  },
]

onMounted(() => void loadApplications())
</script>

<template>
  <section class="integration-panel">
    <div class="panel-head">
      <div>
        <h2>开放 API</h2>
        <span>为外部系统授权指定账号和文件夹，密钥与用户登录相互独立</span>
      </div>
      <div class="panel-actions">
        <NButton tag="a" href="/api/docs" target="_blank">接口文档</NButton>
        <NButton type="primary" @click="openCreate">创建 API 应用</NButton>
      </div>
    </div>
    <NDataTable :columns="columns" :data="applications" :loading="loading" :row-key="(row: ApiApplication) => row.id" :scroll-x="1180" />

    <NModal v-model:show="createDialog.show" preset="dialog" title="创建 API 应用" positive-text="创建应用" negative-text="取消" :loading="createDialog.loading" :mask-closable="false" @positive-click="submitCreate">
      <div class="form-stack">
        <label><span>应用名称</span><NInput v-model:value="createDialog.name" maxlength="80" placeholder="例如：合同管理系统" /></label>
        <label><span>关联账号</span><NSelect :value="createDialog.userId" :options="userOptions" filterable placeholder="选择普通用户" @update:value="selectUser" /></label>
        <label><span>授权目录</span><NSelect v-model:value="createDialog.rootNodeId" :options="folderOptions" :loading="folderLoading" filterable placeholder="该应用只能访问此目录及其子目录" /></label>
        <div class="permission-list">
          <span>接口权限</span>
          <label><NSwitch v-model:value="createDialog.canRead" />读取和下载</label>
          <label><NSwitch v-model:value="createDialog.canWrite" />上传和管理</label>
          <label><NSwitch v-model:value="createDialog.canDelete" />移入回收站</label>
        </div>
      </div>
    </NModal>

    <NModal v-model:show="secretDialog.show" preset="dialog" :title="secretDialog.title" positive-text="复制 API Key" negative-text="关闭" :mask-closable="false" @positive-click="copyApiKey">
      <div class="secret-box">
        <p>API Key 只完整显示这一次，请立即复制并保存在外部系统的安全配置中。</p>
        <NInput :value="secretDialog.apiKey" type="textarea" readonly autosize />
        <small>请求时使用：Authorization: Bearer &lt;API Key&gt;</small>
      </div>
    </NModal>
  </section>
</template>

<style scoped lang="scss">
@use '@/assets/styles/variables' as *;
.integration-panel { overflow: hidden; margin-top: 16px; border: 1px solid $border; border-radius: $radius-lg; background: $surface; }
.panel-head { display: flex; align-items: center; justify-content: space-between; gap: 20px; padding: 18px 20px; border-bottom: 1px solid $border; }.panel-head h2 { margin: 0; font-size: 17px; }.panel-head span { color: $text-muted; font-size: 12px; }.panel-actions { display: flex; gap: 8px; }
:deep(.stack-cell) { display: grid; }:deep(.stack-cell small) { color: $text-muted; }:deep(.permission-tags) { display: flex; flex-wrap: wrap; gap: 4px; }
.form-stack, .secret-box { display: grid; gap: 14px; padding-top: 6px; }.form-stack > label { display: grid; gap: 6px; color: $text-secondary; font-size: 13px; }.permission-list { display: grid; grid-template-columns: 1fr auto auto auto; align-items: center; gap: 12px; padding-top: 4px; }.permission-list > span { color: $text-secondary; font-size: 13px; }.permission-list label { display: flex; align-items: center; gap: 6px; color: $text-secondary; font-size: 12px; }
.secret-box p { margin: 0; padding: 10px 12px; color: $warning; background: #fff7ea; border-radius: $radius-md; }.secret-box small { color: $text-muted; }
@media (max-width: 700px) { .panel-head { align-items: stretch; flex-direction: column; }.panel-actions { justify-content: flex-end; }.permission-list { grid-template-columns: 1fr; }.permission-list > span { margin-bottom: 2px; } }
</style>

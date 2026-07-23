<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue'
import {
  NButton,
  NDataTable,
  NDropdown,
  NInput,
  NModal,
  NSelect,
  NSpace,
  NSwitch,
  NTag,
  useDialog,
  useMessage,
  type DataTableColumns,
} from 'naive-ui'
import {
  createApiApplication,
  deleteApiApplication,
  getApiApplications,
  rotateApiApplicationKey,
  updateApiApplication,
} from '@/api/modules/admin'
import type { AdminUser, ApiApplication } from '@/types'

const props = defineProps<{ users: AdminUser[] }>()
const message = useMessage()
const dialog = useDialog()
const applications = ref<ApiApplication[]>([])
const loading = ref(true)

const defaultPermissions = {
  canRead: true,
  canDownload: false,
  canUpload: false,
  canManage: false,
  canDelete: false,
}

const createDialog = reactive({
  show: false,
  loading: false,
  name: '',
  userId: null as string | null,
  ...defaultPermissions,
})
const permissionDialog = reactive({
  show: false,
  loading: false,
  application: null as ApiApplication | null,
  ...defaultPermissions,
})
const secretDialog = reactive({ show: false, title: '', apiKey: '' })

const userOptions = computed(() =>
  props.users
    .filter((user) => user.is_active)
    .map((user) => ({ label: `${user.name}（${user.email}）`, value: user.id })),
)

const permissionItems = [
  { key: 'canRead', label: '读取列表/详情', hint: '允许查询文件夹、文件信息和搜索资源' },
  { key: 'canDownload', label: '下载文件', hint: '允许获取文件原始内容' },
  { key: 'canUpload', label: '上传文件', hint: '允许新增文件并占用账号容量' },
  { key: 'canManage', label: '管理目录与名称', hint: '允许创建文件夹、重命名、移动资源' },
  { key: 'canDelete', label: '删除到回收站', hint: '允许把文件或文件夹移入回收站' },
] as const

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

function hasAnyPermission(target: typeof createDialog | typeof permissionDialog) {
  return (
    target.canRead ||
    target.canDownload ||
    target.canUpload ||
    target.canManage ||
    target.canDelete
  )
}

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
    loading: false,
    name: '',
    userId: null,
    ...defaultPermissions,
  })
}

function selectUser(userId: string | null) {
  createDialog.userId = userId
}

function permissionPayload(target: typeof createDialog | typeof permissionDialog) {
  return {
    can_read: target.canRead,
    can_download: target.canDownload,
    can_upload: target.canUpload,
    can_manage: target.canManage,
    can_delete: target.canDelete,
  }
}

async function submitCreate() {
  if (!createDialog.name.trim()) return message.warning('请输入应用名称'), false
  if (!createDialog.userId) return message.warning('请选择关联账号'), false
  if (!hasAnyPermission(createDialog)) return message.warning('至少选择一项权限'), false
  createDialog.loading = true
  try {
    const result = await createApiApplication({
      name: createDialog.name,
      user_id: createDialog.userId,
      ...permissionPayload(createDialog),
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

function openPermissions(application: ApiApplication) {
  Object.assign(permissionDialog, {
    show: true,
    loading: false,
    application,
    canRead: application.can_read,
    canDownload: application.can_download,
    canUpload: application.can_upload,
    canManage: application.can_manage,
    canDelete: application.can_delete,
  })
}

async function submitPermissions() {
  if (!permissionDialog.application) return false
  if (!hasAnyPermission(permissionDialog)) return message.warning('至少保留一项权限'), false
  permissionDialog.loading = true
  try {
    const updated = await updateApiApplication(
      permissionDialog.application.id,
      permissionPayload(permissionDialog),
    )
    Object.assign(permissionDialog.application, updated)
    permissionDialog.show = false
    message.success('API 权限已更新')
  } catch (error) {
    message.error(errorText(error))
  } finally {
    permissionDialog.loading = false
  }
  return false
}

async function toggleApplication(application: ApiApplication, active: boolean) {
  try {
    Object.assign(application, await updateApiApplication(application.id, { is_active: active }))
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

function deleteApplication(application: ApiApplication) {
  dialog.warning({
    title: `删除 ${application.name}？`,
    content: '删除后，该应用的 API Key 将立即失效，且无法恢复。绑定账号和账号内文件不会被删除。',
    positiveText: '确认删除',
    negativeText: '取消',
    async onPositiveClick() {
      try {
        await deleteApiApplication(application.id)
        applications.value = applications.value.filter((item) => item.id !== application.id)
        message.success('API 应用已删除')
      } catch (error) {
        message.error(errorText(error))
      }
    },
  })
}

function handleMoreAction(key: string, application: ApiApplication) {
  if (key === 'rotate') rotateKey(application)
  if (key === 'delete') deleteApplication(application)
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
    title: '关联账号',
    key: 'scope',
    render: (row) => h('span', row.user_email),
  },
  {
    title: '权限',
    key: 'permissions',
    render: (row) =>
      h('div', { class: 'permission-tags' }, [
        row.can_read ? h(NTag, { size: 'small' }, { default: () => '读取' }) : null,
        row.can_download ? h(NTag, { size: 'small' }, { default: () => '下载' }) : null,
        row.can_upload ? h(NTag, { size: 'small' }, { default: () => '上传' }) : null,
        row.can_manage ? h(NTag, { size: 'small' }, { default: () => '管理' }) : null,
        row.can_delete ? h(NTag, { size: 'small' }, { default: () => '删除' }) : null,
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
    width: 140,
    render: (row) =>
      h(NSpace, { size: 4 }, {
        default: () => [
          h(NButton, { size: 'small', quaternary: true, onClick: () => openPermissions(row) }, { default: () => '权限' }),
          h(
            NDropdown,
            {
              trigger: 'click',
              options: [
                { label: '轮换密钥', key: 'rotate' },
                { type: 'divider', key: 'divider' },
                { label: '删除应用', key: 'delete' },
              ],
              onSelect: (key: string) => handleMoreAction(key, row),
            },
            { default: () => h(NButton, { size: 'small', quaternary: true }, { default: () => '更多' }) },
          ),
        ],
      }),
  },
]

onMounted(() => void loadApplications())
</script>

<template>
  <section class="integration-panel">
    <div class="panel-head">
      <div>
        <h2>API 应用</h2>
        <span>查看外部系统的授权账号、权限与调用情况</span>
      </div>
      <div class="panel-actions">
        <NButton tag="a" href="/api-docs" target="_blank">接口文档</NButton>
        <NButton type="primary" @click="openCreate">创建 API 应用</NButton>
      </div>
    </div>
    <NDataTable :columns="columns" :data="applications" :loading="loading" :row-key="(row: ApiApplication) => row.id" :scroll-x="1260" />

    <NModal v-model:show="createDialog.show" preset="dialog" title="创建 API 应用" positive-text="创建应用" negative-text="取消" :loading="createDialog.loading" :mask-closable="false" @positive-click="submitCreate">
      <div class="form-stack">
        <label><span>应用名称</span><NInput v-model:value="createDialog.name" maxlength="80" placeholder="例如：合同管理系统" /></label>
        <label><span>关联账号</span><NSelect :value="createDialog.userId" :options="userOptions" filterable placeholder="API 将访问该账号的全部文件" @update:value="selectUser" /></label>
        <div class="permission-list">
          <span>接口权限</span>
          <label v-for="item in permissionItems" :key="item.key">
            <NSwitch v-model:value="createDialog[item.key]" />
            <strong>{{ item.label }}</strong>
            <small>{{ item.hint }}</small>
          </label>
        </div>
      </div>
    </NModal>

    <NModal v-model:show="permissionDialog.show" preset="dialog" title="调整 API 权限" positive-text="保存权限" negative-text="取消" :loading="permissionDialog.loading" :mask-closable="false" @positive-click="submitPermissions">
      <div class="form-stack">
        <p class="permission-note">权限变更会立即影响现有 API Key，不需要重新轮换密钥。</p>
        <div class="permission-list">
          <span>接口权限</span>
          <label v-for="item in permissionItems" :key="item.key">
            <NSwitch v-model:value="permissionDialog[item.key]" />
            <strong>{{ item.label }}</strong>
            <small>{{ item.hint }}</small>
          </label>
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

.integration-panel { overflow: hidden; border: 1px solid $border; border-radius: $radius-md; background: $surface; }
.panel-head { min-height: 64px; display: flex; align-items: center; justify-content: space-between; gap: 20px; padding: 12px 16px; border-bottom: 1px solid $border; }
.panel-head h2 { margin: 0; font-size: 16px; }
.panel-head span { color: $text-muted; font-size: 12px; }
.panel-actions { display: flex; gap: 8px; }
:deep(.stack-cell) { display: grid; }
:deep(.stack-cell small) { color: $text-muted; }
:deep(.permission-tags) { display: flex; flex-wrap: wrap; gap: 4px; }
.form-stack, .secret-box { display: grid; gap: 14px; padding-top: 6px; }
.form-stack > label { display: grid; gap: 6px; color: $text-secondary; font-size: 13px; }
.permission-list { display: grid; gap: 10px; padding-top: 4px; }
.permission-list > span { color: $text-secondary; font-size: 13px; }
.permission-list label { display: grid; grid-template-columns: auto minmax(110px, max-content) 1fr; align-items: center; gap: 8px; color: $text-secondary; font-size: 12px; }
.permission-list strong { color: $text; font-weight: 600; }
.permission-list small { color: $text-muted; }
.permission-note { margin: 0; padding: 10px 12px; border-radius: $radius-md; color: $text-secondary; background: $background; font-size: 12px; }
.secret-box p { margin: 0; padding: 10px 12px; color: $warning; background: #fff7ea; border-radius: $radius-md; }
.secret-box small { color: $text-muted; }

@media (max-width: 700px) {
  .panel-head { align-items: stretch; flex-direction: column; }
  .panel-actions { justify-content: flex-end; }
  .permission-list label { grid-template-columns: auto 1fr; }
  .permission-list small { grid-column: 2; }
}
</style>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ChevronDown,
  ChevronRight,
  Download,
  FolderPlus,
  LayoutGrid,
  List,
  DotsVertical,
  Refresh,
  Search,
  Upload,
} from '@vicons/tabler'
import {
  NButton,
  NCheckbox,
  NDropdown,
  NInput,
  NModal,
  NPagination,
  NProgress,
  NSelect,
  NSkeleton,
  useDialog,
  useMessage,
} from 'naive-ui'
import AppIcon from '@/components/base/AppIcon.vue'
import FileTypeIcon from '@/components/base/FileTypeIcon.vue'
import {
  copyNode,
  createFolder,
  deleteNode,
  fetchPrivateBlob,
  getFolders,
  getNodes,
  moveNode,
  renameNode,
  uploadFile,
} from '@/api/modules/nodes'
import { createShare } from '@/api/modules/shares'
import type { DriveNode, NodeListResponse } from '@/types'

interface UploadTask {
  id: string
  name: string
  progress: number
  status: 'uploading' | 'success' | 'error'
  error?: string
}

const route = useRoute()
const router = useRouter()
const message = useMessage()
const dialog = useDialog()
const fileInput = ref<HTMLInputElement | null>(null)
const data = ref<NodeListResponse | null>(null)
const loading = ref(true)
const loadError = ref('')
const search = ref('')
const sortBy = ref<'name' | 'size' | 'updated_at'>('updated_at')
const sortOrder = ref<'asc' | 'desc'>('desc')
const viewMode = ref<'list' | 'grid'>('list')
const uploadTasks = ref<UploadTask[]>([])
const selectedIds = ref<Set<string>>(new Set())

const folderDialog = reactive({ show: false, name: '', loading: false })
const renameDialog = reactive({ show: false, node: null as DriveNode | null, name: '', loading: false })
const targetDialog = reactive({
  show: false,
  nodes: [] as DriveNode[],
  mode: 'move' as 'move' | 'copy',
  targetId: undefined as string | undefined,
  folders: [] as DriveNode[],
  loading: false,
})
const shareDialog = reactive({
  show: false,
  node: null as DriveNode | null,
  days: 7,
  link: '',
  loading: false,
})
const previewDialog = reactive({
  show: false,
  node: null as DriveNode | null,
  url: '',
  loading: false,
  error: '',
})

const currentFolderId = computed(() =>
  typeof route.query.folder === 'string' ? route.query.folder : undefined,
)
const currentPage = computed(() => Number(route.query.page) || 1)
const totalPages = computed(() => Math.max(1, Math.ceil((data.value?.total || 0) / 50)))
const selectedNodes = computed(() =>
  (data.value?.items || []).filter((node) => selectedIds.value.has(node.id)),
)
const allSelected = computed(
  () => Boolean(data.value?.items.length) && selectedIds.value.size === data.value?.items.length,
)
const partlySelected = computed(() => selectedIds.value.size > 0 && !allSelected.value)

const formatSize = (bytes: number) => {
  if (!bytes) return '—'
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
  new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))

const errorText = (error: unknown) =>
  (error as { userMessage?: string }).userMessage || '操作失败，请重试'

async function loadNodes() {
  selectedIds.value = new Set()
  loading.value = true
  loadError.value = ''
  try {
    data.value = await getNodes({
      parent_id: currentFolderId.value,
      search: search.value || undefined,
      sort_by: sortBy.value,
      sort_order: sortOrder.value,
      page: currentPage.value,
      page_size: 50,
    })
  } catch (error) {
    loadError.value = errorText(error)
  } finally {
    loading.value = false
  }
}

function toggleSelection(nodeId: string, checked: boolean) {
  const next = new Set(selectedIds.value)
  if (checked) next.add(nodeId)
  else next.delete(nodeId)
  selectedIds.value = next
}

function toggleAll(checked: boolean) {
  selectedIds.value = checked ? new Set((data.value?.items || []).map((node) => node.id)) : new Set()
}

function openFolder(node: DriveNode) {
  void router.push({ name: 'files', query: { folder: node.id } })
}

function goBreadcrumb(id: string, index: number) {
  if (index === 0) void router.push({ name: 'files' })
  else void router.push({ name: 'files', query: { folder: id } })
}

async function submitFolder() {
  if (!folderDialog.name.trim()) return
  folderDialog.loading = true
  try {
    await createFolder(currentFolderId.value, folderDialog.name)
    folderDialog.show = false
    folderDialog.name = ''
    message.success('文件夹已创建')
    await loadNodes()
  } catch (error) {
    message.error(errorText(error))
  } finally {
    folderDialog.loading = false
  }
}

async function onFileSelected(event: Event) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files || [])
  input.value = ''
  for (const file of files) {
    const task = reactive<UploadTask>({
      id: `${Date.now()}-${Math.random()}`,
      name: file.name,
      progress: 0,
      status: 'uploading',
    })
    uploadTasks.value.unshift(task)
    try {
      await uploadFile(currentFolderId.value, file, (value) => (task.progress = value))
      task.progress = 100
      task.status = 'success'
      window.dispatchEvent(new Event('pan:storage-changed'))
    } catch (error) {
      task.status = 'error'
      task.error = errorText(error)
    }
  }
  await loadNodes()
}

function openRename(node: DriveNode) {
  renameDialog.node = node
  renameDialog.name = node.name
  renameDialog.show = true
}

async function submitRename() {
  if (!renameDialog.node || !renameDialog.name.trim()) return
  renameDialog.loading = true
  try {
    await renameNode(renameDialog.node.id, renameDialog.name)
    renameDialog.show = false
    message.success('名称已更新')
    await loadNodes()
  } catch (error) {
    message.error(errorText(error))
  } finally {
    renameDialog.loading = false
  }
}

async function openTarget(node: DriveNode, mode: 'move' | 'copy') {
  await openTargets([node], mode)
}

async function openTargets(nodes: DriveNode[], mode: 'move' | 'copy') {
  if (!nodes.length) return
  targetDialog.nodes = nodes
  targetDialog.mode = mode
  targetDialog.targetId = undefined
  targetDialog.show = true
  try {
    targetDialog.folders = await getFolders()
  } catch (error) {
    message.error(errorText(error))
  }
}

async function submitTarget() {
  if (!targetDialog.nodes.length) return
  targetDialog.loading = true
  const results = []
  for (const node of targetDialog.nodes) {
    try {
      if (targetDialog.mode === 'move') await moveNode(node.id, targetDialog.targetId)
      else await copyNode(node.id, targetDialog.targetId)
      results.push(true)
    } catch {
      results.push(false)
    }
  }
  try {
    const succeeded = results.filter(Boolean).length
    const failed = results.length - succeeded
    if (targetDialog.mode === 'copy' && succeeded) window.dispatchEvent(new Event('pan:storage-changed'))
    targetDialog.show = false
    if (failed) message.warning(`已${targetDialog.mode === 'move' ? '移动' : '复制'} ${succeeded} 项，${failed} 项失败`)
    else message.success(`已${targetDialog.mode === 'move' ? '移动' : '复制'} ${succeeded} 项`)
    await loadNodes()
  } finally {
    targetDialog.loading = false
  }
}

function confirmDelete(node: DriveNode) {
  dialog.warning({
    title: '移到回收站？',
    content: `“${node.name}”将移到回收站，并保留 30 天。`,
    positiveText: '移到回收站',
    negativeText: '取消',
    async onPositiveClick() {
      try {
        await deleteNode(node.id)
        message.success('已移到回收站')
        await loadNodes()
      } catch (error) {
        message.error(errorText(error))
      }
    },
  })
}

function confirmBatchDelete() {
  const nodes = selectedNodes.value
  if (!nodes.length) return
  dialog.warning({
    title: `将 ${nodes.length} 项移到回收站？`,
    content: '选中的文件和文件夹将移到回收站，并保留 30 天。',
    positiveText: '移到回收站',
    negativeText: '取消',
    async onPositiveClick() {
      const results = await Promise.allSettled(nodes.map((node) => deleteNode(node.id)))
      const succeeded = results.filter((result) => result.status === 'fulfilled').length
      const failed = results.length - succeeded
      if (failed) message.warning(`已删除 ${succeeded} 项，${failed} 项失败`)
      else message.success(`已将 ${succeeded} 项移到回收站`)
      await loadNodes()
    },
  })
}

async function download(node: DriveNode) {
  try {
    const blob = await fetchPrivateBlob(node.id)
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = node.name
    anchor.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    message.error(errorText(error))
  }
}

async function preview(node: DriveNode) {
  if (node.kind === 'folder') return openFolder(node)
  previewDialog.node = node
  previewDialog.show = true
  previewDialog.loading = true
  previewDialog.error = ''
  if (previewDialog.url) URL.revokeObjectURL(previewDialog.url)
  previewDialog.url = ''
  try {
    const blob = await fetchPrivateBlob(node.id, true)
    previewDialog.url = URL.createObjectURL(blob)
  } catch (error) {
    previewDialog.error = errorText(error)
  } finally {
    previewDialog.loading = false
  }
}

async function openShare(node: DriveNode) {
  shareDialog.node = node
  shareDialog.days = 7
  shareDialog.link = ''
  shareDialog.show = true
}

async function submitShare() {
  if (!shareDialog.node) return
  shareDialog.loading = true
  try {
    const share = await createShare(
      shareDialog.node.id,
      shareDialog.days === 0 ? null : shareDialog.days,
    )
    shareDialog.link = `${window.location.origin}/s/${share.token}`
  } catch (error) {
    message.error(errorText(error))
  } finally {
    shareDialog.loading = false
  }
}

async function copyShareLink() {
  await navigator.clipboard.writeText(shareDialog.link)
  message.success('分享链接已复制')
}

function actionOptions(node: DriveNode) {
  const options: Array<{ label: string; key: string; divider?: boolean }> = []
  if (node.kind === 'file') options.push({ label: '预览', key: 'preview' }, { label: '下载', key: 'download' })
  options.push(
    { label: '分享', key: 'share' },
    { label: '重命名', key: 'rename' },
    { label: '移动到…', key: 'move' },
    { label: '复制到…', key: 'copy' },
    { label: '移到回收站', key: 'delete' },
  )
  return options
}

function handleAction(key: string, node: DriveNode) {
  const actions: Record<string, () => void> = {
    preview: () => void preview(node),
    download: () => void download(node),
    share: () => void openShare(node),
    rename: () => openRename(node),
    move: () => void openTarget(node, 'move'),
    copy: () => void openTarget(node, 'copy'),
    delete: () => confirmDelete(node),
  }
  actions[key]?.()
}

function previewKind(node: DriveNode | null) {
  const type = node?.content_type || ''
  if (type.startsWith('image/')) return 'image'
  if (type.startsWith('video/')) return 'video'
  if (type.startsWith('audio/')) return 'audio'
  if (type === 'application/pdf' || type.startsWith('text/')) return 'frame'
  return 'unsupported'
}

function changePage(page: number) {
  void router.push({ name: 'files', query: { ...route.query, page: page === 1 ? undefined : String(page) } })
}

function submitSearch() {
  if (currentPage.value !== 1) changePage(1)
  else void loadNodes()
}

watch([currentFolderId, currentPage, sortBy, sortOrder], () => void loadNodes())
onMounted(() => void loadNodes())
onBeforeUnmount(() => {
  if (previewDialog.url) URL.revokeObjectURL(previewDialog.url)
})

void nextTick()
</script>

<template>
  <section class="page-shell files-page">
    <header class="page-header">
      <div>
        <h1 class="page-title">我的文件</h1>
        <p class="page-subtitle">整理、预览并分享你的个人资料</p>
      </div>
      <div class="primary-actions">
        <NButton @click="folderDialog.show = true">
          <template #icon><AppIcon :icon="FolderPlus" /></template>新建文件夹
        </NButton>
        <NButton type="primary" @click="fileInput?.click()">
          <template #icon><AppIcon :icon="Upload" /></template>上传文件
        </NButton>
        <input ref="fileInput" class="file-input" type="file" multiple @change="onFileSelected" />
      </div>
    </header>

    <div class="breadcrumbs" aria-label="文件路径">
      <template v-for="(item, index) in data?.breadcrumbs || []" :key="item.id">
        <AppIcon v-if="index > 0" :icon="ChevronRight" :size="15" />
        <button type="button" :disabled="index === (data?.breadcrumbs.length || 0) - 1" @click="goBreadcrumb(item.id, index)">
          {{ index === 0 ? '我的文件' : item.name }}
        </button>
      </template>
    </div>

    <div class="toolbar">
      <NInput v-model:value="search" clearable placeholder="搜索当前文件夹" class="search-input" @keyup.enter="submitSearch" @clear="submitSearch">
        <template #prefix><AppIcon :icon="Search" :size="17" /></template>
      </NInput>
      <div class="toolbar-actions">
        <NDropdown
          trigger="click"
          :options="[
            { label: '按名称', key: 'name' },
            { label: '按大小', key: 'size' },
            { label: '按更新时间', key: 'updated_at' },
          ]"
          @select="(key) => (sortBy = key)"
        >
          <NButton secondary>排序 <template #icon><AppIcon :icon="ChevronDown" :size="16" /></template></NButton>
        </NDropdown>
        <NButton quaternary circle :aria-label="sortOrder === 'asc' ? '切换为降序' : '切换为升序'" @click="sortOrder = sortOrder === 'asc' ? 'desc' : 'asc'">
          {{ sortOrder === 'asc' ? '↑' : '↓' }}
        </NButton>
        <div class="view-toggle" aria-label="视图切换">
          <button type="button" :class="{ active: viewMode === 'list' }" aria-label="列表视图" @click="viewMode = 'list'">
            <AppIcon :icon="List" :size="18" />
          </button>
          <button type="button" :class="{ active: viewMode === 'grid' }" aria-label="网格视图" @click="viewMode = 'grid'">
            <AppIcon :icon="LayoutGrid" :size="18" />
          </button>
        </div>
      </div>
    </div>

    <div v-if="selectedNodes.length" class="batch-bar">
      <div><strong>已选择 {{ selectedNodes.length }} 项</strong><NButton text size="small" @click="selectedIds = new Set()">取消选择</NButton></div>
      <div>
        <NButton size="small" @click="openTargets(selectedNodes, 'move')">移动到…</NButton>
        <NButton size="small" @click="openTargets(selectedNodes, 'copy')">复制到…</NButton>
        <NButton size="small" type="error" secondary @click="confirmBatchDelete">移到回收站</NButton>
      </div>
    </div>

    <div class="panel file-panel">
      <div v-if="loading" class="loading-list">
        <div v-for="index in 6" :key="index" class="skeleton-row">
          <NSkeleton circle size="small" /><NSkeleton text style="width: 32%" /><NSkeleton text style="width: 12%" /><NSkeleton text style="width: 16%" />
        </div>
      </div>
      <div v-else-if="loadError" class="state-view">
        <div><AppIcon :icon="Refresh" :size="30" /><h3>文件暂时没有加载出来</h3><p>{{ loadError }}</p><NButton @click="loadNodes">重新加载</NButton></div>
      </div>
      <div v-else-if="!data?.items.length" class="state-view">
        <div><AppIcon :icon="Upload" :size="32" /><h3>{{ search ? '没有找到匹配内容' : '这个文件夹还是空的' }}</h3><p>{{ search ? '换个关键词，或清空搜索条件。' : '上传文件或新建文件夹，开始整理资料。' }}</p><NButton v-if="!search" type="primary" @click="fileInput?.click()">上传文件</NButton><NButton v-else @click="search = ''; loadNodes()">清空搜索</NButton></div>
      </div>
      <template v-else-if="viewMode === 'list'">
        <div class="file-row file-row--head"><NCheckbox :checked="allSelected" :indeterminate="partlySelected" aria-label="选择当前页全部内容" @update:checked="toggleAll" /><span>名称</span><span>大小</span><span>更新时间</span><span></span></div>
        <div v-for="node in data.items" :key="node.id" class="file-row" :class="{ 'file-row--selected': selectedIds.has(node.id) }" @dblclick="preview(node)">
          <NCheckbox :checked="selectedIds.has(node.id)" :aria-label="`选择 ${node.name}`" @click.stop @update:checked="(checked) => toggleSelection(node.id, checked)" />
          <button class="file-name" type="button" @click="preview(node)"><FileTypeIcon :node="node" /><span><strong>{{ node.name }}</strong><small>{{ node.kind === 'folder' ? '文件夹' : node.content_type || '文件' }}</small></span></button>
          <span class="file-meta">{{ node.kind === 'folder' ? '—' : formatSize(node.size_bytes) }}</span>
          <span class="file-meta">{{ formatDate(node.updated_at) }}</span>
          <NDropdown trigger="click" :options="actionOptions(node)" @select="(key) => handleAction(key, node)">
            <NButton quaternary circle aria-label="更多操作"><template #icon><AppIcon :icon="DotsVertical" :size="18" /></template></NButton>
          </NDropdown>
        </div>
      </template>
      <div v-else class="file-grid">
        <article v-for="node in data.items" :key="node.id" class="file-card" :class="{ 'file-card--selected': selectedIds.has(node.id) }" @dblclick="preview(node)">
          <div class="file-card-head"><NCheckbox :checked="selectedIds.has(node.id)" :aria-label="`选择 ${node.name}`" @click.stop @update:checked="(checked) => toggleSelection(node.id, checked)" /><FileTypeIcon :node="node" :size="28" /><NDropdown trigger="click" :options="actionOptions(node)" @select="(key) => handleAction(key, node)"><NButton quaternary circle size="small" aria-label="更多操作"><template #icon><AppIcon :icon="DotsVertical" :size="17" /></template></NButton></NDropdown></div>
          <button type="button" @click="preview(node)"><strong>{{ node.name }}</strong><small>{{ node.kind === 'folder' ? '文件夹' : `${formatSize(node.size_bytes)} · ${formatDate(node.updated_at)}` }}</small></button>
        </article>
      </div>
    </div>

    <div v-if="totalPages > 1" class="pagination-row">
      <span>共 {{ data?.total }} 项</span>
      <NPagination :page="currentPage" :page-count="totalPages" @update:page="changePage" />
    </div>

    <aside v-if="uploadTasks.length" class="upload-tray">
      <div class="upload-tray-head"><strong>上传任务</strong><button type="button" @click="uploadTasks = uploadTasks.filter((item) => item.status === 'uploading')">清除已完成</button></div>
      <div v-for="task in uploadTasks.slice(0, 4)" :key="task.id" class="upload-task"><div><span>{{ task.name }}</span><small :class="`status-${task.status}`">{{ task.status === 'uploading' ? `${task.progress}%` : task.status === 'success' ? '已完成' : task.error }}</small></div><NProgress type="line" :percentage="task.progress" :status="task.status === 'error' ? 'error' : task.status === 'success' ? 'success' : 'default'" :show-indicator="false" :height="4" /></div>
    </aside>

    <NModal v-model:show="folderDialog.show" preset="dialog" title="新建文件夹" positive-text="创建" negative-text="取消" :loading="folderDialog.loading" @positive-click="submitFolder">
      <NInput v-model:value="folderDialog.name" autofocus placeholder="文件夹名称" maxlength="255" @keyup.enter="submitFolder" />
    </NModal>
    <NModal v-model:show="renameDialog.show" preset="dialog" title="重命名" positive-text="保存" negative-text="取消" :loading="renameDialog.loading" @positive-click="submitRename">
      <NInput v-model:value="renameDialog.name" autofocus maxlength="255" @keyup.enter="submitRename" />
    </NModal>
    <NModal v-model:show="targetDialog.show" preset="dialog" :title="`${targetDialog.mode === 'move' ? '移动' : '复制'} ${targetDialog.nodes.length} 项到`" :positive-text="targetDialog.mode === 'move' ? '移动' : '复制'" negative-text="取消" :loading="targetDialog.loading" @positive-click="submitTarget">
      <p class="dialog-tip">选择目标文件夹；不选择时使用根目录。</p>
      <NSelect v-model:value="targetDialog.targetId" clearable filterable placeholder="我的文件（根目录）" :options="targetDialog.folders.filter((item) => !targetDialog.nodes.some((node) => node.id === item.id)).map((item) => ({ label: item.is_root ? '我的文件（根目录）' : item.name, value: item.id }))" />
    </NModal>
    <NModal v-model:show="shareDialog.show" preset="dialog" title="创建只读分享" :positive-text="shareDialog.link ? undefined : '创建分享'" negative-text="关闭" :loading="shareDialog.loading" @positive-click="shareDialog.link ? undefined : submitShare()">
      <template v-if="!shareDialog.link"><p class="dialog-tip">持有链接的人可以预览和下载“{{ shareDialog.node?.name }}”。</p><NSelect v-model:value="shareDialog.days" :options="[{ label: '1 天', value: 1 }, { label: '7 天', value: 7 }, { label: '30 天', value: 30 }, { label: '永久有效', value: 0 }]" /></template>
      <template v-else><p class="dialog-tip">{{ shareDialog.days === 0 ? '永久分享已创建，手动取消前链接会一直有效。' : `分享已创建，链接将在 ${shareDialog.days} 天后失效。` }}</p><NInput :value="shareDialog.link" readonly><template #suffix><NButton text type="primary" @click="copyShareLink">复制</NButton></template></NInput></template>
    </NModal>
    <NModal v-model:show="previewDialog.show" class="preview-modal" preset="card" :title="previewDialog.node?.name" style="width: min(960px, calc(100vw - 32px))">
      <div class="preview-body">
        <NSkeleton v-if="previewDialog.loading" text :repeat="6" />
        <div v-else-if="previewDialog.error" class="state-view"><div><h3>无法预览</h3><p>{{ previewDialog.error }}</p><NButton v-if="previewDialog.node" @click="download(previewDialog.node)"><template #icon><AppIcon :icon="Download" /></template>下载文件</NButton></div></div>
        <img v-else-if="previewKind(previewDialog.node) === 'image'" :src="previewDialog.url" :alt="previewDialog.node?.name" />
        <video v-else-if="previewKind(previewDialog.node) === 'video'" :src="previewDialog.url" controls />
        <audio v-else-if="previewKind(previewDialog.node) === 'audio'" :src="previewDialog.url" controls />
        <iframe v-else-if="previewKind(previewDialog.node) === 'frame'" :src="previewDialog.url" :title="previewDialog.node?.name" />
        <div v-else class="state-view"><div><h3>此格式暂不支持在线预览</h3><p>你仍然可以下载文件后查看。</p><NButton v-if="previewDialog.node" @click="download(previewDialog.node)"><template #icon><AppIcon :icon="Download" /></template>下载文件</NButton></div></div>
      </div>
    </NModal>
  </section>
</template>

<style scoped lang="scss">
@use '@/assets/styles/variables' as *;

.primary-actions, .toolbar, .toolbar-actions, .breadcrumbs { display: flex; align-items: center; }
.primary-actions { gap: 10px; }
.file-input { display: none; }
.breadcrumbs { min-height: 32px; gap: 4px; margin-bottom: 14px; color: $text-muted; overflow-x: auto; }
.breadcrumbs button { flex: 0 0 auto; padding: 4px 6px; border: 0; background: transparent; color: $text-secondary; cursor: pointer; border-radius: 5px; }
.breadcrumbs button:hover:not(:disabled) { background: $primary-soft; color: $primary; }
.breadcrumbs button:disabled { color: $text; cursor: default; }
.toolbar { justify-content: space-between; gap: 16px; margin-bottom: 16px; }
.batch-bar { min-height: 52px; display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 8px 14px; margin: -4px 0 12px; border: 1px solid #b9d8cf; border-radius: $radius-md; background: $primary-soft; }
.batch-bar > div { display: flex; align-items: center; gap: 8px; }
.batch-bar strong { color: $primary; font-size: 13px; }
.search-input { width: min(360px, 100%); }
.toolbar-actions { gap: 6px; flex: 0 0 auto; }
.view-toggle { display: flex; padding: 3px; background: #e9eeeb; border-radius: 9px; }
.view-toggle button { width: 32px; height: 30px; display: grid; place-items: center; padding: 0; border: 0; color: $text-muted; background: transparent; border-radius: 6px; cursor: pointer; }
.view-toggle button.active { color: $text; background: $surface; box-shadow: 0 1px 2px rgba(20, 34, 29, 0.08); }
.file-panel { overflow: hidden; }
.file-row { min-width: 680px; display: grid; grid-template-columns: 36px minmax(260px, 1fr) 120px 160px 48px; align-items: center; min-height: 62px; padding: 0 16px; border-top: 1px solid $border; }
.file-row:not(.file-row--head):hover { background: $surface-muted; }
.file-row--selected { background: $primary-soft; }
.file-row--head { min-height: 44px; border-top: 0; color: $text-muted; background: $surface-muted; font-size: 12px; font-weight: 500; }
.file-name { min-width: 0; display: flex; align-items: center; gap: 10px; padding: 0; border: 0; background: transparent; color: $text; cursor: pointer; text-align: left; }
.file-name > span:last-child { min-width: 0; display: grid; }
.file-name strong, .file-name small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.file-name strong { font-weight: 520; }
.file-name small { color: $text-muted; font-size: 11px; }
.file-meta { color: $text-secondary; font-size: 13px; font-variant-numeric: tabular-nums; }
.loading-list { padding: 0 16px; }
.skeleton-row { height: 62px; display: flex; align-items: center; gap: 22px; border-bottom: 1px solid $border; }
.file-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; padding: 16px; }
.file-card { min-width: 0; padding: 14px; border: 1px solid $border; border-radius: $radius-md; background: $surface; }
.file-card:hover { border-color: #b8c7c1; background: $surface-muted; }
.file-card--selected { border-color: #8dbdaf; background: $primary-soft; }
.file-card-head { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.file-card-head :deep(.n-dropdown-trigger) { margin-left: auto; }
.file-card > button { width: 100%; display: grid; gap: 3px; padding: 0; border: 0; background: transparent; color: $text; text-align: left; cursor: pointer; }
.file-card strong, .file-card small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.file-card strong { font-weight: 520; }
.file-card small { color: $text-muted; font-size: 11px; }
.pagination-row { display: flex; align-items: center; justify-content: flex-end; gap: 16px; margin: 14px 0; color: $text-muted; font-size: 12px; }
.upload-tray { position: fixed; right: 24px; bottom: 24px; z-index: 20; width: min(360px, calc(100vw - 32px)); padding: 14px; border: 1px solid $border; border-radius: $radius-lg; background: $surface; box-shadow: $shadow-md; }
.upload-tray-head { display: flex; justify-content: space-between; margin-bottom: 10px; }
.upload-tray-head button { border: 0; background: transparent; color: $primary; cursor: pointer; font-size: 12px; }
.upload-task { padding: 9px 0; border-top: 1px solid $border; }
.upload-task > div { display: flex; justify-content: space-between; gap: 12px; margin-bottom: 7px; }
.upload-task span { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.upload-task small { flex: 0 0 auto; color: $text-muted; font-size: 11px; }
.upload-task .status-success { color: $success; }
.upload-task .status-error { color: $danger; max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.dialog-tip { margin: 0 0 14px; color: $text-secondary; }
.preview-body { min-height: 420px; display: grid; place-items: center; background: #eef1ef; border-radius: $radius-md; overflow: hidden; }
.preview-body img, .preview-body video { display: block; max-width: 100%; max-height: 70vh; }
.preview-body audio { width: min(560px, 90%); }
.preview-body iframe { width: 100%; height: 70vh; border: 0; background: white; }

@media (max-width: 760px) {
  .primary-actions { width: 100%; }
  .primary-actions :deep(.n-button) { flex: 1; }
  .toolbar { align-items: stretch; flex-direction: column; }
  .search-input { width: 100%; }
  .toolbar-actions { justify-content: flex-end; }
  .file-panel { overflow-x: auto; }
  .batch-bar { align-items: stretch; flex-direction: column; }
  .batch-bar > div:last-child { flex-wrap: wrap; }
  .file-row { grid-template-columns: 36px minmax(250px, 1fr) 110px 48px; }
  .file-row > :nth-child(4) { display: none; }
}

@media (max-width: 520px) {
  .file-row { min-width: 0; grid-template-columns: 36px minmax(0, 1fr) 44px; }
  .file-row > :nth-child(3), .file-row > :nth-child(4) { display: none; }
  .file-row--head > :nth-child(2) { display: block; }
  .toolbar-actions :deep(.n-button) { display: none; }
  .upload-tray { right: 16px; bottom: 16px; }
}
</style>

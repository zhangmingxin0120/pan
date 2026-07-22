<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Refresh, RotateClockwise2, Trash, TrashX } from '@vicons/tabler'
import { NButton, NSkeleton, useDialog, useMessage } from 'naive-ui'
import AppIcon from '@/components/base/AppIcon.vue'
import FileTypeIcon from '@/components/base/FileTypeIcon.vue'
import { emptyTrash, getTrash, permanentlyDeleteNode, restoreNode } from '@/api/modules/nodes'
import type { DriveNode } from '@/types'

const message = useMessage()
const dialog = useDialog()
const items = ref<DriveNode[]>([])
const loading = ref(true)
const error = ref('')
const emptying = ref(false)
const errorText = (value: unknown) => (value as { userMessage?: string }).userMessage || '操作失败，请重试'
const formatDate = (value: string) => new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).format(new Date(value))

async function load() {
  loading.value = true
  error.value = ''
  try { items.value = await getTrash() } catch (value) { error.value = errorText(value) } finally { loading.value = false }
}

async function restore(node: DriveNode) {
  try { await restoreNode(node.id); message.success('已恢复'); await load() } catch (value) { message.error(errorText(value)) }
}

function removeForever(node: DriveNode) {
  dialog.error({
    title: '永久删除？',
    content: `“${node.name}”及其包含的内容将无法恢复，并释放占用空间。`,
    positiveText: '永久删除', negativeText: '取消',
    async onPositiveClick() {
      try { await permanentlyDeleteNode(node.id); window.dispatchEvent(new Event('pan:storage-changed')); message.success('已永久删除'); await load() } catch (value) { message.error(errorText(value)) }
    },
  })
}

function clearTrash() {
  dialog.error({
    title: '清空回收站？',
    content: `回收站中的 ${items.value.length} 项及其包含的所有内容将被永久删除，此操作无法撤销。`,
    positiveText: '确认清空', negativeText: '取消',
    async onPositiveClick() {
      emptying.value = true
      try {
        await emptyTrash()
        items.value = []
        window.dispatchEvent(new Event('pan:storage-changed'))
        message.success('回收站已清空')
      } catch (value) {
        message.error(errorText(value))
      } finally {
        emptying.value = false
      }
    },
  })
}

onMounted(() => void load())
</script>

<template>
  <section class="page-shell">
    <header class="page-header"><div><h1 class="page-title">回收站</h1><p class="page-subtitle">已删除内容保留 30 天，期间仍会占用空间</p></div><NButton v-if="items.length" type="error" secondary :loading="emptying" @click="clearTrash"><template #icon><AppIcon :icon="TrashX" /></template>清空回收站</NButton></header>
    <div class="panel trash-panel">
      <div v-if="loading" class="loading-list"><div v-for="n in 5" :key="n" class="skeleton-row"><NSkeleton circle size="small" /><NSkeleton text style="width: 36%" /><NSkeleton text style="width: 16%" /></div></div>
      <div v-else-if="error" class="state-view"><div><AppIcon :icon="Refresh" :size="30" /><h3>回收站暂时不可用</h3><p>{{ error }}</p><NButton @click="load">重新加载</NButton></div></div>
      <div v-else-if="!items.length" class="state-view"><div><AppIcon :icon="Trash" :size="32" /><h3>回收站是空的</h3><p>从我的文件删除的内容会出现在这里。</p><RouterLink to="/files"><NButton>返回我的文件</NButton></RouterLink></div></div>
      <template v-else>
        <div class="trash-row trash-row--head"><span>名称</span><span>删除时间</span><span>操作</span></div>
        <div v-for="node in items" :key="node.id" class="trash-row">
          <div class="trash-name"><FileTypeIcon :node="node" /><strong>{{ node.name }}</strong></div>
          <span class="trash-date">{{ node.trashed_at ? formatDate(node.trashed_at) : '—' }}</span>
          <div class="row-actions"><NButton secondary size="small" @click="restore(node)"><template #icon><AppIcon :icon="RotateClockwise2" :size="16" /></template>恢复</NButton><NButton quaternary size="small" type="error" @click="removeForever(node)"><template #icon><AppIcon :icon="TrashX" :size="16" /></template>永久删除</NButton></div>
        </div>
      </template>
    </div>
  </section>
</template>

<style scoped lang="scss">
@use '@/assets/styles/variables' as *;
.trash-panel { overflow: hidden; }
.trash-row { display: grid; grid-template-columns: minmax(260px, 1fr) 180px 220px; align-items: center; min-height: 66px; padding: 0 18px; border-top: 1px solid $border; }
.trash-row--head { min-height: 44px; border-top: 0; color: $text-muted; background: $surface-muted; font-size: 12px; }
.trash-name { min-width: 0; display: flex; align-items: center; gap: 10px; }
.trash-name strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 520; }
.trash-date { color: $text-muted; font-size: 12px; }
.row-actions { display: flex; justify-content: flex-end; gap: 6px; }
.loading-list { padding: 0 18px; }
.skeleton-row { height: 66px; display: flex; align-items: center; gap: 24px; border-bottom: 1px solid $border; }
@media (max-width: 660px) { .trash-panel { overflow-x: auto; } .trash-row { min-width: 620px; } }
</style>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ChevronRight, Download, Refresh, Unlink } from '@vicons/tabler'
import { NButton, NModal, NSkeleton } from 'naive-ui'
import AppIcon from '@/components/base/AppIcon.vue'
import FileTypeIcon from '@/components/base/FileTypeIcon.vue'
import { getPublicShare, publicFileUrl } from '@/api/modules/shares'
import type { DriveNode, PublicShare } from '@/types'

const route = useRoute()
const router = useRouter()
const data = ref<PublicShare | null>(null)
const loading = ref(true)
const error = ref('')
const previewNode = ref<DriveNode | null>(null)
const token = computed(() => String(route.params.token))
const folderId = computed(() => (typeof route.query.folder === 'string' ? route.query.folder : undefined))

const formatSize = (bytes: number) => {
  const units = ['B', 'KB', 'MB', 'GB']
  let value = bytes
  let index = 0
  while (value >= 1024 && index < units.length - 1) { value /= 1024; index += 1 }
  return `${value >= 10 || index === 0 ? value.toFixed(0) : value.toFixed(1)} ${units[index]}`
}
const formatDate = (value: string) => new Intl.DateTimeFormat('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date(value))
const errorText = (value: unknown) => (value as { userMessage?: string }).userMessage || '分享暂时无法打开'

async function load() {
  loading.value = true; error.value = ''
  try { data.value = await getPublicShare(token.value, folderId.value) } catch (value) { error.value = errorText(value) } finally { loading.value = false }
}

function openNode(node: DriveNode) {
  if (node.kind === 'folder') void router.push({ name: 'public-share', params: { token: token.value }, query: { folder: node.id } })
  else previewNode.value = node
}

function goBreadcrumb(id: string, index: number) {
  if (index === 0) void router.push({ name: 'public-share', params: { token: token.value } })
  else void router.push({ name: 'public-share', params: { token: token.value }, query: { folder: id } })
}

function previewKind(node: DriveNode | null) {
  const type = node?.content_type || ''
  if (type.startsWith('image/')) return 'image'
  if (type.startsWith('video/')) return 'video'
  if (type.startsWith('audio/')) return 'audio'
  if (type === 'application/pdf' || type.startsWith('text/')) return 'frame'
  return 'unsupported'
}

watch(folderId, () => void load())
onMounted(() => void load())
</script>

<template>
  <main class="public-page">
    <header class="public-header"><div class="brand"><span class="brand-mark">P</span><span>Pan</span></div><RouterLink to="/login"><NButton text>打开我的云盘</NButton></RouterLink></header>
    <section v-if="loading" class="public-content"><NSkeleton text :repeat="7" /></section>
    <section v-else-if="error" class="public-content state-view"><div><AppIcon :icon="Unlink" :size="34" /><h3>分享不可用</h3><p>{{ error }}</p><NButton @click="load"><template #icon><AppIcon :icon="Refresh" /></template>重新加载</NButton></div></section>
    <section v-else-if="data" class="public-content">
      <div class="share-heading"><div><span class="eyebrow">{{ data.owner_name }} 分享给你</span><h1>{{ data.root.name }}</h1><p>只读分享 · 有效期至 {{ formatDate(data.expires_at) }}</p></div><a v-if="data.root.kind === 'file'" :href="publicFileUrl(token, data.root.id)" download><NButton type="primary"><template #icon><AppIcon :icon="Download" /></template>下载文件</NButton></a></div>
      <div v-if="data.root.kind === 'folder'" class="share-panel">
        <div class="breadcrumbs"><template v-for="(item, index) in data.breadcrumbs" :key="item.id"><AppIcon v-if="index > 0" :icon="ChevronRight" :size="15" /><button type="button" :disabled="index === data.breadcrumbs.length - 1" @click="goBreadcrumb(item.id, index)">{{ item.name }}</button></template></div>
        <div v-if="!data.items.length" class="state-view"><div><h3>这个文件夹是空的</h3><p>分享者还没有在这里放入内容。</p></div></div>
        <template v-else><div class="public-row public-row--head"><span>名称</span><span>大小</span><span></span></div><div v-for="node in data.items" :key="node.id" class="public-row"><button type="button" @click="openNode(node)"><FileTypeIcon :node="node" /><strong>{{ node.name }}</strong></button><span>{{ node.kind === 'folder' ? '—' : formatSize(node.size_bytes) }}</span><a v-if="node.kind === 'file'" :href="publicFileUrl(token, node.id)" download aria-label="下载文件"><NButton quaternary circle><template #icon><AppIcon :icon="Download" /></template></NButton></a></div></template>
      </div>
      <div v-else class="single-file"><FileTypeIcon :node="data.root" :size="34" /><div><strong>{{ data.root.name }}</strong><span>{{ formatSize(data.root.size_bytes) }}</span></div><NButton @click="previewNode = data.root">在线预览</NButton></div>
    </section>
    <footer>由 Pan 提供安全的只读分享</footer>

    <NModal :show="Boolean(previewNode)" preset="card" :title="previewNode?.name" style="width: min(960px, calc(100vw - 32px))" @update:show="(show) => { if (!show) previewNode = null }">
      <div class="preview-body">
        <img v-if="previewKind(previewNode) === 'image'" :src="publicFileUrl(token, previewNode!.id, true)" :alt="previewNode?.name" />
        <video v-else-if="previewKind(previewNode) === 'video'" :src="publicFileUrl(token, previewNode!.id, true)" controls />
        <audio v-else-if="previewKind(previewNode) === 'audio'" :src="publicFileUrl(token, previewNode!.id, true)" controls />
        <iframe v-else-if="previewKind(previewNode) === 'frame'" :src="publicFileUrl(token, previewNode!.id, true)" :title="previewNode?.name" />
        <div v-else class="state-view"><div><h3>此格式暂不支持在线预览</h3><p>你仍然可以下载文件后查看。</p><a :href="publicFileUrl(token, previewNode!.id)" download><NButton type="primary">下载文件</NButton></a></div></div>
      </div>
    </NModal>
  </main>
</template>

<style scoped lang="scss">
@use '@/assets/styles/variables' as *;
.public-page { min-height: 100vh; display: flex; flex-direction: column; background: $background; }
.public-header { height: 68px; display: flex; align-items: center; justify-content: space-between; padding: 0 max(24px, calc((100vw - 1120px) / 2)); background: $surface; border-bottom: 1px solid $border; }
.brand { display: flex; align-items: center; gap: 9px; font-size: 19px; font-weight: 650; }
.brand-mark { width: 29px; height: 29px; display: grid; place-items: center; border-radius: 9px; color: white; background: $primary; }
.public-content { width: min(1120px, calc(100% - 32px)); margin: 56px auto; flex: 1; }
.share-heading { display: flex; justify-content: space-between; align-items: flex-end; gap: 24px; margin-bottom: 24px; }
.eyebrow { color: $primary; font-size: 13px; font-weight: 550; }
.share-heading h1 { margin: 7px 0 4px; font-size: 28px; line-height: 1.3; font-weight: 600; }
.share-heading p { margin: 0; color: $text-muted; }
.share-panel, .single-file { background: $surface; border: 1px solid $border; border-radius: $radius-lg; overflow: hidden; }
.breadcrumbs { min-height: 48px; display: flex; align-items: center; gap: 4px; padding: 0 18px; border-bottom: 1px solid $border; color: $text-muted; }
.breadcrumbs button { padding: 4px 6px; border: 0; background: transparent; color: $text-secondary; cursor: pointer; }
.breadcrumbs button:disabled { color: $text; cursor: default; }
.public-row { display: grid; grid-template-columns: minmax(240px, 1fr) 120px 44px; align-items: center; min-height: 62px; padding: 0 16px; border-top: 1px solid $border; }
.public-row--head { min-height: 42px; border-top: 0; color: $text-muted; background: $surface-muted; font-size: 12px; }
.public-row > button { min-width: 0; display: flex; align-items: center; gap: 10px; padding: 0; border: 0; background: transparent; cursor: pointer; }
.public-row strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 520; }
.public-row > span { color: $text-muted; font-size: 12px; }
.single-file { display: flex; align-items: center; gap: 14px; padding: 24px; }
.single-file > div { flex: 1; display: grid; }
.single-file strong { font-size: 16px; }
.single-file span { color: $text-muted; }
.preview-body { min-height: 420px; display: grid; place-items: center; background: #eef1ef; border-radius: $radius-md; overflow: hidden; }
.preview-body img, .preview-body video { max-width: 100%; max-height: 70vh; }
.preview-body audio { width: min(560px, 90%); }
.preview-body iframe { width: 100%; height: 70vh; border: 0; background: white; }
footer { padding: 24px; color: $text-muted; font-size: 12px; text-align: center; }
@media (max-width: 640px) { .public-header { padding: 0 16px; } .public-content { margin: 32px auto; } .share-heading { align-items: stretch; flex-direction: column; } .share-heading :deep(.n-button) { width: 100%; } .public-row { grid-template-columns: minmax(0, 1fr) 44px; } .public-row > :nth-child(2) { display: none; } .single-file { flex-wrap: wrap; } .single-file :deep(.n-button) { width: 100%; } }
</style>

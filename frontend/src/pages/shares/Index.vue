<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Copy, ExternalLink, Link, Refresh, Trash, Unlink } from '@vicons/tabler'
import { NButton, NSkeleton, NTag, useDialog, useMessage } from 'naive-ui'
import AppIcon from '@/components/base/AppIcon.vue'
import FileTypeIcon from '@/components/base/FileTypeIcon.vue'
import { deleteShareRecord, getShares, revokeShare } from '@/api/modules/shares'
import type { Share } from '@/types'

const message = useMessage()
const dialog = useDialog()
const shares = ref<Share[]>([])
const loading = ref(true)
const error = ref('')

const formatDate = (value: string) =>
  new Intl.DateTimeFormat('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' }).format(
    new Date(value),
  )

const errorText = (value: unknown) =>
  (value as { userMessage?: string }).userMessage || '操作失败，请重试'

async function load() {
  loading.value = true
  error.value = ''
  try {
    shares.value = (await getShares()).items
  } catch (value) {
    error.value = errorText(value)
  } finally {
    loading.value = false
  }
}

const linkFor = (share: Share) => `${window.location.origin}/s/${share.token}`

async function copyLink(share: Share) {
  await navigator.clipboard.writeText(linkFor(share))
  message.success('分享链接已复制')
}

function revoke(share: Share) {
  dialog.warning({
    title: '取消分享？',
    content: `取消后，“${share.node.name}”的链接将立即失效。`,
    positiveText: '取消分享',
    negativeText: '保留分享',
    async onPositiveClick() {
      try {
        await revokeShare(share.id)
        message.success('分享已取消')
        await load()
      } catch (value) {
        message.error(errorText(value))
      }
    },
  })
}

function removeRecord(share: Share) {
  dialog.warning({
    title: '删除分享记录？',
    content: `将永久删除“${share.node.name}”的这条分享记录，但不会删除网盘中的原文件。`,
    positiveText: '删除记录',
    negativeText: '取消',
    async onPositiveClick() {
      try {
        await deleteShareRecord(share.id)
        shares.value = shares.value.filter((item) => item.id !== share.id)
        message.success('分享记录已删除')
      } catch (value) {
        message.error(errorText(value))
      }
    },
  })
}

onMounted(() => void load())
</script>

<template>
  <section class="page-shell">
    <header class="page-header">
      <div><h1 class="page-title">我的分享</h1><p class="page-subtitle">查看有效期、复制链接或随时停止访问</p></div>
    </header>
    <div class="panel share-panel">
      <div v-if="loading" class="loading-list"><div v-for="n in 5" :key="n" class="skeleton-row"><NSkeleton circle size="small" /><NSkeleton text style="width: 36%" /><NSkeleton text style="width: 16%" /></div></div>
      <div v-else-if="error" class="state-view"><div><AppIcon :icon="Refresh" :size="30" /><h3>分享列表暂时不可用</h3><p>{{ error }}</p><NButton @click="load">重新加载</NButton></div></div>
      <div v-else-if="!shares.length" class="state-view"><div><AppIcon :icon="Link" :size="32" /><h3>还没有分享</h3><p>在“我的文件”中选择文件或文件夹，即可创建只读链接。</p><RouterLink to="/files"><NButton type="primary">前往我的文件</NButton></RouterLink></div></div>
      <template v-else>
        <div class="share-row share-row--head"><span>分享内容</span><span>有效期</span><span>状态</span><span></span></div>
        <div v-for="share in shares" :key="share.id" class="share-row">
          <div class="share-name"><FileTypeIcon :node="share.node" /><span><strong>{{ share.node.name }}</strong><small>创建于 {{ formatDate(share.created_at) }}</small></span></div>
          <span class="share-date">{{ share.expires_at ? `至 ${formatDate(share.expires_at)}` : '永久有效' }}</span>
          <NTag :type="share.is_active ? 'success' : 'default'" size="small" round>{{ share.is_active ? '有效' : '已失效' }}</NTag>
          <div class="row-actions">
            <NButton v-if="share.is_active" quaternary circle aria-label="复制分享链接" @click="copyLink(share)"><template #icon><AppIcon :icon="Copy" /></template></NButton>
            <a v-if="share.is_active" :href="linkFor(share)" target="_blank" rel="noopener"><NButton quaternary circle aria-label="打开分享链接"><template #icon><AppIcon :icon="ExternalLink" /></template></NButton></a>
            <NButton v-if="share.is_active" quaternary circle aria-label="取消分享" title="取消分享" @click="revoke(share)"><template #icon><AppIcon :icon="Unlink" /></template></NButton>
            <NButton v-else quaternary circle aria-label="删除分享记录" title="删除分享记录" @click="removeRecord(share)"><template #icon><AppIcon :icon="Trash" /></template></NButton>
          </div>
        </div>
      </template>
    </div>
  </section>
</template>

<style scoped lang="scss">
@use '@/assets/styles/variables' as *;
.share-panel { overflow: hidden; }
.share-row { display: grid; grid-template-columns: minmax(260px, 1fr) 170px 90px 132px; align-items: center; min-height: 66px; padding: 0 18px; border-top: 1px solid $border; }
.share-row--head { min-height: 44px; border-top: 0; color: $text-muted; background: $surface-muted; font-size: 12px; }
.share-name { min-width: 0; display: flex; align-items: center; gap: 10px; }
.share-name > span { min-width: 0; display: grid; }
.share-name strong, .share-name small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.share-name strong { font-weight: 520; }
.share-name small, .share-date { color: $text-muted; font-size: 12px; }
.row-actions { display: flex; justify-content: flex-end; }
.loading-list { padding: 0 18px; }
.skeleton-row { height: 66px; display: flex; align-items: center; gap: 24px; border-bottom: 1px solid $border; }
@media (max-width: 720px) { .share-panel { overflow-x: auto; } .share-row { min-width: 650px; } }
</style>

<script setup lang="ts">
import { computed } from 'vue'
import {
  File,
  FileMusic,
  FileText,
  Folder,
  Photo,
  Video,
} from '@vicons/tabler'
import AppIcon from './AppIcon.vue'
import type { DriveNode } from '@/types'

const props = defineProps<{ node: DriveNode; size?: number }>()
const icon = computed(() => {
  if (props.node.kind === 'folder') return Folder
  const type = props.node.content_type || ''
  if (type.startsWith('image/')) return Photo
  if (type.startsWith('audio/')) return FileMusic
  if (type.startsWith('video/')) return Video
  if (type === 'application/pdf') return FileText
  if (type.startsWith('text/')) return FileText
  return File
})
</script>

<template>
  <span class="file-icon" :class="`file-icon--${node.kind}`">
    <AppIcon :icon="icon" :size="size || 22" />
  </span>
</template>

<style scoped lang="scss">
@use '@/assets/styles/variables' as *;

.file-icon {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  color: $text-secondary;
  flex: 0 0 auto;
}

.file-icon--folder {
  color: #b87a25;
}
</style>

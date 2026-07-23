<script setup lang="ts">
import { computed } from 'vue'
import {
  Database,
  File,
  FileCode,
  FileMusic,
  FileText,
  FileZip,
  Folder,
  Photo,
  Presentation,
  Table,
  Video,
} from '@vicons/tabler'
import AppIcon from './AppIcon.vue'
import type { DriveNode } from '@/types'

const props = defineProps<{ node: DriveNode; size?: number }>()
const extension = computed(() => props.node.name.split('.').pop()?.toLowerCase() || '')
const category = computed(() => {
  if (props.node.kind === 'folder') return 'folder'
  const type = (props.node.content_type || '').toLowerCase()
  const ext = extension.value
  if (type.startsWith('image/')) return 'image'
  if (type.startsWith('audio/')) return 'audio'
  if (type.startsWith('video/')) return 'video'
  if (type === 'application/pdf' || ext === 'pdf') return 'pdf'
  if (
    type.includes('zip') ||
    type.includes('compressed') ||
    ['zip', 'rar', '7z', 'tar', 'gz', 'bz2', 'xz'].includes(ext)
  ) return 'archive'
  if (
    type.includes('spreadsheet') ||
    type.includes('excel') ||
    ['xls', 'xlsx', 'csv', 'ods'].includes(ext)
  ) return 'spreadsheet'
  if (
    type.includes('presentation') ||
    type.includes('powerpoint') ||
    ['ppt', 'pptx', 'odp'].includes(ext)
  ) return 'presentation'
  if (
    type.includes('json') ||
    type.includes('javascript') ||
    type.includes('xml') ||
    ['js', 'jsx', 'ts', 'tsx', 'vue', 'html', 'css', 'scss', 'less', 'py', 'java', 'go', 'rs', 'php', 'sql', 'sh', 'json', 'yaml', 'yml', 'xml'].includes(ext)
  ) return 'code'
  if (['db', 'sqlite', 'sqlite3'].includes(ext)) return 'database'
  if (
    type.startsWith('text/') ||
    type.includes('word') ||
    ['txt', 'md', 'doc', 'docx', 'odt', 'rtf'].includes(ext)
  ) return 'document'
  return 'file'
})
const icon = computed(() => {
  const icons = {
    folder: Folder,
    image: Photo,
    audio: FileMusic,
    video: Video,
    pdf: FileText,
    archive: FileZip,
    spreadsheet: Table,
    presentation: Presentation,
    code: FileCode,
    database: Database,
    document: FileText,
    file: File,
  }
  return icons[category.value]
})
</script>

<template>
  <span class="file-icon" :class="`file-icon--${category}`">
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

.file-icon--folder { color: #b87a25; }
.file-icon--image { color: #43806d; }
.file-icon--audio { color: #78669b; }
.file-icon--video { color: #4d7192; }
.file-icon--pdf { color: #b65353; }
.file-icon--archive { color: #8a6f45; }
.file-icon--spreadsheet { color: #397a59; }
.file-icon--presentation { color: #a76245; }
.file-icon--code { color: #4f6f83; }
.file-icon--database { color: #65767d; }
</style>

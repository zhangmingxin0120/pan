<script setup lang="ts">
import { Check, Copy } from '@vicons/tabler'
import AppIcon from '@/components/base/AppIcon.vue'

const props = withDefaults(
  defineProps<{ title?: string; code: string; copyKey: string; copied?: string }>(),
  { title: '', copied: '' },
)
defineEmits<{ copy: [value: string, key: string] }>()
</script>

<template>
  <div class="code-block">
    <div class="code-head">
      <span>{{ title }}</span>
      <button @click="$emit('copy', code, copyKey)">
        <AppIcon :icon="props.copied === copyKey ? Check : Copy" />
        {{ props.copied === copyKey ? '已复制' : '复制' }}
      </button>
    </div>
    <pre><code>{{ code }}</code></pre>
  </div>
</template>

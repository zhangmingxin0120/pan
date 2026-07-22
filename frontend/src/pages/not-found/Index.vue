<script setup lang="ts">
import { ArrowLeft, FileOff } from '@vicons/tabler'
import { NButton } from 'naive-ui'
import AppIcon from '@/components/base/AppIcon.vue'
</script>

<template>
  <main class="not-found"><div><AppIcon :icon="FileOff" :size="38" /><span>404</span><h1>这个页面不存在</h1><p>地址可能有误，或页面已经被移动。</p><RouterLink to="/"><NButton type="primary"><template #icon><AppIcon :icon="ArrowLeft" /></template>返回云盘</NButton></RouterLink></div></main>
</template>

<style scoped lang="scss">
@use '@/assets/styles/variables' as *;
.not-found { min-height: 100vh; display: grid; place-items: center; padding: 24px; background: $background; text-align: center; }
.not-found > div { width: min(420px, 100%); }
.not-found span { display: block; margin-top: 12px; color: $primary; font-weight: 600; }
.not-found h1 { margin: 8px 0 6px; font-size: 26px; }
.not-found p { margin: 0 0 22px; color: $text-muted; }
</style>

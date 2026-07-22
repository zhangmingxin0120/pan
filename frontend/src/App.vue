<script setup lang="ts">
import { onMounted } from 'vue'
import { NConfigProvider, NDialogProvider, NMessageProvider } from 'naive-ui'
import { RouterView } from 'vue-router'
import { useAuthStore } from '@/stores/auth.store'
import { themeOverrides } from '@/theme'

const authStore = useAuthStore()
onMounted(() => authStore.initialize())
</script>

<template>
  <NConfigProvider :theme-overrides="themeOverrides">
    <NDialogProvider>
      <NMessageProvider>
        <RouterView />
      </NMessageProvider>
    </NDialogProvider>
  </NConfigProvider>
</template>


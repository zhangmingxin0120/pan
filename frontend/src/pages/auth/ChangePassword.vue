<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Lock } from '@vicons/tabler'
import { NButton, NInput, useMessage } from 'naive-ui'
import AppIcon from '@/components/base/AppIcon.vue'
import { useAuthStore } from '@/stores/auth.store'

const router = useRouter()
const authStore = useAuthStore()
const message = useMessage()
const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const loading = ref(false)
const isRequired = computed(() => authStore.user?.must_change_password)

async function submit() {
  if (!currentPassword.value) return message.warning('请输入当前密码')
  if (newPassword.value.length < 8) return message.warning('新密码至少 8 位')
  if (newPassword.value !== confirmPassword.value) return message.warning('两次输入的新密码不一致')
  loading.value = true
  try {
    await authStore.changePassword(currentPassword.value, newPassword.value)
    message.success('密码修改成功')
    await router.replace(authStore.user?.is_admin ? '/admin' : '/files')
  } catch (error) {
    message.error((error as { userMessage?: string }).userMessage || '修改失败，请重试')
  } finally {
    loading.value = false
  }
}

async function logout() {
  const wasAdmin = authStore.user?.is_admin
  await authStore.logout()
  await router.replace(wasAdmin ? '/admin/login' : '/login')
}
</script>

<template>
  <main class="password-page">
    <section class="password-card">
      <div class="icon"><AppIcon :icon="Lock" :size="25" /></div>
      <h1>{{ isRequired ? '首次登录，请修改密码' : '修改密码' }}</h1>
      <p>{{ isRequired ? '初始密码仅用于首次登录。设置新密码后才能使用管理员功能。' : '修改后，其他设备上的登录会立即失效。' }}</p>
      <div class="form">
        <label><span>当前密码</span><NInput v-model:value="currentPassword" type="password" show-password-on="click" autocomplete="current-password" /></label>
        <label><span>新密码</span><NInput v-model:value="newPassword" type="password" show-password-on="click" placeholder="至少 8 位" autocomplete="new-password" /></label>
        <label><span>确认新密码</span><NInput v-model:value="confirmPassword" type="password" show-password-on="click" autocomplete="new-password" @keyup.enter="submit" /></label>
        <NButton type="primary" block size="large" :loading="loading" @click="submit">保存新密码</NButton>
        <NButton v-if="isRequired" text block @click="logout">退出登录</NButton>
      </div>
    </section>
  </main>
</template>

<style scoped lang="scss">
@use '@/assets/styles/variables' as *;
.password-page { min-height: 100vh; display: grid; place-items: center; padding: 24px; background: $background; }
.password-card { width: min(100%, 430px); padding: 36px; border: 1px solid $border; border-radius: $radius-lg; background: $surface; box-shadow: $shadow-md; }
.icon { width: 48px; height: 48px; display: grid; place-items: center; border-radius: 12px; color: $primary; background: $primary-soft; }
h1 { margin: 20px 0 8px; font-size: 25px; font-weight: 620; }
p { margin: 0; color: $text-secondary; line-height: 1.7; }
.form { display: grid; gap: 16px; margin-top: 26px; }
label { display: grid; gap: 7px; color: $text-secondary; font-size: 13px; }
@media (max-width: 480px) { .password-card { padding: 28px 22px; } }
</style>

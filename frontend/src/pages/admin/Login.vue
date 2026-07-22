<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Eye, EyeOff, Lock, ShieldLock, User } from '@vicons/tabler'
import { NButton, NForm, NFormItem, NInput, useMessage, type FormInst, type FormRules } from 'naive-ui'
import AppIcon from '@/components/base/AppIcon.vue'
import { useAuthStore } from '@/stores/auth.store'

const router = useRouter()
const authStore = useAuthStore()
const message = useMessage()
const formRef = ref<FormInst | null>(null)
const form = reactive({ username: '', password: '' })
const loading = ref(false)
const showPassword = ref(false)

const rules: FormRules = {
  username: [{ required: true, message: '请输入管理员账号', trigger: ['input', 'blur'] }],
  password: [{ required: true, message: '请输入管理员密码', trigger: ['input', 'blur'] }],
}

async function submit() {
  await formRef.value?.validate()
  loading.value = true
  try {
    await authStore.adminLogin(form.username, form.password)
    await router.replace(authStore.user?.must_change_password ? '/change-password' : '/admin')
  } catch (error) {
    message.error((error as { userMessage?: string }).userMessage || '管理员登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="admin-login-page">
    <section class="login-card">
      <div class="admin-mark"><AppIcon :icon="ShieldLock" :size="27" /></div>
      <div class="heading">
        <span>Pan 系统管理</span>
        <h1>管理员登录</h1>
        <p>此入口仅供系统管理员使用</p>
      </div>
      <NForm ref="formRef" :model="form" :rules="rules" size="large" @submit.prevent="submit">
        <NFormItem label="管理员账号" path="username">
          <NInput v-model:value="form.username" placeholder="请输入管理员账号" autocomplete="username">
            <template #prefix><AppIcon :icon="User" :size="17" /></template>
          </NInput>
        </NFormItem>
        <NFormItem label="密码" path="password">
          <NInput v-model:value="form.password" :type="showPassword ? 'text' : 'password'" placeholder="请输入密码" autocomplete="current-password" @keyup.enter="submit">
            <template #prefix><AppIcon :icon="Lock" :size="17" /></template>
            <template #suffix>
              <button type="button" class="password-toggle" :aria-label="showPassword ? '隐藏密码' : '显示密码'" @click="showPassword = !showPassword">
                <AppIcon :icon="showPassword ? EyeOff : Eye" :size="17" />
              </button>
            </template>
          </NInput>
        </NFormItem>
        <NButton type="primary" block attr-type="submit" :loading="loading">进入管理后台</NButton>
      </NForm>
      <RouterLink class="user-link" to="/login">返回普通用户登录</RouterLink>
    </section>
  </main>
</template>

<style scoped lang="scss">
@use '@/assets/styles/variables' as *;
.admin-login-page { min-height: 100vh; display: grid; place-items: center; padding: 24px; background: #17231f; background-image: radial-gradient(circle at 50% 10%, rgba(43, 126, 105, .24), transparent 38%); }
.login-card { width: min(100%, 420px); padding: 38px; border: 1px solid rgba(255,255,255,.08); border-radius: 14px; background: $surface; box-shadow: 0 24px 70px rgba(0,0,0,.28); }
.admin-mark { width: 50px; height: 50px; display: grid; place-items: center; border-radius: 12px; color: white; background: $primary; }
.heading { margin: 20px 0 25px; }.heading > span { color: $primary; font-size: 12px; font-weight: 650; letter-spacing: .08em; }.heading h1 { margin: 5px 0 6px; font-size: 26px; }.heading p { margin: 0; color: $text-muted; }
.password-toggle { display: grid; place-items: center; padding: 4px; border: 0; color: $text-muted; background: transparent; cursor: pointer; }
.user-link { display: block; margin-top: 22px; color: $text-secondary; text-align: center; font-size: 13px; text-decoration: none; }.user-link:hover { color: $primary; }
@media (max-width: 480px) { .admin-login-page { padding: 16px; }.login-card { padding: 30px 22px; } }
</style>

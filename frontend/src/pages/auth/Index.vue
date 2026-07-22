<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Eye, EyeOff, Lock, Mail, User } from '@vicons/tabler'
import { NButton, NForm, NFormItem, NInput, useMessage, type FormInst, type FormRules } from 'naive-ui'
import AppIcon from '@/components/base/AppIcon.vue'
import { getPublicSystemConfig } from '@/api/modules/auth'
import { useAuthStore } from '@/stores/auth.store'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const authStore = useAuthStore()
const mode = ref<'login' | 'register'>('login')
const loading = ref(false)
const showPassword = ref(false)
const registrationEnabled = ref(false)
const formRef = ref<FormInst | null>(null)
const form = reactive({ email: '', name: '', password: '' })

const title = computed(() => (mode.value === 'login' ? '欢迎回来' : '创建你的空间'))
const subtitle = computed(() =>
  mode.value === 'login' ? '登录后继续管理你的文件' : '注册后将自动创建一个私人文件空间',
)

const rules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: ['input', 'blur'] },
    { type: 'email', message: '请输入有效邮箱', trigger: ['input', 'blur'] },
  ],
  name: [{ required: true, message: '请输入显示名称', trigger: ['input', 'blur'] }],
  password: [
    { required: true, message: '请输入密码', trigger: ['input', 'blur'] },
    {
      validator: (_rule, value: string) => mode.value === 'login' || value.length >= 8,
      message: '密码至少 8 位',
      trigger: ['input', 'blur'],
    },
  ],
}

const submit = async () => {
  await formRef.value?.validate()
  loading.value = true
  try {
    if (mode.value === 'login') await authStore.login(form.email, form.password)
    else await authStore.register(form.email, form.name, form.password)
    const redirect = authStore.user?.must_change_password
      ? '/change-password'
      : authStore.user?.is_admin
        ? '/admin'
        : typeof route.query.redirect === 'string'
          ? route.query.redirect
          : '/files'
    await router.replace(redirect)
  } catch (error) {
    const text = (error as { userMessage?: string }).userMessage || '提交失败，请重试'
    message.error(text)
  } finally {
    loading.value = false
  }
}

const switchMode = () => {
  if (!registrationEnabled.value) return
  mode.value = mode.value === 'login' ? 'register' : 'login'
  form.password = ''
}

onMounted(async () => {
  try {
    registrationEnabled.value = (await getPublicSystemConfig()).registration_enabled
  } catch {
    registrationEnabled.value = false
  }
})
</script>

<template>
  <main class="auth-page">
    <section class="auth-panel" aria-labelledby="auth-title">
      <div class="brand"><span class="brand-mark">P</span><span>Pan</span></div>
      <div class="auth-heading">
        <h1 id="auth-title">{{ title }}</h1>
        <p>{{ subtitle }}</p>
      </div>
      <div v-if="route.query.expired" class="session-note">登录已失效，请重新登录。</div>
      <NForm ref="formRef" :model="form" :rules="rules" size="large" @submit.prevent="submit">
        <NFormItem v-if="mode === 'register'" label="显示名称" path="name">
          <NInput v-model:value="form.name" placeholder="例如：小潘" maxlength="80">
            <template #prefix><AppIcon :icon="User" :size="17" /></template>
          </NInput>
        </NFormItem>
        <NFormItem label="邮箱" path="email">
          <NInput v-model:value="form.email" placeholder="name@example.com" autocomplete="email">
            <template #prefix><AppIcon :icon="Mail" :size="17" /></template>
          </NInput>
        </NFormItem>
        <NFormItem label="密码" path="password">
          <NInput
            v-model:value="form.password"
            :type="showPassword ? 'text' : 'password'"
            :placeholder="mode === 'login' ? '输入密码' : '至少 8 位'"
            :autocomplete="mode === 'login' ? 'current-password' : 'new-password'"
            @keyup.enter="submit"
          >
            <template #prefix><AppIcon :icon="Lock" :size="17" /></template>
            <template #suffix>
              <button
                type="button"
                class="password-toggle"
                :aria-label="showPassword ? '隐藏密码' : '显示密码'"
                @click="showPassword = !showPassword"
              >
                <AppIcon :icon="showPassword ? EyeOff : Eye" :size="17" />
              </button>
            </template>
          </NInput>
        </NFormItem>
        <NButton type="primary" block :loading="loading" attr-type="submit">
          {{ mode === 'login' ? '登录' : '创建账户' }}
        </NButton>
      </NForm>
      <p v-if="registrationEnabled" class="switch-copy">
        {{ mode === 'login' ? '还没有账户？' : '已经有账户？' }}
        <button type="button" @click="switchMode">
          {{ mode === 'login' ? '立即注册' : '返回登录' }}
        </button>
      </p>
    </section>
    <p class="auth-footer">你的文件默认仅自己可见，只有主动创建的分享链接可以访问。</p>
  </main>
</template>

<style scoped lang="scss">
@use '@/assets/styles/variables' as *;

.auth-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 24px;
  padding: 32px 20px;
  background:
    linear-gradient(rgba(23, 107, 91, 0.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(23, 107, 91, 0.035) 1px, transparent 1px), $background;
  background-size: 32px 32px;
}

.auth-panel {
  width: min(100%, 412px);
  padding: 34px 36px 32px;
  background: $surface;
  border: 1px solid $border;
  border-radius: $radius-lg;
  box-shadow: 0 18px 60px rgba(32, 51, 45, 0.08);
}

.brand {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 19px;
  font-weight: 650;
}

.brand-mark {
  width: 29px;
  height: 29px;
  display: grid;
  place-items: center;
  border-radius: 9px;
  color: white;
  background: $primary;
}

.auth-heading {
  margin: 28px 0 24px;
}

.auth-heading h1 {
  margin: 0;
  font-size: 26px;
  line-height: 1.35;
  font-weight: 600;
  letter-spacing: -0.025em;
}

.auth-heading p {
  margin: 7px 0 0;
  color: $text-secondary;
}

.session-note {
  margin: -8px 0 18px;
  padding: 10px 12px;
  color: $warning;
  background: #fff7ea;
  border-radius: $radius-md;
  font-size: 13px;
}

.password-toggle {
  display: grid;
  place-items: center;
  padding: 4px;
  border: 0;
  color: $text-muted;
  background: transparent;
  cursor: pointer;
}

.switch-copy {
  margin: 22px 0 0;
  color: $text-secondary;
  text-align: center;
  font-size: 13px;
}

.switch-copy button {
  padding: 2px 4px;
  border: 0;
  color: $primary;
  background: transparent;
  cursor: pointer;
  font-weight: 550;
}

.auth-footer {
  max-width: 412px;
  margin: 0;
  color: $text-muted;
  font-size: 12px;
  text-align: center;
}

@media (max-width: 480px) {
  .auth-page {
    display: block;
    padding: 20px 16px;
    background: $surface;
  }

  .auth-panel {
    padding: 24px 4px;
    border: 0;
    box-shadow: none;
  }

  .auth-footer {
    margin: 8px auto;
  }
}
</style>

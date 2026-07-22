import { createRouter, createWebHistory } from 'vue-router'
import { getToken } from '@/api/request'
import { useAuthStore } from '@/stores/auth.store'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: () => import('@/pages/auth/Index.vue'), meta: { guest: true } },
    { path: '/change-password', name: 'change-password', component: () => import('@/pages/auth/ChangePassword.vue'), meta: { requiresAuth: true } },
    { path: '/admin/login', name: 'admin-login', component: () => import('@/pages/admin/Login.vue'), meta: { adminGuest: true } },
    { path: '/admin', name: 'admin', component: () => import('@/pages/admin/Index.vue'), meta: { requiresAuth: true, admin: true } },
    { path: '/api-docs', name: 'api-docs', component: () => import('@/pages/api-docs/Index.vue'), meta: { public: true } },
    {
      path: '/',
      component: () => import('@/components/layout/AppLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        { path: '', redirect: '/files' },
        { path: 'files', name: 'files', component: () => import('@/pages/files/Index.vue') },
        { path: 'shares', name: 'shares', component: () => import('@/pages/shares/Index.vue') },
        { path: 'trash', name: 'trash', component: () => import('@/pages/trash/Index.vue') },
      ],
    },
    { path: '/s/:token', name: 'public-share', component: () => import('@/pages/public-share/Index.vue') },
    { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('@/pages/not-found/Index.vue') },
  ],
})

router.beforeEach(async (to) => {
  const hasToken = Boolean(getToken())
  if (to.matched.some((record) => record.meta.requiresAuth) && !hasToken) {
    return to.meta.admin
      ? { name: 'admin-login' }
      : { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.meta.adminGuest && !hasToken) return
  if (!hasToken) return
  const authStore = useAuthStore()
  await authStore.initialize()
  if (!authStore.user) return { name: 'login' }
  if (to.meta.public) return
  if (authStore.user.must_change_password && to.name !== 'change-password') {
    return { name: 'change-password' }
  }
  if (to.name === 'change-password') return
  if (authStore.user.is_admin && to.name !== 'admin') return { name: 'admin' }
  if (!authStore.user.is_admin && (to.meta.admin || to.meta.adminGuest)) return { name: 'files' }
  if (to.meta.guest) return { name: authStore.user.is_admin ? 'admin' : 'files' }
})

export default router

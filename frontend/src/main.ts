import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth.store'
import './assets/styles/global.scss'

const pinia = createPinia()

window.addEventListener('pan:auth-expired', () => {
  useAuthStore(pinia).clearSession()
  void router.push({ name: 'login', query: { expired: '1' } })
})

createApp(App).use(pinia).use(router).mount('#app')

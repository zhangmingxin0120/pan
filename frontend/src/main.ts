import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './assets/styles/global.scss'

window.addEventListener('pan:auth-expired', () => {
  void router.push({ name: 'login', query: { expired: '1' } })
})

createApp(App).use(createPinia()).use(router).mount('#app')


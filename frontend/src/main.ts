import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import Aura from '@primeuix/themes/aura'
import 'primeicons/primeicons.css'

import App from './App.vue'
import router from './router'
import { initApiClient } from './api/client'
import { useAuthStore } from './stores/auth'
import './style.css'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)

// Restore session from cookie before router guard runs
const authStore = useAuthStore()
await authStore.fetchUser()

app.use(router)
app.use(PrimeVue, {
  theme: {
    preset: Aura,
    options: { darkModeSelector: '[data-theme="dark"]' },
  },
})
app.use(ToastService)
app.mount('#app')
initApiClient(app, router, () => {
  authStore.user = null
  router.push('/login')
})

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Toast from 'primevue/toast'
import { useAuthStore } from './stores/auth'
import { useReferencesStore } from './stores/references'

const auth = useAuthStore()
const refs = useReferencesStore()
const router = useRouter()

onMounted(async () => {
  if (auth.isAuthenticated) {
    await auth.fetchUser()
    if (auth.isAuthenticated) {
      await refs.fetchAll()
    }
  }
})

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <Toast position="top-right" />
  <div v-if="auth.isAuthenticated" class="app-layout">
    <aside class="sidebar">
      <div class="sidebar-brand">Wallet</div>
      <nav class="sidebar-nav">
        <RouterLink to="/"><i class="pi pi-chart-bar"></i> Dashboard</RouterLink>
        <RouterLink to="/transactions"><i class="pi pi-arrow-right-left"></i> Transactions</RouterLink>
        <RouterLink to="/balance-snapshots"><i class="pi pi-wallet"></i> Balances</RouterLink>
        <RouterLink to="/expenses"><i class="pi pi-receipt"></i> Expenses</RouterLink>
        <RouterLink to="/settings"><i class="pi pi-cog"></i> Settings</RouterLink>
      </nav>
      <div class="sidebar-footer">
        <div style="font-size: 0.8125rem; margin-bottom: 8px; color: #94a3b8;">
          {{ auth.user?.email }}
        </div>
        <button @click="logout">Log out</button>
      </div>
    </aside>
    <main class="main-content">
      <RouterView />
    </main>
  </div>
  <RouterView v-else />
</template>

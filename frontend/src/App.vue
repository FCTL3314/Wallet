<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Toast from 'primevue/toast'
import { useAuthStore } from './stores/auth'
import { useReferencesStore } from './stores/references'
import { PhChartBar, PhArrowsLeftRight, PhWallet, PhReceipt, PhBooks, PhGear } from '@phosphor-icons/vue'

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
      <div class="sidebar-brand">
        <span class="sidebar-brand-name">Wallet</span>
      </div>
      <nav class="sidebar-nav">
        <RouterLink to="/"><PhChartBar weight="duotone" /> Dashboard</RouterLink>
        <RouterLink to="/transactions"><PhArrowsLeftRight weight="duotone" /> Income</RouterLink>
        <RouterLink to="/balance-snapshots"><PhWallet weight="duotone" /> Balances</RouterLink>
        <RouterLink to="/expenses"><PhReceipt weight="duotone" /> Regular Expenses</RouterLink>
        <RouterLink to="/references"><PhBooks weight="duotone" /> References</RouterLink>
        <RouterLink to="/settings"><PhGear weight="duotone" /> Settings</RouterLink>
      </nav>
      <div class="sidebar-footer">
        <div class="sidebar-footer-email">{{ auth.user?.email }}</div>
        <button @click="logout">Log out</button>
      </div>
    </aside>
    <main class="main-content">
      <Transition name="page" mode="out-in">
        <RouterView />
      </Transition>
    </main>
  </div>
  <Transition name="page" mode="out-in">
    <RouterView v-if="!auth.isAuthenticated" />
  </Transition>
</template>

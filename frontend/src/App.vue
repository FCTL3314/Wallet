<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Toast from 'primevue/toast'
import { useAuthStore } from './stores/auth'
import { useReferencesStore } from './stores/references'
import {
  PhChartBar, PhArrowsLeftRight, PhWallet, PhReceipt, PhBooks, PhGear,
  PhCaretLeft, PhCaretRight, PhSignOut,
} from '@phosphor-icons/vue'

const auth = useAuthStore()
const refs = useReferencesStore()
const router = useRouter()

const collapsed = ref(localStorage.getItem('sidebar-collapsed') === 'true')
watch(collapsed, (val) => localStorage.setItem('sidebar-collapsed', String(val)))

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

  <div v-if="auth.isAuthenticated" :class="['app-layout', { 'sidebar-collapsed': collapsed }]">
    <aside :class="['sidebar', { 'sidebar--collapsed': collapsed }]">
      <div class="sidebar-brand">
        <span class="sidebar-brand-name">Wallet</span>
        <button
          class="sidebar-toggle"
          :title="collapsed ? 'Expand sidebar' : 'Collapse sidebar'"
          @click="collapsed = !collapsed"
        >
          <PhCaretLeft v-if="!collapsed" :size="14" weight="bold" />
          <PhCaretRight v-else :size="14" weight="bold" />
        </button>
      </div>
      <nav class="sidebar-nav">
        <RouterLink to="/" title="Dashboard"><PhChartBar weight="duotone" /><span>Dashboard</span></RouterLink>
        <RouterLink to="/transactions" title="Income"><PhArrowsLeftRight weight="duotone" /><span>Income</span></RouterLink>
        <RouterLink to="/balance-snapshots" title="Balances"><PhWallet weight="duotone" /><span>Balances</span></RouterLink>
        <RouterLink to="/expenses" title="Regular Expenses"><PhReceipt weight="duotone" /><span>Regular Expenses</span></RouterLink>
        <RouterLink to="/references" title="References"><PhBooks weight="duotone" /><span>References</span></RouterLink>
        <RouterLink to="/settings" title="Settings"><PhGear weight="duotone" /><span>Settings</span></RouterLink>
      </nav>
      <div class="sidebar-footer">
        <div class="sidebar-footer-email">{{ auth.user?.email }}</div>
        <button class="sidebar-logout" title="Log out" @click="logout">
          <PhSignOut weight="duotone" :size="16" />
          <span>Log out</span>
        </button>
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

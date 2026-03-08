<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Toast from 'primevue/toast'
import { useAuthStore } from './stores/auth'
import { useReferencesStore } from './stores/references'
import { useThemeStore } from './stores/theme'
import { useNotificationsStore } from './stores/notifications'
import { useOnboardingStore } from './stores/onboarding'
import { PhChartBar, PhArrowsLeftRight, PhWallet, PhReceipt, PhBooks, PhGear, PhSignOut } from '@phosphor-icons/vue'
import TheBottomNav from './components/TheBottomNav.vue'
import TheAppFooter from './components/TheAppFooter.vue'
import OnboardingGuide from './components/OnboardingGuide.vue'
import AppNotifications from './components/AppNotifications.vue'

const auth = useAuthStore()
const refs = useReferencesStore()
const router = useRouter()
const notifications = useNotificationsStore()
const onboarding = useOnboardingStore()

// Sync Pinia store with what the anti-FOUC script already applied
useThemeStore().init()

onMounted(async () => {
  if (auth.isAuthenticated) {
    await auth.fetchUser()
    if (auth.isAuthenticated) {
      await refs.fetchAll()
      checkOnboardingNotification()
    }
  }
})

function checkOnboardingNotification() {
  if (sessionStorage.getItem('onboarding-notif-shown')) return
  const user = auth.user
  if (!user || user.onboarding_completed) return
  const registeredAt = new Date(user.created_at)
  const daysSinceRegistration = (Date.now() - registeredAt.getTime()) / (1000 * 60 * 60 * 24)
  if (daysSinceRegistration > 7) return

  sessionStorage.setItem('onboarding-notif-shown', '1')
  setTimeout(() => {
    notifications.add({
      type: 'info',
      title: 'Complete your setup',
      message: 'Start the quick onboarding guide to set up your first account and currencies.',
      duration: 0,
      action: {
        label: 'Start guide',
        handler: () => onboarding.start(),
      },
    })
  }, 2000)
}

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <Toast position="top-right" />
  <OnboardingGuide />
  <AppNotifications />

  <div v-if="auth.isAuthenticated" class="app-layout">
    <header class="app-header">
      <span class="header-brand">Wallet</span>
      <nav class="header-nav">
        <RouterLink to="/"><PhChartBar weight="duotone" />Dashboard</RouterLink>
        <RouterLink to="/transactions"><PhArrowsLeftRight weight="duotone" />Income</RouterLink>
        <RouterLink to="/balance-snapshots"><PhWallet weight="duotone" />Balances</RouterLink>
        <RouterLink to="/expenses"><PhReceipt weight="duotone" />Regular Expenses</RouterLink>
        <RouterLink to="/references"><PhBooks weight="duotone" />References</RouterLink>
        <RouterLink to="/settings"><PhGear weight="duotone" />Settings</RouterLink>
      </nav>
      <div class="header-user">
        <button class="header-avatar-chip" @click="logout">
          <span class="header-avatar">{{ auth.user?.email?.charAt(0).toUpperCase() }}</span>
          <span class="header-username">{{ auth.user?.email?.split('@')[0] }}</span>
          <span class="header-logout-label"><PhSignOut weight="duotone" :size="14" />Log out</span>
        </button>
      </div>
    </header>
    <main class="main-content">
      <Transition name="page" mode="out-in">
        <RouterView />
      </Transition>
      <TheAppFooter />
    </main>
    <TheBottomNav />
  </div>
  <Transition name="page" mode="out-in">
    <RouterView v-if="!auth.isAuthenticated" />
  </Transition>
</template>

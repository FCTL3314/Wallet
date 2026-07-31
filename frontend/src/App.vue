<script setup lang="ts">
import { onMounted, onBeforeUnmount, computed, nextTick, ref, useTemplateRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'
import { useReferencesStore } from './stores/references'
import { useThemeStore } from './stores/theme'
import { useNotificationsStore } from './stores/notifications'
import { useOnboardingStore } from './stores/onboarding'
import { PhCaretDown, PhGear, PhSignOut } from '@phosphor-icons/vue'
import { NAV_ITEMS } from './router'
import TheBottomNav from './components/TheBottomNav.vue'
import TheAppFooter from './components/TheAppFooter.vue'
import OnboardingGuide from './components/OnboardingGuide.vue'
import AppNotifications from './components/AppNotifications.vue'
import GlobalLoadingBar from './components/GlobalLoadingBar.vue'
import PageHead from './components/PageHead.vue'

const auth = useAuthStore()
const refs = useReferencesStore()
const router = useRouter()
const route = useRoute()
const pageEyebrow = computed(() => (route.meta.eyebrow as string | undefined) ?? '')
const pageTitle = computed(() => (route.meta.title as string | undefined) ?? '')
const notifications = useNotificationsStore()
const onboarding = useOnboardingStore()

const userEmail = computed(() => auth.user?.email ?? '')
const userInitial = computed(() => userEmail.value.charAt(0).toUpperCase())
const userName = computed(() => userEmail.value.split('@')[0])

const menuOpen = ref(false)
const menuRoot = useTemplateRef<HTMLElement>('menuRoot')
const menuTrigger = useTemplateRef<HTMLButtonElement>('menuTrigger')
const menuPanel = useTemplateRef<HTMLElement>('menuPanel')

// Sync Pinia store with what the anti-FOUC script already applied
useThemeStore().init()

onMounted(async () => {
  if (auth.isAuthenticated) {
    await auth.fetchUser()
    if (auth.isAuthenticated) {
      await refs.fetchAll()
      if (refs.error) {
        notifications.add({
          type: 'error',
          title: 'Failed to load data',
          message: refs.error,
          duration: 0,
        })
      }
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

function menuItems(): HTMLElement[] {
  return Array.from(menuPanel.value?.querySelectorAll<HTMLElement>('[role="menuitem"]') ?? [])
}

function focusMenuItem(offset: number) {
  const items = menuItems()
  if (!items.length) return
  const current = items.indexOf(document.activeElement as HTMLElement)
  const next = (current + offset + items.length) % items.length
  items[next]?.focus()
}

function openMenu() {
  menuOpen.value = true
}

function closeMenu(restoreFocus = false) {
  if (!menuOpen.value) return
  menuOpen.value = false
  if (restoreFocus) menuTrigger.value?.focus()
}

function toggleMenu() {
  if (menuOpen.value) closeMenu()
  else openMenu()
}

function onDocumentPointerDown(event: PointerEvent) {
  if (!menuRoot.value?.contains(event.target as Node)) closeMenu()
}

function onMenuFocusOut(event: FocusEvent) {
  const next = event.relatedTarget as Node | null
  if (next && menuRoot.value?.contains(next)) return
  closeMenu()
}

function onDocumentKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') closeMenu(true)
}

watch(menuOpen, async (open) => {
  if (open) {
    document.addEventListener('pointerdown', onDocumentPointerDown)
    document.addEventListener('keydown', onDocumentKeydown)
    await nextTick()
    menuItems()[0]?.focus()
  } else {
    document.removeEventListener('pointerdown', onDocumentPointerDown)
    document.removeEventListener('keydown', onDocumentKeydown)
  }
})

watch(() => route.fullPath, () => closeMenu())

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', onDocumentPointerDown)
  document.removeEventListener('keydown', onDocumentKeydown)
})

function logout() {
  closeMenu()
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <GlobalLoadingBar />
  <OnboardingGuide />
  <AppNotifications />

  <div v-if="auth.isAuthenticated" class="app-layout">
    <header class="app-header">
      <span class="header-brand">
        <span class="brand-mark">W</span>
        <span>Wallet</span>
      </span>
      <nav class="header-nav" aria-label="Main navigation">
        <RouterLink
          v-for="item in NAV_ITEMS"
          :key="item.path"
          :to="item.path"
          :title="item.label"
          :aria-label="item.label"
        >
          <component :is="item.icon" weight="bold" />
          <span class="nav-label">{{ item.label }}</span>
        </RouterLink>
      </nav>
      <div ref="menuRoot" class="header-user">
        <button
          ref="menuTrigger"
          type="button"
          class="header-avatar-chip"
          aria-haspopup="menu"
          aria-controls="profile-menu"
          :aria-expanded="menuOpen"
          :aria-label="`Account menu for ${userEmail}`"
          @click="toggleMenu"
          @keydown.down.prevent="openMenu"
        >
          <span class="header-avatar">{{ userInitial }}</span>
          <span class="header-username">{{ userName }}</span>
          <PhCaretDown class="header-chip-caret" weight="bold" :size="12" />
        </button>
        <Transition name="profile-menu">
          <div
            v-if="menuOpen"
            id="profile-menu"
            ref="menuPanel"
            class="profile-menu"
            role="menu"
            aria-label="Account"
            tabindex="-1"
            @focusout="onMenuFocusOut"
            @keydown.down.prevent="focusMenuItem(1)"
            @keydown.up.prevent="focusMenuItem(-1)"
          >
            <div class="profile-menu-head">
              <span class="profile-menu-caption">Signed in as</span>
              <span class="profile-menu-email">{{ userEmail }}</span>
            </div>
            <RouterLink to="/settings" class="profile-menu-item" role="menuitem" @click="closeMenu()">
              <PhGear weight="duotone" :size="16" />
              Settings
            </RouterLink>
            <button
              type="button"
              class="profile-menu-item profile-menu-item--danger"
              role="menuitem"
              @click="logout"
            >
              <PhSignOut weight="duotone" :size="16" />
              Log out
            </button>
          </div>
        </Transition>
      </div>
    </header>
    <main class="main-content">
      <PageHead v-if="pageTitle" :eyebrow="pageEyebrow" :title="pageTitle" />
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

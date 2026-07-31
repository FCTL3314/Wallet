import { createRouter, createWebHistory } from 'vue-router'
import type { Component } from 'vue'
import {
  PhSquaresFour,
  PhArrowDown,
  PhWallet,
  PhArrowsClockwise,
  PhBookBookmark,
  PhGear,
} from '@phosphor-icons/vue'
import { useAuthStore } from '../stores/auth'

declare module 'vue-router' {
  interface RouteMeta {
    guest?: boolean
    /** Reachable in both states — neither guard redirects away from it. */
    public?: boolean
    eyebrow?: string
    title?: string
  }
}

export const DEFAULT_ROUTE = '/'
export const NOT_FOUND_ROUTE = 'NotFound'

export interface NavItem {
  path: string
  label: string
  shortLabel: string
  icon: Component
  primary: boolean
}

export const NAV_ITEMS: NavItem[] = [
  { path: '/', label: 'Dashboard', shortLabel: 'Dashboard', icon: PhSquaresFour, primary: true },
  { path: '/transactions', label: 'Income', shortLabel: 'Income', icon: PhArrowDown, primary: true },
  { path: '/balance-snapshots', label: 'Balances', shortLabel: 'Balances', icon: PhWallet, primary: true },
  { path: '/expenses', label: 'Regular Expenses', shortLabel: 'Expenses', icon: PhArrowsClockwise, primary: true },
  { path: '/references', label: 'References', shortLabel: 'References', icon: PhBookBookmark, primary: false },
  { path: '/settings', label: 'Settings', shortLabel: 'Settings', icon: PhGear, primary: false },
]

export const PRIMARY_NAV_ITEMS = NAV_ITEMS.filter((item) => item.primary)
export const SECONDARY_NAV_ITEMS = NAV_ITEMS.filter((item) => !item.primary)

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue'),
    meta: { guest: true },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/RegisterView.vue'),
    meta: { guest: true },
  },
  {
    path: '/oauth/callback',
    name: 'OAuthCallback',
    component: () => import('../views/OAuthCallbackView.vue'),
    // The session cookie is already set by the time we land here, so `guest`
    // would bounce every successful sign-in straight to Dashboard and the view
    // could never render — including its failure state.
    meta: { public: true },
  },
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('../views/DashboardView.vue'),
    meta: { eyebrow: 'Overview', title: 'Dashboard' },
  },
  {
    path: '/transactions',
    name: 'Transactions',
    component: () => import('../views/TransactionsView.vue'),
    meta: { eyebrow: 'Movement', title: 'Income' },
  },
  {
    path: '/balance-snapshots',
    name: 'BalanceSnapshots',
    component: () => import('../views/BalanceSnapshotsView.vue'),
    meta: { eyebrow: 'Accounts', title: 'Balances' },
  },
  {
    path: '/expenses',
    name: 'Expenses',
    component: () => import('../views/ExpensesView.vue'),
    meta: { eyebrow: 'Scheduled', title: 'Regular Expenses' },
  },
  {
    path: '/references',
    name: 'References',
    component: () => import('../views/ReferencesView.vue'),
    meta: { eyebrow: 'Library', title: 'References' },
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('../views/SettingsView.vue'),
    meta: { eyebrow: 'Account', title: 'Settings' },
  },
  {
    path: '/:pathMatch(.*)*',
    name: NOT_FOUND_ROUTE,
    component: () => import('../views/NotFoundView.vue'),
    meta: { eyebrow: 'Error 404', title: 'Page not found' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.public) {
    return
  }
  if (!to.meta.guest && !auth.isAuthenticated) {
    const worthRestoring = to.name !== NOT_FOUND_ROUTE && to.fullPath !== DEFAULT_ROUTE
    return worthRestoring ? { name: 'Login', query: { redirect: to.fullPath } } : { name: 'Login' }
  }
  if (to.meta.guest && auth.isAuthenticated) {
    return { name: 'Dashboard' }
  }
})

export default router

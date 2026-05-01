import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

declare module 'vue-router' {
  interface RouteMeta {
    guest?: boolean
    eyebrow?: string
    title?: string
  }
}

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
    meta: { guest: true },
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
    meta: { eyebrow: 'Movement', title: 'Transactions' },
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
    meta: { eyebrow: 'Scheduled', title: 'Regular expenses' },
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
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.guest && !auth.isAuthenticated) {
    return { name: 'Login' }
  }
  if (to.meta.guest && auth.isAuthenticated) {
    return { name: 'Dashboard' }
  }
})

export default router

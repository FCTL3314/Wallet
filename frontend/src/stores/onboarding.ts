import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { useAuthStore } from './auth'
import { authApi } from '../api/auth'

export const useOnboardingStore = defineStore('onboarding', () => {
  const auth = useAuthStore()
  const active = ref(false)

  const completed = computed(() => auth.user?.onboarding_completed ?? false)

  function start() {
    active.value = true
  }

  async function finish() {
    active.value = false
    try {
      const { data } = await authApi.completeOnboarding()
      auth.user = data
    } catch {
      // best-effort: guide is hidden, backend state update is non-blocking
    }
  }

  function reset() {
    // Allows re-running the guide from Settings without uncompleting on backend
    active.value = false
  }

  return { completed, active, start, finish, reset }
})

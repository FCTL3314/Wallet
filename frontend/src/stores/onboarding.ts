import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { useAuthStore } from './auth'
import { authApi } from '../api/auth'

export const useOnboardingStore = defineStore('onboarding', () => {
  const auth = useAuthStore()
  const active = ref(false)
  const stepIndex = ref(0)

  const completed = computed(() => auth.user?.onboarding_completed ?? false)

  function start() {
    active.value = true
  }

  function goToStep(index: number) {
    stepIndex.value = Math.max(0, index)
  }

  function pause() {
    active.value = false
  }

  function reset() {
    active.value = false
    stepIndex.value = 0
  }

  async function finish() {
    active.value = false
    stepIndex.value = 0
    if (completed.value) return
    const response = await authApi.completeOnboarding().catch(() => null)
    if (response) auth.user = response.data
  }

  return { active, stepIndex, completed, start, goToStep, pause, reset, finish }
})

import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useOnboardingStore = defineStore('onboarding', () => {
  const completed = ref(localStorage.getItem('onboarding-completed') === 'true')
  const active = ref(false)

  function start() {
    active.value = true
  }

  function finish() {
    completed.value = true
    active.value = false
    localStorage.setItem('onboarding-completed', 'true')
  }

  function reset() {
    completed.value = false
    localStorage.removeItem('onboarding-completed')
  }

  return { completed, active, start, finish, reset }
})

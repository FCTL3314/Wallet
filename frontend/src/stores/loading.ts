import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

export const useLoadingStore = defineStore('loading', () => {
  const activeCount = ref(0)

  const isLoading = computed(() => activeCount.value > 0)

  function start() {
    activeCount.value++
  }

  function done() {
    if (activeCount.value > 0) activeCount.value--
  }

  function reset() {
    activeCount.value = 0
  }

  return { activeCount, isLoading, start, done, reset }
})

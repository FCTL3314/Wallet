import { ref } from 'vue'
import type { Ref } from 'vue'
import { getErrorMessage } from '../api/errors'

export function useAsync<T>(fn: () => Promise<T>) {
  const data = ref<T | null>(null) as Ref<T | null>
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function execute() {
    loading.value = true
    error.value = null
    try {
      data.value = await fn()
    } catch (e) {
      error.value = getErrorMessage(e)
    } finally {
      loading.value = false
    }
  }

  return { data, loading, error, execute }
}

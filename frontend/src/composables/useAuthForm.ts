import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useReferencesStore } from '../stores/references'
import { getErrorMessage } from '../api/errors'

export function useAuthForm() {
  const refs = useReferencesStore()
  const router = useRouter()
  const serverError = ref('')

  async function submitAuthAction(action: () => Promise<void>) {
    serverError.value = ''
    try {
      await action()
      await refs.fetchAll()
      router.push('/')
    } catch (e: unknown) {
      serverError.value = getErrorMessage(e)
    }
  }

  return { serverError, submitAuthAction }
}

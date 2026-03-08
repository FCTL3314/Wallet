import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useReferencesStore } from '../stores/references'
import { useOnboardingStore } from '../stores/onboarding'
import { getErrorMessage } from '../api/errors'

export function useAuthForm() {
  const refs = useReferencesStore()
  const onboarding = useOnboardingStore()
  const router = useRouter()
  const serverError = ref('')

  async function submitAuthAction(action: () => Promise<void>, isRegister = false) {
    serverError.value = ''
    try {
      await action()
      await refs.fetchAll()
      if (isRegister && !onboarding.completed) {
        onboarding.start()
      }
      router.push('/')
    } catch (e: unknown) {
      serverError.value = getErrorMessage(e)
    }
  }

  return { serverError, submitAuthAction }
}

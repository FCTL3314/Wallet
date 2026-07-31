import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { LocationQueryValue, Router } from 'vue-router'
import { useReferencesStore } from '../stores/references'
import { useOnboardingStore } from '../stores/onboarding'
import { getErrorMessage } from '../api/errors'
import { DEFAULT_ROUTE, NOT_FOUND_ROUTE } from '../router'

const INTERNAL_PATH = /^\/(?![/\\])/

type QueryValue = LocationQueryValue | LocationQueryValue[] | undefined

function resolveRedirect(router: Router, raw: QueryValue): string {
  const target = Array.isArray(raw) ? raw[0] : raw
  if (typeof target !== 'string' || !INTERNAL_PATH.test(target)) return DEFAULT_ROUTE
  if (router.resolve(target).name === NOT_FOUND_ROUTE) return DEFAULT_ROUTE
  return target
}

export function useAuthForm() {
  const refs = useReferencesStore()
  const onboarding = useOnboardingStore()
  const router = useRouter()
  const route = useRoute()
  const serverError = ref('')

  async function submitAuthAction(action: () => Promise<void>, isRegister = false) {
    serverError.value = ''
    try {
      await action()
      await refs.fetchAll()
      if (isRegister && !onboarding.completed) {
        onboarding.start()
      }
      router.push(resolveRedirect(router, route.query.redirect))
    } catch (e: unknown) {
      serverError.value = getErrorMessage(e)
    }
  }

  return { serverError, submitAuthAction }
}

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useReferencesStore } from '../stores/references'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const refs = useReferencesStore()

const error = ref('')

const ERROR_MESSAGES: Record<string, string> = {
  state:
    'Sign-in request expired or could not be verified. Please start again from the login page.',
  profile:
    'The provider did not return your account details. Please try again in a moment.',
  email_taken:
    'An account with this email already exists. Log in with your password first, then link this provider from Settings.',
}

const FALLBACK_ERROR =
  'Authentication failed: could not complete sign-in. Please try again.'

onMounted(async () => {
  const reason = route.query.error
  if (typeof reason === 'string') {
    error.value = ERROR_MESSAGES[reason] ?? FALLBACK_ERROR
    return
  }

  // fetchUser swallows its own errors, so the outcome has to be read from the
  // store rather than caught — relying on a throw here left the failure state
  // permanently unreachable.
  await auth.fetchUser()
  if (!auth.isAuthenticated) {
    error.value = FALLBACK_ERROR
    return
  }

  await refs.fetchAll()
  router.replace('/')
})
</script>

<template>
  <div class="auth-page">
    <div class="auth-card oauth-callback-card">
      <div class="auth-orb"></div>
      <h1 class="auth-title">Wallet</h1>

      <div v-if="!error" class="oauth-callback-loading">
        <div class="oauth-spinner" aria-label="Signing you in" role="status"></div>
        <p class="oauth-callback-message">Signing you in&hellip;</p>
      </div>

      <div v-else class="oauth-callback-error">
        <p class="error-msg">{{ error }}</p>
        <RouterLink to="/login" class="btn btn-primary btn-block" style="margin-top: 16px">
          Back to Log In
        </RouterLink>
      </div>
    </div>
  </div>
</template>

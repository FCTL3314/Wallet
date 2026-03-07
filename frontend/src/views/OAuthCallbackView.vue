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

onMounted(async () => {
  const accessToken = route.query.access_token
  const refreshToken = route.query.refresh_token

  if (typeof accessToken !== 'string' || !accessToken || typeof refreshToken !== 'string' || !refreshToken) {
    error.value = 'Authentication failed: missing tokens. Please try again.'
    return
  }

  try {
    await auth.loginWithTokens(accessToken, refreshToken)
    await refs.fetchAll()
    router.replace('/')
  } catch {
    error.value = 'Authentication failed: could not complete sign-in. Please try again.'
  }
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

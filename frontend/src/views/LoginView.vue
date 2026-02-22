<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useReferencesStore } from '../stores/references'

const auth = useAuthStore()
const refs = useReferencesStore()
const router = useRouter()
const email = ref('')
const password = ref('')
const error = ref('')

async function submit() {
  error.value = ''
  try {
    await auth.login(email.value, password.value)
    await refs.fetchAll()
    router.push('/')
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'Login failed'
  }
}
</script>

<template>
  <div class="auth-page">
    <div class="auth-card">
      <h1>Log In</h1>
      <form @submit.prevent="submit">
        <div class="form-group">
          <label>Email</label>
          <input v-model="email" type="email" required placeholder="you@example.com" />
        </div>
        <div class="form-group">
          <label>Password</label>
          <input v-model="password" type="password" required placeholder="••••••••" />
        </div>
        <p v-if="error" class="error-msg">{{ error }}</p>
        <button type="submit" class="btn btn-primary btn-block" style="margin-top: 8px">Log In</button>
      </form>
      <p class="auth-link">
        Don't have an account? <RouterLink to="/register">Register</RouterLink>
      </p>
    </div>
  </div>
</template>

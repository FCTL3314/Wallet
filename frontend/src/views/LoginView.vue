<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useForm, useField } from 'vee-validate'
import * as yup from 'yup'
import { useAuthStore } from '../stores/auth'
import { useReferencesStore } from '../stores/references'
import { getErrorMessage } from '../api/errors'

const auth = useAuthStore()
const refs = useReferencesStore()
const router = useRouter()

const schema = yup.object({
  email: yup.string().required('Email is required').email('Invalid email format'),
  password: yup.string().required('Password is required'),
})

const { handleSubmit, errors: formErrors } = useForm({ validationSchema: schema })

const { value: email, meta: emailMeta } = useField<string>('email', undefined, { validateOnValueUpdate: true })
const { value: password, meta: passwordMeta } = useField<string>('password', undefined, { validateOnValueUpdate: true })

const serverError = ref('')

const submit = handleSubmit(async (values) => {
  serverError.value = ''
  try {
    await auth.login(values.email, values.password)
    await refs.fetchAll()
    router.push('/')
  } catch (e: unknown) {
    serverError.value = getErrorMessage(e)
  }
})
</script>

<template>
  <div class="auth-page">
    <div class="auth-card">
      <h1>Log In</h1>
      <form @submit.prevent="submit">
        <div class="form-group">
          <label>Email</label>
          <input
            v-model="email"
            type="email"
            placeholder="you@example.com"
            :class="{
              'input-valid': emailMeta.dirty && emailMeta.valid,
              'input-invalid': emailMeta.dirty && !emailMeta.valid
            }"
          />
          <p v-if="formErrors.email" class="field-error">{{ formErrors.email }}</p>
        </div>
        <div class="form-group">
          <label>Password</label>
          <input
            v-model="password"
            type="password"
            placeholder="••••••••"
            :class="{
              'input-valid': passwordMeta.dirty && passwordMeta.valid,
              'input-invalid': passwordMeta.dirty && !passwordMeta.valid
            }"
          />
          <p v-if="formErrors.password" class="field-error">{{ formErrors.password }}</p>
        </div>
        <p v-if="serverError" class="error-msg">{{ serverError }}</p>
        <button type="submit" class="btn btn-primary btn-block" style="margin-top: 8px">Log In</button>
      </form>
      <p class="auth-link">
        Don't have an account? <RouterLink to="/register">Register</RouterLink>
      </p>
    </div>
  </div>
</template>

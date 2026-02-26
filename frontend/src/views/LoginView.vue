<script setup lang="ts">
import { useForm, useField } from 'vee-validate'
import * as yup from 'yup'
import { useAuthStore } from '../stores/auth'
import { useAuthForm } from '../composables/useAuthForm'

const auth = useAuthStore()
const { serverError, submitAuthAction } = useAuthForm()

const schema = yup.object({
  email: yup.string().required('Email is required').email('Invalid email format'),
  password: yup.string().required('Password is required'),
})

const { handleSubmit, errors: formErrors } = useForm({ validationSchema: schema })

const { value: email, meta: emailMeta } = useField<string>('email', undefined, { validateOnValueUpdate: true })
const { value: password, meta: passwordMeta } = useField<string>('password', undefined, { validateOnValueUpdate: true })

const submit = handleSubmit((values) => {
  submitAuthAction(() => auth.login(values.email, values.password))
})
</script>

<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-orb"></div>
      <h1 class="auth-title">Wallet</h1>
      <p class="auth-tagline">Your money, beautifully tracked</p>
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

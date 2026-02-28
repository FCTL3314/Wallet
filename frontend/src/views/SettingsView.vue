<script setup lang="ts">
import { ref } from 'vue'
import { useForm, useField } from 'vee-validate'
import * as yup from 'yup'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '../stores/auth'
import { authApi } from '../api/auth'
import { getErrorMessage } from '../api/errors'
import BaseCard from '../components/BaseCard.vue'
import BaseButton from '../components/BaseButton.vue'

const auth = useAuthStore()
const { user } = storeToRefs(auth)

// ── Change Email ─────────────────────────────────────────────
const emailSchema = yup.object({
  currentPasswordForEmail: yup.string().required('Current password is required'),
  newEmail: yup.string().required('New email is required').email('Invalid email format'),
})

const { handleSubmit: handleEmailSubmit, errors: emailErrors, resetForm: resetEmailForm } = useForm({ validationSchema: emailSchema })
const { value: currentPasswordForEmail, meta: cpfeMeta } = useField<string>('currentPasswordForEmail', undefined, { validateOnValueUpdate: true })
const { value: newEmail, meta: newEmailMeta } = useField<string>('newEmail', undefined, { validateOnValueUpdate: true })

const emailServerError = ref('')
const emailSuccess = ref('')

const submitEmail = handleEmailSubmit(async (values) => {
  emailServerError.value = ''
  emailSuccess.value = ''
  try {
    const { data } = await authApi.changeEmail(values.currentPasswordForEmail, values.newEmail)
    auth.user = data
    emailSuccess.value = 'Email updated successfully.'
    resetEmailForm()
  } catch (err) {
    emailServerError.value = getErrorMessage(err)
  }
})

// ── Change Password ──────────────────────────────────────────
const passwordSchema = yup.object({
  currentPassword: yup.string().required('Current password is required'),
  newPassword: yup.string()
    .required('New password is required')
    .min(8, 'At least 8 characters')
    .matches(/[A-Z]/, 'At least one uppercase letter')
    .matches(/[a-z]/, 'At least one lowercase letter')
    .matches(/\d/, 'At least one digit (0–9)'),
  confirmNewPassword: yup.string()
    .required('Please confirm your password')
    .oneOf([yup.ref('newPassword')], 'Passwords do not match'),
})

const { handleSubmit: handlePasswordSubmit, errors: passwordErrors, resetForm: resetPasswordForm } = useForm({ validationSchema: passwordSchema })
const { value: currentPassword, meta: cpMeta } = useField<string>('currentPassword', undefined, { validateOnValueUpdate: true })
const { value: newPassword, meta: newPasswordMeta } = useField<string>('newPassword', undefined, { validateOnValueUpdate: true })
const { value: confirmNewPassword, meta: confirmMeta } = useField<string>('confirmNewPassword', undefined, { validateOnValueUpdate: true })

const passwordServerError = ref('')
const passwordSuccess = ref('')

const submitPassword = handlePasswordSubmit(async (values) => {
  passwordServerError.value = ''
  passwordSuccess.value = ''
  try {
    await authApi.changePassword(values.currentPassword, values.newPassword)
    passwordSuccess.value = 'Password updated successfully.'
    resetPasswordForm()
  } catch (err) {
    passwordServerError.value = getErrorMessage(err)
  }
})
</script>

<template>
  <h1 class="page-title">Settings</h1>

  <div class="settings-grid">
    <BaseCard title="Change Email">
      <p style="font-size: 0.875rem; color: var(--text-secondary); margin-bottom: 16px">
        Current email: <strong style="color: var(--text-primary)">{{ user?.email }}</strong>
      </p>
      <form @submit.prevent="submitEmail">
        <div class="form-group">
          <label>Current Password</label>
          <input
            v-model="currentPasswordForEmail"
            type="password"
            placeholder="••••••••"
            :class="{
              'input-valid': cpfeMeta.dirty && cpfeMeta.valid,
              'input-invalid': cpfeMeta.dirty && !cpfeMeta.valid,
            }"
          />
          <p v-if="emailErrors.currentPasswordForEmail" class="field-error">{{ emailErrors.currentPasswordForEmail }}</p>
        </div>
        <div class="form-group">
          <label>New Email</label>
          <input
            v-model="newEmail"
            type="email"
            placeholder="new@example.com"
            :class="{
              'input-valid': newEmailMeta.dirty && newEmailMeta.valid,
              'input-invalid': newEmailMeta.dirty && !newEmailMeta.valid,
            }"
          />
          <p v-if="emailErrors.newEmail" class="field-error">{{ emailErrors.newEmail }}</p>
        </div>
        <p v-if="emailServerError" class="error-msg">{{ emailServerError }}</p>
        <p v-if="emailSuccess" class="success-msg">{{ emailSuccess }}</p>
        <BaseButton type="submit" variant="primary" style="margin-top: 4px">Update Email</BaseButton>
      </form>
    </BaseCard>

    <BaseCard title="Change Password">
      <form @submit.prevent="submitPassword">
        <div class="form-group">
          <label>Current Password</label>
          <input
            v-model="currentPassword"
            type="password"
            placeholder="••••••••"
            :class="{
              'input-valid': cpMeta.dirty && cpMeta.valid,
              'input-invalid': cpMeta.dirty && !cpMeta.valid,
            }"
          />
          <p v-if="passwordErrors.currentPassword" class="field-error">{{ passwordErrors.currentPassword }}</p>
        </div>
        <div class="form-group">
          <label>New Password</label>
          <input
            v-model="newPassword"
            type="password"
            placeholder="••••••••"
            :class="{
              'input-valid': newPasswordMeta.dirty && newPasswordMeta.valid,
              'input-invalid': newPasswordMeta.dirty && !newPasswordMeta.valid,
            }"
          />
          <p v-if="passwordErrors.newPassword" class="field-error">{{ passwordErrors.newPassword }}</p>
          <div class="password-requirements" v-if="newPassword">
            <div :class="['req-item', newPassword.length >= 8 ? 'req-met' : 'req-unmet']">
              <span class="req-icon">{{ newPassword.length >= 8 ? '✓' : '✗' }}</span>
              At least 8 characters
            </div>
            <div :class="['req-item', /[A-Z]/.test(newPassword) ? 'req-met' : 'req-unmet']">
              <span class="req-icon">{{ /[A-Z]/.test(newPassword) ? '✓' : '✗' }}</span>
              Uppercase letter (A–Z)
            </div>
            <div :class="['req-item', /[a-z]/.test(newPassword) ? 'req-met' : 'req-unmet']">
              <span class="req-icon">{{ /[a-z]/.test(newPassword) ? '✓' : '✗' }}</span>
              Lowercase letter (a–z)
            </div>
            <div :class="['req-item', /\d/.test(newPassword) ? 'req-met' : 'req-unmet']">
              <span class="req-icon">{{ /\d/.test(newPassword) ? '✓' : '✗' }}</span>
              At least one digit (0–9)
            </div>
          </div>
        </div>
        <div class="form-group">
          <label>Confirm New Password</label>
          <input
            v-model="confirmNewPassword"
            type="password"
            placeholder="••••••••"
            :class="{
              'input-valid': confirmMeta.dirty && confirmMeta.valid,
              'input-invalid': confirmMeta.dirty && !confirmMeta.valid,
            }"
          />
          <p v-if="passwordErrors.confirmNewPassword" class="field-error">{{ passwordErrors.confirmNewPassword }}</p>
        </div>
        <p v-if="passwordServerError" class="error-msg">{{ passwordServerError }}</p>
        <p v-if="passwordSuccess" class="success-msg">{{ passwordSuccess }}</p>
        <BaseButton type="submit" variant="primary" style="margin-top: 4px">Update Password</BaseButton>
      </form>
    </BaseCard>
  </div>
</template>

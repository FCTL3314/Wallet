<script setup lang="ts">
import { ref } from 'vue'
import { useForm, useField } from 'vee-validate'
import * as yup from 'yup'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '../stores/auth'
import { useThemeStore, ACCENT_PRESETS, type AccentKey } from '../stores/theme'
import { useOnboardingStore } from '../stores/onboarding'
import { authApi } from '../api/auth'
import { getErrorMessage } from '../api/errors'
import BaseCard from '../components/BaseCard.vue'
import BaseButton from '../components/BaseButton.vue'
import PasswordRequirements from '../components/PasswordRequirements.vue'
import { PhBookOpen } from '@phosphor-icons/vue'

const auth = useAuthStore()
const { user } = storeToRefs(auth)

const onboarding = useOnboardingStore()

function replayGuide() {
  onboarding.reset()
  onboarding.start()
}

const themeStore = useThemeStore()
const { mode: themeMode, accent: themeAccent } = storeToRefs(themeStore)

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
  <div class="page-sections page-narrow">
  <BaseCard title="Appearance" style="align-self: flex-start; min-width: 420px">
    <div class="appearance-section">
      <div class="appearance-row">
        <span class="appearance-label">Theme</span>
        <div class="theme-segmented">
          <button
            :class="['theme-btn', { 'theme-btn--active': themeMode === 'light' }]"
            @click="themeStore.setMode('light')"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
            Light
          </button>
          <button
            :class="['theme-btn', { 'theme-btn--active': themeMode === 'dark' }]"
            @click="themeStore.setMode('dark')"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
            Dark
          </button>
        </div>
      </div>
      <div class="appearance-row">
        <span class="appearance-label">Accent Color</span>
        <div class="accent-swatches">
          <button
            v-for="(preset, key) in ACCENT_PRESETS"
            :key="key"
            class="accent-swatch"
            :class="{ 'accent-swatch--active': themeAccent === key }"
            :style="{ background: preset.main }"
            :title="preset.label"
            @click="themeStore.setAccent(key as AccentKey)"
          />
        </div>
      </div>
    </div>
  </BaseCard>

  <BaseCard title="Onboarding Guide" style="align-self: flex-start; min-width: 420px">
    <div class="guide-section">
      <p class="guide-desc">Replay the interactive guide to learn about all app features.</p>
      <BaseButton variant="secondary" @click="replayGuide">
        <PhBookOpen :size="16" weight="duotone" /> Replay Guide
      </BaseButton>
    </div>
  </BaseCard>

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
          <PasswordRequirements :password="newPassword ?? ''" />
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
  </div>
</template>

<style scoped>
/* ── Appearance section ─────────────────────────────────── */

.appearance-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.appearance-row {
  display: flex;
  align-items: center;
  gap: 24px;
}

.appearance-label {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-secondary);
  width: 100px;
  flex-shrink: 0;
}

/* Theme segmented control */

.theme-segmented {
  display: flex;
  background: rgba(0, 0, 0, 0.05);
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 12px;
  padding: 3px;
  gap: 2px;
}

[data-theme="dark"] .theme-segmented {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.08);
}

.theme-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 9px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-family: var(--font-body);
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.18s var(--ease-smooth);
}

.theme-btn:hover {
  color: var(--text-primary);
}

.theme-btn--active {
  background: var(--card-bg);
  color: var(--color-accent);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.10);
}

[data-theme="dark"] .theme-btn--active {
  background: rgba(255, 255, 255, 0.10);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.30);
}

/* Accent color swatches */

.accent-swatches {
  display: flex;
  gap: 8px;
}

.accent-swatch {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 2px solid transparent;
  cursor: pointer;
  transition: transform 0.18s var(--ease-spring), box-shadow 0.18s;
  outline: none;
  padding: 0;
}

.accent-swatch:hover {
  transform: scale(1.15);
}

.accent-swatch--active {
  /* card-bg gap ring + subtle outer border */
  box-shadow: 0 0 0 2px var(--card-bg), 0 0 0 4px rgba(0, 0, 0, 0.30);
  transform: scale(1.12);
}

[data-theme="dark"] .accent-swatch--active {
  box-shadow: 0 0 0 2px var(--card-bg), 0 0 0 4px rgba(255, 255, 255, 0.40);
}

/* ── Guide section ──────────────────────────────────────── */

.guide-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.guide-desc {
  font-size: 0.875rem;
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.5;
}
</style>

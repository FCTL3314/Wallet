<script setup lang="ts">
import { ref } from 'vue'
import { useForm, useField } from 'vee-validate'
import * as yup from 'yup'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '../stores/auth'
import { useOnboardingStore } from '../stores/onboarding'
import { authApi } from '../api/auth'
import { getErrorMessage } from '../api/errors'
import BaseCard from '../components/BaseCard.vue'
import BaseButton from '../components/BaseButton.vue'
import PasswordRequirements from '../components/PasswordRequirements.vue'
import ThemeToggle from '../components/ThemeToggle.vue'
import AccentPicker from '../components/AccentPicker.vue'
import { PhBookOpen, PhFileXls } from '@phosphor-icons/vue'
import { reportsApi } from '../api/reports'

const auth = useAuthStore()
const { user } = storeToRefs(auth)

const onboarding = useOnboardingStore()

function replayGuide() {
  onboarding.reset()
  onboarding.start()
}

type SettingsTab = 'email' | 'password' | 'appearance' | 'data'
const activeTab = ref<SettingsTab>('email')
const TABS: { id: SettingsTab; label: string }[] = [
  { id: 'email', label: 'Change email' },
  { id: 'password', label: 'Password' },
  { id: 'appearance', label: 'Appearance' },
  { id: 'data', label: 'Data' },
]

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

// ── Data Export ──────────────────────────────────────────────
const exportLoading = ref(false)
const exportError = ref('')
const exportSuccess = ref('')

async function requestExport() {
  exportLoading.value = true
  exportError.value = ''
  exportSuccess.value = ''
  try {
    const { data } = await reportsApi.requestExport()
    await pollUntilReady(data.job_id)
  } catch (err) {
    exportError.value = getErrorMessage(err)
  } finally {
    exportLoading.value = false
  }
}

async function pollUntilReady(jobId: string) {
  for (let i = 0; i < 60; i++) {
    await new Promise((r) => setTimeout(r, 2000))
    const { data } = await reportsApi.getStatus(jobId)
    if (data.status === 'ready') {
      await triggerDownload(jobId)
      exportSuccess.value = 'Export ready — downloading…'
      setTimeout(() => { exportSuccess.value = '' }, 3000)
      return
    }
  }
  throw new Error('Export timed out. Please try again.')
}

async function triggerDownload(jobId: string) {
  const response = await reportsApi.downloadExport(jobId)
  const url = URL.createObjectURL(new Blob([response.data]))
  const a = document.createElement('a')
  a.href = url
  a.download = `wallet-export-${jobId}.xlsx`
  a.click()
  URL.revokeObjectURL(url)
}

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
  <div class="sections page-narrow">

  <BaseCard class="settings-tabs-card">
    <div class="segmented settings-tabs">
      <button
        v-for="t in TABS"
        :key="t.id"
        :class="{ on: activeTab === t.id }"
        @click="activeTab = t.id"
      >{{ t.label }}</button>
    </div>
  </BaseCard>

  <template v-if="activeTab === 'appearance'">
  <BaseCard title="Appearance">
    <div class="appearance-section">
      <div class="appearance-row">
        <div class="appearance-row-text">
          <span class="appearance-label">Theme</span>
          <span class="appearance-hint">Light or dark surface tones.</span>
        </div>
        <ThemeToggle />
      </div>
      <div class="appearance-row">
        <div class="appearance-row-text">
          <span class="appearance-label">Accent</span>
          <span class="appearance-hint">The brand hue used for primary actions and highlights.</span>
        </div>
        <AccentPicker />
      </div>
    </div>
  </BaseCard>

  </template>

  <template v-if="activeTab === 'data'">
  <BaseCard title="Onboarding Guide">
    <div class="guide-section">
      <p class="guide-desc">Replay the interactive guide to learn about all app features.</p>
      <BaseButton variant="secondary" @click="replayGuide">
        <PhBookOpen :size="16" weight="duotone" /> Replay Guide
      </BaseButton>
    </div>
  </BaseCard>

  <BaseCard title="Data Export">
    <div class="export-section">
      <p class="export-desc">Export all your transactions and balance snapshots to an Excel file.</p>
      <div class="export-actions">
        <BaseButton variant="primary" :disabled="exportLoading" @click="requestExport">
          <PhFileXls :size="16" weight="duotone" />
          {{ exportLoading ? 'Generating…' : 'Export to Excel' }}
        </BaseButton>
        <p v-if="exportError" class="error-msg">{{ exportError }}</p>
        <p v-if="exportSuccess" class="success-msg">{{ exportSuccess }}</p>
      </div>
    </div>
  </BaseCard>

  </template>

  <template v-if="activeTab === 'email'">
  <div class="settings-single">
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

  </div>
  </template>

  <template v-if="activeTab === 'password'">
  <div class="settings-single">
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
  </template>
  </div>
</template>

<style scoped>
.settings-tabs-card { padding: 14px 16px; }
.settings-tabs { flex-wrap: nowrap; overflow-x: auto; max-width: 100%; }
.settings-single { display: flex; flex-direction: column; gap: var(--gap-section); }
.settings-single .card { max-width: 560px; }

/* ── Appearance section ─────────────────────────────────── */

.appearance-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.appearance-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 14px 16px;
  background: var(--surface-2);
  border-radius: 14px;
}

.appearance-row-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.appearance-label {
  font-weight: 500;
  color: var(--ink);
}

.appearance-hint {
  font-size: 12px;
  color: var(--ink-3);
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

/* ── Export section ─────────────────────────────────────── */

.export-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.export-desc {
  font-size: 0.875rem;
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.5;
}

.export-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 10px;
}
</style>

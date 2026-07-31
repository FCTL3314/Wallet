<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useForm, useField } from 'vee-validate'
import * as yup from 'yup'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '../stores/auth'
import { useOnboardingStore } from '../stores/onboarding'
import { useReferencesStore } from '../stores/references'
import { authApi } from '../api/auth'
import { getErrorMessage } from '../api/errors'
import BaseCard from '../components/BaseCard.vue'
import BaseButton from '../components/BaseButton.vue'
import PasswordRequirements from '../components/PasswordRequirements.vue'
import ThemeToggle from '../components/ThemeToggle.vue'
import AccentPicker from '../components/AccentPicker.vue'
import { PhBookOpen, PhFileXls, PhX } from '@phosphor-icons/vue'
import { reportsApi } from '../api/reports'

const auth = useAuthStore()
const { user } = storeToRefs(auth)
const refs = useReferencesStore()

const onboarding = useOnboardingStore()

function replayGuide() {
  onboarding.reset()
  onboarding.start()
}

type SettingsTab = 'general' | 'data' | 'account' | 'help'

const TABS: { id: SettingsTab; label: string }[] = [
  { id: 'general', label: 'General' },
  { id: 'data', label: 'Data' },
  { id: 'account', label: 'Account' },
  { id: 'help', label: 'Help' },
]
const DEFAULT_TAB: SettingsTab = 'general'

const route = useRoute()
const router = useRouter()

function isSettingsTab(value: unknown): value is SettingsTab {
  return TABS.some((tab) => tab.id === value)
}

const activeTab = computed<SettingsTab>({
  get: () => (isSettingsTab(route.query.tab) ? route.query.tab : DEFAULT_TAB),
  set: (value) => {
    router.replace({ query: { ...route.query, tab: value } })
  },
})

const baseCurrencyCode = computed(() => user.value?.base_currency_code ?? 'USD')
const baseCurrencySaving = ref(false)

async function changeBaseCurrency(code: string) {
  if (code === baseCurrencyCode.value) return
  baseCurrencySaving.value = true
  try {
    await auth.updateBaseCurrency(code)
  } finally {
    baseCurrencySaving.value = false
  }
}

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

const EXPORT_POLL_INTERVAL_MS = 2000
const EXPORT_TIMEOUT_MS = 120_000
const EXPORT_TICK_MS = 500

type ExportPhase = 'idle' | 'preparing' | 'downloading' | 'done' | 'cancelled' | 'timeout' | 'failed'

interface ExportRun {
  cancelled: boolean
  ticker: ReturnType<typeof setInterval> | null
}

const exportPhase = ref<ExportPhase>('idle')
const exportElapsedMs = ref(0)
const exportMessage = ref('')

let activeExportRun: ExportRun | null = null

const exportRunning = computed(
  () => exportPhase.value === 'preparing' || exportPhase.value === 'downloading'
)
const exportElapsedSeconds = computed(() => Math.floor(exportElapsedMs.value / 1000))
const exportTimeoutSeconds = Math.round(EXPORT_TIMEOUT_MS / 1000)
const exportProgress = computed(() =>
  Math.min(100, Math.round((exportElapsedMs.value / EXPORT_TIMEOUT_MS) * 100))
)
const exportStatusText = computed(() =>
  exportPhase.value === 'downloading'
    ? 'Report ready — downloading the file…'
    : 'Generating your report…'
)

function stopTicker(run: ExportRun) {
  if (run.ticker !== null) {
    clearInterval(run.ticker)
    run.ticker = null
  }
}

function wait(ms: number) {
  return new Promise<void>((resolve) => setTimeout(resolve, ms))
}

async function requestExport() {
  if (exportRunning.value) return

  const run: ExportRun = { cancelled: false, ticker: null }
  activeExportRun = run
  exportPhase.value = 'preparing'
  exportMessage.value = ''
  exportElapsedMs.value = 0

  const startedAt = Date.now()
  run.ticker = setInterval(() => {
    exportElapsedMs.value = Date.now() - startedAt
  }, EXPORT_TICK_MS)

  try {
    const { data: job } = await reportsApi.requestExport()
    if (run.cancelled) return

    while (Date.now() - startedAt < EXPORT_TIMEOUT_MS) {
      const { data: status } = await reportsApi.getStatus(job.job_id)
      if (run.cancelled) return

      if (status.status === 'ready') {
        exportPhase.value = 'downloading'
        await triggerDownload(job.job_id)
        if (run.cancelled) return
        exportPhase.value = 'done'
        exportMessage.value = 'Your Excel file has been downloaded.'
        return
      }

      await wait(EXPORT_POLL_INTERVAL_MS)
      if (run.cancelled) return
    }

    exportPhase.value = 'timeout'
    exportMessage.value = `The report is still being generated after ${exportTimeoutSeconds} seconds. It may finish on its own — start the export again in a minute.`
  } catch (err) {
    if (run.cancelled) return
    exportPhase.value = 'failed'
    exportMessage.value = `Export failed: ${getErrorMessage(err)}`
  } finally {
    stopTicker(run)
    if (activeExportRun === run) activeExportRun = null
  }
}

function cancelExport() {
  const run = activeExportRun
  if (!run) return
  run.cancelled = true
  stopTicker(run)
  activeExportRun = null
  exportPhase.value = 'cancelled'
  exportMessage.value = 'Export cancelled. The file was not downloaded.'
}

onBeforeUnmount(() => {
  if (!activeExportRun) return
  activeExportRun.cancelled = true
  stopTicker(activeExportRun)
  activeExportRun = null
})

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
    <div class="segmented settings-tabs" role="group" aria-label="Settings sections">
      <button
        v-for="t in TABS"
        :key="t.id"
        type="button"
        :class="{ on: activeTab === t.id }"
        :aria-current="activeTab === t.id ? 'page' : undefined"
        @click="activeTab = t.id"
      >{{ t.label }}</button>
    </div>
  </BaseCard>

  <template v-if="activeTab === 'general'">
  <BaseCard title="Preferences">
    <div class="appearance-section">
      <div class="appearance-row">
        <div class="appearance-row-text">
          <label class="appearance-label" for="base-currency">Base currency</label>
          <span class="appearance-hint">Every amount on the dashboard is converted to this currency.</span>
        </div>
        <select
          id="base-currency"
          class="form-input-sm base-currency-select"
          :value="baseCurrencyCode"
          :disabled="baseCurrencySaving"
          @change="changeBaseCurrency(($event.target as HTMLSelectElement).value)"
        >
          <option v-if="!refs.currencies.length" :value="baseCurrencyCode">{{ baseCurrencyCode }}</option>
          <option v-for="c in refs.currencies" :key="c.code" :value="c.code">
            {{ c.code }}<template v-if="c.name"> — {{ c.name }}</template>
          </option>
        </select>
      </div>
    </div>
  </BaseCard>

  <BaseCard title="Appearance">
    <div class="appearance-section">
      <div class="appearance-row">
        <div class="appearance-row-text">
          <span class="appearance-label">Theme</span>
          <span class="appearance-hint">Light, dark, or follow your device setting.</span>
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
  <BaseCard title="Data Export">
    <div class="export-section">
      <p class="export-desc">Export all your transactions and balance snapshots to an Excel file.</p>
      <div class="export-actions">
        <div class="export-buttons">
          <BaseButton variant="primary" :loading="exportRunning" :disabled="exportRunning" @click="requestExport">
            <PhFileXls :size="16" weight="duotone" />
            {{ exportRunning ? 'Generating…' : 'Export to Excel' }}
          </BaseButton>
          <BaseButton v-if="exportRunning" variant="secondary" @click="cancelExport">
            <PhX :size="16" weight="bold" /> Cancel
          </BaseButton>
        </div>

        <div v-if="exportRunning" class="export-progress">
          <div
            class="export-progress-track"
            role="progressbar"
            aria-label="Export progress"
            :aria-valuenow="exportProgress"
            aria-valuemin="0"
            aria-valuemax="100"
            :aria-valuetext="`${exportElapsedSeconds} of ${exportTimeoutSeconds} seconds elapsed`"
          >
            <div class="export-progress-bar" :style="{ width: `${exportProgress}%` }" />
          </div>
          <p class="export-status" aria-live="polite">
            {{ exportStatusText }}
            <span class="export-elapsed">{{ exportElapsedSeconds }}s / {{ exportTimeoutSeconds }}s</span>
          </p>
        </div>

        <p v-if="exportPhase === 'done'" class="success-msg" role="status">{{ exportMessage }}</p>
        <p v-else-if="exportPhase === 'cancelled'" class="export-note" role="status">{{ exportMessage }}</p>
        <p v-else-if="exportPhase === 'timeout' || exportPhase === 'failed'" class="error-msg" role="alert">{{ exportMessage }}</p>
      </div>
    </div>
  </BaseCard>

  </template>

  <template v-if="activeTab === 'help'">
  <BaseCard title="Onboarding Guide">
    <div class="guide-section">
      <p class="guide-desc">Replay the interactive guide to learn about all app features.</p>
      <BaseButton variant="secondary" @click="replayGuide">
        <PhBookOpen :size="16" weight="duotone" /> Replay Guide
      </BaseButton>
    </div>
  </BaseCard>

  </template>

  <template v-if="activeTab === 'account'">
  <div class="settings-single">
    <BaseCard title="Change Email">
      <p class="current-email">
        Current email: <strong>{{ user?.email }}</strong>
      </p>
      <form @submit.prevent="submitEmail">
        <div class="form-group">
          <label for="email-current-password">Current Password</label>
          <input
            id="email-current-password"
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
          <label for="new-email">New Email</label>
          <input
            id="new-email"
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
        <p v-if="emailServerError" class="error-msg" role="alert">{{ emailServerError }}</p>
        <p v-if="emailSuccess" class="success-msg" role="status">{{ emailSuccess }}</p>
        <BaseButton type="submit" variant="primary" class="form-submit">Update Email</BaseButton>
      </form>
    </BaseCard>

    <BaseCard title="Change Password">
      <form @submit.prevent="submitPassword">
        <div class="form-group">
          <label for="current-password">Current Password</label>
          <input
            id="current-password"
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
          <label for="new-password">New Password</label>
          <input
            id="new-password"
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
          <label for="confirm-new-password">Confirm New Password</label>
          <input
            id="confirm-new-password"
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
        <p v-if="passwordServerError" class="error-msg" role="alert">{{ passwordServerError }}</p>
        <p v-if="passwordSuccess" class="success-msg" role="status">{{ passwordSuccess }}</p>
        <BaseButton type="submit" variant="primary" class="form-submit">Update Password</BaseButton>
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
  width: 100%;
}

.export-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.export-progress {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
  max-width: 420px;
}

.export-progress-track {
  height: 6px;
  width: 100%;
  border-radius: 999px;
  background: var(--surface-2);
  overflow: hidden;
}

.export-progress-bar {
  height: 100%;
  border-radius: 999px;
  background: var(--accent);
  transition: width var(--t-fast) var(--ease);
}

.export-status {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0;
  font-size: 13px;
  color: var(--text-secondary);
}

.export-elapsed {
  color: var(--ink-3);
  font-variant-numeric: tabular-nums;
}

.export-note {
  margin: 0;
  font-size: 13px;
  color: var(--text-secondary);
}

/* ── Account forms ──────────────────────────────────────── */

.current-email {
  font-size: 0.875rem;
  color: var(--text-secondary);
  margin-bottom: 16px;
}

.current-email strong {
  color: var(--text-primary);
}

.form-submit {
  margin-top: 4px;
}

.base-currency-select {
  min-width: 180px;
}
</style>

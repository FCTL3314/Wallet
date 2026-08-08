<script setup lang="ts">
import { ref, computed, useTemplateRef, onMounted, watch } from 'vue'
import { balanceSnapshotsApi, type BalanceSnapshot, type BalanceSnapshotCreate } from '../api/balanceSnapshots'
import {
  analyticsApi,
  type BalanceByStorageEntry,
  type BalanceByStorageAccount,
  type BalanceBreakdownItem,
  type GroupBy,
  type SnapshotTimelineEntry,
} from '../api/analytics'
import { useReferencesStore } from '../stores/references'
import { fmtAmount, fmtMoney, fmtPeriod, fmtSignedMoney, localDateStr } from '../utils/format'
import { useCrudModal } from '../composables/useCrudModal'
import { useDateRange } from '../composables/useDateRange'
import BaseModal from '../components/BaseModal.vue'
import BaseDataTable from '../components/BaseDataTable.vue'
import BaseCard from '../components/BaseCard.vue'
import BaseStatCard from '../components/BaseStatCard.vue'
import GrowthBadge from '../components/GrowthBadge.vue'
import BaseButton from '../components/BaseButton.vue'
import EditDeleteActions from '../components/EditDeleteActions.vue'
import PeriodFilterBar from '../components/PeriodFilterBar.vue'
import { useSuccessAnimation } from '../composables/useSuccessAnimation'
import { PhWallet, PhCaretDown, PhPlus } from '@phosphor-icons/vue'
import { storageLocationsApi, storageAccountsApi } from '../api/references'

const HINT_TOTAL_BALANCE =
  'The most recent snapshot of every account, summed per currency. Accounts you have not re-snapshotted keep their last recorded amount, so this is your latest known position rather than a live balance.'

const refs = useReferencesStore()
const { spawn } = useSuccessAnimation()
const addBtnRef = useTemplateRef<HTMLElement>('addBtn')
const storageData = ref<BalanceByStorageEntry[]>([])
const timeline = ref<SnapshotTimelineEntry[]>([])
const latestByAccount = ref<BalanceBreakdownItem[]>([])
const currentTotals = ref<Record<string, number>>({})
const loading = ref(false)

const allCurrencies = computed(() => {
  const seen = new Set<string>()
  for (const row of storageData.value) {
    for (const cur of Object.keys(row.totals)) seen.add(cur)
  }
  return [...seen]
})

const allAccounts = computed(() => {
  const map = new Map<string, BalanceByStorageAccount>()
  for (const row of storageData.value) {
    for (const acc of row.accounts) {
      if (!map.has(acc.name)) map.set(acc.name, acc)
    }
  }
  return [...map.values()]
})

function accountCell(row: BalanceByStorageEntry, name: string): string {
  const acc = row.accounts.find(a => a.name === name)
  if (!acc) return '—'
  return fmtMoney(acc.amount, acc.currency)
}

const groupBy = ref<GroupBy>('month')
const { dateFrom, dateTo, activePreset, allRange, initRange } = useDateRange('YTD')

// A snapshot records what an account holds. Zero is a real balance and a credit
// card is legitimately negative, so the only thing to reject here is a non-number.
const formErrors = computed(() => ({
  amount: Number.isFinite(form.value.amount) ? null : 'Enter an amount',
}))

const amountFieldLabel = computed(() => {
  const code = accountCurrency(form.value.storage_account_id)
  return code ? `Amount (${code})` : 'Amount'
})

const {
  showModal,
  editing,
  removingId,
  touchedFields,
  form,
  openCreate: crudOpenCreate,
  openEdit,
  save: crudSave,
  remove: crudRemove,
} = useCrudModal<BalanceSnapshot, BalanceSnapshotCreate>({
  defaultForm: () => ({
    storage_account_id: refs.storageAccounts[0]?.id || 0,
    date: localDateStr(),
    amount: 0,
  }),
  toForm: (snap) => ({
    storage_account_id: snap.storage_account_id,
    date: snap.date,
    amount: snap.amount,
  }),
  onCreate: async (data) => {
    const { data: result } = await balanceSnapshotsApi.create(data)
    return result as BalanceSnapshot
  },
  onUpdate: async (id, data) => {
    const { data: result } = await balanceSnapshotsApi.update(id, data)
    return result as BalanceSnapshot
  },
  onDelete: async (id) => {
    await balanceSnapshotsApi.delete(id)
  },
  afterSave: async (isCreate) => {
    await load()
    if (isCreate && addBtnRef.value) {
      const rect = addBtnRef.value.getBoundingClientRect()
      spawn({ x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 })
    }
  },
  afterDelete: () => load(),
})

const openTimelineDates = ref<Set<string>>(new Set())

function toggleTimelineDate(d: string) {
  const s = new Set(openTimelineDates.value)
  s.has(d) ? s.delete(d) : s.add(d)
  openTimelineDates.value = s
}

// The row carries everything the edit form needs, so reopening a snapshot costs
// no extra request. Rows whose amount was carried forward have no id and are not
// editable from here — there is nothing recorded on this date to edit.
function snapshotOf(entryDate: string, row: SnapshotTimelineEntry['rows'][number]): BalanceSnapshot | null {
  if (row.snapshot_id === null) return null
  return {
    id: row.snapshot_id,
    storage_account_id: row.account_id,
    date: entryDate,
    amount: row.amount,
  }
}

function dateParts(d: string): { day: string; month: string; year: string } {
  const dt = new Date(d)
  return {
    day: String(dt.getDate()),
    month: dt.toLocaleString('en-US', { month: 'short' }),
    year: String(dt.getFullYear()),
  }
}

function accountCurrency(accountId: number): string {
  const acc = refs.storageAccounts.find((a) => a.id === accountId)
  if (!acc) return ''
  return refs.currencyById(acc.currency_id)?.code ?? ''
}

interface LocationCard {
  id: number
  name: string
  accounts: { id: number; ccy: string; name: string; latest: number }[]
}

// Latest amounts come from /analytics/balance-breakdown rather than being picked
// out of the raw snapshot list here: the backend already decides which snapshot
// counts as "latest", and re-deciding it in the browser is how this page and the
// dashboard drifted apart.
const latestAmounts = computed(
  () => new Map(latestByAccount.value.map((b) => [b.account_id, b.latest_snapshot_amount])),
)

function latestAmountForAccount(accountId: number): number {
  return latestAmounts.value.get(accountId) ?? 0
}

const locationCards = computed<LocationCard[]>(() =>
  refs.storageLocations.map((loc) => {
    const accounts = refs.storageAccounts
      .filter((a) => a.storage_location_id === loc.id)
      .map((a) => {
        const cur = refs.currencyById(a.currency_id)
        return {
          id: a.id,
          ccy: cur?.code ?? '?',
          name: cur?.name ?? cur?.code ?? '?',
          latest: latestAmountForAccount(a.id),
        }
      })
    return { id: loc.id, name: loc.name, accounts }
  }),
)

const newLocationName = ref('')
const showNewLocationDialog = ref(false)

async function createLocation() {
  const name = newLocationName.value.trim()
  if (!name) return
  await storageLocationsApi.create({ name })
  newLocationName.value = ''
  showNewLocationDialog.value = false
  await refs.fetchAll()
}

const showNewAccountDialog = ref(false)
const newAccountLocationId = ref<number | null>(null)
const newAccountCurrencyId = ref<number | null>(null)

const newAccountLocationName = computed(
  () => refs.storageLocations.find((l) => l.id === newAccountLocationId.value)?.name ?? '',
)

const availableCurrenciesForNewAccount = computed(() => {
  const taken = new Set(
    refs.storageAccounts
      .filter((a) => a.storage_location_id === newAccountLocationId.value)
      .map((a) => a.currency_id),
  )
  return refs.currencies.filter((c) => !taken.has(c.id))
})

function openNewAccount(locationId: number) {
  newAccountLocationId.value = locationId
  newAccountCurrencyId.value = null
  showNewAccountDialog.value = true
}

async function createAccount() {
  const locationId = newAccountLocationId.value
  const currencyId = newAccountCurrencyId.value
  if (!locationId || !currencyId) return
  await storageAccountsApi.create({ storage_location_id: locationId, currency_id: currencyId })
  showNewAccountDialog.value = false
  await refs.fetchAll()
}

const distinctSnapshotDates = computed(() => timeline.value.length)
const totalKpiCount = computed(() =>
  timeline.value.reduce((sum, entry) => sum + entry.captured_count, 0),
)

const totalEntries = computed(() =>
  Object.entries(currentTotals.value)
    .map(([code, amount]) => ({ code, amount }))
    .sort((a, b) => b.amount - a.amount),
)

function openCreate() {
  crudOpenCreate()
  form.value.amount = latestAmountForAccount(form.value.storage_account_id)
}

watch(() => form.value.storage_account_id, (accountId) => {
  if (!editing.value) {
    form.value.amount = latestAmountForAccount(accountId)
  }
})

async function save() {
  if (formErrors.value.amount) {
    touchedFields.value = new Set([...touchedFields.value, 'amount'])
    return
  }
  await crudSave()
}

async function load() {
  loading.value = true
  try {
    const [byStorage, snapshotTimeline, breakdown] = await Promise.all([
      analyticsApi.balanceByStorage({
        date_from: dateFrom.value, date_to: dateTo.value, group_by: groupBy.value,
      }),
      analyticsApi.snapshotTimeline({ date_from: dateFrom.value, date_to: dateTo.value }),
      analyticsApi.balanceBreakdown(),
    ])
    storageData.value = byStorage.data
    timeline.value = snapshotTimeline.data
    latestByAccount.value = breakdown.data.accounts
    currentTotals.value = breakdown.data.totals
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  load()
  initRange()
})
watch([dateFrom, dateTo, groupBy], load)
</script>

<template>
  <div class="sections">
  <BaseCard>
    <PeriodFilterBar
      v-model:dateFrom="dateFrom"
      v-model:dateTo="dateTo"
      v-model:groupBy="groupBy"
      v-model:activePreset="activePreset"
      :allRange="allRange"
    >
      <div ref="addBtn" data-onboarding="add-snapshot-btn"><BaseButton variant="primary" size="sm" @click="openCreate">+ Add Snapshot</BaseButton></div>
    </PeriodFilterBar>
  </BaseCard>

  <div class="kpis">
    <BaseStatCard label="Total balance" variant="profit" :hint="HINT_TOTAL_BALANCE">
      <template v-if="!totalEntries.length">
        <div class="stat-value">—</div>
      </template>
      <template v-else-if="totalEntries.length === 1">
        <div class="stat-value">
          <span class="stat-currency">{{ totalEntries[0]?.code }}</span>{{ fmtAmount(totalEntries[0]?.amount ?? 0) }}
        </div>
      </template>
      <template v-else>
        <div class="totals-list">
          <div v-for="entry in totalEntries" :key="entry.code" class="totals-row">
            <span class="totals-code">{{ entry.code }}</span>
            <span class="num totals-amount">{{ fmtAmount(entry.amount) }}</span>
          </div>
        </div>
      </template>
    </BaseStatCard>
    <BaseStatCard label="Locations">
      <div class="stat-value">{{ refs.storageLocations.length }}</div>
      <div class="stat-foot"><span class="muted">{{ refs.storageAccounts.length }} accounts</span></div>
    </BaseStatCard>
    <BaseStatCard label="Snapshot sets">
      <div class="stat-value">{{ distinctSnapshotDates }}</div>
      <div class="stat-foot"><span class="muted">{{ totalKpiCount }} rows total</span></div>
    </BaseStatCard>
  </div>

  <div class="locations-grid">
    <div v-for="loc in locationCards" :key="loc.id" class="card location-card">
      <div class="row-between location-card-head">
        <div class="row">
          <span class="location-icon"><PhWallet :size="16" weight="duotone" /></span>
          <span class="location-name">{{ loc.name }}</span>
        </div>
      </div>
      <div class="stack location-accounts">
        <div v-if="!loc.accounts.length" class="muted location-empty">No accounts yet</div>
        <div v-for="acc in loc.accounts" :key="acc.id" class="row-between location-acc-row">
          <span class="muted">{{ acc.name }}</span>
          <span class="num location-acc-val">{{ fmtMoney(acc.latest, acc.ccy) }}</span>
        </div>
      </div>
      <button
        type="button"
        class="location-add-acc"
        :aria-label="`Add an account to ${loc.name}`"
        @click="openNewAccount(loc.id)"
      >
        <PhPlus :size="13" weight="bold" />
        <span>Add account</span>
      </button>
    </div>
    <button
      class="card location-add"
      type="button"
      @click="showNewLocationDialog = true"
    >
      <PhPlus :size="18" weight="bold" />
      <span>New location</span>
    </button>
  </div>

  <BaseDataTable title="Balances by Storage" :loading="loading" :empty="!storageData.length" empty-message="No balance data for selected period.">
    <template #head>
      <tr>
        <th>Period</th>
        <th v-for="cur in allCurrencies" :key="cur" class="col-num">{{ cur }} Total</th>
        <th v-for="acc in allAccounts" :key="acc.name" class="col-num">{{ acc.name }}</th>
      </tr>
    </template>
    <template #body>
      <tr
        v-for="(row, index) in storageData"
        :key="row.period"
        class="table-row"
        :style="{ '--i': String(Math.min(index, 15)) }"
      >
        <td>{{ fmtPeriod(row.period, groupBy) }}</td>
        <td v-for="cur in allCurrencies" :key="cur" class="col-num">
          <template v-if="row.totals[cur] != null">{{ fmtMoney(row.totals[cur], cur) }}</template>
          <template v-else>—</template>
        </td>
        <td v-for="col in allAccounts" :key="col.name" class="col-num">{{ accountCell(row, col.name) }}</td>
      </tr>
    </template>
  </BaseDataTable>

  <BaseCard v-if="timeline.length" class="card--flush snap-timeline-card">
    <div class="snap-header">
      <div>
        <div class="label">History</div>
        <div class="snap-subtitle">Snapshot timeline</div>
        <div class="muted snap-hint">Each entry is one moment in time across every account. Movement is measured the same way the dashboard measures profit, so an account tracked for the first time counts as opening capital rather than a gain. Expand a date to edit or delete the snapshots taken that day.</div>
      </div>
    </div>
    <div class="snap-timeline">
      <div
        v-for="(set, i) in timeline"
        :key="set.date"
        class="snap-set"
        :class="{ 'snap-set--open': openTimelineDates.has(set.date) }"
      >
        <button class="snap-head" @click="toggleTimelineDate(set.date)">
          <span class="snap-rail">
            <span class="snap-dot" />
            <span v-if="i < timeline.length - 1" class="snap-line" />
          </span>
          <div class="snap-date">
            <span class="snap-day">{{ dateParts(set.date).day }}</span>
            <span class="snap-month">{{ dateParts(set.date).month }}</span>
            <span class="snap-year">{{ dateParts(set.date).year }}</span>
          </div>
          <div class="snap-meta">
            <span class="snap-locs">
              <span v-for="loc in set.locations" :key="loc" class="snap-loc-chip">{{ loc }}</span>
            </span>
            <span class="muted snap-meta-count">{{ set.captured_count }} of {{ set.rows.length }} updated</span>
          </div>
          <div class="snap-total">
            <div v-for="c in set.currencies" :key="c.code" class="snap-ccy-line">
              <span class="muted snap-ccy-code">{{ c.code }}</span>
              <span class="num snap-total-num">{{ fmtAmount(c.total) }}</span>
              <GrowthBadge v-if="c.delta !== null" :delta="c.delta" :show-icon="false">
                {{ fmtSignedMoney(c.delta, c.code) }}
                <span v-if="c.delta_pct !== null" class="snap-delta-pct">·
                  {{ c.delta_pct >= 0 ? '+' : '' }}{{ c.delta_pct.toFixed(1) }}%
                </span>
              </GrowthBadge>
              <span v-if="c.opening_capital" class="muted snap-opening">
                +{{ fmtMoney(c.opening_capital, c.code) }} opening
              </span>
            </div>
          </div>
          <div class="snap-actions">
            <span class="snap-chevron"><PhCaretDown :size="14" /></span>
          </div>
        </button>
        <div v-if="openTimelineDates.has(set.date)" class="snap-body">
          <div class="snap-grid">
            <div
              v-for="r in set.rows"
              :key="r.account_id"
              class="snap-cell"
              :class="{
                'snap-cell--carried': r.snapshot_id === null,
                'snap-cell--removing': r.snapshot_id !== null && r.snapshot_id === removingId,
              }"
            >
              <div class="snap-cell-head">
                <span class="snap-cell-icon"><PhWallet :size="14" /></span>
                <div class="stack snap-cell-meta">
                  <span class="snap-cell-name">{{ r.label }}</span>
                </div>
              </div>
              <div class="snap-cell-foot">
                <div class="snap-cell-amt">
                  <span class="num">{{ fmtMoney(r.amount, r.currency) }}</span>
                  <span v-if="r.snapshot_id === null" class="muted snap-cell-since">
                    unchanged since {{ dateParts(r.since).day }} {{ dateParts(r.since).month }}
                  </span>
                  <span v-else-if="r.is_opening_capital" class="muted snap-cell-since">
                    first tracked here
                  </span>
                </div>
                <EditDeleteActions
                  v-if="r.snapshot_id !== null"
                  @edit="openEdit(snapshotOf(set.date, r)!)"
                  @confirm="crudRemove(r.snapshot_id)"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </BaseCard>
  </div>

  <BaseModal :show="showNewLocationDialog" title="New storage location" @close="showNewLocationDialog = false" @submit="createLocation">
    <div class="form-group">
      <label for="new-location-name">Name</label>
      <input id="new-location-name" v-model="newLocationName" type="text" placeholder="e.g. Revolut" required />
    </div>
  </BaseModal>

  <BaseModal
    :show="showNewAccountDialog"
    :title="`New account in ${newAccountLocationName}`"
    @close="showNewAccountDialog = false"
    @submit="createAccount"
  >
    <div class="form-group">
      <label for="new-account-currency">Currency</label>
      <select id="new-account-currency" v-model.number="newAccountCurrencyId" required>
        <option :value="null" disabled>Select a currency</option>
        <option v-for="cur in availableCurrenciesForNewAccount" :key="cur.id" :value="cur.id">
          {{ cur.code }}<template v-if="cur.name"> — {{ cur.name }}</template>
        </option>
      </select>
      <p v-if="!availableCurrenciesForNewAccount.length" class="field-error">
        {{
          refs.currencies.length
            ? 'This location already has an account in every currency you track.'
            : 'Add a currency in References before creating an account.'
        }}
      </p>
    </div>
  </BaseModal>

  <BaseModal :show="showModal" :title="`${editing ? 'Edit' : 'New'} Balance Snapshot`" @close="showModal = false" @submit="save">
    <div class="form-group">
      <label>Account</label>
      <select v-model.number="form.storage_account_id" required>
        <option v-for="acc in refs.storageAccounts" :key="acc.id" :value="acc.id">
          {{ refs.storageAccountLabel(acc) }}
        </option>
      </select>
    </div>
    <div class="form-group">
      <label>Date</label>
      <input v-model="form.date" type="date" required />
    </div>
    <div class="form-group">
      <label>{{ amountFieldLabel }}</label>
      <input
        v-model.number="form.amount"
        type="number"
        step="any"
        required
        :class="{ 'input-invalid': formErrors.amount && touchedFields.has('amount') }"
        @blur="touchedFields = new Set([...touchedFields, 'amount'])"
      />
      <p v-if="formErrors.amount && touchedFields.has('amount')" class="field-error">{{ formErrors.amount }}</p>
    </div>
  </BaseModal>
</template>

<style scoped>
.locations-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(260px, 100%), 1fr));
  gap: var(--gap-section);
}
.location-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 180px;
}
.location-card-head { gap: 10px; }
.location-icon {
  width: 36px;
  height: 36px;
  border-radius: 11px;
  background: var(--accent-soft);
  color: var(--accent-ink);
  display: grid;
  place-items: center;
  flex-shrink: 0;
}
.location-name {
  font-weight: 600;
  font-family: var(--font-display);
  letter-spacing: -0.005em;
}
.location-accounts { gap: 6px; }
.location-acc-row { font-size: 13px; }
.location-acc-val { font-weight: 500; }
.location-empty {
  font-size: 12px;
  font-style: italic;
}
.location-add-acc {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-top: auto;
  padding: 8px 12px;
  border: 1px dashed var(--hairline-strong);
  border-radius: var(--r-inner);
  background: transparent;
  color: var(--ink-3);
  font-family: var(--font-sans);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: color var(--t-fast) var(--ease),
              border-color var(--t-fast) var(--ease),
              background var(--t-fast) var(--ease);
}
.location-add-acc:focus-visible {
  border-color: var(--accent);
  color: var(--accent-ink);
  background: var(--accent-soft);
}

.location-add {
  border: 1.5px dashed var(--hairline-strong);
  background: transparent;
  box-shadow: none;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  min-height: 180px;
  color: var(--ink-3);
  cursor: pointer;
  transition: all var(--t-fast) var(--ease);
  font-size: 14px;
  font-weight: 500;
  font-family: var(--font-sans);
}
.location-add:focus-visible {
  border-color: var(--accent);
  color: var(--accent-ink);
  background: var(--accent-soft);
}

@media (hover: hover) {
  .location-add-acc:hover,
  .location-add:hover {
    border-color: var(--accent);
    color: var(--accent-ink);
    background: var(--accent-soft);
  }
}

.snap-header {
  padding: 18px 22px 16px;
}
.snap-subtitle {
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 600;
  margin-top: 4px;
  letter-spacing: -0.01em;
}
.snap-hint {
  font-size: 12px;
  margin-top: 2px;
}
.snap-meta-count {
  font-size: 11px;
}
.snap-delta-pct {
  opacity: 0.7;
  margin-left: 2px;
}
.snap-opening {
  font-size: 11px;
  white-space: nowrap;
}
.snap-cell-icon {
  width: 28px;
  height: 28px;
  border-radius: 9px;
  background: var(--surface);
  border: 1px solid var(--hairline);
  display: grid;
  place-items: center;
  flex-shrink: 0;
  color: var(--accent-ink);
}
.snap-cell-meta { gap: 1px; min-width: 0; flex: 1; }
.snap-cell-name { font-weight: 500; font-size: 13px; }
.snap-cell-foot {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.snap-cell--removing {
  opacity: 0;
  transform: scale(0.96);
  transition: opacity var(--t-med) var(--ease), transform var(--t-med) var(--ease);
}
</style>

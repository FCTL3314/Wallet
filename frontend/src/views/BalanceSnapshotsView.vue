<script setup lang="ts">
import { ref, computed, useTemplateRef, onMounted, watch } from 'vue'
import { balanceSnapshotsApi, type BalanceSnapshot, type BalanceSnapshotCreate } from '../api/balanceSnapshots'
import { analyticsApi, type BalanceByStorageEntry, type BalanceByStorageAccount, type GroupBy } from '../api/analytics'
import { useReferencesStore } from '../stores/references'
import { fmtAmount, fmtPeriod, localDateStr } from '../utils/format'
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
import { PhWallet, PhCaretDown, PhPlus, PhWarning } from '@phosphor-icons/vue'
import { storageLocationsApi, storageAccountsApi } from '../api/references'

const SNAPSHOT_PAGE_SIZE = 1000
const SNAPSHOT_MAX_PAGES = 25

const HINT_TOTAL_BALANCE =
  'The most recent snapshot of every account, summed per currency. Accounts you have not re-snapshotted keep their last recorded amount, so this is your latest known position rather than a live balance.'

const refs = useReferencesStore()
const { spawn } = useSuccessAnimation()
const addBtnRef = useTemplateRef<HTMLElement>('addBtn')
const allSnapshots = ref<BalanceSnapshot[]>([])
const historyTruncated = ref(false)
const storageData = ref<BalanceByStorageEntry[]>([])
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
  return `${refs.currencyByCode(acc.currency)?.symbol ?? acc.currency}${fmtAmount(acc.amount)}`
}

const groupBy = ref<GroupBy>('month')
const { dateFrom, dateTo, activePreset, allRange, initRange } = useDateRange('YTD')

const snapshots = computed(() =>
  allSnapshots.value.filter((s) => s.date >= dateFrom.value && s.date <= dateTo.value),
)

// A snapshot records what an account holds. Zero is a real balance and a credit
// card is legitimately negative, so the only thing to reject here is a non-number.
const formErrors = computed(() => ({
  amount: Number.isFinite(form.value.amount) ? null : 'Enter an amount',
}))

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

interface TimelineRow {
  accountId: number
  ccy: string
  amount: number
  snapshot: BalanceSnapshot | null
  since: string
}

interface TimelineCurrency {
  code: string
  total: number
  delta: number | null
  deltaPct: number | null
}

interface TimelineSet {
  date: string
  rows: TimelineRow[]
  currencies: TimelineCurrency[]
  capturedCount: number
  locations: string[]
}

const openTimelineDates = ref<Set<string>>(new Set())

function toggleTimelineDate(d: string) {
  const s = new Set(openTimelineDates.value)
  s.has(d) ? s.delete(d) : s.add(d)
  openTimelineDates.value = s
}

const timelineSets = computed<TimelineSet[]>(() => {
  const byDate = new Map<string, BalanceSnapshot[]>()
  for (const s of allSnapshots.value) {
    const arr = byDate.get(s.date) ?? []
    arr.push(s)
    byDate.set(s.date, arr)
  }

  const state = new Map<number, { snapshot: BalanceSnapshot; since: string }>()
  const built: { date: string; rows: TimelineRow[]; totals: Record<string, number> }[] = []

  for (const date of [...byDate.keys()].sort()) {
    for (const s of byDate.get(date) ?? []) {
      const cur = state.get(s.storage_account_id)
      if (!cur || cur.since < date || s.id > cur.snapshot.id) {
        state.set(s.storage_account_id, { snapshot: s, since: date })
      }
    }

    const rows: TimelineRow[] = [...state.entries()]
      .map(([accountId, held]) => ({
        accountId,
        ccy: accountCurrency(accountId),
        amount: Number(held.snapshot.amount),
        snapshot: held.since === date ? held.snapshot : null,
        since: held.since,
      }))
      .sort((a, b) =>
        (refs.storageAccountLabelById(a.accountId) || '').localeCompare(
          refs.storageAccountLabelById(b.accountId) || '',
        ),
      )

    const totals: Record<string, number> = {}
    for (const r of rows) totals[r.ccy] = (totals[r.ccy] ?? 0) + r.amount

    built.push({ date, rows, totals })
  }

  const sets: TimelineSet[] = built.map((entry, i) => {
    const prev = i > 0 ? built[i - 1] : null
    const currencies = Object.entries(entry.totals)
      .map(([code, total]) => {
        const before = prev?.totals[code]
        const delta = before === undefined ? null : total - before
        return {
          code,
          total,
          delta,
          deltaPct: delta !== null && before ? (delta / before) * 100 : null,
        }
      })
      .sort((a, b) => a.code.localeCompare(b.code))

    return {
      date: entry.date,
      rows: entry.rows,
      currencies,
      capturedCount: entry.rows.filter((r) => r.snapshot).length,
      locations: [...new Set(entry.rows.map((r) => locationNameForAccount(r.accountId)))],
    }
  })

  return sets
    .filter((s) => s.date >= dateFrom.value && s.date <= dateTo.value)
    .reverse()
})

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

function locationNameForAccount(accountId: number): string {
  const acc = refs.storageAccounts.find((a) => a.id === accountId)
  const loc = acc ? refs.storageLocations.find((l) => l.id === acc.storage_location_id) : null
  return loc?.name ?? '—'
}

interface LocationCard {
  id: number
  name: string
  accounts: { id: number; ccy: string; latest: number; symbol: string }[]
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
          symbol: cur?.symbol ?? '',
          latest: latestAmountForAccount(a.id),
        }
      })
    return { id: loc.id, name: loc.name, accounts }
  }),
)

function latestAmountForAccount(accountId: number): number {
  const held = allSnapshots.value
    .filter((s) => s.storage_account_id === accountId)
    .sort((a, b) => b.date.localeCompare(a.date) || b.id - a.id)
  return held[0]?.amount ?? 0
}

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

const totalKpiCount = computed(() => snapshots.value.length)
const distinctSnapshotDates = computed(() => new Set(snapshots.value.map((s) => s.date)).size)
const totalsByCcy = computed(() => {
  const totals: Record<string, number> = {}
  for (const a of refs.storageAccounts) {
    const cur = refs.currencyById(a.currency_id)
    if (!cur) continue
    totals[cur.code] = (totals[cur.code] ?? 0) + Number(latestAmountForAccount(a.id))
  }
  return totals
})

const totalEntries = computed(() =>
  Object.entries(totalsByCcy.value)
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

async function fetchSnapshotHistory(): Promise<{ items: BalanceSnapshot[]; truncated: boolean }> {
  const byId = new Map<number, BalanceSnapshot>()
  let cursor: string | undefined

  for (let page = 0; page < SNAPSHOT_MAX_PAGES; page++) {
    const { data } = await balanceSnapshotsApi.list({
      limit: SNAPSHOT_PAGE_SIZE,
      date_to: cursor,
    })
    const knownBefore = byId.size
    let oldest: string | null = null
    for (const snap of data) {
      byId.set(snap.id, snap)
      if (oldest === null || snap.date < oldest) oldest = snap.date
    }
    if (data.length < SNAPSHOT_PAGE_SIZE) return { items: [...byId.values()], truncated: false }
    if (oldest === null || oldest === cursor || byId.size === knownBefore) break
    cursor = oldest
  }

  return { items: [...byId.values()], truncated: true }
}

async function load() {
  loading.value = true
  try {
    const [history, analytics] = await Promise.all([
      fetchSnapshotHistory(),
      analyticsApi.balanceByStorage({
        date_from: dateFrom.value, date_to: dateTo.value, group_by: groupBy.value,
      }),
    ])
    allSnapshots.value = history.items
    historyTruncated.value = history.truncated
    storageData.value = analytics.data
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

  <BaseCard v-if="historyTruncated" class="warning-card">
    <div class="row warning-row">
      <PhWarning :size="18" weight="fill" class="warning-icon" />
      <span>
        Your history is longer than Wallet can load in one go. The totals, the location cards and the
        timeline on this page cover only the {{ allSnapshots.length }} most recent snapshots — anything
        older is not reflected here.
      </span>
    </div>
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
          <span class="muted">{{ acc.ccy }}</span>
          <span class="num location-acc-val">{{ acc.symbol }}{{ fmtAmount(acc.latest) }}</span>
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
          <template v-if="row.totals[cur] != null">{{ refs.currencyByCode(cur)?.symbol ?? cur }}{{ fmtAmount(row.totals[cur]) }}</template>
          <template v-else>—</template>
        </td>
        <td v-for="col in allAccounts" :key="col.name" class="col-num">{{ accountCell(row, col.name) }}</td>
      </tr>
    </template>
  </BaseDataTable>

  <BaseCard v-if="timelineSets.length" class="card--flush snap-timeline-card">
    <div class="snap-header">
      <div>
        <div class="label">History</div>
        <div class="snap-subtitle">Snapshot timeline</div>
        <div class="muted snap-hint">Each entry is one moment in time across every account. Expand a date to edit or delete the snapshots taken that day.</div>
      </div>
    </div>
    <div class="snap-timeline">
      <div
        v-for="(set, i) in timelineSets"
        :key="set.date"
        class="snap-set"
        :class="{ 'snap-set--open': openTimelineDates.has(set.date) }"
      >
        <button class="snap-head" @click="toggleTimelineDate(set.date)">
          <span class="snap-rail">
            <span class="snap-dot" />
            <span v-if="i < timelineSets.length - 1" class="snap-line" />
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
            <span class="muted snap-meta-count">{{ set.capturedCount }} of {{ set.rows.length }} updated</span>
          </div>
          <div class="snap-total">
            <div v-for="c in set.currencies" :key="c.code" class="snap-ccy-line">
              <span class="muted snap-ccy-code">{{ c.code }}</span>
              <span class="num snap-total-num">{{ fmtAmount(c.total) }}</span>
              <GrowthBadge v-if="c.delta !== null" :delta="c.delta" :show-icon="false">
                {{ c.delta >= 0 ? '+' : '−' }}{{ fmtAmount(Math.abs(c.delta)) }}
                <span v-if="c.deltaPct !== null" class="snap-delta-pct">·
                  {{ c.deltaPct >= 0 ? '+' : '' }}{{ c.deltaPct.toFixed(1) }}%
                </span>
              </GrowthBadge>
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
              :key="r.accountId"
              class="snap-cell"
              :class="{
                'snap-cell--carried': !r.snapshot,
                'snap-cell--removing': r.snapshot && r.snapshot.id === removingId,
              }"
            >
              <div class="snap-cell-head">
                <span class="snap-cell-icon"><PhWallet :size="14" /></span>
                <div class="stack snap-cell-meta">
                  <span class="snap-cell-name">{{ refs.storageAccountLabelById(r.accountId) }}</span>
                  <span class="muted snap-cell-ccy">{{ r.ccy }}</span>
                </div>
              </div>
              <div class="snap-cell-foot">
                <div class="snap-cell-amt">
                  <span class="num">{{ fmtAmount(r.amount) }}</span>
                  <span v-if="!r.snapshot" class="muted snap-cell-since">
                    unchanged since {{ dateParts(r.since).day }} {{ dateParts(r.since).month }}
                  </span>
                </div>
                <EditDeleteActions
                  v-if="r.snapshot"
                  @edit="openEdit(r.snapshot)"
                  @confirm="crudRemove(r.snapshot.id)"
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
      <label>Amount</label>
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

.warning-card {
  background: var(--warning-soft);
  border-color: transparent;
}
.warning-row {
  gap: 10px;
  flex-wrap: wrap;
  font-size: 13px;
}
.warning-icon {
  color: var(--warning-ink);
  flex-shrink: 0;
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
.snap-cell-ccy {
  font-size: 10px;
  font-family: var(--font-mono);
}
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

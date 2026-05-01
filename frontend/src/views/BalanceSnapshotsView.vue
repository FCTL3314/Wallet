<script setup lang="ts">
import { ref, computed, useTemplateRef, onMounted, watch } from 'vue'
import { balanceSnapshotsApi, type BalanceSnapshot, type BalanceSnapshotCreate } from '../api/balanceSnapshots'
import { analyticsApi, type BalanceByStorageEntry, type BalanceByStorageAccount, type GroupBy } from '../api/analytics'
import { useReferencesStore } from '../stores/references'
import { fmtAmount, fmtPeriod } from '../utils/format'
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
import { PhWallet, PhCaretDown, PhPencilSimple, PhPlus } from '@phosphor-icons/vue'
import { storageLocationsApi } from '../api/references'

const refs = useReferencesStore()
const { spawn } = useSuccessAnimation()
const addBtnRef = useTemplateRef<HTMLElement>('addBtn')
const snapshots = ref<BalanceSnapshot[]>([])
const storageData = ref<BalanceByStorageEntry[]>([])
const loading = ref(false)

// All currencies and accounts across ALL periods (not just the first row)
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

// Expandable rows
const expandedPeriods = ref<Set<string>>(new Set())

function togglePeriod(period: string) {
  const s = new Set(expandedPeriods.value)
  s.has(period) ? s.delete(period) : s.add(period)
  expandedPeriods.value = s
}

function snapshotsForPeriod(period: string): BalanceSnapshot[] {
  if (period.includes('-Q')) {
    const [year, q] = period.split('-Q') as [string, string]
    const startM = (parseInt(q) - 1) * 3 + 1
    return snapshots.value.filter(s => {
      const parts = s.date.split('-').map(Number)
      const [y, m] = parts as [number, number]
      return String(y) === year && m >= startM && m <= startM + 2
    })
  }
  // period is "YYYY-MM-01" for month, "YYYY-01-01" for year — use appropriate prefix
  const prefix = groupBy.value === 'year' ? period.slice(0, 4) : period.slice(0, 7)
  return snapshots.value.filter(s => s.date.startsWith(prefix))
}

const groupBy = ref<GroupBy>('month')
const { dateFrom, dateTo, activePreset, allRange, initRange } = useDateRange('YTD')

const formErrors = computed(() => ({
  amount: (form.value.amount ?? -1) < 0 ? 'Must be 0 or greater' : null,
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
    date: new Date().toISOString().slice(0, 10),
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

// ── Snapshot timeline (group all individual snapshots by date) ────────────
interface TimelineSet {
  date: string
  rows: BalanceSnapshot[]
  total: number
  delta: number | null
  deltaPct: number | null
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
  for (const s of snapshots.value) {
    const arr = byDate.get(s.date) ?? []
    arr.push(s)
    byDate.set(s.date, arr)
  }
  // sort each group; aggregate totals (in nominal account currency, so we sum raw)
  const dates = [...byDate.keys()].sort().reverse()
  const sets: TimelineSet[] = dates.map((date) => {
    const rows = (byDate.get(date) ?? []).slice().sort((a, b) =>
      (refs.storageAccountLabelById(a.storage_account_id) || '').localeCompare(
        refs.storageAccountLabelById(b.storage_account_id) || '',
      ),
    )
    const total = rows.reduce((sum, r) => sum + Number(r.amount), 0)
    const locations = [...new Set(rows.map((r) => {
      const acc = refs.storageAccounts.find((a) => a.id === r.storage_account_id)
      const loc = acc ? refs.storageLocations.find((l) => l.id === acc.storage_location_id) : null
      return loc?.name ?? '—'
    }))]
    return { date, rows, total, delta: null, deltaPct: null, locations }
  })
  // delta vs the next (older) set
  for (let i = 0; i < sets.length - 1; i++) {
    const cur = sets[i]
    const prev = sets[i + 1]
    if (!cur || !prev) continue
    cur.delta = cur.total - prev.total
    cur.deltaPct = prev.total !== 0 ? (cur.delta / prev.total) * 100 : null
  }
  return sets
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

// ── Locations grid (per design) ────────────────────────────────────────────
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
          latest: latestAmountForAccountSafe(a.id),
        }
      })
    return { id: loc.id, name: loc.name, accounts }
  }),
)

function latestAmountForAccountSafe(accountId: number): number {
  const sorted = snapshots.value
    .filter((s) => s.storage_account_id === accountId)
    .sort((a, b) => b.date.localeCompare(a.date))
  return sorted[0]?.amount ?? 0
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

const totalKpiCount = computed(() => snapshots.value.length)
const distinctSnapshotDates = computed(() => new Set(snapshots.value.map((s) => s.date)).size)
const totalsByCcy = computed(() => {
  const totals: Record<string, number> = {}
  for (const a of refs.storageAccounts) {
    const cur = refs.currencyById(a.currency_id)
    if (!cur) continue
    totals[cur.code] = (totals[cur.code] ?? 0) + Number(latestAmountForAccountSafe(a.id))
  }
  return totals
})

const totalEntries = computed(() =>
  Object.entries(totalsByCcy.value)
    .map(([code, amount]) => ({ code, amount }))
    .sort((a, b) => b.amount - a.amount),
)

function latestAmountForAccount(accountId: number): number {
  const sorted = snapshots.value
    .filter(s => s.storage_account_id === accountId)
    .sort((a, b) => b.date.localeCompare(a.date))
  return sorted[0]?.amount ?? 0
}

// Wrap openCreate to reset tagInput etc. if needed (none here — just delegate)
function openCreate() {
  crudOpenCreate()
  form.value.amount = latestAmountForAccount(form.value.storage_account_id)
}

// When account changes in create mode, auto-fill amount from last snapshot
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
  const [snaps, analytics] = await Promise.all([
    balanceSnapshotsApi.list({ date_from: dateFrom.value, date_to: dateTo.value }),
    analyticsApi.balanceByStorage({
      date_from: dateFrom.value, date_to: dateTo.value, group_by: groupBy.value,
    }),
  ])
  snapshots.value = snaps.data
  storageData.value = analytics.data
  loading.value = false
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
    <div class="card stat-card stat-card--profit">
      <div class="stat-label">Total balance</div>
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
    </div>
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
        <th style="width: 36px;"></th>
        <th>Period</th>
        <th v-for="cur in allCurrencies" :key="cur" class="col-num">{{ cur }} Total</th>
        <th v-for="acc in allAccounts" :key="acc.name" class="col-num">{{ acc.name }}</th>
      </tr>
    </template>
    <template #body>
      <template v-for="(row, index) in storageData" :key="row.period">
        <tr
          class="table-row period-row"
          :style="{ '--i': String(Math.min(index, 15)) }"
          @click="togglePeriod(row.period)"
        >
          <td>
            <button class="expand-btn" :class="{ expanded: expandedPeriods.has(row.period) }">▶</button>
          </td>
          <td>{{ fmtPeriod(row.period) }}</td>
          <td v-for="cur in allCurrencies" :key="cur" class="col-num">
            <template v-if="row.totals[cur] != null">{{ refs.currencyByCode(cur)?.symbol ?? cur }}{{ fmtAmount(row.totals[cur]) }}</template>
            <template v-else>—</template>
          </td>
          <td v-for="col in allAccounts" :key="col.name" class="col-num">{{ accountCell(row, col.name) }}</td>
        </tr>

        <template v-if="expandedPeriods.has(row.period)">
          <tr
            v-for="snap in snapshotsForPeriod(row.period)"
            :key="snap.id"
            class="detail-row"
            :class="{ removing: snap.id === removingId }"
          >
            <td></td>
            <td :colspan="1 + allCurrencies.length + allAccounts.length" class="detail-cell">
              <div class="detail-content">
                <span class="detail-date">{{ snap.date }}</span>
                <span class="detail-account">{{ refs.storageAccountLabelById(snap.storage_account_id) }}</span>
                <span class="detail-amount">{{ fmtAmount(snap.amount) }}</span>
                <div class="detail-actions">
                  <EditDeleteActions @edit="openEdit(snap)" @confirm="crudRemove(snap.id)" />
                </div>
              </div>
            </td>
          </tr>
          <tr v-if="!snapshotsForPeriod(row.period).length" class="detail-row">
            <td></td>
            <td :colspan="1 + allCurrencies.length + allAccounts.length" class="detail-cell no-snapshots-msg">
              No individual snapshots in this period
            </td>
          </tr>
        </template>
      </template>
    </template>
  </BaseDataTable>

  <BaseCard v-if="timelineSets.length" class="card--flush snap-timeline-card">
    <div class="snap-header">
      <div>
        <div class="label">History</div>
        <div class="snap-subtitle">Snapshot timeline</div>
        <div class="muted snap-hint">Each entry is one moment in time across every account. Click to expand.</div>
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
            <span class="muted snap-meta-count">{{ set.rows.length }} balances captured</span>
          </div>
          <div class="snap-total">
            <span class="num snap-total-num">{{ fmtAmount(set.total) }}</span>
            <GrowthBadge v-if="set.delta !== null" :delta="set.delta" :show-icon="false">
              {{ set.delta >= 0 ? '+' : '−' }}{{ fmtAmount(Math.abs(set.delta)) }}
              <span v-if="set.deltaPct !== null" class="snap-delta-pct">·
                {{ set.deltaPct >= 0 ? '+' : '' }}{{ set.deltaPct.toFixed(1) }}%
              </span>
            </GrowthBadge>
          </div>
          <div class="snap-actions">
            <span class="snap-chevron"><PhCaretDown :size="14" /></span>
          </div>
        </button>
        <div v-if="openTimelineDates.has(set.date)" class="snap-body">
          <div class="snap-grid">
            <div v-for="r in set.rows" :key="r.id" class="snap-cell">
              <div class="snap-cell-head">
                <span class="snap-cell-icon"><PhWallet :size="14" /></span>
                <div class="stack snap-cell-meta">
                  <span class="snap-cell-name">{{ refs.storageAccountLabelById(r.storage_account_id) }}</span>
                  <span class="muted snap-cell-ccy">{{ accountCurrency(r.storage_account_id) }}</span>
                </div>
                <div class="snap-cell-actions">
                  <button class="icon-btn" @click="openEdit(r)" title="Edit"><PhPencilSimple :size="13" /></button>
                </div>
              </div>
              <div class="snap-cell-amt">
                <span class="num">{{ fmtAmount(r.amount) }}</span>
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
      <label>Name</label>
      <input v-model="newLocationName" type="text" placeholder="e.g. Revolut" required />
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
        step="0.01"
        min="0"
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
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
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
.location-add:hover {
  border-color: var(--accent);
  color: var(--accent-ink);
  background: var(--accent-soft);
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
.snap-cell-actions {
  display: inline-flex;
  gap: 2px;
}
.snap-cell-actions .icon-btn { width: 28px; height: 28px; }

.period-row {
  cursor: pointer;
}

.expand-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-placeholder);
  font-size: 0.6rem;
  padding: 4px 6px;
  border-radius: 4px;
  transition: color 0.15s, transform 0.2s;
  pointer-events: none;
}

.period-row:hover .expand-btn {
  color: var(--text-secondary);
}

.expand-btn.expanded {
  transform: rotate(90deg);
  color: var(--color-accent);
}

.detail-row td {
  background: rgba(0, 0, 0, 0.03);
  border-top: none;
}

[data-theme="dark"] .detail-row td {
  background: rgba(255, 255, 255, 0.02);
}

.detail-cell {
  padding: 6px 14px 6px 20px !important;
}

.detail-content {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.detail-date {
  font-size: 0.8rem;
  color: var(--text-label);
  min-width: 90px;
}

.no-snapshots-msg {
  font-style: italic;
  color: var(--text-placeholder);
}

.detail-account {
  font-size: 0.85rem;
  color: var(--text-secondary);
  flex: 1;
}

.detail-amount {
  font-size: 0.85rem;
  font-variant-numeric: tabular-nums;
  color: var(--text-primary);
}

.detail-actions {
  display: flex;
  gap: 0.5rem;
  margin-left: auto;
}

@media (max-width: 640px) {
  .detail-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.4rem;
  }

  .detail-actions {
    margin-left: 0;
  }
}
</style>

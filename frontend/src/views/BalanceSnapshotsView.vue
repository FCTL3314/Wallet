<script setup lang="ts">
import { ref, computed, useTemplateRef, onMounted, watch } from 'vue'
import { balanceSnapshotsApi, type BalanceSnapshot, type BalanceSnapshotCreate } from '../api/balanceSnapshots'
import { analyticsApi, type BalanceByStorageEntry, type BalanceByStorageAccount, type GroupBy } from '../api/analytics'
import { useReferencesStore } from '../stores/references'
import { fmtAmount, fmtPeriod } from '../utils/format'
import BaseModal from '../components/BaseModal.vue'
import BaseDataTable from '../components/BaseDataTable.vue'
import BaseButton from '../components/BaseButton.vue'
import EditDeleteActions from '../components/EditDeleteActions.vue'
import PeriodFilterBar from '../components/PeriodFilterBar.vue'
import { useSuccessAnimation } from '../composables/useSuccessAnimation'

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
    const [year, q] = period.split('-Q')
    const startM = (parseInt(q) - 1) * 3 + 1
    return snapshots.value.filter(s => {
      const [y, m] = s.date.split('-').map(Number)
      return String(y) === year && m >= startM && m <= startM + 2
    })
  }
  // period is "YYYY-MM-01" for month, "YYYY-01-01" for year — use appropriate prefix
  const prefix = groupBy.value === 'year' ? period.slice(0, 4) : period.slice(0, 7)
  return snapshots.value.filter(s => s.date.startsWith(prefix))
}

const showModal = ref(false)
const editing = ref<BalanceSnapshot | null>(null)

const today = new Date()
const dateFrom = ref(`${today.getFullYear()}-01-01`)
const dateTo = ref(today.toISOString().slice(0, 10))
const groupBy = ref<GroupBy>('month')
const activePreset = ref('YTD')
const allRange = ref<{ from: string; to: string } | null>(null)

const removingId = ref<number | null>(null)

const touchedFields = ref(new Set<string>())

const form = ref<BalanceSnapshotCreate>({
  storage_account_id: 0, date: new Date().toISOString().slice(0, 10), amount: 0,
})

const formErrors = computed(() => ({
  amount: (form.value.amount ?? -1) < 0 ? 'Must be 0 or greater' : null,
}))

watch(showModal, (val) => {
  if (!val) touchedFields.value = new Set()
})

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
  analyticsApi.dateRange().then(({ data: dr }) => {
    if (dr.min_date && dr.max_date) {
      allRange.value = { from: dr.min_date, to: dr.max_date }
      if (activePreset.value === 'All') {
        dateFrom.value = dr.min_date
        dateTo.value = dr.max_date
      }
    }
  })
})
watch([dateFrom, dateTo, groupBy], load)

function openCreate() {
  editing.value = null
  form.value = {
    storage_account_id: refs.storageAccounts[0]?.id || 0,
    date: new Date().toISOString().slice(0, 10),
    amount: 0,
  }
  showModal.value = true
}

function openEdit(snap: BalanceSnapshot) {
  editing.value = snap
  form.value = { storage_account_id: snap.storage_account_id, date: snap.date, amount: snap.amount }
  showModal.value = true
}

async function save() {
  if (formErrors.value.amount) {
    touchedFields.value = new Set([...touchedFields.value, 'amount'])
    return
  }
  const isCreate = !editing.value
  if (editing.value) {
    await balanceSnapshotsApi.update(editing.value.id, form.value)
  } else {
    await balanceSnapshotsApi.create(form.value)
  }
  showModal.value = false
  await load()
  if (isCreate && addBtnRef.value) {
    const rect = addBtnRef.value.getBoundingClientRect()
    spawn({ x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 })
  }
}

async function remove(id: number) {
  removingId.value = id
  await new Promise((resolve) => setTimeout(resolve, 280))
  await balanceSnapshotsApi.delete(id)
  removingId.value = null
  await load()
}
</script>

<template>
  <h1 class="page-title">Balance Snapshots</h1>

  <PeriodFilterBar
    v-model:dateFrom="dateFrom"
    v-model:dateTo="dateTo"
    v-model:groupBy="groupBy"
    v-model:activePreset="activePreset"
    :allRange="allRange"
  >
    <div ref="addBtn"><BaseButton variant="primary" size="sm" @click="openCreate">+ Add Snapshot</BaseButton></div>
  </PeriodFilterBar>

  <BaseDataTable title="Balances by Storage" :loading="loading" :empty="!storageData.length" empty-message="No balance data for selected period.">
    <template #head>
      <tr>
        <th style="width: 36px;"></th>
        <th>Period</th>
        <th v-for="cur in allCurrencies" :key="cur">{{ cur }} Total</th>
        <th v-for="acc in allAccounts" :key="acc.name">{{ acc.name }}</th>
      </tr>
    </template>
    <template #body>
      <template v-for="(row, index) in storageData" :key="row.period">
        <tr
          class="table-row period-row"
          :style="{ '--i': Math.min(index, 15) }"
          @click="togglePeriod(row.period)"
        >
          <td>
            <button class="expand-btn" :class="{ expanded: expandedPeriods.has(row.period) }">▶</button>
          </td>
          <td>{{ fmtPeriod(row.period) }}</td>
          <td v-for="cur in allCurrencies" :key="cur">
            <template v-if="row.totals[cur] != null">{{ refs.currencyByCode(cur)?.symbol ?? cur }}{{ fmtAmount(row.totals[cur]) }}</template>
            <template v-else>—</template>
          </td>
          <td v-for="col in allAccounts" :key="col.name">{{ accountCell(row, col.name) }}</td>
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
                  <EditDeleteActions @edit="openEdit(snap)" @confirm="remove(snap.id)" />
                </div>
              </div>
            </td>
          </tr>
          <tr v-if="!snapshotsForPeriod(row.period).length" class="detail-row">
            <td></td>
            <td :colspan="1 + allCurrencies.length + allAccounts.length" class="detail-cell" style="font-style: italic; color: rgba(255,255,255,0.35);">
              No individual snapshots in this period
            </td>
          </tr>
        </template>
      </template>
    </template>
  </BaseDataTable>

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
.period-row {
  cursor: pointer;
}

.expand-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.35);
  font-size: 0.6rem;
  padding: 4px 6px;
  border-radius: 4px;
  transition: color 0.15s, transform 0.2s;
  pointer-events: none;
}

.period-row:hover .expand-btn {
  color: rgba(255, 255, 255, 0.7);
}

.expand-btn.expanded {
  transform: rotate(90deg);
  color: #a78bfa;
}

.detail-row td {
  background: rgba(0, 0, 0, 0.18);
  border-top: none;
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
  color: rgba(255, 255, 255, 0.45);
  min-width: 90px;
}

.detail-account {
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.65);
  flex: 1;
}

.detail-amount {
  font-size: 0.85rem;
  font-variant-numeric: tabular-nums;
  color: rgba(255, 255, 255, 0.8);
}

.detail-actions {
  display: flex;
  gap: 0.5rem;
  margin-left: auto;
}
</style>

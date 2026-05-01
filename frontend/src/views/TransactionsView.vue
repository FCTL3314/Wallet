<script setup lang="ts">
import { ref, computed, useTemplateRef, onMounted, onUnmounted, watch } from 'vue'
import {
  transactionsApi,
  type Transaction,
  type TransactionCreate,
  type TransactionFilters,
  type TransactionSortField,
  type SortOrder,
} from '../api/transactions'
import { useReferencesStore } from '../stores/references'
import { fmtAmount } from '../utils/format'
import { useSuccessAnimation } from '../composables/useSuccessAnimation'
import { useTable, createColumnHelper } from '../composables/useTable'
import { useCrudModal } from '../composables/useCrudModal'
import { useDateRange } from '../composables/useDateRange'
import BaseModal from '../components/BaseModal.vue'
import BaseDataTable from '../components/BaseDataTable.vue'
import BaseCard from '../components/BaseCard.vue'
import BaseStatCard from '../components/BaseStatCard.vue'
import BaseButton from '../components/BaseButton.vue'
import EditDeleteActions from '../components/EditDeleteActions.vue'
import PeriodFilterBar from '../components/PeriodFilterBar.vue'

const refs = useReferencesStore()
const { spawn } = useSuccessAnimation()
const addBtnRef = useTemplateRef<HTMLElement>('addBtn')
const sentinel = useTemplateRef<HTMLElement>('sentinel')
const items = ref<Transaction[]>([])
const loading = ref(false)

const PAGE_SIZE = 50
const offset = ref(0)
const hasMore = ref(true)

const { dateFrom, dateTo, activePreset, allRange, initRange } = useDateRange('All')

// Server-side sorting state (derived from TanStack table sorting state)
const sortField = ref<TransactionSortField | undefined>(undefined)
const sortOrder = ref<SortOrder>('desc')

function defaultForm(): TransactionCreate {
  const firstAccount = refs.storageAccounts[0]
  return {
    type: 'income',
    date: new Date().toISOString().slice(0, 10),
    amount: 0,
    currency_id: firstAccount?.currency_id || refs.currencies[0]?.id || 0,
    storage_account_id: firstAccount?.id || 0,
    income_source_id: null,
    expense_category_id: null,
    description: '',
  }
}

const {
  showModal,
  editing,
  removingId,
  newId,
  touchedFields,
  form,
  openCreate,
  openEdit,
  save: crudSave,
  remove: crudRemove,
} = useCrudModal<Transaction, TransactionCreate>({
  defaultForm,
  toForm: (tx) => ({ ...tx }),
  onCreate: async (data) => {
    const { data: result } = await transactionsApi.create(data)
    return result as Transaction
  },
  onUpdate: async (id, data) => {
    const { data: result } = await transactionsApi.update(id, data)
    return result as Transaction
  },
  onDelete: async (id) => {
    await transactionsApi.delete(id)
  },
  afterSave: async (isCreate) => {
    await loadPage(true)
    if (isCreate && addBtnRef.value) {
      const rect = addBtnRef.value.getBoundingClientRect()
      spawn({ x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 })
    }
  },
  afterDelete: () => loadPage(true),
})

const filteredAccounts = computed(() =>
  refs.storageAccounts.filter(a => a.currency_id === form.value.currency_id)
)

watch(() => form.value.currency_id, (currencyId) => {
  const first = refs.storageAccounts.find(a => a.currency_id === currencyId)
  form.value.storage_account_id = first?.id || 0
})

const formErrors = computed(() => ({
  amount: (form.value.amount ?? 0) <= 0 ? 'Must be greater than 0' : null,
}))

async function save() {
  if (formErrors.value.amount) {
    touchedFields.value = new Set([...touchedFields.value, 'amount'])
    return
  }
  await crudSave()
}

let loadGen = 0

// ── TanStack Table (manual/server-side sort) ──────────────────────────────────

const colHelper = createColumnHelper<Transaction>()

// Map column id → API sort field name
const SORT_FIELD_MAP: Record<string, TransactionSortField> = {
  date: 'date',
  amount: 'amount',
  storage_account: 'storage_account',
  income_source: 'income_source',
}

const txColumns = [
  colHelper.accessor('date', {
    id: 'date',
    header: 'Date',
    enableSorting: true,
  }),
  colHelper.accessor('amount', {
    id: 'amount',
    header: 'Amount',
    enableSorting: true,
    meta: { class: 'col-num' },
  }),
  colHelper.accessor('storage_account_id', {
    id: 'storage_account',
    header: 'Account',
    enableSorting: true,
  }),
  colHelper.accessor('income_source_id', {
    id: 'income_source',
    header: 'Source',
    enableSorting: true,
  }),
  colHelper.accessor('description', {
    id: 'description',
    header: 'Description',
    enableSorting: false,
  }),
  colHelper.display({
    id: 'actions',
    header: '',
    enableSorting: false,
    meta: { style: 'text-align: right' },
  }),
]

const { table, sortingState } = useTable(
  txColumns as import('../composables/useTable').ColumnDef<Transaction>[],
  items,
  { manualSorting: true },
)

// When TanStack sorting state changes, sync to API params and reload
watch(
  sortingState,
  (state) => {
    const first = state[0]
    if (first && first.id in SORT_FIELD_MAP) {
      sortField.value = SORT_FIELD_MAP[first.id]
      sortOrder.value = first.desc ? 'desc' : 'asc'
    } else {
      sortField.value = undefined
      sortOrder.value = 'desc'
    }
    loadPage(true)
  },
  { deep: true },
)

// ─────────────────────────────────────────────────────────────────────────────

async function loadPage(reset = false) {
  if (reset) {
    offset.value = 0
    items.value = []
    hasMore.value = true
    loading.value = false
  }
  if (!hasMore.value || loading.value) return
  loading.value = true
  const gen = ++loadGen
  const params: TransactionFilters = {
    type: 'income',
    limit: PAGE_SIZE,
    offset: offset.value,
    ...(dateFrom.value && { date_from: dateFrom.value }),
    ...(dateTo.value && { date_to: dateTo.value }),
    ...(sortField.value && { sort_by: sortField.value }),
    ...(sortField.value && { sort_order: sortOrder.value }),
  }
  const { data } = await transactionsApi.list(params)
  if (gen !== loadGen) return
  items.value = reset ? data : [...items.value, ...data]
  hasMore.value = data.length === PAGE_SIZE
  offset.value += data.length
  loading.value = false
}

let observer: IntersectionObserver | null = null

onMounted(() => {
  loadPage(true)
  initRange()
  observer = new IntersectionObserver((entries) => {
    if (entries[0]?.isIntersecting) loadPage(false)
  }, { rootMargin: '200px' })
  if (sentinel.value) observer.observe(sentinel.value)
})

onUnmounted(() => {
  observer?.disconnect()
})

watch(sentinel, (el) => {
  if (el && observer) observer.observe(el)
})

watch([dateFrom, dateTo], () => loadPage(true))

function sourceName(id: number | null) {
  if (!id) return '—'
  return refs.incomeSourceById(id)?.name ?? '?'
}

const totalsByCcy = computed(() => {
  const totals: Record<string, number> = {}
  for (const t of items.value) {
    const code = refs.currencyById(t.currency_id)?.code ?? '?'
    totals[code] = (totals[code] ?? 0) + Number(t.amount)
  }
  return totals
})

const totalEntries = computed(() =>
  Object.entries(totalsByCcy.value)
    .map(([code, amount]) => ({ code, amount }))
    .sort((a, b) => b.amount - a.amount),
)

const totalCount = computed(() => items.value.length)
</script>

<template>
  <div class="sections">
  <BaseCard>
    <PeriodFilterBar
      v-model:dateFrom="dateFrom"
      v-model:dateTo="dateTo"
      v-model:activePreset="activePreset"
      :showGroupBy="false"
      :allRange="allRange"
    >
      <div ref="addBtn" data-onboarding="add-income-btn"><BaseButton variant="primary" size="sm" @click="openCreate">+ Add Income</BaseButton></div>
    </PeriodFilterBar>
  </BaseCard>

  <div v-if="items.length || loading" class="kpis">
    <BaseStatCard label="Income" variant="income">
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
    <BaseStatCard label="Entries">
      <div class="stat-value">{{ totalCount }}</div>
      <div class="stat-foot">
        <span class="muted">{{ activePreset === 'custom' ? 'custom range' : activePreset }}</span>
      </div>
    </BaseStatCard>
  </div>

  <BaseDataTable
    :table="table"
    :loading="loading && !items.length"
    :empty="!loading && !items.length"
    empty-message="No income transactions yet."
  >
    <template #body="{ rows }">
      <tr
        v-for="(row, index) in rows"
        :key="row.original.id"
        class="table-row"
        :style="{ '--i': String(Math.min(index, 15)) }"
        :class="{ removing: row.original.id === removingId, 'row-new': row.original.id === newId }"
      >
        <td>{{ row.original.date }}</td>
        <td class="col-num amount-positive">{{ fmtAmount(row.original.amount) }}</td>
        <td>{{ refs.storageAccountLabelById(row.original.storage_account_id) }}</td>
        <td>{{ sourceName(row.original.income_source_id) }}</td>
        <td>{{ row.original.description || '' }}</td>
        <td style="white-space: nowrap; text-align: right">
          <EditDeleteActions @edit="openEdit(row.original)" @confirm="crudRemove(row.original.id)" />
        </td>
      </tr>
    </template>
  </BaseDataTable>
  </div>

  <div ref="sentinel" style="height: 1px;" />
  <p v-if="loading && items.length" class="text-muted" style="text-align: center; padding: 1rem;">Loading more...</p>

  <BaseModal :show="showModal" :title="`${editing ? 'Edit' : 'New'} Income`" @close="showModal = false" @submit="save">
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
    <div class="form-group">
      <label>Currency</label>
      <select v-model.number="form.currency_id" required>
        <option v-for="cur in refs.currencies" :key="cur.id" :value="cur.id">
          {{ cur.code }} ({{ cur.symbol }})
        </option>
      </select>
    </div>
    <div class="form-group">
      <label>Account</label>
      <select v-model.number="form.storage_account_id" required>
        <option v-for="acc in filteredAccounts" :key="acc.id" :value="acc.id">
          {{ refs.storageAccountLabel(acc) }}
        </option>
      </select>
    </div>
    <div class="form-group">
      <label>Source</label>
      <select v-model.number="form.income_source_id">
        <option :value="null">— None —</option>
        <option v-for="s in refs.incomeSources" :key="s.id" :value="s.id">{{ s.name }}</option>
      </select>
    </div>
    <div class="form-group">
      <label>Description</label>
      <input v-model="form.description" type="text" />
    </div>
  </BaseModal>
</template>

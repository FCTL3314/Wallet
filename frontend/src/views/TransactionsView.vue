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
import { analyticsApi } from '../api/analytics'
import { useReferencesStore } from '../stores/references'
import { fmtAmount } from '../utils/format'
import { useSuccessAnimation } from '../composables/useSuccessAnimation'
import { useTable, createColumnHelper } from '../composables/useTable'
import BaseModal from '../components/BaseModal.vue'
import BaseDataTable from '../components/BaseDataTable.vue'
import BaseCard from '../components/BaseCard.vue'
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

const today = new Date().toISOString().slice(0, 10)
const dateFrom = ref('2000-01-01')
const dateTo = ref(today)
const activePreset = ref('All')
const allRange = ref<{ from: string; to: string } | null>(null)

// Server-side sorting state (derived from TanStack table sorting state)
const sortField = ref<TransactionSortField | undefined>(undefined)
const sortOrder = ref<SortOrder>('desc')

const showModal = ref(false)
const editing = ref<Transaction | null>(null)
const form = ref<TransactionCreate>({
  type: 'income', date: new Date().toISOString().slice(0, 10),
  amount: 0, currency_id: 0, storage_account_id: 0,
  income_source_id: null, expense_category_id: null, description: '',
})

const removingId = ref<number | null>(null)
const newId = ref<number | null>(null)
let loadGen = 0

const touchedFields = ref(new Set<string>())

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

watch(showModal, (val) => {
  if (!val) touchedFields.value = new Set()
})

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
  analyticsApi.dateRange().then(({ data }) => {
    if (data.min_date && data.max_date) {
      allRange.value = { from: data.min_date, to: data.max_date }
      if (activePreset.value === 'All') {
        dateFrom.value = data.min_date
        dateTo.value = data.max_date
      }
    }
  })
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

function openCreate() {
  editing.value = null
  const firstAccount = refs.storageAccounts[0]
  form.value = {
    type: 'income', date: new Date().toISOString().slice(0, 10),
    amount: 0,
    currency_id: firstAccount?.currency_id || refs.currencies[0]?.id || 0,
    storage_account_id: firstAccount?.id || 0,
    income_source_id: null, expense_category_id: null, description: '',
  }
  showModal.value = true
}

function openEdit(tx: Transaction) {
  editing.value = tx
  form.value = { ...tx }
  showModal.value = true
}

async function save() {
  if (formErrors.value.amount) {
    touchedFields.value = new Set([...touchedFields.value, 'amount'])
    return
  }
  const isCreate = !editing.value
  if (editing.value) {
    await transactionsApi.update(editing.value.id, form.value)
  } else {
    const { data } = await transactionsApi.create(form.value)
    newId.value = (data as { id: number }).id
  }
  showModal.value = false
  await loadPage(true)
  if (isCreate && addBtnRef.value) {
    const rect = addBtnRef.value.getBoundingClientRect()
    spawn({ x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 })
  }
  if (newId.value !== null) {
    setTimeout(() => { newId.value = null }, 1500)
  }
}

async function remove(id: number) {
  removingId.value = id
  await new Promise((resolve) => setTimeout(resolve, 280))
  await transactionsApi.delete(id)
  removingId.value = null
  await loadPage(true)
}

function sourceName(id: number | null) {
  if (!id) return '—'
  return refs.incomeSourceById(id)?.name ?? '?'
}
</script>

<template>
  <div class="page-sections">
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
          <EditDeleteActions @edit="openEdit(row.original)" @confirm="remove(row.original.id)" />
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

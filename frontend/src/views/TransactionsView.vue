<script setup lang="ts">
import { ref, computed, useTemplateRef, onMounted, onUnmounted, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { storeToRefs } from 'pinia'
import {
  transactionsApi,
  type Transaction,
  type TransactionCreate,
  type TransactionFilters,
  type TransactionQueryFilters,
  type TransactionSummary,
  type TransactionSortField,
  type SortOrder,
} from '../api/transactions'
import { useReferencesStore } from '../stores/references'
import { fmtAmount, localDateStr } from '../utils/format'
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
import { PhWallet } from '@phosphor-icons/vue'

const ALL_FILTER = 'all' as const
type OptionFilter = number | typeof ALL_FILTER

const PAGE_SIZE = 50

const refs = useReferencesStore()
const { currencies, storageAccounts, incomeSources, loaded: refsLoaded } = storeToRefs(refs)
const { spawn } = useSuccessAnimation()
const addBtnRef = useTemplateRef<HTMLElement>('addBtn')
const sentinel = useTemplateRef<HTMLElement>('sentinel')

const items = ref<Transaction[]>([])
const loading = ref(false)
const offset = ref(0)
const hasMore = ref(true)

const summary = ref<TransactionSummary | null>(null)
const summaryUnavailable = ref(false)

const { dateFrom, dateTo, activePreset, allRange, initRange } = useDateRange('All')

const sourceFilter = ref<OptionFilter>(ALL_FILTER)
const accountFilter = ref<OptionFilter>(ALL_FILTER)

const sortField = ref<TransactionSortField | undefined>(undefined)
const sortOrder = ref<SortOrder>('desc')

const hasAccounts = computed(() => storageAccounts.value.length > 0)
const needsSetup = computed(() => refsLoaded.value && !hasAccounts.value)

const accountOptions = computed(() =>
  storageAccounts.value.map((acc) => ({
    id: acc.id,
    currencyId: acc.currency_id,
    label: refs.storageAccountLabel(acc),
  })),
)

const queryFilters = computed<TransactionQueryFilters>(() => {
  const source = sourceFilter.value
  const account = accountFilter.value
  return {
    type: 'income',
    ...(dateFrom.value ? { date_from: dateFrom.value } : {}),
    ...(dateTo.value ? { date_to: dateTo.value } : {}),
    ...(source !== ALL_FILTER ? { income_source_id: source } : {}),
    ...(account !== ALL_FILTER ? { storage_account_id: account } : {}),
  }
})

const hasActiveFilters = computed(
  () => sourceFilter.value !== ALL_FILTER || accountFilter.value !== ALL_FILTER,
)

const tableEmptyMessage = computed(() => {
  if (needsSetup.value) return 'Create a storage account first — income needs an account to land in.'
  if (hasActiveFilters.value) return 'No income matches the current filters.'
  return 'No income transactions yet.'
})

const addButtonHint = computed(() =>
  needsSetup.value ? 'Create a storage account before adding income.' : undefined,
)

const periodLabel = computed(() =>
  activePreset.value === 'custom' ? 'custom range' : activePreset.value,
)

function defaultForm(): TransactionCreate {
  const firstAccount = storageAccounts.value[0]
  return {
    type: 'income',
    date: localDateStr(),
    amount: 0,
    currency_id: firstAccount?.currency_id || currencies.value[0]?.id || 0,
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
  openCreate: crudOpenCreate,
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
    await reload()
    if (isCreate && addBtnRef.value) {
      const rect = addBtnRef.value.getBoundingClientRect()
      spawn({ x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 })
    }
  },
  afterDelete: () => reload(),
})

const formAccountOptions = computed(() =>
  accountOptions.value.filter((acc) => acc.currencyId === form.value.currency_id),
)

function openCreate() {
  if (!hasAccounts.value) return
  crudOpenCreate()
}

function onCurrencyChange(event: Event) {
  const currencyId = Number((event.target as HTMLSelectElement).value)
  form.value.currency_id = currencyId
  const selected = accountOptions.value.find((acc) => acc.id === form.value.storage_account_id)
  if (selected?.currencyId === currencyId) return
  form.value.storage_account_id =
    accountOptions.value.find((acc) => acc.currencyId === currencyId)?.id ?? 0
}

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

const colHelper = createColumnHelper<Transaction>()

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
  }),
]

const { table, sortingState } = useTable(
  txColumns as import('../composables/useTable').ColumnDef<Transaction>[],
  items,
  { manualSorting: true },
)

let loadGen = 0
let summaryGen = 0

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
    ...queryFilters.value,
    limit: PAGE_SIZE,
    offset: offset.value,
    ...(sortField.value ? { sort_by: sortField.value, sort_order: sortOrder.value } : {}),
  }
  try {
    const { data } = await transactionsApi.list(params)
    if (gen !== loadGen) return
    items.value = reset ? data : [...items.value, ...data]
    hasMore.value = data.length === PAGE_SIZE
    offset.value += data.length
  } catch {
    if (gen === loadGen) hasMore.value = false
  } finally {
    if (gen === loadGen) loading.value = false
  }
}

async function loadSummary() {
  const gen = ++summaryGen
  try {
    const { data } = await transactionsApi.summary(queryFilters.value)
    if (gen !== summaryGen) return
    summary.value = data
    summaryUnavailable.value = false
  } catch {
    if (gen !== summaryGen) return
    summary.value = null
    summaryUnavailable.value = true
  }
}

async function reload() {
  await Promise.all([loadPage(true), loadSummary()])
}

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

watch([dateFrom, dateTo, sourceFilter, accountFilter], () => reload())

let observer: IntersectionObserver | null = null

onMounted(() => {
  reload()
  initRange()
  observer = new IntersectionObserver(
    (entries) => {
      if (entries[0]?.isIntersecting) loadPage(false)
    },
    { rootMargin: '200px' },
  )
  if (sentinel.value) observer.observe(sentinel.value)
})

onUnmounted(() => {
  observer?.disconnect()
})

watch(sentinel, (el) => {
  if (el && observer) observer.observe(el)
})

function sourceName(id: number | null) {
  if (!id) return '—'
  return refs.incomeSourceById(id)?.name ?? '?'
}

const totalEntries = computed(() =>
  (summary.value?.totals ?? []).map((total) => ({
    code: total.currency_code,
    amount: total.amount,
  })),
)

const totalCount = computed(() => summary.value?.count ?? 0)
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
        <template #middle>
          <label class="filter-field">
            <span class="label">Source</span>
            <select v-model="sourceFilter" class="form-input-sm filter-select">
              <option :value="ALL_FILTER">All</option>
              <option v-for="src in incomeSources" :key="src.id" :value="src.id">{{ src.name }}</option>
            </select>
          </label>
          <label class="filter-field">
            <span class="label">Account</span>
            <select v-model="accountFilter" class="form-input-sm filter-select">
              <option :value="ALL_FILTER">All</option>
              <option v-for="acc in accountOptions" :key="acc.id" :value="acc.id">{{ acc.label }}</option>
            </select>
          </label>
        </template>

        <div ref="addBtn" data-onboarding="add-income-btn" :title="addButtonHint">
          <BaseButton variant="primary" size="sm" :disabled="needsSetup" @click="openCreate">
            + Add Income
          </BaseButton>
        </div>
      </PeriodFilterBar>
    </BaseCard>

    <BaseCard v-if="needsSetup">
      <div class="empty">
        <div class="empty-illust"><PhWallet :size="34" weight="duotone" /></div>
        <p class="empty-title">No storage accounts yet</p>
        <p class="empty-sub">
          Income has to land somewhere. Add a storage location and an account for it, then come back
          to record your income.
        </p>
        <RouterLink to="/references" class="btn btn--primary">Set up accounts</RouterLink>
      </div>
    </BaseCard>

    <div v-else class="kpis">
      <BaseStatCard label="Income" variant="income">
        <template v-if="summaryUnavailable">
          <div class="stat-value">—</div>
          <div class="stat-foot"><span class="muted">Totals unavailable</span></div>
        </template>
        <template v-else-if="!totalEntries.length">
          <div class="stat-value">—</div>
        </template>
        <template v-else-if="totalEntries.length === 1">
          <div class="stat-value">
            <span class="stat-currency">{{ totalEntries[0]?.code }}</span
            >{{ fmtAmount(totalEntries[0]?.amount ?? 0) }}
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
        <div class="stat-value">{{ summaryUnavailable ? '—' : totalCount }}</div>
        <div class="stat-foot">
          <span class="muted">{{ summaryUnavailable ? 'Count unavailable' : periodLabel }}</span>
        </div>
      </BaseStatCard>
    </div>

    <BaseDataTable
      :table="table"
      :loading="loading && !items.length"
      :empty="!loading && !items.length"
      :empty-message="tableEmptyMessage"
      mobile-cards
    >
      <template #card="{ rows }">
        <li
          v-for="(row, index) in rows"
          :key="row.original.id"
          class="row-card table-row"
          :style="{ '--i': String(Math.min(index, 15)) }"
          :class="{ removing: row.original.id === removingId, 'row-new': row.original.id === newId }"
        >
          <div class="row-card-body">
            <div class="row-card-top">
              <span class="row-card-title">{{ row.original.date }}</span>
              <span class="row-card-amount row-card-amount--income num">
                {{ fmtAmount(row.original.amount) }}
              </span>
            </div>
            <div class="row-card-meta">
              <span>{{ refs.storageAccountLabelById(row.original.storage_account_id) }}</span>
              <span aria-hidden="true">·</span>
              <span>{{ sourceName(row.original.income_source_id) }}</span>
            </div>
            <p v-if="row.original.description" class="row-card-note">
              {{ row.original.description }}
            </p>
          </div>
          <div class="row-card-actions">
            <EditDeleteActions
              @edit="openEdit(row.original)"
              @confirm="crudRemove(row.original.id)"
            />
          </div>
        </li>
      </template>

      <template #body="{ rows }">
        <tr
          v-for="(row, index) in rows"
          :key="row.original.id"
          class="table-row"
          :style="{ '--i': String(Math.min(index, 15)) }"
          :class="{ removing: row.original.id === removingId, 'row-new': row.original.id === newId }"
        >
          <td class="col-date">{{ row.original.date }}</td>
          <td class="col-num amount-positive">{{ fmtAmount(row.original.amount) }}</td>
          <td>{{ refs.storageAccountLabelById(row.original.storage_account_id) }}</td>
          <td>{{ sourceName(row.original.income_source_id) }}</td>
          <td class="col-desc">{{ row.original.description || '' }}</td>
          <td class="col-actions">
            <EditDeleteActions
              @edit="openEdit(row.original)"
              @confirm="crudRemove(row.original.id)"
            />
          </td>
        </tr>
      </template>
    </BaseDataTable>
  </div>

  <div ref="sentinel" class="scroll-sentinel" />
  <p v-if="loading && items.length" class="text-muted load-more">Loading more...</p>

  <BaseModal
    :show="showModal"
    :title="`${editing ? 'Edit' : 'New'} Income`"
    @close="showModal = false"
    @submit="save"
  >
    <div class="form-group">
      <label for="income-date">Date</label>
      <input id="income-date" v-model="form.date" type="date" required />
    </div>
    <div class="form-group">
      <label for="income-amount">Amount</label>
      <input
        id="income-amount"
        v-model.number="form.amount"
        type="number"
        step="0.01"
        min="0"
        required
        :class="{ 'input-invalid': formErrors.amount && touchedFields.has('amount') }"
        @blur="touchedFields = new Set([...touchedFields, 'amount'])"
      />
      <p v-if="formErrors.amount && touchedFields.has('amount')" class="field-error">
        {{ formErrors.amount }}
      </p>
    </div>
    <div class="form-group">
      <label for="income-currency">Currency</label>
      <select id="income-currency" :value="form.currency_id" required @change="onCurrencyChange">
        <option v-for="cur in currencies" :key="cur.id" :value="cur.id">
          {{ cur.code }} ({{ cur.symbol }})
        </option>
      </select>
    </div>
    <div class="form-group">
      <label for="income-account">Account</label>
      <select id="income-account" v-model.number="form.storage_account_id" required>
        <option v-for="acc in formAccountOptions" :key="acc.id" :value="acc.id">
          {{ acc.label }}
        </option>
      </select>
    </div>
    <div class="form-group">
      <label for="income-source">Source</label>
      <select id="income-source" v-model.number="form.income_source_id">
        <option :value="null">— None —</option>
        <option v-for="src in incomeSources" :key="src.id" :value="src.id">{{ src.name }}</option>
      </select>
    </div>
    <div class="form-group">
      <label for="income-description">Description</label>
      <input id="income-description" v-model="form.description" type="text" />
    </div>
  </BaseModal>
</template>

<style scoped>
.filter-field {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.filter-select {
  max-width: 180px;
}

.col-actions {
  white-space: nowrap;
  text-align: right;
}

.col-date {
  white-space: nowrap;
}

.col-desc {
  max-width: 320px;
  overflow-wrap: anywhere;
}

.scroll-sentinel {
  height: 1px;
}

.load-more {
  text-align: center;
  padding: 1rem;
}

@media (max-width: 640px) {
  .filter-field {
    flex: 1 1 100%;
    min-width: 0;
  }

  .filter-select {
    flex: 1;
    min-width: 0;
    max-width: none;
  }
}
</style>

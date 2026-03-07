<script setup lang="ts">
import { ref, computed, useTemplateRef, onMounted, onUnmounted, watch } from 'vue'
import { transactionsApi, type Transaction, type TransactionCreate, type TransactionFilters } from '../api/transactions'
import { analyticsApi } from '../api/analytics'
import { useReferencesStore } from '../stores/references'
import { fmtAmount } from '../utils/format'
import { useSuccessAnimation } from '../composables/useSuccessAnimation'
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

const showModal = ref(false)
const editing = ref<Transaction | null>(null)
const form = ref<TransactionCreate>({
  type: 'income', date: new Date().toISOString().slice(0, 10),
  amount: 0, currency_id: 0, storage_account_id: 0,
  income_source_id: null, expense_category_id: null, description: '',
})

const removingId = ref<number | null>(null)
const newId = ref<number | null>(null)

const touchedFields = ref(new Set<string>())

const formErrors = computed(() => ({
  amount: (form.value.amount ?? 0) <= 0 ? 'Must be greater than 0' : null,
}))

watch(showModal, (val) => {
  if (!val) touchedFields.value = new Set()
})

async function loadPage(reset = false) {
  if (reset) {
    offset.value = 0
    items.value = []
    hasMore.value = true
  }
  if (!hasMore.value || loading.value) return
  loading.value = true
  const params: TransactionFilters = {
    type: 'income',
    limit: PAGE_SIZE,
    offset: offset.value,
    ...(dateFrom.value && { date_from: dateFrom.value }),
    ...(dateTo.value && { date_to: dateTo.value }),
  }
  const { data } = await transactionsApi.list(params)
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
      <div ref="addBtn"><BaseButton variant="primary" size="sm" @click="openCreate">+ Add Income</BaseButton></div>
    </PeriodFilterBar>
  </BaseCard>

  <BaseDataTable :loading="loading && !items.length" :empty="!loading && !items.length" empty-message="No income transactions yet.">
    <template #head>
      <tr>
        <th>Date</th>
        <th class="col-num">Amount</th>
        <th>Account</th>
        <th>Source</th>
        <th>Description</th>
        <th></th>
      </tr>
    </template>
    <template #body>
      <tr
        v-for="(tx, index) in items"
        :key="tx.id"
        class="table-row"
        :style="{ '--i': String(Math.min(index, 15)) }"
        :class="{ removing: tx.id === removingId, 'row-new': tx.id === newId }"
      >
        <td>{{ tx.date }}</td>
        <td class="col-num amount-positive">{{ fmtAmount(tx.amount) }}</td>
        <td>{{ refs.storageAccountLabelById(tx.storage_account_id) }}</td>
        <td>{{ sourceName(tx.income_source_id) }}</td>
        <td>{{ tx.description || '' }}</td>
        <td style="white-space: nowrap">
          <EditDeleteActions @edit="openEdit(tx)" @confirm="remove(tx.id)" />
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
      <label>Account</label>
      <select v-model.number="form.storage_account_id" required>
        <option v-for="acc in refs.storageAccounts" :key="acc.id" :value="acc.id">
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

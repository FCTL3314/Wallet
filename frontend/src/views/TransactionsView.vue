<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { transactionsApi, type Transaction, type TransactionCreate, type TransactionFilters } from '../api/transactions'
import { useReferencesStore } from '../stores/references'
import { fmtAmount } from '../utils/format'
import BaseModal from '../components/BaseModal.vue'
import BaseDataTable from '../components/BaseDataTable.vue'
import BaseConfirmButton from '../components/BaseConfirmButton.vue'

const refs = useReferencesStore()
const items = ref<Transaction[]>([])
const loading = ref(false)

const filterType = ref<'' | 'income' | 'expense'>('')
const filterDateFrom = ref('')
const filterDateTo = ref('')

const showModal = ref(false)
const editing = ref<Transaction | null>(null)
const form = ref<TransactionCreate>({
  type: 'income', date: new Date().toISOString().slice(0, 10),
  amount: 0, currency_id: 0, storage_account_id: 0,
  income_source_id: null, expense_category_id: null, description: '',
})

async function load() {
  loading.value = true
  const params: TransactionFilters = {}
  if (filterType.value) params.type = filterType.value
  if (filterDateFrom.value) params.date_from = filterDateFrom.value
  if (filterDateTo.value) params.date_to = filterDateTo.value
  const { data } = await transactionsApi.list(params)
  items.value = data
  loading.value = false
}

onMounted(load)
watch([filterType, filterDateFrom, filterDateTo], load)

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
  if (editing.value) {
    await transactionsApi.update(editing.value.id, form.value)
  } else {
    await transactionsApi.create(form.value)
  }
  showModal.value = false
  await load()
}

async function remove(id: number) {
  await transactionsApi.delete(id)
  await load()
}

function sourceName(id: number | null) {
  if (!id) return '—'
  return refs.incomeSourceById(id)?.name ?? '?'
}

function categoryName(id: number | null) {
  if (!id) return '—'
  return refs.expenseCategoryById(id)?.name ?? '?'
}
</script>

<template>
  <h1 class="page-title">Transactions</h1>

  <div class="toolbar">
    <select v-model="filterType">
      <option value="">All types</option>
      <option value="income">Income</option>
      <option value="expense">Expense</option>
    </select>
    <input v-model="filterDateFrom" type="date" placeholder="From" />
    <input v-model="filterDateTo" type="date" placeholder="To" />
    <button class="btn btn-primary btn-sm" @click="openCreate">+ Add Transaction</button>
  </div>

  <BaseDataTable :loading="loading" :empty="!items.length" empty-message="No transactions yet.">
    <template #head>
      <tr>
        <th>Date</th>
        <th>Type</th>
        <th>Amount</th>
        <th>Account</th>
        <th>Source / Category</th>
        <th>Description</th>
        <th></th>
      </tr>
    </template>
    <template #body>
      <tr v-for="tx in items" :key="tx.id">
        <td>{{ tx.date }}</td>
        <td><span :class="['chip', tx.type === 'income' ? 'chip-income' : 'chip-expense']">{{ tx.type }}</span></td>
        <td :class="tx.type === 'income' ? 'amount-positive' : 'amount-negative'">
          {{ tx.type === 'expense' ? '-' : '' }}{{ fmtAmount(tx.amount) }}
        </td>
        <td>{{ refs.storageAccountLabelById(tx.storage_account_id) }}</td>
        <td>{{ tx.type === 'income' ? sourceName(tx.income_source_id) : categoryName(tx.expense_category_id) }}</td>
        <td>{{ tx.description || '' }}</td>
        <td style="white-space: nowrap">
          <button class="btn btn-secondary btn-sm" @click="openEdit(tx)">Edit</button>
          <BaseConfirmButton @confirm="remove(tx.id)" />
        </td>
      </tr>
    </template>
  </BaseDataTable>

  <BaseModal :show="showModal" :title="`${editing ? 'Edit' : 'New'} Transaction`" @close="showModal = false" @submit="save">
    <div class="form-group">
      <label>Type</label>
      <div class="type-toggle">
        <select v-model="form.type">
          <option value="income">Income</option>
          <option value="expense">Expense</option>
        </select>
      </div>
    </div>
    <div class="form-group">
      <label>Date</label>
      <input v-model="form.date" type="date" required />
    </div>
    <div class="form-group">
      <label>Amount</label>
      <input v-model.number="form.amount" type="number" step="0.01" min="0" required />
    </div>
    <div class="form-group">
      <label>Account</label>
      <select v-model.number="form.storage_account_id" required>
        <option v-for="acc in refs.storageAccounts" :key="acc.id" :value="acc.id">
          {{ refs.storageAccountLabel(acc) }}
        </option>
      </select>
    </div>
    <div class="form-group" v-if="form.type === 'income'">
      <label>Income Source</label>
      <select v-model.number="form.income_source_id">
        <option :value="null">— None —</option>
        <option v-for="s in refs.incomeSources" :key="s.id" :value="s.id">{{ s.name }}</option>
      </select>
    </div>
    <div class="form-group" v-if="form.type === 'expense'">
      <label>Expense Category</label>
      <select v-model.number="form.expense_category_id">
        <option :value="null">— None —</option>
        <option v-for="c in refs.expenseCategories" :key="c.id" :value="c.id">{{ c.name }}</option>
      </select>
    </div>
    <div class="form-group">
      <label>Description</label>
      <input v-model="form.description" type="text" />
    </div>
  </BaseModal>
</template>

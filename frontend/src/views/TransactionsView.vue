<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { transactionsApi, type Transaction, type TransactionCreate } from '../api/transactions'
import { useReferencesStore } from '../stores/references'

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
  const params: any = {}
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
  if (!confirm('Delete this transaction?')) return
  await transactionsApi.delete(id)
  await load()
}

function fmt(n: number) {
  return new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n)
}

function accountLabel(id: number) {
  const acc = refs.storageAccounts.find((a) => a.id === id)
  return acc ? refs.storageAccountLabel(acc) : '?'
}

function sourceName(id: number | null) {
  if (!id) return '—'
  return refs.incomeSources.find((s) => s.id === id)?.name ?? '?'
}

function categoryName(id: number | null) {
  if (!id) return '—'
  return refs.expenseCategories.find((c) => c.id === id)?.name ?? '?'
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

  <div class="card">
    <p v-if="loading">Loading...</p>
    <p v-else-if="!items.length" class="text-muted">No transactions yet.</p>
    <table v-else class="data-table">
      <thead>
        <tr>
          <th>Date</th>
          <th>Type</th>
          <th>Amount</th>
          <th>Account</th>
          <th>Source / Category</th>
          <th>Description</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="tx in items" :key="tx.id">
          <td>{{ tx.date }}</td>
          <td><span :class="['chip', tx.type === 'income' ? 'chip-income' : 'chip-expense']">{{ tx.type }}</span></td>
          <td :class="tx.type === 'income' ? 'amount-positive' : 'amount-negative'">
            {{ tx.type === 'expense' ? '-' : '' }}{{ fmt(tx.amount) }}
          </td>
          <td>{{ accountLabel(tx.storage_account_id) }}</td>
          <td>{{ tx.type === 'income' ? sourceName(tx.income_source_id) : categoryName(tx.expense_category_id) }}</td>
          <td>{{ tx.description || '' }}</td>
          <td style="white-space: nowrap">
            <button class="btn btn-secondary btn-sm" @click="openEdit(tx)">Edit</button>
            <button class="btn btn-danger btn-sm" style="margin-left: 4px" @click="remove(tx.id)">Del</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>

  <!-- Modal -->
  <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
    <div class="modal">
      <h2>{{ editing ? 'Edit' : 'New' }} Transaction</h2>
      <form @submit.prevent="save">
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
        <div class="modal-actions">
          <button type="button" class="btn btn-secondary" @click="showModal = false">Cancel</button>
          <button type="submit" class="btn btn-primary">Save</button>
        </div>
      </form>
    </div>
  </div>
</template>

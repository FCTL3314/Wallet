<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { balanceSnapshotsApi, type BalanceSnapshot, type BalanceSnapshotCreate } from '../api/balanceSnapshots'
import { analyticsApi, type BalanceByStorageEntry, type GroupBy } from '../api/analytics'
import { useReferencesStore } from '../stores/references'

const refs = useReferencesStore()
const snapshots = ref<BalanceSnapshot[]>([])
const storageData = ref<BalanceByStorageEntry[]>([])
const loading = ref(false)
const showModal = ref(false)
const editing = ref<BalanceSnapshot | null>(null)

const year = ref(new Date().getFullYear())
const groupBy = ref<GroupBy>('month')

const form = ref<BalanceSnapshotCreate>({
  storage_account_id: 0, date: new Date().toISOString().slice(0, 10), amount: 0,
})

async function load() {
  loading.value = true
  const [snaps, analytics] = await Promise.all([
    balanceSnapshotsApi.list({ date_from: `${year.value}-01-01`, date_to: `${year.value}-12-31` }),
    analyticsApi.balanceByStorage({
      date_from: `${year.value}-01-01`, date_to: `${year.value}-12-31`, group_by: groupBy.value,
    }),
  ])
  snapshots.value = snaps.data
  storageData.value = analytics.data
  loading.value = false
}

onMounted(load)

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
  if (editing.value) {
    await balanceSnapshotsApi.update(editing.value.id, form.value)
  } else {
    await balanceSnapshotsApi.create(form.value)
  }
  showModal.value = false
  await load()
}

async function remove(id: number) {
  if (!confirm('Delete this snapshot?')) return
  await balanceSnapshotsApi.delete(id)
  await load()
}

function fmt(n: number) {
  return new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n)
}

function accountLabel(id: number) {
  const acc = refs.storageAccounts.find((a) => a.id === id)
  return acc ? refs.storageAccountLabel(acc) : '?'
}

function formatPeriod(iso: string) {
  const d = new Date(iso)
  return d.toLocaleDateString('ru-RU', { year: 'numeric', month: 'short' })
}
</script>

<template>
  <h1 class="page-title">Balance Snapshots</h1>

  <div class="toolbar">
    <input v-model.number="year" type="number" min="2020" max="2030" style="width: 100px" @change="load" />
    <select v-model="groupBy" @change="load">
      <option value="month">Month</option>
      <option value="quarter">Quarter</option>
      <option value="year">Year</option>
    </select>
    <button class="btn btn-primary btn-sm" @click="openCreate">+ Add Snapshot</button>
  </div>

  <!-- Aggregated view -->
  <div class="card" v-if="storageData.length">
    <div class="card-title">Balances by Storage</div>
    <table class="data-table">
      <thead>
        <tr>
          <th>Period</th>
          <th v-for="(_, cur) in storageData[0]?.totals" :key="cur">{{ cur }} Total</th>
          <th v-for="acc in storageData[0]?.accounts" :key="acc.name">{{ acc.name }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in storageData" :key="row.period">
          <td>{{ formatPeriod(row.period) }}</td>
          <td v-for="(val, cur) in row.totals" :key="cur">{{ cur === 'USD' ? '$' : '€' }}{{ fmt(val) }}</td>
          <td v-for="acc in row.accounts" :key="acc.name">
            {{ acc.currency === 'USD' ? '$' : '€' }}{{ fmt(acc.amount) }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>

  <!-- Raw snapshots -->
  <div class="card">
    <div class="card-title">All Snapshots</div>
    <p v-if="loading">Loading...</p>
    <p v-else-if="!snapshots.length" style="color: #94a3b8">No snapshots yet.</p>
    <table v-else class="data-table">
      <thead>
        <tr>
          <th>Date</th>
          <th>Account</th>
          <th>Amount</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="s in snapshots" :key="s.id">
          <td>{{ s.date }}</td>
          <td>{{ accountLabel(s.storage_account_id) }}</td>
          <td>{{ fmt(s.amount) }}</td>
          <td style="white-space: nowrap">
            <button class="btn btn-secondary btn-sm" @click="openEdit(s)">Edit</button>
            <button class="btn btn-danger btn-sm" style="margin-left: 4px" @click="remove(s.id)">Del</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>

  <!-- Modal -->
  <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
    <div class="modal">
      <h2>{{ editing ? 'Edit' : 'New' }} Balance Snapshot</h2>
      <form @submit.prevent="save">
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
          <input v-model.number="form.amount" type="number" step="0.01" min="0" required />
        </div>
        <div class="modal-actions">
          <button type="button" class="btn btn-secondary" @click="showModal = false">Cancel</button>
          <button type="submit" class="btn btn-primary">Save</button>
        </div>
      </form>
    </div>
  </div>
</template>

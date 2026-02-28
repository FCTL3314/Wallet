<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { balanceSnapshotsApi, type BalanceSnapshot, type BalanceSnapshotCreate } from '../api/balanceSnapshots'
import { analyticsApi, type BalanceByStorageEntry, type GroupBy } from '../api/analytics'
import { useReferencesStore } from '../stores/references'
import { fmtAmount, fmtPeriod } from '../utils/format'
import BaseModal from '../components/BaseModal.vue'
import BaseDataTable from '../components/BaseDataTable.vue'
import BaseConfirmButton from '../components/BaseConfirmButton.vue'
import BaseButton from '../components/BaseButton.vue'

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
watch([year, groupBy], load)

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
  await balanceSnapshotsApi.delete(id)
  await load()
}
</script>

<template>
  <h1 class="page-title">Balance Snapshots</h1>

  <div class="toolbar">
    <input v-model.number="year" type="number" min="2020" max="2030" style="width: 100px" />
    <select v-model="groupBy">
      <option value="month">Month</option>
      <option value="quarter">Quarter</option>
      <option value="year">Year</option>
    </select>
    <BaseButton variant="primary" size="sm" @click="openCreate">+ Add Snapshot</BaseButton>
  </div>

  <!-- Aggregated view -->
  <BaseDataTable title="Balances by Storage" :loading="loading" :empty="!storageData.length" empty-message="No balance data for selected period.">
    <template #head>
      <tr>
        <th>Period</th>
        <th v-for="(_, cur) in storageData[0]?.totals" :key="cur">{{ cur }} Total</th>
        <th v-for="acc in storageData[0]?.accounts" :key="acc.name">{{ acc.name }}</th>
      </tr>
    </template>
    <template #body>
      <tr v-for="row in storageData" :key="row.period">
        <td>{{ fmtPeriod(row.period) }}</td>
        <td v-for="(val, cur) in row.totals" :key="cur">{{ refs.currencyByCode(cur)?.symbol ?? cur }}{{ fmtAmount(val) }}</td>
        <td v-for="acc in row.accounts" :key="acc.name">
          {{ refs.currencyByCode(acc.currency)?.symbol ?? acc.currency }}{{ fmtAmount(acc.amount) }}
        </td>
      </tr>
    </template>
  </BaseDataTable>

  <!-- Raw snapshots -->
  <BaseDataTable title="All Snapshots" :loading="loading" :empty="!snapshots.length" empty-message="No snapshots yet.">
    <template #head>
      <tr>
        <th>Date</th>
        <th>Account</th>
        <th>Amount</th>
        <th></th>
      </tr>
    </template>
    <template #body>
      <tr v-for="s in snapshots" :key="s.id">
        <td>{{ s.date }}</td>
        <td>{{ refs.storageAccountLabelById(s.storage_account_id) }}</td>
        <td>{{ fmtAmount(s.amount) }}</td>
        <td style="white-space: nowrap">
          <BaseButton variant="secondary" size="sm" @click="openEdit(s)">Edit</BaseButton>
          <BaseConfirmButton @confirm="remove(s.id)" />
        </td>
      </tr>
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
      <input v-model.number="form.amount" type="number" step="0.01" min="0" required />
    </div>
  </BaseModal>
</template>

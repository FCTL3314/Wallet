<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { analyticsApi, type ExpenseTemplate, type ExpenseVsBudgetItem, type ExpenseTemplateItem } from '../api/analytics'
import { expenseCategoriesApi } from '../api/references'
import { useReferencesStore } from '../stores/references'
import { fmtAmount } from '../utils/format'
import BaseModal from '../components/BaseModal.vue'
import BaseDataTable from '../components/BaseDataTable.vue'
import BaseStatCard from '../components/BaseStatCard.vue'
import BaseConfirmButton from '../components/BaseConfirmButton.vue'
import BaseButton from '../components/BaseButton.vue'

const refs = useReferencesStore()
const template = ref<ExpenseTemplate | null>(null)
const vsBudget = ref<Map<number, ExpenseVsBudgetItem>>(new Map())
const loading = ref(false)
const showModal = ref(false)
const editing = ref<ExpenseTemplateItem | null>(null)

const form = ref({ name: '', budgeted_amount: 0, is_tax: false, is_rent: false })

const resolvedItems = computed(() => {
  if (!template.value) return []
  return template.value.items.map((item) => ({
    ...item,
    actual: vsBudget.value.get(item.id)?.actual ?? 0,
    remaining: vsBudget.value.get(item.id)?.remaining ?? 0,
  }))
})

async function load() {
  loading.value = true
  const [templateRes, budgetRes] = await Promise.all([
    analyticsApi.expenseTemplate(),
    analyticsApi.expenseVsBudget(),
  ])
  template.value = templateRes.data
  vsBudget.value = new Map(budgetRes.data.map((item) => [item.id, item]))
  loading.value = false
}

onMounted(load)

function openCreate() {
  editing.value = null
  form.value = { name: '', budgeted_amount: 0, is_tax: false, is_rent: false }
  showModal.value = true
}

function openEdit(cat: ExpenseTemplateItem) {
  editing.value = cat
  form.value = { name: cat.name, budgeted_amount: cat.budgeted_amount, is_tax: cat.is_tax, is_rent: cat.is_rent }
  showModal.value = true
}

async function save() {
  if (editing.value) {
    await expenseCategoriesApi.update(editing.value.id, form.value)
  } else {
    await expenseCategoriesApi.create(form.value)
  }
  showModal.value = false
  await refs.fetchAll()
  await load()
}

async function remove(id: number) {
  await expenseCategoriesApi.delete(id)
  await refs.fetchAll()
  await load()
}
</script>

<template>
  <h1 class="page-title">Expense Template</h1>

  <div class="toolbar">
    <BaseButton variant="primary" size="sm" @click="openCreate">+ Add Category</BaseButton>
  </div>

  <div v-if="template" class="stats-grid">
    <BaseStatCard label="Total Monthly">
      <div class="stat-value">{{ fmtAmount(template.total) }}</div>
    </BaseStatCard>
    <BaseStatCard label="Without Tax">
      <div class="stat-value">{{ fmtAmount(template.without_tax) }}</div>
    </BaseStatCard>
    <BaseStatCard label="Without Rent">
      <div class="stat-value">{{ fmtAmount(template.without_rent) }}</div>
    </BaseStatCard>
    <BaseStatCard label="Without Tax & Rent">
      <div class="stat-value">{{ fmtAmount(template.without_tax_and_rent) }}</div>
    </BaseStatCard>
  </div>

  <BaseDataTable :loading="loading" :empty="!resolvedItems.length" empty-message="No expense categories yet.">
    <template #head>
      <tr>
        <th>Name</th>
        <th>Budget / Month</th>
        <th>Actual (this month)</th>
        <th>Remaining</th>
        <th>Tax</th>
        <th>Rent</th>
        <th></th>
      </tr>
    </template>
    <template #body>
      <tr v-for="item in resolvedItems" :key="item.id">
        <td>{{ item.name }}</td>
        <td>{{ fmtAmount(item.budgeted_amount) }}</td>
        <td :class="item.actual > 0 ? 'amount-negative' : ''">
          {{ fmtAmount(item.actual) }}
        </td>
        <td :class="item.remaining < 0 ? 'amount-negative' : 'amount-positive'">
          {{ fmtAmount(item.remaining) }}
        </td>
        <td>{{ item.is_tax ? 'Yes' : '' }}</td>
        <td>{{ item.is_rent ? 'Yes' : '' }}</td>
        <td style="white-space: nowrap">
          <BaseButton variant="secondary" size="sm" @click="openEdit(item)">Edit</BaseButton>
          <BaseConfirmButton @confirm="remove(item.id)" />
        </td>
      </tr>
    </template>
  </BaseDataTable>

  <BaseModal :show="showModal" :title="`${editing ? 'Edit' : 'New'} Expense Category`" @close="showModal = false" @submit="save">
    <div class="form-group">
      <label>Name</label>
      <input v-model="form.name" required />
    </div>
    <div class="form-group">
      <label>Monthly Amount ($)</label>
      <input v-model.number="form.budgeted_amount" type="number" step="0.01" min="0" required />
    </div>
    <div class="form-group">
      <div class="checkbox-group">
        <label><input type="checkbox" v-model="form.is_tax" /> Is Tax</label>
        <label><input type="checkbox" v-model="form.is_rent" /> Is Rent</label>
      </div>
    </div>
  </BaseModal>
</template>

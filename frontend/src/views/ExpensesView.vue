<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { analyticsApi, type ExpenseTemplate, type ExpenseTemplateItem } from '../api/analytics'
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
const loading = ref(false)
const showModal = ref(false)
const editing = ref<ExpenseTemplateItem | null>(null)

const form = ref({ name: '', budgeted_amount: 0, is_tax: false, is_rent: false })

async function load() {
  loading.value = true
  const { data } = await analyticsApi.expenseTemplate()
  template.value = data
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
  <h1 class="page-title">Regular Expenses</h1>

  <div class="toolbar">
    <BaseButton variant="primary" size="sm" @click="openCreate">+ Add Category</BaseButton>
  </div>

  <div v-if="template" class="stats-grid">
    <BaseStatCard label="Total Monthly">
      <div class="stat-value">{{ fmtAmount(template.total) }}</div>
    </BaseStatCard>
    <BaseStatCard label="Annual Total">
      <div class="stat-value">{{ fmtAmount(template.total * 12) }}</div>
    </BaseStatCard>
    <BaseStatCard label="Fixed Costs">
      <div class="stat-value">{{ fmtAmount(template.total - template.without_tax_and_rent) }}</div>
    </BaseStatCard>
    <BaseStatCard label="Discretionary">
      <div class="stat-value">{{ fmtAmount(template.without_tax_and_rent) }}</div>
    </BaseStatCard>
  </div>

  <BaseDataTable :loading="loading" :empty="!template?.items.length" empty-message="No expense categories yet.">
    <template #head>
      <tr>
        <th>Name</th>
        <th>Budget / Month</th>
        <th>Tags</th>
        <th></th>
      </tr>
    </template>
    <template #body>
      <tr v-for="item in template?.items" :key="item.id">
        <td>{{ item.name }}</td>
        <td>{{ fmtAmount(item.budgeted_amount) }}</td>
        <td>
          <span v-if="item.is_tax" class="type-tag">tax</span>
          <span v-if="item.is_rent" class="type-tag">rent</span>
        </td>
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

<style scoped>
.type-tag {
  display: inline-block;
  font-size: 0.7rem;
  padding: 1px 6px;
  border-radius: 9999px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: rgba(255, 255, 255, 0.35);
  margin-right: 4px;
  letter-spacing: 0.02em;
}
</style>

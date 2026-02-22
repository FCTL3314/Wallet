<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { analyticsApi, type ExpenseTemplate } from '../api/analytics'
import { expenseCategoriesApi, type ExpenseCategory } from '../api/references'
import { useReferencesStore } from '../stores/references'

const refs = useReferencesStore()
const template = ref<ExpenseTemplate | null>(null)
const loading = ref(false)
const showModal = ref(false)
const editing = ref<ExpenseCategory | null>(null)

const form = ref({ name: '', monthly_amount: 0, is_tax: false, is_rent: false })

async function load() {
  loading.value = true
  const { data } = await analyticsApi.expenseTemplate()
  template.value = data
  loading.value = false
}

onMounted(load)

function openCreate() {
  editing.value = null
  form.value = { name: '', monthly_amount: 0, is_tax: false, is_rent: false }
  showModal.value = true
}

function openEdit(cat: ExpenseCategory) {
  editing.value = cat
  form.value = { name: cat.name, monthly_amount: cat.monthly_amount, is_tax: cat.is_tax, is_rent: cat.is_rent }
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
  if (!confirm('Delete this category?')) return
  await expenseCategoriesApi.delete(id)
  await refs.fetchAll()
  await load()
}

function fmt(n: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n)
}
</script>

<template>
  <h1 class="page-title">Expense Template</h1>

  <div class="toolbar">
    <button class="btn btn-primary btn-sm" @click="openCreate">+ Add Category</button>
  </div>

  <div v-if="template" class="stats-grid">
    <div class="stat-card">
      <div class="stat-label">Total Monthly</div>
      <div class="stat-value">{{ fmt(template.total) }}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Without Tax</div>
      <div class="stat-value">{{ fmt(template.without_tax) }}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Without Rent</div>
      <div class="stat-value">{{ fmt(template.without_rent) }}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Without Tax & Rent</div>
      <div class="stat-value">{{ fmt(template.without_tax_and_rent) }}</div>
    </div>
  </div>

  <div class="card">
    <p v-if="loading">Loading...</p>
    <p v-else-if="!template?.items.length" style="color: #94a3b8">No expense categories yet.</p>
    <table v-else class="data-table">
      <thead>
        <tr>
          <th>Name</th>
          <th>Cost / Month</th>
          <th>Tax</th>
          <th>Rent</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in template!.items" :key="item.id">
          <td>{{ item.name }}</td>
          <td>{{ fmt(item.monthly_amount) }}</td>
          <td>{{ item.is_tax ? 'Yes' : '' }}</td>
          <td>{{ item.is_rent ? 'Yes' : '' }}</td>
          <td style="white-space: nowrap">
            <button class="btn btn-secondary btn-sm" @click="openEdit(item as any)">Edit</button>
            <button class="btn btn-danger btn-sm" style="margin-left: 4px" @click="remove(item.id)">Del</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>

  <!-- Modal -->
  <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
    <div class="modal">
      <h2>{{ editing ? 'Edit' : 'New' }} Expense Category</h2>
      <form @submit.prevent="save">
        <div class="form-group">
          <label>Name</label>
          <input v-model="form.name" required />
        </div>
        <div class="form-group">
          <label>Monthly Amount ($)</label>
          <input v-model.number="form.monthly_amount" type="number" step="0.01" min="0" required />
        </div>
        <div class="form-group" style="display: flex; gap: 24px">
          <label><input type="checkbox" v-model="form.is_tax" /> Is Tax</label>
          <label><input type="checkbox" v-model="form.is_rent" /> Is Rent</label>
        </div>
        <div class="modal-actions">
          <button type="button" class="btn btn-secondary" @click="showModal = false">Cancel</button>
          <button type="submit" class="btn btn-primary">Save</button>
        </div>
      </form>
    </div>
  </div>
</template>

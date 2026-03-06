<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { analyticsApi, type ExpenseTemplate, type ExpenseTemplateItem } from '../api/analytics'
import { expenseCategoriesApi } from '../api/references'
import { useReferencesStore } from '../stores/references'
import { fmtAmount } from '../utils/format'
import BaseModal from '../components/BaseModal.vue'
import BaseDataTable from '../components/BaseDataTable.vue'
import BaseCard from '../components/BaseCard.vue'
import BaseStatCard from '../components/BaseStatCard.vue'
import BaseButton from '../components/BaseButton.vue'
import EditDeleteActions from '../components/EditDeleteActions.vue'

const refs = useReferencesStore()
const template = ref<ExpenseTemplate | null>(null)
const loading = ref(false)
const showModal = ref(false)
const editing = ref<ExpenseTemplateItem | null>(null)
const removingId = ref<number | null>(null)
const newId = ref<number | null>(null)

const form = ref({ name: '', budgeted_amount: 0, tags: [] as string[] })
const tagInput = ref('')

function addTag() {
  const tag = tagInput.value.trim()
  if (tag && !form.value.tags.includes(tag)) {
    form.value.tags.push(tag)
  }
  tagInput.value = ''
}

function removeTag(tag: string) {
  form.value.tags = form.value.tags.filter(t => t !== tag)
}

function onTagKeydown(e: KeyboardEvent) {
  if (e.key === ',') {
    e.preventDefault()
    addTag()
  }
}

async function load() {
  loading.value = true
  const { data } = await analyticsApi.expenseTemplate()
  template.value = data
  loading.value = false
}

onMounted(load)

function openCreate() {
  editing.value = null
  form.value = { name: '', budgeted_amount: 0, tags: [] }
  tagInput.value = ''
  showModal.value = true
}

function openEdit(cat: ExpenseTemplateItem) {
  editing.value = cat
  form.value = { name: cat.name, budgeted_amount: cat.budgeted_amount, tags: [...cat.tags] }
  tagInput.value = ''
  showModal.value = true
}

async function save() {
  if (editing.value) {
    await expenseCategoriesApi.update(editing.value.id, form.value)
  } else {
    const { data } = await expenseCategoriesApi.create(form.value)
    newId.value = (data as { id: number }).id
  }
  showModal.value = false
  await refs.fetchAll()
  await load()
  if (newId.value !== null) {
    setTimeout(() => { newId.value = null }, 1500)
  }
}

async function remove(id: number) {
  removingId.value = id
  await new Promise((resolve) => setTimeout(resolve, 280))
  await expenseCategoriesApi.delete(id)
  removingId.value = null
  await refs.fetchAll()
  await load()
}
</script>

<template>
  <h1 class="page-title">Regular Expenses</h1>

  <div class="page-sections">
  <BaseCard>
    <BaseButton variant="primary" size="sm" @click="openCreate">+ Add Category</BaseButton>
  </BaseCard>

  <div v-if="template" class="stats-grid">
    <BaseStatCard label="Total Monthly">
      <div class="stat-value">{{ fmtAmount(template.total) }}</div>
    </BaseStatCard>
    <BaseStatCard label="Annual Total">
      <div class="stat-value">{{ fmtAmount(template.total * 12) }}</div>
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
      <tr
        v-for="(item, index) in template?.items"
        :key="item.id"
        class="table-row"
        :style="{ '--i': String(Math.min(index, 15)) }"
        :class="{ removing: item.id === removingId, 'row-new': item.id === newId }"
      >
        <td>{{ item.name }}</td>
        <td>{{ fmtAmount(item.budgeted_amount) }}</td>
        <td>
          <span v-for="tag in item.tags" :key="tag" class="type-tag">{{ tag }}</span>
        </td>
        <td style="white-space: nowrap">
          <EditDeleteActions @edit="openEdit(item)" @confirm="remove(item.id)" />
        </td>
      </tr>
    </template>
  </BaseDataTable>
  </div>

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
      <label>Tags</label>
      <div class="tag-input-wrap">
        <span v-for="tag in form.tags" :key="tag" class="type-tag editable">
          {{ tag }}<button type="button" class="tag-remove" @click="removeTag(tag)">×</button>
        </span>
        <input
          v-model="tagInput"
          class="tag-text-input"
          @keydown.enter.prevent="addTag"
          @keydown="onTagKeydown"
          placeholder="Add tag…"
        />
      </div>
    </div>
  </BaseModal>
</template>

<style scoped>
.type-tag {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 0.7rem;
  padding: 1px 6px;
  border-radius: 9999px;
  border: 1px solid rgba(0, 0, 0, 0.15);
  color: rgba(0, 0, 0, 0.40);
  margin-right: 4px;
  letter-spacing: 0.02em;
}

.tag-remove {
  background: none;
  border: none;
  color: rgba(0, 0, 0, 0.35);
  cursor: pointer;
  font-size: 0.85rem;
  line-height: 1;
  padding: 0;
  margin-left: 2px;
}

.tag-remove:hover {
  color: rgba(0, 0, 0, 0.70);
}

.tag-input-wrap {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
  padding: 6px 8px;
  border: 1px solid rgba(0, 0, 0, 0.10);
  border-radius: 6px;
  background: rgba(0, 0, 0, 0.03);
  min-height: 38px;
}

.tag-text-input {
  border: none;
  background: transparent;
  outline: none;
  color: inherit;
  font-size: 0.875rem;
  min-width: 80px;
  flex: 1;
  padding: 0;
}
</style>

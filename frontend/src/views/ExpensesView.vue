<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { analyticsApi, type ExpenseTemplate, type ExpenseTemplateItem } from '../api/analytics'
import { expenseCategoriesApi } from '../api/references'
import { useReferencesStore } from '../stores/references'
import { fmtAmount } from '../utils/format'
import { useTable, createColumnHelper } from '../composables/useTable'
import { useCrudModal } from '../composables/useCrudModal'
import BaseModal from '../components/BaseModal.vue'
import BaseDataTable from '../components/BaseDataTable.vue'
import BaseStatCard from '../components/BaseStatCard.vue'
import BaseButton from '../components/BaseButton.vue'
import EditDeleteActions from '../components/EditDeleteActions.vue'

interface ExpenseCategoryForm {
  name: string
  budgeted_amount: number
  tags: string[]
}

const refs = useReferencesStore()
const template = ref<ExpenseTemplate | null>(null)
const loading = ref(false)
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

// ── TanStack Table (client-side sort + global search) ────────────────────────

const expColHelper = createColumnHelper<ExpenseTemplateItem>()

const expenseItems = computed<ExpenseTemplateItem[]>(() => template.value?.items ?? [])

/**
 * Custom global filter function that searches across both name and tags array.
 * TanStack's built-in global filter only handles string/number scalars.
 */
function expenseGlobalFilter(
  row: { original: ExpenseTemplateItem },
  _columnId: string,
  filterValue: string,
): boolean {
  const query = String(filterValue).toLowerCase()
  if (!query) return true
  const item = row.original
  if (item.name.toLowerCase().includes(query)) return true
  return item.tags.some((t) => t.toLowerCase().includes(query))
}
expenseGlobalFilter.autoRemove = (val: unknown) => !val

const expenseColumns = [
  expColHelper.accessor('name', {
    id: 'name',
    header: 'Name',
    enableSorting: true,
    filterFn: expenseGlobalFilter as never,
  }),
  expColHelper.accessor('budgeted_amount', {
    id: 'budgeted_amount',
    header: 'Budget / Month',
    enableSorting: true,
    meta: { class: 'col-num' },
  }),
  expColHelper.accessor('tags', {
    id: 'tags',
    header: 'Tags',
    enableSorting: false,
  }),
  expColHelper.display({
    id: 'actions',
    header: '',
    enableSorting: false,
    meta: { style: 'text-align: right' },
  }),
]

const { table: expenseTable } = useTable(
  expenseColumns as import('../composables/useTable').ColumnDef<ExpenseTemplateItem>[],
  expenseItems,
  { globalFilter: true },
)

// ─────────────────────────────────────────────────────────────────────────────

async function load() {
  loading.value = true
  const { data } = await analyticsApi.expenseTemplate()
  template.value = data
  loading.value = false
}

async function afterMutate() {
  await refs.fetchAll()
  await load()
}

const {
  showModal,
  editing,
  removingId,
  newId,
  form,
  openCreate: crudOpenCreate,
  openEdit: crudOpenEdit,
  save,
  remove,
} = useCrudModal<ExpenseTemplateItem, ExpenseCategoryForm>({
  defaultForm: () => ({ name: '', budgeted_amount: 0, tags: [] }),
  toForm: (cat) => ({ name: cat.name, budgeted_amount: cat.budgeted_amount, tags: [...cat.tags] }),
  onCreate: async (data) => {
    const { data: result } = await expenseCategoriesApi.create(data)
    return result as ExpenseTemplateItem
  },
  onUpdate: async (id, data) => {
    const { data: result } = await expenseCategoriesApi.update(id, data)
    return result as ExpenseTemplateItem
  },
  onDelete: async (id) => {
    await expenseCategoriesApi.delete(id)
  },
  afterSave: () => afterMutate(),
  afterDelete: () => afterMutate(),
})

function openCreate() {
  tagInput.value = ''
  crudOpenCreate()
}

function openEdit(cat: ExpenseTemplateItem) {
  tagInput.value = ''
  crudOpenEdit(cat)
}

onMounted(load)
</script>

<template>
  <div class="sections">
  <div v-if="template" class="kpis">
    <BaseStatCard label="Budget · monthly">
      <div class="stat-value">{{ fmtAmount(template.total) }}</div>
      <div class="stat-foot"><span class="muted">{{ template.items.length }} categories</span></div>
    </BaseStatCard>
    <BaseStatCard label="Annual projection" variant="profit">
      <div class="stat-value">{{ fmtAmount(template.total * 12) }}</div>
      <div class="stat-foot"><span class="muted">If pace continues</span></div>
    </BaseStatCard>
  </div>

  <BaseDataTable
    title="Regular Expenses"
    :table="expenseTable"
    :loading="loading"
    :empty="!template?.items.length"
    empty-message="No expense categories yet."
    searchable
  >
    <template #actions>
      <div data-onboarding="add-expense-btn" style="display: inline-flex">
        <BaseButton variant="primary" size="sm" @click="openCreate">+ Add Category</BaseButton>
      </div>
    </template>
    <template #body="{ rows }">
      <tr
        v-for="(row, index) in rows"
        :key="row.original.id"
        class="table-row"
        :style="{ '--i': String(Math.min(index, 15)) }"
        :class="{ removing: row.original.id === removingId, 'row-new': row.original.id === newId }"
      >
        <td>{{ row.original.name }}</td>
        <td class="col-num">{{ fmtAmount(row.original.budgeted_amount) }}</td>
        <td>
          <span class="tag-chips">
            <span v-for="tag in row.original.tags" :key="tag" class="tag-chip">{{ tag }}</span>
          </span>
        </td>
        <td style="white-space: nowrap; text-align: right">
          <EditDeleteActions @edit="openEdit(row.original)" @confirm="remove(row.original.id)" />
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
        <span v-for="tag in form.tags" :key="tag" class="tag-chip">
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
.tag-remove {
  background: none;
  border: none;
  color: var(--ink-4);
  cursor: pointer;
  font-size: 13px;
  line-height: 1;
  padding: 0;
  margin-left: 2px;
}

.tag-remove:hover { color: var(--ink-2); }

.tag-input-wrap {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  border: 1px solid var(--hairline);
  border-radius: var(--r-inner);
  background: var(--surface);
  min-height: 40px;
  transition: border-color var(--t-fast) var(--ease), box-shadow var(--t-fast) var(--ease);
}

.tag-input-wrap:focus-within {
  border-color: var(--accent);
  box-shadow: var(--focus-ring);
}

.tag-text-input {
  border: none;
  background: transparent;
  outline: none;
  color: inherit;
  font-size: 14px;
  min-width: 80px;
  flex: 1;
  padding: 0;
}
</style>

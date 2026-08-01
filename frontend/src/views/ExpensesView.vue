<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { analyticsApi, type ExpenseTemplate, type ExpenseTemplateItem } from '../api/analytics'
import { expenseCategoriesApi } from '../api/references'
import { useReferencesStore } from '../stores/references'
import { useAuthStore } from '../stores/auth'
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

const MONTHS_PER_YEAR = 12

const refs = useReferencesStore()
const { user } = storeToRefs(useAuthStore())
const template = ref<ExpenseTemplate | null>(null)
const loading = ref(false)
const tagInput = ref('')

const baseCurrencyCode = computed(() => user.value?.base_currency_code ?? null)

const annualTotal = computed(() => (template.value?.total ?? 0) * MONTHS_PER_YEAR)

const amountFieldLabel = computed(() =>
  baseCurrencyCode.value ? `Monthly Amount (${baseCurrencyCode.value})` : 'Monthly Amount',
)

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

const expColHelper = createColumnHelper<ExpenseTemplateItem>()

const expenseItems = computed<ExpenseTemplateItem[]>(() => template.value?.items ?? [])

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
  }),
]

const { table: expenseTable } = useTable(
  expenseColumns as import('../composables/useTable').ColumnDef<ExpenseTemplateItem>[],
  expenseItems,
  { globalFilter: true },
)

async function load() {
  loading.value = true
  try {
    const { data } = await analyticsApi.expenseTemplate()
    template.value = data
  } finally {
    loading.value = false
  }
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
      <div class="stat-value">
        <span v-if="baseCurrencyCode" class="stat-currency">{{ baseCurrencyCode }}</span
        >{{ fmtAmount(template.total) }}
      </div>
      <div class="stat-foot"><span class="muted">{{ template.items.length }} categories</span></div>
    </BaseStatCard>
    <BaseStatCard label="Annual projection" variant="profit">
      <div class="stat-value">
        <span v-if="baseCurrencyCode" class="stat-currency">{{ baseCurrencyCode }}</span
        >{{ fmtAmount(annualTotal) }}
      </div>
      <div class="stat-foot"><span class="muted">Monthly budget × {{ MONTHS_PER_YEAR }}</span></div>
    </BaseStatCard>
  </div>

  <BaseDataTable
    title="Regular Expenses"
    :table="expenseTable"
    :loading="loading"
    :empty="!template?.items.length"
    empty-message="No expense categories yet."
    searchable
    mobile-cards
  >
    <template #actions>
      <div data-onboarding="add-expense-btn" class="actions-slot">
        <BaseButton variant="primary" size="sm" @click="openCreate">+ Add Category</BaseButton>
      </div>
    </template>

    <template #card="{ rows }">
      <li
        v-for="(row, index) in rows"
        :key="row.original.id"
        class="row-card table-row"
        :style="{ '--i': String(Math.min(index, 15)) }"
        :class="{ removing: row.original.id === removingId, 'row-new': row.original.id === newId }"
      >
        <div class="row-card-body">
          <div class="row-card-top">
            <span class="row-card-title">{{ row.original.name }}</span>
            <span class="row-card-amount row-card-amount--expense num">
              {{ fmtAmount(row.original.budgeted_amount) }}
            </span>
          </div>
          <span v-if="row.original.tags.length" class="tag-chips">
            <span v-for="tag in row.original.tags" :key="tag" class="tag-chip">{{ tag }}</span>
          </span>
        </div>
        <div class="row-card-actions">
          <EditDeleteActions @edit="openEdit(row.original)" @confirm="remove(row.original.id)" />
        </div>
      </li>
    </template>

    <template #body="{ rows }">
      <tr
        v-for="(row, index) in rows"
        :key="row.original.id"
        class="table-row"
        :style="{ '--i': String(Math.min(index, 15)) }"
        :class="{ removing: row.original.id === removingId, 'row-new': row.original.id === newId }"
      >
        <td class="col-name">{{ row.original.name }}</td>
        <td class="col-num">{{ fmtAmount(row.original.budgeted_amount) }}</td>
        <td class="col-tags">
          <span class="tag-chips">
            <span v-for="tag in row.original.tags" :key="tag" class="tag-chip">{{ tag }}</span>
          </span>
        </td>
        <td class="col-actions">
          <EditDeleteActions @edit="openEdit(row.original)" @confirm="remove(row.original.id)" />
        </td>
      </tr>
    </template>
  </BaseDataTable>
  </div>

  <BaseModal :show="showModal" :title="`${editing ? 'Edit' : 'New'} Expense Category`" @close="showModal = false" @submit="save">
    <div class="form-group">
      <label for="expense-name">Name</label>
      <input id="expense-name" v-model="form.name" required />
    </div>
    <div class="form-group">
      <label for="expense-amount">{{ amountFieldLabel }}</label>
      <input id="expense-amount" v-model.number="form.budgeted_amount" type="number" step="0.01" min="0" required />
    </div>
    <div class="form-group">
      <label for="expense-tags">Tags</label>
      <div class="tag-input-wrap">
        <span v-for="tag in form.tags" :key="tag" class="tag-chip">
          {{ tag }}<button type="button" class="tag-remove" :aria-label="`Remove tag ${tag}`" @click="removeTag(tag)">×</button>
        </span>
        <input
          id="expense-tags"
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
.actions-slot {
  display: inline-flex;
}

.col-actions {
  white-space: nowrap;
  text-align: right;
}

.col-name {
  overflow-wrap: anywhere;
}

.col-tags {
  max-width: 260px;
}

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

@media (hover: hover) {
  .tag-remove:hover { color: var(--ink-2); }
}

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

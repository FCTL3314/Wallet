import { computed, ref, watch, type Ref } from 'vue'

export interface CrudModalOptions<T extends { id: number }, TCreate> {
  defaultForm: () => TCreate
  toForm: (item: T) => TCreate
  onCreate: (form: TCreate) => Promise<T>
  onUpdate: (id: number, form: TCreate) => Promise<T>
  onDelete: (id: number) => Promise<void>
  afterSave?: (isCreate: boolean, result: T) => void
  afterDelete?: () => void
}

const REMOVE_ANIMATION_MS = 280
const NEW_HIGHLIGHT_MS = 1500

export function useCrudModal<T extends { id: number }, TCreate>(
  options: CrudModalOptions<T, TCreate>,
) {
  const showModal = ref(false)
  const editing = ref<T | null>(null) as Ref<T | null>
  const removingId = ref<number | null>(null)
  const newId = ref<number | null>(null)
  const touchedFields = ref(new Set<string>())
  const form = ref<TCreate>(options.defaultForm()) as Ref<TCreate>
  const saving = ref(false)
  const deleting = ref(false)
  const busy = computed(() => saving.value || deleting.value)

  watch(showModal, (val) => {
    if (!val) touchedFields.value = new Set()
  })

  function openCreate() {
    editing.value = null
    form.value = options.defaultForm()
    showModal.value = true
  }

  function openEdit(item: T) {
    editing.value = item
    form.value = options.toForm(item)
    showModal.value = true
  }

  async function save() {
    if (saving.value) return
    const current = editing.value
    const isCreate = !current
    saving.value = true
    let result: T
    try {
      result = current
        ? await options.onUpdate(current.id, form.value)
        : await options.onCreate(form.value)
    } finally {
      saving.value = false
    }
    if (isCreate) newId.value = result.id
    showModal.value = false
    options.afterSave?.(isCreate, result)
    if (isCreate) {
      setTimeout(() => {
        newId.value = null
      }, NEW_HIGHLIGHT_MS)
    }
  }

  async function remove(id: number) {
    if (deleting.value) return
    removingId.value = id
    deleting.value = true
    try {
      await new Promise<void>((resolve) => setTimeout(resolve, REMOVE_ANIMATION_MS))
      await options.onDelete(id)
    } finally {
      removingId.value = null
      deleting.value = false
    }
    options.afterDelete?.()
  }

  return {
    showModal,
    editing,
    removingId,
    newId,
    touchedFields,
    form,
    saving,
    deleting,
    busy,
    openCreate,
    openEdit,
    save,
    remove,
  }
}

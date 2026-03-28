import { ref, watch } from 'vue'

export interface CrudModalOptions<T extends { id: number }, TCreate> {
  defaultForm: () => TCreate
  toForm: (item: T) => TCreate
  onCreate: (form: TCreate) => Promise<T>
  onUpdate: (id: number, form: TCreate) => Promise<T>
  onDelete: (id: number) => Promise<void>
  afterSave?: (isCreate: boolean, result: T) => void
  afterDelete?: () => void
}

export function useCrudModal<T extends { id: number }, TCreate>(
  options: CrudModalOptions<T, TCreate>,
) {
  const showModal = ref(false)
  const editing = ref<T | null>(null)
  const removingId = ref<number | null>(null)
  const newId = ref<number | null>(null)
  const touchedFields = ref(new Set<string>())
  const form = ref<TCreate>(options.defaultForm()) as import('vue').Ref<TCreate>

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
    const isCreate = !editing.value
    let result: T
    if (editing.value) {
      result = await options.onUpdate(editing.value.id, form.value)
    } else {
      result = await options.onCreate(form.value)
      newId.value = result.id
    }
    showModal.value = false
    options.afterSave?.(isCreate, result)
    if (isCreate) {
      setTimeout(() => {
        newId.value = null
      }, 1500)
    }
  }

  async function remove(id: number) {
    removingId.value = id
    await new Promise<void>((resolve) => setTimeout(resolve, 280))
    await options.onDelete(id)
    removingId.value = null
    options.afterDelete?.()
  }

  return {
    showModal,
    editing,
    removingId,
    newId,
    touchedFields,
    form,
    openCreate,
    openEdit,
    save,
    remove,
  }
}

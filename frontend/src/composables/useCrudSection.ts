import { useNotificationsStore } from '../stores/notifications'

interface CrudOptions {
  entityName?: string
  addSuccessMessage?: string
  removeSuccessMessage?: string
}

const DEFAULT_ENTITY_NAME = 'Item'

export function useCrudSection<TCreate>(
  api: {
    create: (data: TCreate) => Promise<unknown>
    delete: (id: number) => Promise<unknown>
  },
  afterMutate: () => Promise<void>,
  options: CrudOptions = {},
) {
  const notifications = useNotificationsStore()
  const entityName = options.entityName ?? DEFAULT_ENTITY_NAME

  function notifySuccess(message: string) {
    notifications.add({ type: 'success', title: 'Success', message })
  }

  async function add(data: TCreate) {
    await api.create(data)
    await afterMutate()
    notifySuccess(options.addSuccessMessage ?? `${entityName} added`)
  }

  async function remove(id: number) {
    await api.delete(id)
    await afterMutate()
    notifySuccess(options.removeSuccessMessage ?? `${entityName} deleted`)
  }

  return { add, remove }
}

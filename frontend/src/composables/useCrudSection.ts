import { useNotificationsStore } from '../stores/notifications'

interface CrudOptions {
  addSuccessMessage?: string
  removeSuccessMessage?: string
}

export function useCrudSection<TCreate>(
  api: {
    create: (data: TCreate) => Promise<unknown>
    delete: (id: number) => Promise<unknown>
  },
  afterMutate: () => Promise<void>,
  options: CrudOptions = {},
) {
  const notifications = useNotificationsStore()

  async function add(data: TCreate) {
    await api.create(data)
    await afterMutate()
    if (options.addSuccessMessage) {
      notifications.add({ type: 'success', title: 'Success', message: options.addSuccessMessage })
    }
  }

  async function remove(id: number) {
    await api.delete(id)
    await afterMutate()
    if (options.removeSuccessMessage) {
      notifications.add({ type: 'success', title: 'Success', message: options.removeSuccessMessage })
    }
  }

  return { add, remove }
}

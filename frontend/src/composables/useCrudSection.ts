export function useCrudSection<TCreate>(
  api: {
    create: (data: TCreate) => Promise<unknown>
    delete: (id: number) => Promise<unknown>
  },
  afterMutate: () => Promise<void>,
) {
  async function add(data: TCreate) {
    await api.create(data)
    await afterMutate()
  }

  async function remove(id: number, confirmMsg: string) {
    if (!confirm(confirmMsg)) return
    await api.delete(id)
    await afterMutate()
  }

  return { add, remove }
}

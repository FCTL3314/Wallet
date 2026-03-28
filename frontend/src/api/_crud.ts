import api from './client'

/**
 * Creates a standard CRUD API object for a given endpoint.
 *
 * @template T  - Response type (the entity returned by the API)
 * @template C  - Create/update payload type
 * @template P  - List params type (defaults to Record<string, unknown>)
 */
export function createCrudApi<T, C, P = Record<string, unknown>>(endpoint: string) {
  return {
    list: (params?: P) => api.get<T[]>(`/${endpoint}/`, { params }),
    create: (data: C) => api.post<T>(`/${endpoint}/`, data),
    update: (id: number, data: Partial<C>) => api.put<T>(`/${endpoint}/${id}`, data),
    delete: (id: number) => api.delete(`/${endpoint}/${id}`),
  }
}

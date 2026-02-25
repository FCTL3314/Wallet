import api from './client'

export interface Currency {
  id: number
  code: string
  symbol: string
}

export interface StorageLocation {
  id: number
  name: string
}

export interface StorageAccount {
  id: number
  storage_location_id: number
  currency_id: number
  storage_location?: StorageLocation
  currency?: Currency
}

export interface IncomeSource {
  id: number
  name: string
}

export interface ExpenseCategory {
  id: number
  name: string
  budgeted_amount: number
  is_tax: boolean
  is_rent: boolean
}

export const currenciesApi = {
  list: () => api.get<Currency[]>('/currencies/'),
  create: (data: Omit<Currency, 'id'>) => api.post<Currency>('/currencies/', data),
  update: (id: number, data: Partial<Currency>) => api.put<Currency>(`/currencies/${id}`, data),
  delete: (id: number) => api.delete(`/currencies/${id}`),
}

export const storageLocationsApi = {
  list: () => api.get<StorageLocation[]>('/storage-locations/'),
  create: (data: { name: string }) => api.post<StorageLocation>('/storage-locations/', data),
  update: (id: number, data: { name?: string }) => api.put<StorageLocation>(`/storage-locations/${id}`, data),
  delete: (id: number) => api.delete(`/storage-locations/${id}`),
}

export const storageAccountsApi = {
  list: () => api.get<StorageAccount[]>('/storage-accounts/'),
  create: (data: { storage_location_id: number; currency_id: number }) =>
    api.post<StorageAccount>('/storage-accounts/', data),
  update: (id: number, data: { storage_location_id?: number }) =>
    api.put<StorageAccount>(`/storage-accounts/${id}`, data),
  delete: (id: number) => api.delete(`/storage-accounts/${id}`),
}

export const incomeSourcesApi = {
  list: () => api.get<IncomeSource[]>('/income-sources/'),
  create: (data: { name: string }) => api.post<IncomeSource>('/income-sources/', data),
  update: (id: number, data: { name?: string }) => api.put<IncomeSource>(`/income-sources/${id}`, data),
  delete: (id: number) => api.delete(`/income-sources/${id}`),
}

export const expenseCategoriesApi = {
  list: () => api.get<ExpenseCategory[]>('/expense-categories/'),
  create: (data: Omit<ExpenseCategory, 'id'>) => api.post<ExpenseCategory>('/expense-categories/', data),
  update: (id: number, data: Partial<ExpenseCategory>) =>
    api.put<ExpenseCategory>(`/expense-categories/${id}`, data),
  delete: (id: number) => api.delete(`/expense-categories/${id}`),
}

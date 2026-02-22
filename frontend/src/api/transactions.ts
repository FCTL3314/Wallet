import api from './client'

export interface Transaction {
  id: number
  type: 'income' | 'expense'
  date: string
  amount: number
  description: string | null
  currency_id: number
  storage_account_id: number
  income_source_id: number | null
  expense_category_id: number | null
}

export interface TransactionCreate {
  type: 'income' | 'expense'
  date: string
  amount: number
  description?: string | null
  currency_id: number
  storage_account_id: number
  income_source_id?: number | null
  expense_category_id?: number | null
}

export interface TransactionFilters {
  type?: 'income' | 'expense'
  date_from?: string
  date_to?: string
  income_source_id?: number
  expense_category_id?: number
  storage_account_id?: number
  limit?: number
  offset?: number
}

export const transactionsApi = {
  list: (filters?: TransactionFilters) => api.get<Transaction[]>('/transactions/', { params: filters }),
  create: (data: TransactionCreate) => api.post<Transaction>('/transactions/', data),
  update: (id: number, data: Partial<TransactionCreate>) => api.put<Transaction>(`/transactions/${id}`, data),
  delete: (id: number) => api.delete(`/transactions/${id}`),
}

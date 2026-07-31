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

export type TransactionSortField = 'date' | 'amount' | 'income_source' | 'storage_account'
export type SortOrder = 'asc' | 'desc'

export interface TransactionQueryFilters {
  type?: 'income' | 'expense'
  date_from?: string
  date_to?: string
  income_source_id?: number
  expense_category_id?: number
  storage_account_id?: number
}

export interface TransactionFilters extends TransactionQueryFilters {
  limit?: number
  offset?: number
  sort_by?: TransactionSortField
  sort_order?: SortOrder
}

export interface TransactionCurrencyTotal {
  currency_id: number
  currency_code: string
  amount: number
}

export interface TransactionSummary {
  count: number
  totals: TransactionCurrencyTotal[]
}

export const transactionsApi = {
  list: (filters?: TransactionFilters) => api.get<Transaction[]>('/transactions/', { params: filters }),
  summary: (filters?: TransactionQueryFilters) =>
    api.get<TransactionSummary>('/transactions/summary', { params: filters }),
  create: (data: TransactionCreate) => api.post<Transaction>('/transactions/', data),
  update: (id: number, data: Partial<TransactionCreate>) => api.put<Transaction>(`/transactions/${id}`, data),
  delete: (id: number) => api.delete(`/transactions/${id}`),
}

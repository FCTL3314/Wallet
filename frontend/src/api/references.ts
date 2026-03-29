import api from './client'
import { createCrudApi } from './_crud'

export interface Currency {
  id: number
  code: string
  symbol: string
  name: string | null
  catalog_id: number | null
  is_custom: boolean
}

export interface CatalogCurrency {
  id: number
  code: string
  symbol: string
  name: string
  currency_type: 'fiat' | 'crypto'
  has_rates: boolean
}

export interface RateInfo {
  status: 'ok' | 'stale' | 'missing'
  valid_date: string | null
  source: string
  rate: string | null
}

export interface UserManualRate {
  id: number
  from_code: string
  to_code: string
  rate: string
  valid_from: string
  valid_to: string | null
}

export interface ManualRateCreate {
  to_code: string
  rate: number
  valid_from: string
  valid_to?: string | null
}

export type CurrencyCreatePayload =
  | { catalog_id: number }
  | { code: string; symbol: string; name?: string }

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
  tags: string[]
}

export const currenciesApi = {
  list: () => api.get<Currency[]>('/currencies/'),
  catalog: (params?: { search?: string; limit?: number }) =>
    api.get<CatalogCurrency[]>('/currencies/catalog', { params }),
  create: (data: CurrencyCreatePayload) => api.post<Currency>('/currencies/', data),
  update: (id: number, data: Partial<Pick<Currency, 'code' | 'symbol' | 'name'>>) =>
    api.put<Currency>(`/currencies/${id}`, data),
  delete: (id: number) => api.delete(`/currencies/${id}`),
  getRate: (currencyId: number) => api.get<RateInfo>(`/currencies/${currencyId}/rates`),
  getManualRates: (currencyId: number) =>
    api.get<UserManualRate[]>(`/currencies/${currencyId}/manual-rates`),
  createManualRate: (currencyId: number, data: ManualRateCreate) =>
    api.post<UserManualRate>(`/currencies/${currencyId}/manual-rate`, data),
  deleteManualRate: (currencyId: number, rateId: number) =>
    api.delete(`/currencies/${currencyId}/manual-rates/${rateId}`),
  rateHistory: (currencyId: number, days?: number) =>
    api.get<RateInfo[]>(`/currencies/${currencyId}/rates/history`, { params: { days } }),
  ratesAll: (toCode?: string) =>
    api.get<Record<number, RateInfo>>('/currencies/rates/all', toCode ? { params: { to_code: toCode } } : undefined),
}

export const storageLocationsApi = createCrudApi<StorageLocation, { name: string }>('storage-locations')

export const storageAccountsApi = createCrudApi<
  StorageAccount,
  { storage_location_id: number; currency_id: number }
>('storage-accounts')

export const incomeSourcesApi = createCrudApi<IncomeSource, { name: string }>('income-sources')

export const expenseCategoriesApi = createCrudApi<ExpenseCategory, Omit<ExpenseCategory, 'id'>>('expense-categories')

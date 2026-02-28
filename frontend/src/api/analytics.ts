import api from './client'

export type GroupBy = 'month' | 'quarter' | 'year'

export interface SummaryEntry {
  period: string
  income: number
  profit: number
  derived_expense: number
  avg_income: number
  avg_profit: number
  balances: Record<string, number>
  balance_change: Record<string, number>
}

export interface IncomeBySourceEntry {
  period: string
  total: number
  sources: Record<string, number>
}

export interface BalanceByStorageAccount {
  name: string
  currency: string
  amount: number
}

export interface BalanceByStorageEntry {
  period: string
  accounts: BalanceByStorageAccount[]
  totals: Record<string, number>
}

export interface ExpenseTemplateItem {
  id: number
  name: string
  budgeted_amount: number
  is_tax: boolean
  is_rent: boolean
}

export interface ExpenseTemplate {
  items: ExpenseTemplateItem[]
  total: number
  without_tax: number
  without_rent: number
  without_tax_and_rent: number
}

export interface AnalyticsParams {
  date_from: string
  date_to: string
  group_by?: GroupBy
}

export interface ExpenseVsBudgetItem {
  id: number
  name: string
  budgeted: number
  actual: number
  remaining: number
}

export const analyticsApi = {
  summary: (params: AnalyticsParams) => api.get<SummaryEntry[]>('/analytics/summary', { params }),
  incomeBySource: (params: AnalyticsParams) =>
    api.get<IncomeBySourceEntry[]>('/analytics/income-by-source', { params }),
  balanceByStorage: (params: AnalyticsParams) =>
    api.get<BalanceByStorageEntry[]>('/analytics/balance-by-storage', { params }),
  expenseTemplate: () => api.get<ExpenseTemplate>('/analytics/expense-template'),
  expenseVsBudget: (params?: { year?: number; month?: number }) =>
    api.get<ExpenseVsBudgetItem[]>('/analytics/expense-vs-budget', { params }),
}

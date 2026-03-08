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
  is_bootstrap?: boolean
}

export interface GrowthStat {
  delta: number
  pct: number | null
  from_period: string
  to_period: string
}

export interface BalanceGrowth {
  delta: Record<string, number>
  pct: Record<string, number | null>
}

export interface SummaryStats {
  income_growth: GrowthStat | null
  profit_growth: GrowthStat | null
  balance_growth: BalanceGrowth
  total_income: number
  total_profit: number
  active_period_count: number
  income_period_count: number
}

export interface SummaryResponse {
  periods: SummaryEntry[]
  stats: SummaryStats | null
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
  tags: string[]
}

export interface ExpenseTemplate {
  items: ExpenseTemplateItem[]
  total: number
}

export interface AnalyticsParams {
  date_from: string
  date_to: string
  group_by?: GroupBy
  currency_id?: number
}

export interface ExpenseVsBudgetItem {
  id: number
  name: string
  budgeted: number
  actual: number
  remaining: number
}

export interface BalanceBreakdownItem {
  account_id: number
  account_label: string
  currency: string
  latest_snapshot_date: string
  latest_snapshot_amount: number
}

export interface DateRange {
  min_date: string | null
  max_date: string | null
}

export const analyticsApi = {
  summary: (params: AnalyticsParams) => api.get<SummaryResponse>('/analytics/summary', { params }),
  incomeBySource: (params: AnalyticsParams) =>
    api.get<IncomeBySourceEntry[]>('/analytics/income-by-source', { params }),
  balanceByStorage: (params: AnalyticsParams) =>
    api.get<BalanceByStorageEntry[]>('/analytics/balance-by-storage', { params }),
  expenseTemplate: () => api.get<ExpenseTemplate>('/analytics/expense-template'),
  expenseVsBudget: (params?: { year?: number; month?: number }) =>
    api.get<ExpenseVsBudgetItem[]>('/analytics/expense-vs-budget', { params }),
  balanceBreakdown: () => api.get<BalanceBreakdownItem[]>('/analytics/balance-breakdown'),
  dateRange: () => api.get<DateRange>('/analytics/date-range'),
}

import api from './client'

export type GroupBy = 'month' | 'quarter' | 'year'

export interface SummaryEntry {
  period: string
  income: number
  profit: number
  derived_expense: number
  avg_income: number
  avg_profit: number
  avg_expense: number
  balances: Record<string, number>
  balance_change: Record<string, number>
  /** Balance brought in by accounts tracked for the first time in this period. */
  opening_capital: Record<string, number>
  is_bootstrap?: boolean
  /** False when the balance was only carried forward, so profit is unknown rather than zero. */
  is_measured: boolean
  converted_balance?: number
  /** Currencies left out of converted_balance because no rate was available. */
  conversion_missing?: string[]
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

export interface BalanceGrowthConverted {
  delta: number
  pct: number | null
  currency: string
}

export interface SummaryStats {
  income_growth: GrowthStat | null
  profit_growth: GrowthStat | null
  balance_growth: BalanceGrowth
  balance_growth_converted: BalanceGrowthConverted | null
  total_income: number
  total_profit: number
  total_expense: number
  avg_income: number
  avg_profit: number
  avg_expense: number
  /** Periods where profit could actually be measured — the denominator of every average. */
  accountable_period_count: number
  income_period_count: number
}

export interface RateCoverageEntry {
  status: 'ok' | 'stale' | 'missing'
  valid_date: string | null
  source: string
  rate: string | null
}

export interface RateCoverage {
  base_currency: string
  currencies: Record<string, RateCoverageEntry>
  conversion_available: boolean
}

export interface SummaryResponse {
  periods: SummaryEntry[]
  stats: SummaryStats | null
  rate_coverage: RateCoverage | null
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
  convert_to?: string
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
  balanceBreakdown: () => api.get<BalanceBreakdownItem[]>('/analytics/balance-breakdown'),
  dateRange: () => api.get<DateRange>('/analytics/date-range'),
}

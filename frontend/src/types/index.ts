// Re-export analytics response types for convenient importing
export type {
  GroupBy,
  SummaryEntry,
  SummaryResponse,
  SummaryStats,
  GrowthStat,
  BalanceGrowth,
  BalanceByStorageEntry,
  ExpenseVsBudgetItem,
  ExpenseTemplateItem,
  ExpenseTemplate,
} from '../api/analytics'

export type Preset = 'All' | 'YTD' | '3M' | '6M' | '12M' | 'custom'
export const PRESET_OPTIONS: Preset[] = ['All', 'YTD', '3M', '6M', '12M']

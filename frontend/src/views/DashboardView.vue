<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { useThemeStore } from '../stores/theme'
import { analyticsApi, type GroupBy, type IncomeBySourceEntry, type BalanceBreakdownItem, type SummaryStats, type RateCoverage } from '../api/analytics'
import { useReferencesStore } from '../stores/references'
import { storeToRefs } from 'pinia'
import { fmtAmount, fmtPeriod } from '../utils/format'
import { buildLineChartOption, buildDonutChartOption, DONUT_COLORS, type TooltipBreakdownRow } from '../utils/charts'
import { useTable, createColumnHelper } from '../composables/useTable'
import { useDateRange } from '../composables/useDateRange'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import BaseCard from '../components/BaseCard.vue'
import BaseDataTable from '../components/BaseDataTable.vue'
import BaseStatCard from '../components/BaseStatCard.vue'
import PeriodFilterBar from '../components/PeriodFilterBar.vue'
import type { SummaryEntry } from '../types/index'
import { PhWallet, PhTrendUp, PhChartLine, PhCaretUp, PhCaretDown, PhWarning, PhArrowsClockwise, PhCurrencyCircleDollar } from '@phosphor-icons/vue'

use([CanvasRenderer, LineChart, PieChart, GridComponent, TooltipComponent, LegendComponent])

const refs = useReferencesStore()
const { currencies } = storeToRefs(refs)
const themeStore = useThemeStore()
const isDark = computed(() => themeStore.mode === 'dark')

const groupBy = ref<GroupBy>('month')
const periods = ref<SummaryEntry[]>([])
const stats = ref<SummaryStats | null>(null)
const rateCoverage = ref<RateCoverage | null>(null)
const sourceData = ref<IncomeBySourceEntry[]>([])
const loading = ref(false)
const selectedCurrencyId = ref<number | 'all'>('all')
const convertToCurrency = ref<string>('USD')

const isAllMode = computed(() => selectedCurrencyId.value === 'all')

watch(
  currencies,
  () => {
    // Set default convert-to currency to USD if available, else first currency
    const usd = refs.currencyByCode('USD')
    if (usd) {
      convertToCurrency.value = 'USD'
    } else if (currencies.value.length) {
      const first = currencies.value[0]
      if (first) convertToCurrency.value = first.code
    }
  },
  { immediate: true },
)
const { dateFrom, dateTo, activePreset, allRange, initRange } = useDateRange('YTD')

const breakdown = ref<BalanceBreakdownItem[]>([])
const showBreakdown = ref(false)
const hoveredPeriod = ref<string | null>(null)

async function loadBreakdown() {
  const { data: bd } = await analyticsApi.balanceBreakdown()
  breakdown.value = bd
}

async function load() {
  loading.value = true
  try {
    const params = {
      date_from: dateFrom.value,
      date_to: dateTo.value,
      group_by: groupBy.value,
      currency_id: isAllMode.value ? undefined : (selectedCurrencyId.value as number),
      convert_to: isAllMode.value ? convertToCurrency.value : undefined,
    }
    const [summaryRes, sourceRes] = await Promise.all([
      analyticsApi.summary(params),
      analyticsApi.incomeBySource(params),
    ])
    periods.value = summaryRes.data.periods
    stats.value = summaryRes.data.stats
    rateCoverage.value = summaryRes.data.rate_coverage ?? null
    sourceData.value = sourceRes.data
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  load()
  loadBreakdown()
  initRange()
})
watch([dateFrom, dateTo, groupBy, selectedCurrencyId, convertToCurrency], load)

const lastEntry = computed(() => periods.value[periods.value.length - 1] ?? null)
const chartEntries = computed(() => periods.value.filter((e) => !e.is_bootstrap))
const avgIncome = computed(() => lastEntry.value?.avg_income ?? 0)
const avgProfit = computed(() => lastEntry.value?.avg_profit ?? 0)

const totalIncome = computed(() => stats.value?.total_income ?? 0)
const totalProfit = computed(() => stats.value?.total_profit ?? 0)
const activePeriodCount = computed(() => stats.value?.active_period_count ?? 0)
const incomePeriodCount = computed(() => stats.value?.income_period_count ?? 0)

const incomeGrowthLong = computed(() => {
  const g = stats.value?.income_growth
  if (!g) return null
  return { delta: g.delta, pct: g.pct, firstPeriod: g.from_period, lastPeriod: g.to_period }
})

const profitGrowthLong = computed(() => {
  const g = stats.value?.profit_growth
  if (!g) return null
  return { delta: g.delta, pct: g.pct, firstPeriod: g.from_period, lastPeriod: g.to_period }
})

const balanceGrowth = computed(() => stats.value?.balance_growth ?? null)
const balanceGrowthConverted = computed(() => stats.value?.balance_growth_converted ?? null)
const isConverted = computed(() => isAllMode.value && hasMultipleCurrencies.value)

const missingCurrencies = computed<string[]>(() => {
  const rc = rateCoverage.value
  if (!rc || rc.conversion_available) return []
  if (!isAllMode.value && currencies.value.length <= 1) return []
  return Object.entries(rc.currencies)
    .filter(([, entry]) => entry.status === 'missing' || entry.status === 'stale')
    .map(([code]) => code)
})

interface RowDelta {
  income: { delta: number; pct: number | null } | null
  profit: { delta: number; pct: number | null } | null
}

// Shape of each row in the summary table (entry + delta annotations)
interface SummaryTableRow {
  entry: SummaryEntry
  income: RowDelta['income']
  profit: RowDelta['profit']
}

const tableData = computed<SummaryTableRow[]>(() => {
  const nonBoot = periods.value.filter((e) => !e.is_bootstrap)
  const indexMap = new Map(nonBoot.map((e, i) => [e.period, i]))
  return periods.value.map((entry) => {
    const deltas: RowDelta = { income: null, profit: null }
    if (!entry.is_bootstrap) {
      const idx = indexMap.get(entry.period)
      if (idx !== undefined && idx > 0) {
        const prev = nonBoot[idx - 1]!
        const id = entry.income - prev.income
        const pd = entry.profit - prev.profit
        deltas.income = { delta: id, pct: prev.income !== 0 ? (id / prev.income) * 100 : null }
        deltas.profit = { delta: pd, pct: prev.profit !== 0 ? (pd / Math.abs(prev.profit)) * 100 : null }
      }
    }
    return { entry, ...deltas }
  })
})

// ── TanStack Table for Summary Table (client-side sort, no text filter) ───────

const summaryColHelper = createColumnHelper<SummaryTableRow>()

const summaryColumns = [
  summaryColHelper.accessor((row) => row.entry.period, {
    id: 'period',
    header: 'Period',
    enableSorting: false,
  }),
  summaryColHelper.accessor((row) => Object.values(row.entry.balances).reduce((s, v) => s + Number(v), 0), {
    id: 'balance',
    header: 'Balance',
    enableSorting: true,
    meta: { class: 'col-num' },
  }),
  summaryColHelper.accessor((row) => row.entry.income, {
    id: 'income',
    header: 'Income',
    enableSorting: true,
    meta: { class: 'col-num' },
  }),
  summaryColHelper.accessor((row) => row.entry.profit, {
    id: 'profit',
    header: 'Profit',
    enableSorting: true,
    meta: { class: 'col-num' },
  }),
  summaryColHelper.accessor((row) => row.entry.derived_expense, {
    id: 'expense',
    header: 'Expense',
    enableSorting: true,
    meta: { class: 'col-num' },
  }),
  summaryColHelper.accessor((row) => row.entry.avg_income, {
    id: 'avg_income',
    header: 'Avg Income',
    enableSorting: true,
    meta: { class: 'col-num' },
  }),
  summaryColHelper.accessor((row) => row.entry.avg_profit, {
    id: 'avg_profit',
    header: 'Avg Profit',
    enableSorting: true,
    meta: { class: 'col-num' },
  }),
]

const { table: summaryTable } = useTable(
  summaryColumns as import('../composables/useTable').ColumnDef<SummaryTableRow>[],
  tableData,
)

// ─────────────────────────────────────────────────────────────────────────────

const avgIncomeHint = computed(() =>
  `Average income per active period.\n\nTotal income: ${fmtAmount(totalIncome.value)}\nActive periods: ${incomePeriodCount.value}\nResult: ${fmtAmount(totalIncome.value)} ÷ ${incomePeriodCount.value} = ${fmtAmount(avgIncome.value)}\n\nPeriods with no income are excluded.`
)
const avgProfitHint = computed(() =>
  `Average profit per active period.\n\nTotal profit: ${fmtAmount(totalProfit.value)}\nActive periods: ${activePeriodCount.value}\nResult: ${fmtAmount(totalProfit.value)} ÷ ${activePeriodCount.value} = ${fmtAmount(avgProfit.value)}\n\nProfit = Income − Expenses. Can be negative if spending exceeds income.`
)

const displayCurrencyCode = computed(() => {
  if (isAllMode.value) return convertToCurrency.value
  return refs.currencyById(selectedCurrencyId.value as number)?.code ?? null
})

const displayedBalances = computed(() => lastEntry.value?.balances ?? {})

const hasMultipleCurrencies = computed(() => Object.keys(displayedBalances.value).length > 1)

const showRateDetails = ref(false)

type TrendKey = 'income' | 'expense' | 'profit'
const selectedTrend = ref<TrendKey>('income')

const TREND_OPTIONS: { key: TrendKey; label: string; borderColor: string; backgroundColor: string }[] = [
  { key: 'income',  label: 'Income',  borderColor: '#1fa068', backgroundColor: 'rgba(31,160,104,0.10)' },
  { key: 'expense', label: 'Expense', borderColor: '#e84565', backgroundColor: 'rgba(232,69,101,0.08)' },
  { key: 'profit',  label: 'Profit',  borderColor: '#2272cc', backgroundColor: 'rgba(34,114,204,0.08)' },
]

const sourceByPeriod = computed(() => {
  const m = new Map<string, Record<string, number>>()
  for (const entry of sourceData.value) m.set(entry.period, entry.sources)
  return m
})

const trendBreakdown = computed<(TooltipBreakdownRow[] | null)[]>(() => {
  const key = selectedTrend.value
  return chartEntries.value.map((e) => {
    if (key === 'income') {
      const sources = sourceByPeriod.value.get(e.period)
      if (!sources) return null
      const rows = Object.entries(sources)
        .map(([label, value]) => ({ label, value: Number(value) }))
        .filter((r) => r.value !== 0)
        .sort((a, b) => b.value - a.value)
      return rows.length ? rows : null
    }
    if (key === 'profit') {
      const rows = Object.entries(e.balance_change ?? {})
        .map(([label, value]) => ({ label, value: Number(value), prefix: Number(value) >= 0 ? '+' : '' }))
        .filter((r) => r.value !== 0)
        .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
      return rows.length ? rows : null
    }
    // expense = income − profit → show the decomposition
    if (e.income === 0 && e.profit === 0) return null
    const rows: TooltipBreakdownRow[] = [
      { label: 'Income', value: e.income },
      { label: '− Profit', value: e.profit },
    ]
    return rows
  })
})

const lineOption = computed(() => {
  const t = TREND_OPTIONS.find((o) => o.key === selectedTrend.value)!
  const dataMap: Record<TrendKey, (e: SummaryEntry) => number> = {
    income:  (e) => e.income,
    expense: (e) => e.derived_expense,
    profit:  (e) => e.profit,
  }
  return buildLineChartOption(
    chartEntries.value.map((e) => fmtPeriod(e.period)),
    chartEntries.value.map(dataMap[selectedTrend.value]),
    t.label,
    t.borderColor,
    t.backgroundColor,
    displayCurrencyCode.value,
    (idx) => { hoveredPeriod.value = idx !== null ? (chartEntries.value[idx]?.period ?? null) : null },
    isDark.value,
    trendBreakdown.value,
  )
})

const balanceLineOption = computed(() => {
  const code = displayCurrencyCode.value
  const values = chartEntries.value.map((e) => {
    if (isAllMode.value && e.converted_balance != null) return e.converted_balance
    return code ? (e.balances[code] ?? 0) : Object.values(e.balances)[0] ?? 0
  })
  return buildLineChartOption(
    chartEntries.value.map((e) => fmtPeriod(e.period)),
    values,
    'Balance',
    '#5585c5',
    'rgba(85,133,197,0.09)',
    code,
    () => {},
    isDark.value,
  )
})

const donutTotals = computed(() => {
  const totals: Record<string, number> = {}
  for (const entry of sourceData.value) {
    for (const [source, amount] of Object.entries(entry.sources)) {
      totals[source] = (totals[source] ?? 0) + Number(amount)
    }
  }
  return totals
})

const donutStats = computed(() => {
  const entries = Object.entries(donutTotals.value)
    .map(([name, amount], i) => ({ name, amount, color: DONUT_COLORS[i] ?? '#ccc' }))
    .sort((a, b) => b.amount - a.amount)
  const total = entries.reduce((s, e) => s + e.amount, 0)
  return { entries, total }
})

const donutOption = computed(() => {
  const labels = Object.keys(donutTotals.value)
  return buildDonutChartOption(
    labels,
    labels.map((l) => donutTotals.value[l] ?? 0),
    DONUT_COLORS.slice(0, labels.length),
    isDark.value,
  )
})


</script>

<template>
  <div class="page-sections">
  <BaseCard data-onboarding="dashboard-period-filter">
    <PeriodFilterBar
      v-model:dateFrom="dateFrom"
      v-model:dateTo="dateTo"
      v-model:groupBy="groupBy"
      v-model:activePreset="activePreset"
      :allRange="allRange"
    />
    <div v-if="currencies.length" class="currency-bar">
      <div class="currency-tabs">
        <div class="all-group" :class="{ 'all-group--active': selectedCurrencyId === 'all' }">
          <button
            class="tab-pill tab-pill--all"
            :class="{ 'tab-pill--active': selectedCurrencyId === 'all' }"
            @click="selectedCurrencyId = 'all'"
            :title="isAllMode && currencies.length > 1 ? `Combine all currencies into ${convertToCurrency}` : 'Show all currencies'"
          ><PhCurrencyCircleDollar :size="14" weight="bold" /> All</button>
          <template v-if="isAllMode && currencies.length > 1">
            <span class="all-group-arrow" aria-hidden="true">→</span>
            <label class="all-group-select">
              <PhArrowsClockwise :size="12" weight="bold" class="convert-to-icon" />
              <select v-model="convertToCurrency" class="convert-select" aria-label="Convert all currencies to">
                <option v-for="cur in currencies" :key="cur.code" :value="cur.code">{{ cur.code }}</option>
              </select>
            </label>
          </template>
        </div>
        <button
          v-for="cur in currencies"
          :key="cur.id"
          class="tab-pill"
          :class="{ 'tab-pill--active': selectedCurrencyId === cur.id }"
          @click="selectedCurrencyId = cur.id"
        >{{ cur.code }}</button>
      </div>
    </div>
  </BaseCard>

  <!-- Rate warning — inline, after controls, only when there's a problem -->
  <BaseCard v-if="missingCurrencies.length" class="rate-coverage-warning">
    <div class="warning-content">
      <PhWarning :size="18" weight="fill" class="warning-icon" />
      <span>Rates missing or stale for <strong>{{ missingCurrencies.join(', ') }}</strong> — converted totals may be inaccurate. Rates sync automatically; you can also set manual rates.</span>
      <RouterLink to="/references" class="warning-link">Set manual rate</RouterLink>
    </div>
  </BaseCard>

  <div v-if="periods.length" class="stats-grid">
    <BaseStatCard label="Current Balance" :icon="PhWallet">
      <!-- All mode: converted total is the hero number -->
      <template v-if="isAllMode && lastEntry?.converted_balance != null && hasMultipleCurrencies">
        <div class="stat-value">
          <span class="stat-currency">≈{{ convertToCurrency }}</span>{{ fmtAmount(lastEntry.converted_balance) }}
        </div>
        <div class="balance-breakdown-mini">
          <span v-for="(val, cur) in displayedBalances" :key="cur" class="balance-part">
            {{ cur }} {{ fmtAmount(val) }}
          </span>
        </div>
      </template>
      <!-- Single currency mode: show the one balance -->
      <template v-else>
        <div v-for="(val, cur) in displayedBalances" :key="cur" class="stat-value">
          <span class="stat-currency">{{ cur }}</span>{{ fmtAmount(val) }}
        </div>
      </template>
      <div v-if="!Object.keys(displayedBalances).length" class="stat-value">—</div>
      <!-- All mode with multiple currencies: show single converted growth -->
      <template v-if="isAllMode && hasMultipleCurrencies && balanceGrowthConverted">
        <div
          class="stat-trend"
          :class="balanceGrowthConverted.delta >= 0 ? 'trend--up' : 'trend--down'"
        >
          <PhCaretUp v-if="balanceGrowthConverted.delta >= 0" :size="9" weight="fill" />
          <PhCaretDown v-else :size="9" weight="fill" />
          <span>≈{{ balanceGrowthConverted.currency }} {{ balanceGrowthConverted.delta >= 0 ? '+' : '' }}{{ fmtAmount(balanceGrowthConverted.delta) }}</span>
          <span v-if="balanceGrowthConverted.pct !== null" class="stat-trend-label">
            ({{ Math.abs(balanceGrowthConverted.pct).toFixed(1) }}%)
          </span>
        </div>
      </template>
      <!-- Single currency or no conversion: show per-currency growth -->
      <template v-else-if="balanceGrowth">
        <div
          v-for="(delta, cur) in balanceGrowth.delta"
          :key="cur"
          class="stat-trend"
          :class="delta >= 0 ? 'trend--up' : 'trend--down'"
        >
          <PhCaretUp v-if="delta >= 0" :size="9" weight="fill" />
          <PhCaretDown v-else :size="9" weight="fill" />
          <span>{{ cur }} {{ delta >= 0 ? '+' : '' }}{{ fmtAmount(delta) }}</span>
          <span v-if="balanceGrowth.pct[cur] !== null" class="stat-trend-label">
            ({{ Math.abs(balanceGrowth.pct[cur]!).toFixed(1) }}%)
          </span>
        </div>
      </template>
      <button class="breakdown-toggle" @click="showBreakdown = !showBreakdown">
        <span class="breakdown-toggle-line" />
        <span class="breakdown-toggle-label">Accounts</span>
        <PhCaretDown :size="11" weight="bold" class="breakdown-toggle-caret" :class="{ 'breakdown-toggle-caret--open': showBreakdown }" />
      </button>
      <div v-if="showBreakdown && breakdown.length" class="breakdown-list">
        <div v-for="item in breakdown" :key="item.account_id" class="breakdown-row">
          <span class="breakdown-label">{{ item.account_label }}</span>
          <span class="breakdown-amount">{{ item.currency }} {{ fmtAmount(item.latest_snapshot_amount) }}</span>
          <span class="breakdown-date">{{ item.latest_snapshot_date }}</span>
        </div>
      </div>
    </BaseStatCard>
    <BaseStatCard
      label="Avg Income"
      variant="income"
      :hint="avgIncomeHint"
      :icon="PhTrendUp"
    >
      <div class="stat-value amount-positive">
        <span class="stat-currency">{{ displayCurrencyCode }}</span>{{ fmtAmount(avgIncome) }}
      </div>
      <span v-if="isAllMode && hasMultipleCurrencies" class="converted-hint">≈ converted</span>
      <div
        v-if="incomeGrowthLong"
        class="stat-trend"
        :class="incomeGrowthLong.delta >= 0 ? 'trend--up' : 'trend--down'"
      >
        <PhCaretUp v-if="incomeGrowthLong.delta >= 0" :size="9" weight="fill" />
        <PhCaretDown v-else :size="9" weight="fill" />
        <span v-if="incomeGrowthLong.pct !== null">{{ Math.abs(incomeGrowthLong.pct).toFixed(1) }}%</span>
        <span class="stat-trend-label">{{ fmtPeriod(incomeGrowthLong.firstPeriod) }} → {{ fmtPeriod(incomeGrowthLong.lastPeriod) }}</span>
      </div>
    </BaseStatCard>
    <BaseStatCard
      label="Avg Profit"
      variant="profit"
      :hint="avgProfitHint"
      :icon="PhChartLine"
    >
      <div class="stat-value" :class="avgProfit >= 0 ? 'amount-positive' : 'amount-negative'">
        <span class="stat-currency">{{ displayCurrencyCode }}</span>{{ fmtAmount(avgProfit) }}
      </div>
      <span v-if="isAllMode && hasMultipleCurrencies" class="converted-hint">≈ converted</span>
      <div
        v-if="profitGrowthLong"
        class="stat-trend"
        :class="profitGrowthLong.delta >= 0 ? 'trend--up' : 'trend--down'"
      >
        <PhCaretUp v-if="profitGrowthLong.delta >= 0" :size="9" weight="fill" />
        <PhCaretDown v-else :size="9" weight="fill" />
        <span v-if="profitGrowthLong.pct !== null">{{ Math.abs(profitGrowthLong.pct).toFixed(1) }}%</span>
        <span class="stat-trend-label">{{ fmtPeriod(profitGrowthLong.firstPeriod) }} → {{ fmtPeriod(profitGrowthLong.lastPeriod) }}</span>
      </div>
    </BaseStatCard>
  </div>

  <!-- Rate details — collapsible, only in All mode with actual rate data -->
  <button
    v-if="isAllMode && rateCoverage && Object.keys(rateCoverage.currencies).length"
    class="rate-details-toggle"
    @click="showRateDetails = !showRateDetails"
  >
    <PhArrowsClockwise :size="13" weight="bold" />
    <span>Exchange rates</span>
    <span v-if="rateCoverage.conversion_available" class="rate-details-status rate-details-status--ok">up to date</span>
    <span v-else class="rate-details-status rate-details-status--warn">issues</span>
    <PhCaretDown :size="10" weight="bold" :class="{ 'caret--open': showRateDetails }" />
  </button>
  <BaseCard v-if="showRateDetails && rateCoverage" class="rate-info-card">
    <div class="rate-info-grid">
      <div v-for="(entry, code) in rateCoverage.currencies" :key="code" class="rate-info-row">
        <span class="rate-info-pair">1 {{ code }}</span>
        <span class="rate-info-eq">=</span>
        <span class="rate-info-rate" :class="{ 'rate-info-rate--missing': !entry.rate }">
          {{ entry.rate ? fmtAmount(Number(entry.rate)) : '?' }} {{ rateCoverage.base_currency }}
        </span>
        <span class="rate-status" :class="'rate-status--' + entry.status">{{ entry.status }}</span>
        <RouterLink
          v-if="refs.currencyByCode(String(code))"
          :to="{ path: '/references', query: { openRates: refs.currencyByCode(String(code))!.id } }"
          class="rate-set-btn"
        >Set rate</RouterLink>
      </div>
    </div>
  </BaseCard>

  <BaseCard v-if="periods.length" :title="isConverted ? `Trends (≈${convertToCurrency})` : 'Trends'">
    <template #actions>
      <div class="trend-tabs">
        <button
          v-for="t in TREND_OPTIONS"
          :key="t.key"
          class="tab-pill"
          :class="{ 'tab-pill--active': selectedTrend === t.key }"
          @click="selectedTrend = t.key"
        >{{ t.label }}</button>
      </div>
    </template>
    <v-chart :option="lineOption" :style="{ height: '280px' }" autoresize @globalout="hoveredPeriod = null" />
  </BaseCard>

  <BaseCard v-if="chartEntries.length" :title="isAllMode && hasMultipleCurrencies ? `Balance Over Time (≈${convertToCurrency})` : 'Balance Over Time'">
    <v-chart :option="balanceLineOption" :style="{ height: '280px' }" autoresize />
  </BaseCard>

  <BaseCard v-if="Object.keys(donutTotals).length" :title="isConverted ? `Income by Source (≈${convertToCurrency})` : 'Income by Source'">
    <div class="donut-layout">
      <v-chart :option="donutOption" class="donut-chart" autoresize />
      <div class="donut-stats">
        <div v-for="item in donutStats.entries" :key="item.name" class="donut-stat-row">
          <span class="donut-dot" :style="{ background: item.color }" />
          <span class="donut-stat-name">{{ item.name }}</span>
          <span class="donut-stat-pct">{{ donutStats.total > 0 ? Math.round(item.amount / donutStats.total * 100) : 0 }}%</span>
          <span class="donut-stat-amount">{{ isConverted ? '≈' : '' }}{{ fmtAmount(item.amount) }}</span>
        </div>
        <div class="donut-stat-total">
          <span>Total</span>
          <span>{{ isConverted ? '≈' : '' }}{{ fmtAmount(donutStats.total) }}</span>
        </div>
      </div>
    </div>
  </BaseCard>

  <BaseDataTable
    :title="isConverted ? `Summary Table (≈${convertToCurrency})` : 'Summary Table'"
    :table="summaryTable"
    :loading="loading"
    :empty="!periods.length"
    empty-message="No data for selected period."
  >
    <template #body="{ rows }">
      <tr
        v-for="tableRow in rows"
        :key="tableRow.original.entry.period"
        :class="{ 'row-highlighted': tableRow.original.entry.period === hoveredPeriod }"
      >
        <td>
          {{ fmtPeriod(tableRow.original.entry.period) }}
          <span
            v-if="tableRow.original.entry.is_bootstrap"
            class="badge-initial"
            title="Starting balance snapshot — reflects initial capital entered by the user, not real earned income or profit."
          >Initial</span>
        </td>
        <td class="col-num">
          <template v-if="Object.keys(tableRow.original.entry.balances).length">
            <!-- All mode: show converted total as primary, per-currency as secondary -->
            <template v-if="isAllMode && tableRow.original.entry.converted_balance != null && Object.keys(tableRow.original.entry.balances).length > 1">
              <span class="balance-line balance-line--primary">≈{{ convertToCurrency }} {{ fmtAmount(tableRow.original.entry.converted_balance) }}</span>
              <span v-for="(val, cur) in tableRow.original.entry.balances" :key="cur" class="balance-line balance-line--secondary">{{ cur }} {{ fmtAmount(val) }}</span>
            </template>
            <!-- Single currency: just show the value -->
            <template v-else>
              <span v-for="(val, cur) in tableRow.original.entry.balances" :key="cur" class="balance-line">{{ cur }} {{ fmtAmount(val) }}</span>
            </template>
          </template>
          <span v-else>—</span>
        </td>
        <td class="col-num">
          <div class="amount-positive">{{ isConverted ? '≈' : '' }}{{ fmtAmount(tableRow.original.entry.income) }}</div>
          <div v-if="tableRow.original.income" class="cell-delta" :class="tableRow.original.income.delta >= 0 ? 'trend--up' : 'trend--down'">
            <PhCaretUp v-if="tableRow.original.income.delta >= 0" :size="7" weight="fill" />
            <PhCaretDown v-else :size="7" weight="fill" />
            <span v-if="tableRow.original.income.pct !== null">{{ Math.abs(tableRow.original.income.pct).toFixed(1) }}%</span>
            <span v-else>{{ tableRow.original.income.delta >= 0 ? '+' : '' }}{{ isConverted ? '≈' : '' }}{{ fmtAmount(tableRow.original.income.delta) }}</span>
          </div>
        </td>
        <td class="col-num">
          <div :class="tableRow.original.entry.profit >= 0 ? 'amount-positive' : 'amount-negative'">{{ isConverted ? '≈' : '' }}{{ fmtAmount(tableRow.original.entry.profit) }}</div>
          <div v-if="tableRow.original.profit" class="cell-delta" :class="tableRow.original.profit.delta >= 0 ? 'trend--up' : 'trend--down'">
            <PhCaretUp v-if="tableRow.original.profit.delta >= 0" :size="7" weight="fill" />
            <PhCaretDown v-else :size="7" weight="fill" />
            <span v-if="tableRow.original.profit.pct !== null">{{ Math.abs(tableRow.original.profit.pct).toFixed(1) }}%</span>
            <span v-else>{{ tableRow.original.profit.delta >= 0 ? '+' : '' }}{{ isConverted ? '≈' : '' }}{{ fmtAmount(tableRow.original.profit.delta) }}</span>
          </div>
        </td>
        <td class="col-num" :class="tableRow.original.entry.derived_expense > 0 ? 'amount-negative' : 'amount-positive'">
          {{ tableRow.original.entry.income === 0 && tableRow.original.entry.profit === 0 ? '—' : `${isConverted ? '≈' : ''}${fmtAmount(tableRow.original.entry.derived_expense)}` }}
        </td>
        <td class="col-num">{{ isConverted ? '≈' : '' }}{{ fmtAmount(tableRow.original.entry.avg_income) }}</td>
        <td class="col-num" :class="tableRow.original.entry.avg_profit >= 0 ? 'amount-positive' : 'amount-negative'">{{ isConverted ? '≈' : '' }}{{ fmtAmount(tableRow.original.entry.avg_profit) }}</td>
      </tr>
    </template>
  </BaseDataTable>
  </div>
</template>

<style scoped>
/* ── Currency bar: tabs + convert-to control ────────────────── */

.currency-bar {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-top: 0.75rem;
  flex-wrap: wrap;
}

.currency-tabs {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.tab-pill {
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid var(--card-border);
  background: rgba(0, 0, 0, 0.05);
  color: var(--text-secondary);
  transition: background 0.15s, color 0.15s;
}

[data-theme="dark"] .tab-pill { background: rgba(255, 255, 255, 0.05); }
.tab-pill:hover:not(:disabled) { background: rgba(0, 0, 0, 0.10); color: var(--text-primary); }
[data-theme="dark"] .tab-pill:hover:not(:disabled) { background: rgba(255, 255, 255, 0.10); }
.tab-pill:disabled { cursor: default; }

.tab-pill--active {
  background: rgba(var(--color-accent-rgb), 0.10);
  border-color: rgba(var(--color-accent-rgb), 0.40);
  color: var(--color-accent);
}

.tab-pill--all {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.all-group {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 2px;
  border-radius: 9999px;
  transition: background 0.15s, border-color 0.15s;
}

.all-group--active {
  background: rgba(var(--color-accent-rgb), 0.06);
  box-shadow: inset 0 0 0 1px rgba(var(--color-accent-rgb), 0.25);
}

.all-group .tab-pill--all {
  margin: 0;
}

.all-group-arrow {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-accent);
  opacity: 0.7;
  user-select: none;
}

.all-group-select {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 0.22rem 0.6rem 0.22rem 0.55rem;
  border-radius: 9999px;
  background: var(--card-bg);
  border: 1px solid rgba(var(--color-accent-rgb), 0.35);
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}

.all-group-select:hover {
  border-color: rgba(var(--color-accent-rgb), 0.55);
}

.convert-to-icon {
  color: var(--color-accent);
  opacity: 0.75;
  flex-shrink: 0;
}

.convert-select {
  border: none;
  outline: none;
  background: transparent;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--color-accent);
  cursor: pointer;
  padding: 0;
  padding-right: 2px;
  appearance: none;
  -webkit-appearance: none;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='10' height='10' viewBox='0 0 24 24' fill='none' stroke='%235585c5' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'><polyline points='6 9 12 15 18 9'/></svg>");
  background-repeat: no-repeat;
  background-position: right center;
  padding-right: 14px;
}

/* ── Trend tabs ─────────────────────────────────────────────── */

.trend-tabs {
  display: flex;
  gap: 0.3rem;
}

.trend-tabs .tab-pill {
  padding: 0.15rem 0.5rem;
  font-size: 0.72rem;
}

/* ── Balance stat card — All mode breakdown ─────────────────── */

.balance-breakdown-mini {
  display: flex;
  flex-wrap: wrap;
  gap: 0.15rem 0.65rem;
  margin-top: 0.35rem;
}

.balance-part {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--text-label);
  font-variant-numeric: tabular-nums;
}

/* "converted" hint below stat values in All mode */
.converted-hint {
  display: inline-block;
  font-size: 0.6rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-placeholder);
  margin-top: 2px;
}

/* ── Summary table: balance lines ───────────────────────────── */

.balance-line {
  display: block;
}

.balance-line--primary {
  display: block;
  font-weight: 600;
}

.balance-line--secondary {
  display: block;
  font-size: 0.72rem;
  color: var(--text-label);
  font-weight: 400;
}

/* ── Rate details toggle (between stat cards and charts) ────── */

.rate-details-toggle {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 0.3rem 0.7rem;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 0.72rem;
  font-weight: 500;
  color: var(--text-label);
  transition: color 0.15s;
}

.rate-details-toggle:hover {
  color: var(--text-secondary);
}

.rate-details-toggle .caret--open {
  transform: rotate(180deg);
}

.rate-details-status {
  font-size: 0.65rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 0.05rem 0.35rem;
  border-radius: 9999px;
}

.rate-details-status--ok {
  background: rgba(74, 170, 128, 0.12);
  color: var(--color-income);
}

.rate-details-status--warn {
  background: rgba(224, 184, 74, 0.15);
  color: var(--color-warning);
}

/* ── Rate info card (expanded) ──────────────────────────────── */

.rate-info-card {
  font-size: 0.82rem;
}

.rate-info-grid {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.rate-info-row {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  font-size: 0.82rem;
}

.rate-info-pair {
  font-weight: 600;
  min-width: 4rem;
  color: var(--text-primary);
}

.rate-info-eq {
  color: var(--text-placeholder);
  font-size: 0.75rem;
}

.rate-info-rate {
  font-variant-numeric: tabular-nums;
  font-weight: 600;
  color: var(--text-primary);
  min-width: 6rem;
}

.rate-info-rate--missing {
  color: var(--color-expense);
}

.rate-status {
  font-size: 0.6rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 0.1rem 0.35rem;
  border-radius: 9999px;
  min-width: 3rem;
  text-align: center;
}

.rate-status--ok {
  background: rgba(74, 170, 128, 0.12);
  color: var(--color-income);
}

.rate-status--stale {
  background: rgba(224, 184, 74, 0.12);
  color: var(--color-warning);
}

.rate-status--missing {
  background: rgba(212, 104, 120, 0.12);
  color: var(--color-expense);
}

.rate-set-btn {
  margin-left: auto;
  padding: 0.15rem 0.5rem;
  font-size: 0.7rem;
  font-weight: 500;
  border-radius: 6px;
  border: 1px solid var(--card-border);
  background: rgba(var(--color-accent-rgb), 0.08);
  color: var(--color-accent);
  text-decoration: none;
  transition: background 0.15s, border-color 0.15s;
}

.rate-set-btn:hover {
  background: rgba(var(--color-accent-rgb), 0.15);
  border-color: rgba(var(--color-accent-rgb), 0.40);
}

/* ── Rate coverage warning ──────────────────────────────────── */

.rate-coverage-warning {
  border-left: 4px solid var(--color-warning);
  background: rgba(224, 184, 74, 0.08);
}

.warning-content {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  font-size: 0.82rem;
  flex-wrap: wrap;
}

.warning-icon {
  color: var(--color-warning);
  flex-shrink: 0;
}

.warning-link {
  margin-left: auto;
  color: var(--color-accent);
  font-weight: 500;
  text-decoration: none;
  white-space: nowrap;
  flex-shrink: 0;
}

.warning-link:hover {
  text-decoration: underline;
}

/* ── Breakdown toggle + list ────────────────────────────────── */

.breakdown-toggle {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin-top: 0.75rem;
  width: 100%;
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  color: var(--text-placeholder);
  transition: color 0.15s;
}

.breakdown-toggle:hover { color: var(--text-secondary); }

.breakdown-toggle-line {
  flex: 1;
  height: 1px;
  background: var(--card-border);
}

.breakdown-toggle-label {
  font-size: 0.7rem;
  font-weight: 500;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  flex-shrink: 0;
}

.breakdown-toggle-caret {
  flex-shrink: 0;
  transition: transform 0.2s ease;
}

.breakdown-toggle-caret--open { transform: rotate(180deg); }

.breakdown-list {
  margin-top: 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.breakdown-row {
  display: flex;
  gap: 0.5rem;
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.breakdown-label { flex: 1; }
.breakdown-amount { color: var(--text-primary); }
.breakdown-date { color: var(--text-label); }

/* ── Table misc ─────────────────────────────────────────────── */

.row-highlighted { background: rgba(14, 96, 192, 0.08); }

.cell-delta {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: 0.68rem;
  font-weight: 600;
  margin-top: 2px;
  font-variant-numeric: tabular-nums;
}

.cell-delta.trend--up { color: var(--color-income); }
.cell-delta.trend--down { color: var(--color-expense); }

.badge-initial {
  display: inline-block;
  margin-left: 0.4rem;
  padding: 0.1rem 0.45rem;
  font-size: 0.65rem;
  font-weight: 600;
  letter-spacing: 0.03em;
  border-radius: 9999px;
  background: rgba(255, 193, 7, 0.15);
  color: #b45309;
  border: 1px solid rgba(255, 193, 7, 0.40);
  vertical-align: middle;
  cursor: default;
}

[data-theme="dark"] .badge-initial {
  background: rgba(255, 193, 7, 0.12);
  color: var(--color-warning);
  border-color: rgba(255, 193, 7, 0.30);
}

/* ── Donut chart ────────────────────────────────────────────── */

.donut-layout {
  display: flex;
  align-items: center;
  gap: 2rem;
}

.donut-chart {
  flex: 0 0 220px;
  height: 220px;
}

.donut-stats {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.donut-stat-row {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  font-size: 0.85rem;
}

.donut-dot {
  flex-shrink: 0;
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.donut-stat-name {
  flex: 1;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.donut-stat-pct {
  font-size: 0.75rem;
  color: var(--text-label);
  min-width: 2.8rem;
  text-align: right;
}

.donut-stat-amount {
  font-variant-numeric: tabular-nums;
  font-weight: 500;
  color: var(--text-primary);
  min-width: 5rem;
  text-align: right;
}

.donut-stat-total {
  display: flex;
  justify-content: space-between;
  padding-top: 0.5rem;
  margin-top: 0.25rem;
  border-top: 1px solid var(--card-border);
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-secondary);
}

/* ── Responsive ─────────────────────────────────────────────── */

@media (max-width: 640px) {
  .currency-bar { flex-direction: column; align-items: stretch; }
  .all-group { flex-wrap: wrap; }
  .trend-tabs { flex-wrap: wrap; }
  .warning-link { margin-left: 0; }
  .donut-layout { flex-direction: column; align-items: stretch; }
  .donut-chart { flex: none; width: 100%; }
}
</style>

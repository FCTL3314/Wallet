<script setup lang="ts">
import {computed, onMounted, ref, watch} from 'vue'
import {RouterLink} from 'vue-router'
import {useThemeStore} from '../stores/theme'
import {
  analyticsApi,
  type BalanceBreakdownItem,
  type GroupBy,
  type IncomeBySourceEntry,
  type RateCoverage,
  type SummaryStats
} from '../api/analytics'
import {useReferencesStore} from '../stores/references'
import {storeToRefs} from 'pinia'
import {fmtAmount, fmtPeriod} from '../utils/format'
import {buildDonutChartOption, buildLineChartOption, DONUT_COLORS, type TooltipBreakdownRow} from '../utils/charts'
import {useDateRange} from '../composables/useDateRange'
import VChart from 'vue-echarts'
import {use} from 'echarts/core'
import {CanvasRenderer} from 'echarts/renderers'
import {LineChart, PieChart} from 'echarts/charts'
import {GridComponent, LegendComponent, TooltipComponent} from 'echarts/components'
import BaseCard from '../components/BaseCard.vue'
import BaseDataTable from '../components/BaseDataTable.vue'
import PeriodFilterBar from '../components/PeriodFilterBar.vue'
import RateBadge from '../components/RateBadge.vue'
import GrowthBadge from '../components/GrowthBadge.vue'
import type {SummaryEntry} from '../types/index'
import {PhArrowsClockwise, PhCaretDown, PhCaretRight, PhWallet, PhWarning,} from '@phosphor-icons/vue'

use([CanvasRenderer, LineChart, PieChart, GridComponent, TooltipComponent, LegendComponent])

const refs = useReferencesStore()
const {currencies} = storeToRefs(refs)
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
      const usd = refs.currencyByCode('USD')
      if (usd) convertToCurrency.value = 'USD'
      else if (currencies.value.length) {
        const first = currencies.value[0]
        if (first) convertToCurrency.value = first.code
      }
    },
    {immediate: true},
)
const {dateFrom, dateTo, activePreset, allRange, initRange} = useDateRange('YTD')

const breakdown = ref<BalanceBreakdownItem[]>([])
const showBreakdown = ref(false)
const hoveredPeriod = ref<string | null>(null)

async function loadBreakdown() {
  const {data: bd} = await analyticsApi.balanceBreakdown()
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
const avgExpense = computed(() => Math.max(0, avgIncome.value - avgProfit.value))

const balanceGrowth = computed(() => stats.value?.balance_growth ?? null)
const balanceGrowthConverted = computed(() => stats.value?.balance_growth_converted ?? null)
const isConverted = computed(() => isAllMode.value && hasMultipleCurrencies.value)

const incomeGrowth = computed(() => stats.value?.income_growth ?? null)
const profitGrowth = computed(() => stats.value?.profit_growth ?? null)

const rateAsOf = computed<string | null>(() => {
  const rc = rateCoverage.value
  if (!rc) return null
  let newest: string | null = null
  for (const entry of Object.values(rc.currencies)) {
    if (entry.valid_date && (!newest || entry.valid_date > newest)) newest = entry.valid_date
  }
  return newest
})

const showRateBadge = computed(() => isAllMode.value && hasMultipleCurrencies.value && rateAsOf.value !== null)

const missingCurrencies = computed<string[]>(() => {
  const rc = rateCoverage.value
  if (!rc || rc.conversion_available) return []
  if (!isAllMode.value && currencies.value.length <= 1) return []
  return Object.entries(rc.currencies)
      .filter(([, e]) => e.status === 'missing' || e.status === 'stale')
      .map(([code]) => code)
})

const displayCurrencyCode = computed(() => {
  if (isAllMode.value) return convertToCurrency.value
  return refs.currencyById(selectedCurrencyId.value as number)?.code ?? null
})

const displayedBalances = computed(() => lastEntry.value?.balances ?? {})
const hasMultipleCurrencies = computed(() => Object.keys(displayedBalances.value).length > 1)

// Hero number split: integer + cents
const heroTotalRaw = computed(() => {
  if (isAllMode.value && lastEntry.value?.converted_balance != null && hasMultipleCurrencies.value) {
    return lastEntry.value.converted_balance
  }
  const vals = Object.values(displayedBalances.value)
  return vals.length ? Number(vals[0]) : 0
})

const heroWhole = computed(() => Math.floor(Math.abs(heroTotalRaw.value)))
const heroCents = computed(() =>
    String(Math.round((Math.abs(heroTotalRaw.value) - heroWhole.value) * 100)).padStart(2, '0'),
)
const heroCcy = computed(() => displayCurrencyCode.value || '')

// Hero growth (converted in All mode if available)
const heroGrowth = computed(() => {
  if (isAllMode.value && hasMultipleCurrencies.value && balanceGrowthConverted.value) {
    return {
      delta: balanceGrowthConverted.value.delta,
      pct: balanceGrowthConverted.value.pct,
    }
  }
  if (balanceGrowth.value && heroCcy.value) {
    return {
      delta: balanceGrowth.value.delta[heroCcy.value] ?? 0,
      pct: balanceGrowth.value.pct[heroCcy.value] ?? null,
    }
  }
  return null
})

// Trend chart
type TrendKey = 'balance' | 'income' | 'expense' | 'profit'
const selectedTrend = ref<TrendKey>('balance')

const TREND_OPTIONS: { key: TrendKey; label: string; borderColor: string; backgroundColor: string }[] = [
  {key: 'balance', label: 'Balance', borderColor: '#4aaa80', backgroundColor: 'rgba(74,170,128,0.10)'},
  {key: 'income', label: 'Income', borderColor: '#4aaa80', backgroundColor: 'rgba(74,170,128,0.10)'},
  {key: 'expense', label: 'Expenses', borderColor: '#d46878', backgroundColor: 'rgba(212,104,120,0.10)'},
  {key: 'profit', label: 'Profit', borderColor: '#5e8b6e', backgroundColor: 'rgba(94,139,110,0.10)'},
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
          .map(([label, value]) => ({label, value: Number(value)}))
          .filter((r) => r.value !== 0)
          .sort((a, b) => b.value - a.value)
      return rows.length ? rows : null
    }
    if (key === 'profit') {
      const rows = Object.entries(e.balance_change ?? {})
          .map(([label, value]) => ({label, value: Number(value), prefix: Number(value) >= 0 ? '+' : ''}))
          .filter((r) => r.value !== 0)
          .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
      return rows.length ? rows : null
    }
    if (key === 'expense') {
      if (e.income === 0 && e.profit === 0) return null
      return [
        {label: 'Income', value: e.income},
        {label: '− Profit', value: e.profit},
      ]
    }
    return null
  })
})

const lineOption = computed(() => {
  const t = TREND_OPTIONS.find((o) => o.key === selectedTrend.value)!
  if (selectedTrend.value === 'balance') {
    const code = displayCurrencyCode.value
    const values = chartEntries.value.map((e) => {
      if (isAllMode.value && e.converted_balance != null) return e.converted_balance
      return code ? (e.balances[code] ?? 0) : Object.values(e.balances)[0] ?? 0
    })
    return buildLineChartOption(
        chartEntries.value.map((e) => fmtPeriod(e.period)),
        values,
        'Balance',
        t.borderColor,
        t.backgroundColor,
        code,
        () => {
        },
        isDark.value,
    )
  }
  const dataMap: Record<Exclude<TrendKey, 'balance'>, (e: SummaryEntry) => number> = {
    income: (e) => e.income,
    expense: (e) => e.derived_expense,
    profit: (e) => e.profit,
  }
  return buildLineChartOption(
      chartEntries.value.map((e) => fmtPeriod(e.period)),
      chartEntries.value.map(dataMap[selectedTrend.value as Exclude<TrendKey, 'balance'>]),
      t.label,
      t.borderColor,
      t.backgroundColor,
      displayCurrencyCode.value,
      (idx) => {
        hoveredPeriod.value = idx !== null ? (chartEntries.value[idx]?.period ?? null) : null
      },
      isDark.value,
      trendBreakdown.value,
  )
})

// Donut: income by source
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
      .map(([name, amount], i) => ({name, amount, color: DONUT_COLORS[i] ?? '#ccc'}))
      .sort((a, b) => b.amount - a.amount)
  const total = entries.reduce((s, e) => s + e.amount, 0)
  return {entries, total}
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


const showRateDetails = ref(false)
</script>

<template>
  <div class="sections">
    <BaseCard data-onboarding="dashboard-period-filter" class="filter-card">
      <PeriodFilterBar
          v-model:dateFrom="dateFrom"
          v-model:dateTo="dateTo"
          v-model:groupBy="groupBy"
          v-model:activePreset="activePreset"
          :allRange="allRange"
      >
        <template #middle>
          <span class="label">Currency</span>
          <div class="segmented">
            <button :class="{ on: selectedCurrencyId === 'all' }" @click="selectedCurrencyId = 'all'">All</button>
            <button
                v-for="cur in currencies"
                :key="cur.id"
                :class="{ on: selectedCurrencyId === cur.id }"
                @click="selectedCurrencyId = cur.id"
            >{{ cur.code }}
            </button>
          </div>
          <template v-if="isAllMode && currencies.length > 1">
            <span class="muted ccy-arrow">→</span>
            <span class="label">in</span>
            <div class="segmented segmented--mini">
              <button
                  v-for="cur in currencies"
                  :key="cur.code"
                  :class="{ on: convertToCurrency === cur.code }"
                  @click="convertToCurrency = cur.code"
              >{{ cur.code }}
              </button>
            </div>
          </template>
        </template>
      </PeriodFilterBar>
    </BaseCard>

    <BaseCard v-if="missingCurrencies.length" class="warning-card">
      <div class="row warning-row">
        <PhWarning :size="18" weight="fill" class="warning-icon"/>
        <span>
          Rates missing or stale for <strong>{{ missingCurrencies.join(', ') }}</strong> — converted totals may be inaccurate.
        </span>
        <RouterLink to="/references" class="warning-link">Set manual rate</RouterLink>
      </div>
    </BaseCard>

    <!-- Hero balance card -->
    <div v-if="periods.length" class="card hero">
      <div class="hero-main">
        <div class="hero-label">
          <span class="label">Total balance</span>
          <GrowthBadge v-if="heroGrowth" :delta="heroGrowth.delta">
            <span v-if="heroGrowth.pct !== null">
              {{ heroGrowth.pct >= 0 ? '+' : '' }}{{ heroGrowth.pct.toFixed(1) }}%
            </span>
            <span v-else>
              {{ heroGrowth.delta >= 0 ? '+' : '−' }}{{ fmtAmount(Math.abs(heroGrowth.delta)) }}
            </span>
          </GrowthBadge>
          <RateBadge v-if="showRateBadge" :as-of="rateAsOf"/>
        </div>
        <div class="hero-number">
          <span class="ccy">{{ heroCcy }}</span>
          <span>{{ heroWhole.toLocaleString('en-US') }}</span>
          <span class="cents">.{{ heroCents }}</span>
        </div>
        <div v-if="hasMultipleCurrencies" class="hero-foot">
          <span
              v-for="(val, cur) in displayedBalances"
              :key="cur"
              class="num"
          >{{ cur }} {{ fmtAmount(val) }}</span>
        </div>
        <div class="hero-actions row">
          <RouterLink to="/transactions" class="btn btn--primary">+ Add transaction</RouterLink>
          <RouterLink to="/balance-snapshots" class="btn">+ New snapshot</RouterLink>
          <button
              v-if="breakdown.length"
              class="btn btn--ghost"
              @click="showBreakdown = !showBreakdown"
          >
            <PhCaretRight
                :size="13"
                weight="bold"
                :class="['accounts-caret', { 'accounts-caret--open': showBreakdown }]"
            />
            Accounts
          </button>
        </div>
        <div v-if="showBreakdown" class="hero-breakdown">
          <div v-for="item in breakdown" :key="item.account_id" class="hero-breakdown-row">
            <PhWallet :size="13" weight="duotone"/>
            <span class="muted hero-breakdown-label">{{ item.account_label }}</span>
            <span class="num hero-breakdown-amt">{{ item.currency }} {{ fmtAmount(item.latest_snapshot_amount) }}</span>
            <span class="muted hero-breakdown-date">{{ item.latest_snapshot_date }}</span>
          </div>
        </div>
      </div>
      <div class="hero-side">
        <div class="stat-card stat-card--income card--flat">
          <div class="stat-label">Avg income / period</div>
          <div class="stat-value">
            <span class="stat-currency">{{ heroCcy }}</span>{{ fmtAmount(avgIncome) }}
          </div>
          <div v-if="incomeGrowth" class="stat-foot">
            <GrowthBadge :delta="incomeGrowth.delta">
              <span v-if="incomeGrowth.pct !== null">{{ Math.abs(incomeGrowth.pct).toFixed(1) }}%</span>
            </GrowthBadge>
          </div>
        </div>
        <hr class="divider"/>
        <div class="stat-card stat-card--expense card--flat">
          <div class="stat-label">Avg expense / period</div>
          <div class="stat-value">
            <span class="stat-currency">{{ heroCcy }}</span>{{ fmtAmount(avgExpense) }}
          </div>
        </div>
        <hr class="divider"/>
        <div class="stat-card stat-card--profit card--flat">
          <div class="stat-label">Avg profit / period</div>
          <div class="stat-value">
            <span class="stat-currency">{{ heroCcy }}</span>{{ fmtAmount(avgProfit) }}
          </div>
          <div v-if="profitGrowth" class="stat-foot">
            <GrowthBadge :delta="profitGrowth.delta">
              <span v-if="profitGrowth.pct !== null">{{ Math.abs(profitGrowth.pct).toFixed(1) }}%</span>
            </GrowthBadge>
          </div>
        </div>
      </div>
    </div>

    <!-- Trend chart -->
    <BaseCard v-if="periods.length" class="card--flush trend-card">
      <div class="trend-head">
        <div>
          <div class="label">Trend</div>
          <div class="trend-title">
            {{ TREND_OPTIONS.find(o => o.key === selectedTrend)?.label }}
            <span v-if="isConverted" class="muted">· ≈{{ convertToCurrency }}</span>
          </div>
        </div>
        <div class="segmented">
          <button
              v-for="t in TREND_OPTIONS"
              :key="t.key"
              :class="{ on: selectedTrend === t.key }"
              @click="selectedTrend = t.key"
          >{{ t.label }}
          </button>
        </div>
      </div>
      <v-chart :option="lineOption" :style="{ height: '260px' }" autoresize @globalout="hoveredPeriod = null"/>
    </BaseCard>

    <!-- Income by source (donut) -->
    <BaseCard v-if="Object.keys(donutTotals).length"
              :title="isConverted ? `Income by source · ≈${convertToCurrency}` : 'Income by source'">
      <div class="donut-wrap">
        <v-chart :option="donutOption" class="donut-chart" autoresize/>
        <div class="donut-legend">
          <div v-for="item in donutStats.entries" :key="item.name" class="row-between donut-row">
            <span class="row donut-row-name">
              <span class="dot" :style="{ background: item.color }"/>
              <span>{{ item.name }}</span>
            </span>
            <span class="num muted">
              {{ donutStats.total > 0 ? Math.round(item.amount / donutStats.total * 100) : 0 }}%
            </span>
          </div>
          <div v-if="donutStats.entries.length" class="donut-total row-between">
            <span class="label">Total</span>
            <span class="num">{{ isConverted ? '≈' : '' }}{{ fmtAmount(donutStats.total) }}</span>
          </div>
        </div>
      </div>
    </BaseCard>

    <!-- Full Summary Table — every period in range -->
    <BaseDataTable
      title="Summary Table"
      :loading="loading"
      :empty="!periods.length"
      empty-message="No data for selected period."
    >
      <template #head>
        <tr>
          <th>Period</th>
          <th class="col-num">Balance</th>
          <th class="col-num">Income</th>
          <th class="col-num">Profit</th>
          <th class="col-num">Expense</th>
          <th class="col-num">Avg Income</th>
          <th class="col-num">Avg Profit</th>
        </tr>
      </template>
      <template #body>
        <tr
          v-for="row in periods"
          :key="row.period"
          :class="{ 'row-highlighted': row.period === hoveredPeriod }"
        >
          <td>
            {{ fmtPeriod(row.period) }}
            <span
              v-if="row.is_bootstrap"
              class="badge-initial"
              title="Starting balance snapshot — reflects initial capital, not earned income."
            >Initial</span>
          </td>
          <td class="col-num">
            <template v-if="Object.keys(row.balances).length">
              <div class="balance-cell">
                <span v-for="(val, cur) in row.balances" :key="cur" class="num">
                  {{ cur }} {{ fmtAmount(val) }}
                </span>
              </div>
            </template>
            <span v-else class="muted">—</span>
          </td>
          <td class="col-num up">{{ fmtAmount(row.income) }}</td>
          <td class="col-num" :class="row.profit >= 0 ? 'up' : 'down'">
            {{ fmtAmount(row.profit) }}
          </td>
          <td class="col-num" :class="row.derived_expense > 0 ? 'down' : 'muted'">
            {{ row.income === 0 && row.profit === 0 ? '—' : fmtAmount(row.derived_expense) }}
          </td>
          <td class="col-num">{{ fmtAmount(row.avg_income) }}</td>
          <td class="col-num">{{ fmtAmount(row.avg_profit) }}</td>
        </tr>
      </template>
    </BaseDataTable>

    <!-- Rate details (collapsible) -->
    <button
        v-if="isAllMode && rateCoverage && Object.keys(rateCoverage.currencies).length"
        class="btn btn--ghost rate-toggle"
        @click="showRateDetails = !showRateDetails"
    >
      <PhArrowsClockwise :size="13" weight="bold"/>
      Exchange rates
      <span v-if="rateCoverage.conversion_available" class="chip chip--income">up to date</span>
      <span v-else class="chip chip--warn">issues</span>
      <PhCaretDown :size="11" weight="bold" :class="{ 'rot-180-on': showRateDetails }"/>
    </button>

    <BaseCard v-if="showRateDetails && rateCoverage">
      <div class="stack rate-grid">
        <div v-for="(entry, code) in rateCoverage.currencies" :key="code" class="row rate-row">
          <span class="num rate-pair">1 {{ code }}</span>
          <span class="muted rate-eq">=</span>
          <span class="num rate-rate" :class="{ 'down': !entry.rate }">
            {{ entry.rate ? fmtAmount(Number(entry.rate)) : '?' }} {{ rateCoverage.base_currency }}
          </span>
          <span class="chip" :class="{
            'chip--income': entry.status === 'ok',
            'chip--warn': entry.status === 'stale',
            'chip--expense': entry.status === 'missing'
          }">{{ entry.status }}</span>
          <RouterLink
              v-if="refs.currencyByCode(String(code))"
              :to="{ path: '/references', query: { openRates: refs.currencyByCode(String(code))!.id } }"
              class="btn btn--sm btn--ghost rate-set-btn"
          >Set rate
          </RouterLink>
        </div>
      </div>
    </BaseCard>
  </div>
</template>

<style scoped>
.filter-card {
  padding: 14px 16px;
}

/* Summary Table cells */
.balance-cell {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
  font-variant-numeric: tabular-nums;
}

.row-highlighted {
  background: var(--accent-soft);
  transition: background var(--t-fast) var(--ease);
}

.badge-initial {
  display: inline-block;
  margin-left: 8px;
  padding: 2px 8px;
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--accent-ink);
  background: var(--accent-soft);
  border-radius: var(--r-pill);
  vertical-align: middle;
}

.ccy-arrow {
  font-size: 14px;
  color: var(--ink-4);
}

.warning-card {
  background: var(--warning-soft);
  border-color: transparent;
}

.warning-row {
  gap: 10px;
  flex-wrap: wrap;
  font-size: 13px;
}

.warning-icon {
  color: var(--warning-ink);
  flex-shrink: 0;
}

.warning-link {
  margin-left: auto;
  color: var(--accent-ink);
  font-weight: 500;
  text-decoration: none;
}

.warning-link:hover {
  text-decoration: underline;
}

.hero-actions {
  gap: 10px;
  flex-wrap: wrap;
}

.hero-breakdown {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--hairline);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.accounts-caret {
  transition: transform var(--t-fast) var(--ease);
}

.accounts-caret--open {
  transform: rotate(90deg);
}

.hero-breakdown-row {
  display: grid;
  grid-template-columns: 14px 1fr auto auto;
  align-items: center;
  gap: 10px;
  font-size: 13px;
}

.hero-breakdown-label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}

.hero-breakdown-amt {
  font-weight: 500;
}

.hero-breakdown-date {
  font-size: 11px;
}

.trend-card {
  padding: 18px 22px 8px;
}

.trend-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}

.trend-title {
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 600;
  margin-top: 4px;
  letter-spacing: -0.01em;
}

.grid-2 {
  display: grid;
  grid-template-columns: 1fr 1.4fr;
  gap: var(--gap-section);
}

@media (max-width: 900px) {
  .grid-2 {
    grid-template-columns: 1fr;
  }
}

.donut-chart {
  width: 220px;
  height: 220px;
  flex-shrink: 0;
}

.donut-row {
  font-size: 13px;
}

.donut-row-name {
  gap: 8px;
  min-width: 0;
  overflow: hidden;
}

.donut-total {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--hairline);
  font-weight: 600;
}

.summary-head {
  padding: 18px 22px 12px;
}

.summary-title {
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 600;
  margin-top: 4px;
  letter-spacing: -0.01em;
}

.center-cell {
  text-align: center;
  padding: 32px 16px;
}

.right {
  text-align: right;
}

.rate-toggle {
  align-self: flex-start;
  font-size: 12px;
  font-weight: 500;
  color: var(--ink-3);
}

.rot-180-on {
  transform: rotate(180deg);
  transition: transform var(--t-fast) var(--ease);
}

.rate-grid {
  gap: 8px;
}

.rate-row {
  font-size: 13px;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.rate-pair {
  font-weight: 600;
  min-width: 60px;
}

.rate-eq {
  font-size: 12px;
}

.rate-rate {
  font-weight: 600;
  min-width: 110px;
}

.rate-set-btn {
  margin-left: auto;
}
</style>

<script setup lang="ts">
import {computed, onBeforeUnmount, onMounted, ref, watch} from 'vue'
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
import {useAuthStore} from '../stores/auth'
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
import BaseStatCard from '../components/BaseStatCard.vue'
import PeriodFilterBar from '../components/PeriodFilterBar.vue'
import RateBadge from '../components/RateBadge.vue'
import GrowthBadge from '../components/GrowthBadge.vue'
import type {SummaryEntry} from '../types/index'
import {
  PhArrowsClockwise,
  PhCaretDown,
  PhCaretRight,
  PhCheck,
  PhInfo,
  PhWallet,
  PhWarning,
} from '@phosphor-icons/vue'

use([CanvasRenderer, LineChart, PieChart, GridComponent, TooltipComponent, LegendComponent])

const HINT_AVG_INCOME =
    'Average income per period, across the periods where profit could be measured. Income is the sum of the income transactions you recorded.'
const HINT_AVG_EXPENSE =
    'Derived, not recorded: the average of income minus profit per period. It is what your balances imply you spent — Wallet never sums up expense entries for this number.'
const HINT_AVG_PROFIT =
    'Average profit per period. Profit is how much your total balance grew, measured from balance snapshots. All three averages share one denominator, so they reconcile with each other.'
const HINT_COL_PROFIT =
    'Change in your total balance over the period, taken from balance snapshots — not income minus recorded expenses. Money in an account you started tracking this period counts as opening capital, not profit.'
const HINT_COL_EXPENSE =
    'Income minus profit for the period: the money that came in but did not end up in your balances. It is derived from the two columns to the left, never entered by hand, and never goes below zero.'
const HINT_UNMEASURED =
    'No new snapshot in this period, so the balance was only carried forward. Profit is unknown rather than zero, and this period is left out of the averages.'
const HINT_OPENING =
    'Opening balance of an account tracked for the first time in this period. It is money you already had, so it is not counted as profit.'

const NARROW_QUERY = '(max-width: 640px)'
const NARROW_X_LABEL_LIMIT = 5
const TREND_HEIGHT = '260px'
const TREND_HEIGHT_NARROW = '220px'

const refs = useReferencesStore()
const {currencies, loaded: refsLoaded} = storeToRefs(refs)
const {user} = storeToRefs(useAuthStore())
const themeStore = useThemeStore()
const isDark = computed(() => themeStore.mode === 'dark')

const groupBy = ref<GroupBy>('month')
const periods = ref<SummaryEntry[]>([])
const stats = ref<SummaryStats | null>(null)
const rateCoverage = ref<RateCoverage | null>(null)
const sourceData = ref<IncomeBySourceEntry[]>([])
const loading = ref(false)
const selectedCurrencyId = ref<number | 'all'>('all')
// Empty until the currency list loads. Sending a guessed code on the first paint
// used to 422 for anyone whose currencies do not include it; omitting the param
// lets the backend fall back to the user's base currency instead.
const convertToCurrency = ref<string>('')

const isAllMode = computed(() => selectedCurrencyId.value === 'all')

watch(
    currencies,
    () => {
      if (!currencies.value.length) return
      const preferred = user.value?.base_currency_code
      if (preferred && refs.currencyByCode(preferred)) {
        convertToCurrency.value = preferred
        return
      }
      if (refs.currencyByCode('USD')) {
        convertToCurrency.value = 'USD'
        return
      }
      const first = currencies.value[0]
      if (first) convertToCurrency.value = first.code
    },
    {immediate: true},
)
const {dateFrom, dateTo, activePreset, allRange, initRange} = useDateRange('YTD')

const breakdown = ref<BalanceBreakdownItem[]>([])
const breakdownLoaded = ref(false)
const showBreakdown = ref(false)
const hoveredPeriod = ref<string | null>(null)

async function loadBreakdown() {
  try {
    const {data: bd} = await analyticsApi.balanceBreakdown()
    breakdown.value = bd
  } finally {
    breakdownLoaded.value = true
  }
}

async function load() {
  loading.value = true
  try {
    const params = {
      date_from: dateFrom.value,
      date_to: dateTo.value,
      group_by: groupBy.value,
      currency_id: isAllMode.value ? undefined : (selectedCurrencyId.value as number),
      convert_to: isAllMode.value && convertToCurrency.value ? convertToCurrency.value : undefined,
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

const isNarrow = ref(false)
let narrowQuery: MediaQueryList | null = null

function syncNarrow(event: MediaQueryList | MediaQueryListEvent) {
  isNarrow.value = event.matches
}

// The summary needs to know which currencies exist before it can name a conversion
// target, so the first request waits for the reference data rather than guessing.
watch(refsLoaded, (isLoaded) => {
  if (isLoaded) load()
}, {immediate: true})

onMounted(() => {
  loadBreakdown()
  initRange()
  narrowQuery = window.matchMedia(NARROW_QUERY)
  syncNarrow(narrowQuery)
  narrowQuery.addEventListener('change', syncNarrow)
})

onBeforeUnmount(() => {
  narrowQuery?.removeEventListener('change', syncNarrow)
  narrowQuery = null
})

watch([dateFrom, dateTo, groupBy, selectedCurrencyId, convertToCurrency], load)

const lastEntry = computed(() => periods.value[periods.value.length - 1] ?? null)
const chartEntries = computed(() => periods.value.filter((e) => !e.is_bootstrap))

// All three averages come from the backend over one shared set of periods. Deriving
// expense here as avgIncome - avgProfit would subtract two different denominators.
const hasAverages = computed(() => (stats.value?.accountable_period_count ?? 0) > 0)
const avgIncome = computed(() => stats.value?.avg_income ?? 0)
const avgProfit = computed(() => stats.value?.avg_profit ?? 0)
const avgExpense = computed(() => stats.value?.avg_expense ?? 0)

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
// Whether conversion is in play at all. Derived from the currencies the user owns,
// not from the last period's balances: a period holding only one of two currencies
// used to make the hero print that raw amount under the other currency's code.
const hasMultipleCurrencies = computed(() => currencies.value.length > 1)
const showBalanceSplit = computed(() => Object.keys(displayedBalances.value).length > 1)

const heroTotalRaw = computed(() => {
  if (isAllMode.value) return lastEntry.value?.converted_balance ?? 0
  const code = displayCurrencyCode.value
  if (code) return displayedBalances.value[code] ?? 0
  const vals = Object.values(displayedBalances.value)
  return vals.length ? Number(vals[0]) : 0
})

// Currencies dropped from the hero total because no rate covered them.
const heroMissingRates = computed<string[]>(() => lastEntry.value?.conversion_missing ?? [])

const heroTotalCents = computed(() => Math.round(Math.abs(heroTotalRaw.value) * 100))
const heroSign = computed(() => (heroTotalRaw.value < 0 && heroTotalCents.value > 0 ? '−' : ''))
const heroWhole = computed(() => Math.floor(heroTotalCents.value / 100))
const heroCents = computed(() => String(heroTotalCents.value % 100).padStart(2, '0'))
const heroCcy = computed(() => displayCurrencyCode.value || '')

const heroGrowth = computed(() => {
  if (isAllMode.value && balanceGrowthConverted.value) {
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

interface SetupStep {
  title: string
  description: string
  to: string
  cta: string
  done: boolean
}

const hasIncomeRecorded = computed(() => periods.value.some((e) => e.income > 0))
const hasBalanceRecorded = computed(() => breakdown.value.length > 0)

const isEmptyDashboard = computed(
    () => !loading.value && breakdownLoaded.value && !hasIncomeRecorded.value && !hasBalanceRecorded.value,
)

const setupSteps = computed<SetupStep[]>(() => [
  {
    title: 'Create a storage account',
    description: 'A storage location (a bank, a wallet, cash) plus the currency you keep there.',
    to: '/references',
    cta: 'Open references',
    done: refs.storageAccounts.length > 0,
  },
  {
    title: 'Record your income',
    description: 'Every payment you receive, tagged with the source it came from.',
    to: '/transactions',
    cta: 'Add income',
    done: hasIncomeRecorded.value,
  },
  {
    title: 'Take your first balance snapshot',
    description: 'What each account actually holds today. Profit is the change between snapshots, so nothing is charted until there is one.',
    to: '/balance-snapshots',
    cta: 'Add snapshot',
    done: hasBalanceRecorded.value,
  },
])

const showOverview = computed(() => periods.value.length > 0 && !isEmptyDashboard.value)

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
      if (!e.is_measured) return null
      return [
        {label: 'Income', value: e.income},
        {label: '− Profit', value: e.profit},
      ]
    }
    return null
  })
})

const baseLineOption = computed(() => {
  const t = TREND_OPTIONS.find((o) => o.key === selectedTrend.value)!
  if (selectedTrend.value === 'balance') {
    const code = displayCurrencyCode.value
    const values = chartEntries.value.map((e) => {
      if (isAllMode.value && e.converted_balance != null) return e.converted_balance
      return code ? (e.balances[code] ?? 0) : Object.values(e.balances)[0] ?? 0
    })
    return buildLineChartOption(
        chartEntries.value.map((e) => fmtPeriod(e.period, groupBy.value)),
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
      chartEntries.value.map((e) => fmtPeriod(e.period, groupBy.value)),
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

const trendChartHeight = computed(() => (isNarrow.value ? TREND_HEIGHT_NARROW : TREND_HEIGHT))

const xLabelInterval = computed(() => {
  const count = chartEntries.value.length
  if (count <= NARROW_X_LABEL_LIMIT) return 0
  return Math.ceil(count / NARROW_X_LABEL_LIMIT) - 1
})

const lineOption = computed(() => {
  const base = baseLineOption.value
  if (!isNarrow.value) return base
  return {
    ...base,
    grid: {...base.grid, left: 2, right: 10, bottom: 2, top: 28},
    tooltip: {
      ...base.tooltip,
      triggerOn: 'mousemove|click',
      axisPointer: {...base.tooltip.axisPointer, type: 'line'},
    },
    xAxis: {
      ...base.xAxis,
      axisLabel: {
        ...base.xAxis.axisLabel,
        fontSize: 10,
        rotate: 40,
        interval: xLabelInterval.value,
        hideOverlap: true,
        margin: 10,
      },
    },
    yAxis: {
      ...base.yAxis,
      axisLabel: {...base.yAxis.axisLabel, fontSize: 10},
    },
  }
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

    <BaseCard v-if="isEmptyDashboard" class="getting-started">
      <div>
        <div class="label">Getting started</div>
        <h2 class="gs-title">Nothing to chart yet</h2>
        <p class="muted gs-lead">
          Wallet reads profit as the change in what you hold, not as income minus receipts. That takes
          three things — an account to hold money, the income you received, and a snapshot of the real
          balance. Once all three exist, every card on this page fills in.
        </p>
      </div>
      <ol class="gs-steps">
        <li
            v-for="(step, i) in setupSteps"
            :key="step.to"
            class="gs-step"
            :class="{ 'gs-step--done': step.done }"
        >
          <span class="gs-step-num" aria-hidden="true">
            <PhCheck v-if="step.done" :size="13" weight="bold"/>
            <template v-else>{{ i + 1 }}</template>
          </span>
          <div class="gs-step-body">
            <div class="gs-step-title">
              {{ step.title }}
              <span v-if="step.done" class="chip chip--income gs-step-chip">done</span>
            </div>
            <p class="muted gs-step-text">{{ step.description }}</p>
          </div>
          <RouterLink :to="step.to" class="btn btn--sm gs-step-link">{{ step.cta }}</RouterLink>
        </li>
      </ol>
    </BaseCard>

    <div v-if="showOverview" class="card hero">
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
          <span>{{ heroSign }}{{ heroWhole.toLocaleString('en-US') }}</span>
          <span class="cents">.{{ heroCents }}</span>
        </div>
        <div v-if="showBalanceSplit" class="hero-foot">
          <span
              v-for="(val, cur) in displayedBalances"
              :key="cur"
              class="num"
          >{{ cur }} {{ fmtAmount(val) }}</span>
        </div>
        <p v-if="heroMissingRates.length" class="muted hero-incomplete">
          Excludes {{ heroMissingRates.join(', ') }} — no exchange rate available, so this total is
          lower than what you actually hold.
        </p>
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
        <BaseStatCard flat variant="income" label="Avg income / period" :hint="HINT_AVG_INCOME">
          <div class="stat-value">
            <template v-if="hasAverages">
              <span class="stat-currency">{{ heroCcy }}</span>{{ fmtAmount(avgIncome) }}
            </template>
            <span v-else class="muted">—</span>
          </div>
          <div v-if="incomeGrowth" class="stat-foot">
            <GrowthBadge :delta="incomeGrowth.delta">
              <span v-if="incomeGrowth.pct !== null">{{ Math.abs(incomeGrowth.pct).toFixed(1) }}%</span>
            </GrowthBadge>
          </div>
        </BaseStatCard>
        <hr class="divider"/>
        <BaseStatCard flat variant="expense" label="Avg expense / period" :hint="HINT_AVG_EXPENSE">
          <div class="stat-value">
            <template v-if="hasAverages">
              <span class="stat-currency">{{ heroCcy }}</span>{{ fmtAmount(avgExpense) }}
            </template>
            <span v-else class="muted">—</span>
          </div>
        </BaseStatCard>
        <hr class="divider"/>
        <BaseStatCard flat variant="profit" label="Avg profit / period" :hint="HINT_AVG_PROFIT">
          <div class="stat-value">
            <template v-if="hasAverages">
              <span class="stat-currency">{{ heroCcy }}</span>{{ fmtAmount(avgProfit) }}
            </template>
            <span v-else class="muted">—</span>
          </div>
          <div v-if="profitGrowth" class="stat-foot">
            <GrowthBadge :delta="profitGrowth.delta">
              <span v-if="profitGrowth.pct !== null">{{ Math.abs(profitGrowth.pct).toFixed(1) }}%</span>
            </GrowthBadge>
          </div>
        </BaseStatCard>
      </div>
    </div>

    <BaseCard v-if="showOverview" class="card--flush trend-card">
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
      <v-chart :option="lineOption" :style="{ height: trendChartHeight }" autoresize @globalout="hoveredPeriod = null"/>
    </BaseCard>

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

    <BaseDataTable
      v-if="!isEmptyDashboard"
      title="Summary Table"
      :loading="loading"
      :empty="!periods.length"
      empty-message="No data for the selected period. Try a wider date range."
    >
      <template #head>
        <tr>
          <th>Period</th>
          <th class="col-num">Balance</th>
          <th class="col-num">Income</th>
          <th class="col-num">
            <span class="th-hint" :title="HINT_COL_PROFIT">
              Profit<PhInfo :size="12" weight="bold" aria-hidden="true"/>
            </span>
          </th>
          <th class="col-num">
            <span class="th-hint" :title="HINT_COL_EXPENSE">
              Expense<PhInfo :size="12" weight="bold" aria-hidden="true"/>
            </span>
          </th>
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
            {{ fmtPeriod(row.period, groupBy) }}
            <span
              v-if="row.is_bootstrap"
              class="badge-initial"
              title="Starting balance snapshot — reflects initial capital, not earned income."
            >Initial</span>
            <span
              v-else-if="Object.keys(row.opening_capital ?? {}).length"
              class="badge-initial"
              :title="HINT_OPENING"
            >Opening</span>
            <span
              v-if="!row.is_measured && !row.is_bootstrap"
              class="badge-unmeasured"
              :title="HINT_UNMEASURED"
            >No snapshot</span>
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
          <td class="col-num" :class="row.is_measured ? (row.profit >= 0 ? 'up' : 'down') : 'muted'">
            {{ row.is_measured ? fmtAmount(row.profit) : '—' }}
          </td>
          <td class="col-num" :class="row.is_measured && row.derived_expense > 0 ? 'down' : 'muted'">
            {{ row.is_measured ? fmtAmount(row.derived_expense) : '—' }}
          </td>
          <td class="col-num">{{ fmtAmount(row.avg_income) }}</td>
          <td class="col-num">{{ fmtAmount(row.avg_profit) }}</td>
        </tr>
      </template>
    </BaseDataTable>

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

.getting-started {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.gs-title {
  font-family: var(--font-display);
  font-size: 24px;
  font-weight: 600;
  letter-spacing: -0.02em;
  margin: 6px 0 0;
}

.gs-lead {
  font-size: 13px;
  line-height: 1.65;
  max-width: 62ch;
  margin: 8px 0 0;
}

.gs-steps {
  display: flex;
  flex-direction: column;
  gap: 10px;
  list-style: none;
  margin: 0;
  padding: 0;
  counter-reset: none;
}

.gs-step {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 14px 16px;
  border: 1px solid var(--hairline);
  border-radius: var(--r-inner);
  background: var(--surface-2);
}

.gs-step-num {
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  flex-shrink: 0;
  border-radius: var(--r-pill);
  background: var(--surface);
  border: 1px solid var(--hairline-strong);
  font-size: 12px;
  font-weight: 600;
  color: var(--ink-3);
  font-variant-numeric: tabular-nums;
}

.gs-step--done .gs-step-num {
  background: var(--accent-soft);
  border-color: transparent;
  color: var(--accent-ink);
}

.gs-step-body {
  min-width: 0;
  flex: 1;
}

.gs-step-title {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  font-size: 14px;
  font-weight: 600;
}

.gs-step-chip {
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-size: 10px;
}

.gs-step-text {
  font-size: 12px;
  line-height: 1.6;
  margin: 4px 0 0;
}

.gs-step-link {
  flex-shrink: 0;
  text-decoration: none;
}

@media (max-width: 640px) {
  .gs-step {
    flex-wrap: wrap;
  }

  .gs-step-link {
    margin-left: 40px;
  }
}

.th-hint {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: help;
}

.th-hint svg {
  color: var(--ink-4);
  flex-shrink: 0;
}

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

.badge-unmeasured {
  display: inline-block;
  margin-left: 8px;
  padding: 2px 8px;
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--ink-3);
  background: var(--surface-2);
  border: 1px solid var(--hairline);
  border-radius: var(--r-pill);
  vertical-align: middle;
  cursor: help;
}

.hero-incomplete {
  margin: 10px 0 0;
  font-size: 12px;
  line-height: 1.55;
  max-width: 52ch;
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

@media (hover: hover) {
  .warning-link:hover {
    text-decoration: underline;
  }
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

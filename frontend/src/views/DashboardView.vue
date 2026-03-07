<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { analyticsApi, type GroupBy, type IncomeBySourceEntry, type BalanceBreakdownItem } from '../api/analytics'
import { useReferencesStore } from '../stores/references'
import { storeToRefs } from 'pinia'
import { fmtAmount, fmtPeriod } from '../utils/format'
import { buildLineChartOption, buildDonutChartOption, DONUT_COLORS } from '../utils/charts'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import BaseCard from '../components/BaseCard.vue'
import BaseDataTable from '../components/BaseDataTable.vue'
import BaseStatCard from '../components/BaseStatCard.vue'
import PeriodFilterBar from '../components/PeriodFilterBar.vue'
import type { Preset, SummaryEntry } from '../types/index'

use([CanvasRenderer, LineChart, PieChart, GridComponent, TooltipComponent, LegendComponent])

const refs = useReferencesStore()
const { currencies } = storeToRefs(refs)

const groupBy = ref<GroupBy>('month')
const data = ref<SummaryEntry[]>([])
const sourceData = ref<IncomeBySourceEntry[]>([])
const loading = ref(false)
const selectedCurrencyId = ref<number | null>(null)

watch(
  currencies,
  () => {
    if (selectedCurrencyId.value === null) {
      selectedCurrencyId.value = refs.currencyByCode('USD')?.id ?? currencies.value[0]?.id ?? null
    }
  },
  { immediate: true },
)
const activePreset = ref<Preset>('YTD')
const allRange = ref<{ from: string; to: string } | null>(null)

const today = new Date()
const dateFrom = ref(`${today.getFullYear()}-01-01`)
const dateTo = ref(today.toISOString().slice(0, 10))

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
      currency_id: selectedCurrencyId.value ?? undefined,
    }
    const [summaryRes, sourceRes] = await Promise.all([
      analyticsApi.summary(params),
      analyticsApi.incomeBySource(params),
    ])
    data.value = summaryRes.data
    sourceData.value = sourceRes.data
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  load()
  loadBreakdown()
  analyticsApi.dateRange().then(({ data: dr }) => {
    if (dr.min_date && dr.max_date) {
      allRange.value = { from: dr.min_date, to: dr.max_date }
      if (activePreset.value === 'All') {
        dateFrom.value = dr.min_date
        dateTo.value = dr.max_date
      }
    }
  })
})
watch([dateFrom, dateTo, groupBy, selectedCurrencyId], load)

const lastEntry = computed(() => data.value[data.value.length - 1] ?? null)
const chartEntries = computed(() => data.value.filter((e) => !e.is_bootstrap))
const avgIncome = computed(() => lastEntry.value?.avg_income ?? 0)
const avgProfit = computed(() => lastEntry.value?.avg_profit ?? 0)

const activePeriods = computed(() => data.value.filter((e) => e.income > 0 && !e.is_bootstrap))
const totalIncome = computed(() => activePeriods.value.reduce((s, e) => s + e.income, 0))
const totalProfit = computed(() => activePeriods.value.reduce((s, e) => s + e.profit, 0))

const avgIncomeHint = computed(() =>
  `Average income per active period.\n\nTotal income: ${fmtAmount(totalIncome.value)}\nActive periods: ${activePeriods.value.length}\nResult: ${fmtAmount(totalIncome.value)} ÷ ${activePeriods.value.length} = ${fmtAmount(avgIncome.value)}\n\nPeriods with no income are excluded.`
)
const avgProfitHint = computed(() =>
  `Average profit per active period.\n\nTotal profit: ${fmtAmount(totalProfit.value)}\nActive periods: ${activePeriods.value.length}\nResult: ${fmtAmount(totalProfit.value)} ÷ ${activePeriods.value.length} = ${fmtAmount(avgProfit.value)}\n\nProfit = Income − Expenses. Can be negative if spending exceeds income.`
)

const selectedCurrencyCode = computed(() => {
  if (selectedCurrencyId.value === null) return null
  return refs.currencyById(selectedCurrencyId.value)?.code ?? null
})

const displayedBalances = computed(() => lastEntry.value?.balances ?? {})

type TrendKey = 'income' | 'expense' | 'profit'
const selectedTrend = ref<TrendKey>('income')

const TREND_OPTIONS: { key: TrendKey; label: string; borderColor: string; backgroundColor: string }[] = [
  { key: 'income',  label: 'Income',  borderColor: '#1fa068', backgroundColor: 'rgba(31,160,104,0.10)' },
  { key: 'expense', label: 'Expense', borderColor: '#e84565', backgroundColor: 'rgba(232,69,101,0.08)' },
  { key: 'profit',  label: 'Profit',  borderColor: '#2272cc', backgroundColor: 'rgba(34,114,204,0.08)' },
]

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
    selectedCurrencyCode.value,
    (idx) => { hoveredPeriod.value = idx !== null ? (chartEntries.value[idx]?.period ?? null) : null },
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
  )
})


</script>

<template>
  <div class="page-sections">
  <BaseCard>
    <PeriodFilterBar
      v-model:dateFrom="dateFrom"
      v-model:dateTo="dateTo"
      v-model:groupBy="groupBy"
      v-model:activePreset="activePreset"
      :allRange="allRange"
    />
    <div v-if="currencies.length" class="currency-tabs">
      <button
        v-for="cur in currencies"
        :key="cur.id"
        class="tab-pill"
        :class="{ 'tab-pill--active': selectedCurrencyId === cur.id }"
        @click="selectedCurrencyId = cur.id"
      >{{ cur.code }}</button>
    </div>
  </BaseCard>

  <div v-if="data.length" class="stats-grid">
    <BaseStatCard label="Current Balance">
      <div v-for="(val, cur) in displayedBalances" :key="cur" class="stat-value">
        {{ cur }}: {{ fmtAmount(val) }}
      </div>
      <div v-if="!Object.keys(displayedBalances).length" class="stat-value">—</div>
      <button class="breakdown-toggle" @click="showBreakdown = !showBreakdown">
        {{ showBreakdown ? 'Hide breakdown' : 'Show breakdown' }}
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
    >
      <div class="stat-value amount-positive">{{ fmtAmount(avgIncome) }}</div>
    </BaseStatCard>
    <BaseStatCard
      label="Avg Profit"
      variant="profit"
      :hint="avgProfitHint"
    >
      <div class="stat-value" :class="avgProfit >= 0 ? 'amount-positive' : 'amount-negative'">
        {{ fmtAmount(avgProfit) }}
      </div>
    </BaseStatCard>
  </div>

  <BaseCard v-if="data.length" title="Trends">
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

  <BaseCard v-if="Object.keys(donutTotals).length" title="Income by Source">
    <div class="donut-layout">
      <v-chart :option="donutOption" class="donut-chart" autoresize />
      <div class="donut-stats">
        <div v-for="item in donutStats.entries" :key="item.name" class="donut-stat-row">
          <span class="donut-dot" :style="{ background: item.color }" />
          <span class="donut-stat-name">{{ item.name }}</span>
          <span class="donut-stat-pct">{{ donutStats.total > 0 ? Math.round(item.amount / donutStats.total * 100) : 0 }}%</span>
          <span class="donut-stat-amount">{{ fmtAmount(item.amount) }}</span>
        </div>
        <div class="donut-stat-total">
          <span>Total</span>
          <span>{{ fmtAmount(donutStats.total) }}</span>
        </div>
      </div>
    </div>
  </BaseCard>

  <BaseDataTable title="Summary Table" :loading="loading" :empty="!data.length" empty-message="No data for selected period.">
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
      <tr v-for="row in data" :key="row.period" :class="{ 'row-highlighted': row.period === hoveredPeriod }">
        <td>
          {{ fmtPeriod(row.period) }}
          <span
            v-if="row.is_bootstrap"
            class="badge-initial"
            title="Starting balance snapshot — reflects initial capital entered by the user, not real earned income or profit."
          >Initial</span>
        </td>
        <td class="col-num">
          <template v-if="Object.keys(row.balances).length">
            <span v-for="(val, cur) in row.balances" :key="cur">{{ cur }} {{ fmtAmount(val) }}</span>
          </template>
          <span v-else>—</span>
        </td>
        <td class="col-num amount-positive">{{ fmtAmount(row.income) }}</td>
        <td class="col-num" :class="row.profit >= 0 ? 'amount-positive' : 'amount-negative'">{{ fmtAmount(row.profit) }}</td>
        <td class="col-num" :class="row.derived_expense > 0 ? 'amount-negative' : 'amount-positive'">
          {{ row.income === 0 && row.profit === 0 ? '—' : fmtAmount(row.derived_expense) }}
        </td>
        <td class="col-num">{{ fmtAmount(row.avg_income) }}</td>
        <td class="col-num">{{ fmtAmount(row.avg_profit) }}</td>
      </tr>
    </template>
  </BaseDataTable>
  </div>
</template>

<style scoped>
.trend-tabs {
  display: flex;
  gap: 0.3rem;
}

.trend-tabs .tab-pill {
  padding: 0.15rem 0.5rem;
  font-size: 0.72rem;
}

.currency-tabs {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-top: 0.75rem;
}

.tab-pill {
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid rgba(0, 0, 0, 0.12);
  background: rgba(0, 0, 0, 0.05);
  color: rgba(0, 0, 0, 0.55);
  transition: background 0.15s, color 0.15s;
}

.tab-pill:hover:not(:disabled) {
  background: rgba(0, 0, 0, 0.10);
  color: rgba(0, 0, 0, 0.80);
}

.tab-pill:disabled {
  cursor: default;
}

.tab-pill--active {
  background: rgba(34, 114, 204, 0.10);
  border-color: rgba(34, 114, 204, 0.40);
  color: #2272cc;
}

@media (max-width: 640px) {
  .trend-tabs {
    flex-wrap: wrap;
  }

  .currency-tabs {
    flex-wrap: wrap;
  }

}

.breakdown-toggle {
  margin-top: 0.5rem;
  background: none;
  border: none;
  color: #2272cc;
  font-size: 0.75rem;
  cursor: pointer;
  padding: 0;
  text-decoration: underline;
}

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
  color: rgba(0, 0, 0, 0.55);
}

.breakdown-label {
  flex: 1;
}

.breakdown-amount {
  color: rgba(0, 0, 0, 0.80);
}

.breakdown-date {
  color: rgba(0, 0, 0, 0.40);
}

.row-highlighted {
  background: rgba(14, 96, 192, 0.08);
}

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
  color: rgba(0, 0, 0, 0.75);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.donut-stat-pct {
  font-size: 0.75rem;
  color: rgba(0, 0, 0, 0.4);
  min-width: 2.8rem;
  text-align: right;
}

.donut-stat-amount {
  font-variant-numeric: tabular-nums;
  font-weight: 500;
  color: rgba(0, 0, 0, 0.8);
  min-width: 5rem;
  text-align: right;
}

.donut-stat-total {
  display: flex;
  justify-content: space-between;
  padding-top: 0.5rem;
  margin-top: 0.25rem;
  border-top: 1px solid rgba(0, 0, 0, 0.08);
  font-size: 0.85rem;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.65);
}

@media (max-width: 640px) {
  .donut-layout {
    flex-direction: column;
    align-items: stretch;
  }

  .donut-chart {
    flex: none;
    width: 100%;
  }
}
</style>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { analyticsApi, type GroupBy, type IncomeBySourceEntry, type BalanceBreakdownItem } from '../api/analytics'
import { useReferencesStore } from '../stores/references'
import { storeToRefs } from 'pinia'
import { fmtAmount, fmtPeriod } from '../utils/format'
import { buildLineChartOptions, donutOptions, DONUT_COLORS } from '../utils/charts'
import { Line, Doughnut } from 'vue-chartjs'
import {
  Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Filler,
  ArcElement,
} from 'chart.js'
import BaseCard from '../components/BaseCard.vue'
import BaseDataTable from '../components/BaseDataTable.vue'
import BaseStatCard from '../components/BaseStatCard.vue'
import PeriodFilterBar from '../components/PeriodFilterBar.vue'
import type { Preset, SummaryEntry } from '../types/index'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Filler, ArcElement)

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

const selectedCurrencyCode = computed(() => {
  if (selectedCurrencyId.value === null) return null
  return refs.currencyById(selectedCurrencyId.value)?.code ?? null
})

const displayedBalances = computed(() => lastEntry.value?.balances ?? {})

const chartData = computed(() => ({
  labels: chartEntries.value.map((e) => fmtPeriod(e.period)),
  datasets: [
    {
      label: 'Income',
      data: chartEntries.value.map((e) => e.income),
      borderColor: '#059669',
      backgroundColor: 'rgba(5,150,105,0.10)',
      fill: true,
      tension: 0.3,
    },
    {
      label: 'Expense',
      data: chartEntries.value.map((e) => e.derived_expense),
      borderColor: '#dc2626',
      backgroundColor: 'rgba(220,38,38,0.08)',
      fill: true,
      tension: 0.3,
    },
    {
      label: 'Profit',
      data: chartEntries.value.map((e) => e.profit),
      borderColor: '#0e60c0',
      backgroundColor: 'rgba(14,96,192,0.08)',
      fill: true,
      tension: 0.3,
    },
  ],
}))

const chartOptions = computed(() =>
  buildLineChartOptions(selectedCurrencyCode.value, (p) => { hoveredPeriod.value = p }, chartEntries.value)
)

const donutChartData = computed(() => {
  const totals: Record<string, number> = {}
  for (const entry of sourceData.value) {
    for (const [source, amount] of Object.entries(entry.sources)) {
      totals[source] = (totals[source] ?? 0) + Number(amount)
    }
  }
  const labels = Object.keys(totals)
  return {
    labels,
    datasets: [{
      data: labels.map((l) => totals[l] ?? 0),
      backgroundColor: DONUT_COLORS.slice(0, labels.length),
      borderWidth: 0,
    }],
  }
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
    <BaseStatCard label="Avg Income" variant="income">
      <div class="stat-value amount-positive">{{ fmtAmount(avgIncome) }}</div>
    </BaseStatCard>
    <BaseStatCard label="Avg Profit" variant="profit">
      <div class="stat-value" :class="avgProfit >= 0 ? 'amount-positive' : 'amount-negative'">
        {{ fmtAmount(avgProfit) }}
      </div>
    </BaseStatCard>
  </div>

  <BaseCard v-if="data.length" title="Trends">
    <Line :data="chartData" :options="chartOptions" />
  </BaseCard>

  <BaseCard v-if="donutChartData.labels.length" title="Income by Source">
    <div class="donut-wrap">
      <Doughnut :data="donutChartData" :options="donutOptions" />
    </div>
  </BaseCard>

  <BaseDataTable title="Summary Table" :loading="loading" :empty="!data.length" empty-message="No data for selected period.">
    <template #head>
      <tr>
        <th>Period</th>
        <th>Balance</th>
        <th>Income</th>
        <th>Profit</th>
        <th>Expense</th>
        <th>Avg Income</th>
        <th>Avg Profit</th>
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
        <td>
          <template v-if="Object.keys(row.balances).length">
            <span v-for="(val, cur) in row.balances" :key="cur">{{ cur }} {{ fmtAmount(val) }}</span>
          </template>
          <span v-else>—</span>
        </td>
        <td class="amount-positive">{{ fmtAmount(row.income) }}</td>
        <td :class="row.profit >= 0 ? 'amount-positive' : 'amount-negative'">{{ fmtAmount(row.profit) }}</td>
        <td :class="row.derived_expense > 0 ? 'amount-negative' : 'amount-positive'">
          {{ row.income === 0 && row.profit === 0 ? '—' : fmtAmount(row.derived_expense) }}
        </td>
        <td>{{ fmtAmount(row.avg_income) }}</td>
        <td>{{ fmtAmount(row.avg_profit) }}</td>
      </tr>
    </template>
  </BaseDataTable>
  </div>
</template>

<style scoped>
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
  background: rgba(14, 96, 192, 0.10);
  border-color: rgba(14, 96, 192, 0.40);
  color: #0e60c0;
}

.donut-wrap {
  max-width: 400px;
  margin: 0 auto;
}

.breakdown-toggle {
  margin-top: 0.5rem;
  background: none;
  border: none;
  color: #0e60c0;
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
</style>

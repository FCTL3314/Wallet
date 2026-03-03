<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { analyticsApi, type SummaryEntry, type GroupBy, type IncomeBySourceEntry, type BalanceBreakdownItem } from '../api/analytics'
import { useReferencesStore } from '../stores/references'
import { storeToRefs } from 'pinia'
import { fmtAmount, fmtPeriod } from '../utils/format'
import { Line, Doughnut } from 'vue-chartjs'
import {
  Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Filler,
  ArcElement,
} from 'chart.js'
import BaseCard from '../components/BaseCard.vue'
import BaseDataTable from '../components/BaseDataTable.vue'
import BaseStatCard from '../components/BaseStatCard.vue'
import PeriodFilterBar from '../components/PeriodFilterBar.vue'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Filler, ArcElement)

const refs = useReferencesStore()
const { currencies } = storeToRefs(refs)

type Preset = 'YTD' | '3M' | '6M' | '12M' | 'custom'

const groupBy = ref<GroupBy>('month')
const data = ref<SummaryEntry[]>([])
const sourceData = ref<IncomeBySourceEntry[]>([])
const loading = ref(false)
const selectedCurrencyId = ref<number | null>(null)
const activePreset = ref<Preset>('YTD')

const today = new Date()
const dateFrom = ref(`${today.getFullYear()}-01-01`)
const dateTo = ref(today.toISOString().slice(0, 10))

const breakdown = ref<BalanceBreakdownItem[]>([])
const showBreakdown = ref(false)

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

onMounted(() => { load(); loadBreakdown() })
watch([dateFrom, dateTo, groupBy, selectedCurrencyId], load)

const lastEntry = computed(() => data.value[data.value.length - 1] ?? null)
const avgIncome = computed(() => lastEntry.value?.avg_income ?? 0)
const avgProfit = computed(() => lastEntry.value?.avg_profit ?? 0)

const selectedCurrencyCode = computed(() => {
  if (selectedCurrencyId.value === null) return null
  return refs.currencyById(selectedCurrencyId.value)?.code ?? null
})

const displayedBalances = computed(() => {
  if (!lastEntry.value?.balances) return {}
  if (selectedCurrencyId.value === null) return lastEntry.value.balances
  const code = selectedCurrencyCode.value
  if (!code) return lastEntry.value.balances
  const filtered: Record<string, number> = {}
  if (code in lastEntry.value.balances) filtered[code] = lastEntry.value.balances[code]
  return filtered
})

const chartData = computed(() => ({
  labels: data.value.map((e) => fmtPeriod(e.period)),
  datasets: [
    {
      label: 'Income',
      data: data.value.map((e) => e.income),
      borderColor: '#34d399',
      backgroundColor: 'rgba(52,211,153,0.15)',
      fill: true,
      tension: 0.3,
    },
    {
      label: 'Expense',
      data: data.value.map((e) => e.income - e.profit),
      borderColor: '#fb7185',
      backgroundColor: 'rgba(251,113,133,0.15)',
      fill: true,
      tension: 0.3,
    },
    {
      label: 'Profit',
      data: data.value.map((e) => e.profit),
      borderColor: '#a78bfa',
      backgroundColor: 'rgba(167,139,250,0.15)',
      fill: true,
      tension: 0.3,
    },
  ],
}))

const chartOptions = computed(() => ({
  responsive: true,
  plugins: {
    legend: {
      position: 'top' as const,
      labels: {
        color: 'rgba(255,255,255,0.60)',
        font: { family: 'DM Sans', size: 12 },
      },
    },
  },
  scales: {
    y: {
      beginAtZero: true,
      grid: { color: 'rgba(255,255,255,0.07)' },
      ticks: { color: 'rgba(255,255,255,0.50)' },
      title: selectedCurrencyCode.value
        ? { display: true, text: selectedCurrencyCode.value, color: 'rgba(255,255,255,0.50)' }
        : { display: false },
    },
    x: {
      grid: { color: 'rgba(255,255,255,0.07)' },
      ticks: { color: 'rgba(255,255,255,0.50)' },
    },
  },
}))

const DONUT_COLORS = ['#fbbf24', '#34d399', '#06b6d4', '#a78bfa', '#fb7185', '#f97316']

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
      data: labels.map((l) => totals[l]),
      backgroundColor: DONUT_COLORS.slice(0, labels.length),
      borderWidth: 0,
    }],
  }
})

const donutOptions = {
  responsive: true,
  plugins: {
    legend: {
      position: 'right' as const,
      labels: {
        color: 'rgba(255,255,255,0.60)',
        font: { family: 'DM Sans', size: 12 },
      },
    },
  },
}
</script>

<template>
  <h1 class="page-title">Dashboard</h1>

  <PeriodFilterBar
    v-model:dateFrom="dateFrom"
    v-model:dateTo="dateTo"
    v-model:groupBy="groupBy"
    v-model:activePreset="activePreset"
  />

  <div class="currency-tabs">
    <button
      class="tab-pill"
      :class="{ 'tab-pill--active': selectedCurrencyId === null }"
      @click="selectedCurrencyId = null"
    >All</button>
    <button
      v-for="cur in currencies"
      :key="cur.id"
      class="tab-pill"
      :class="{ 'tab-pill--active': selectedCurrencyId === cur.id }"
      @click="selectedCurrencyId = cur.id"
    >{{ cur.code }}</button>
  </div>

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
      <tr v-for="row in data" :key="row.period">
        <td>{{ fmtPeriod(row.period) }}</td>
        <td>
          <template v-if="selectedCurrencyCode">
            <span v-if="row.balances[selectedCurrencyCode] !== undefined">
              {{ selectedCurrencyCode }} {{ fmtAmount(row.balances[selectedCurrencyCode]) }}
            </span>
            <span v-else>—</span>
          </template>
          <template v-else>
            <span v-for="(val, cur) in row.balances" :key="cur">{{ cur }} {{ fmtAmount(val) }}&nbsp;</span>
            <span v-if="!row.balances || !Object.keys(row.balances).length">—</span>
          </template>
        </td>
        <td class="amount-positive">{{ fmtAmount(row.income) }}</td>
        <td :class="row.profit >= 0 ? 'amount-positive' : 'amount-negative'">{{ fmtAmount(row.profit) }}</td>
        <td :class="(row.income - row.profit) > 0 ? 'amount-negative' : 'amount-positive'">
          {{ row.income === 0 && row.profit === 0 ? '—' : fmtAmount(row.income - row.profit) }}
        </td>
        <td>{{ fmtAmount(row.avg_income) }}</td>
        <td>{{ fmtAmount(row.avg_profit) }}</td>
      </tr>
    </template>
  </BaseDataTable>
</template>

<style scoped>
.currency-tabs {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-bottom: 1rem;
}

.tab-pill {
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid rgba(255, 255, 255, 0.15);
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.6);
  transition: background 0.15s, color 0.15s;
}

.tab-pill:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.10);
  color: rgba(255, 255, 255, 0.9);
}

.tab-pill:disabled {
  cursor: default;
}

.tab-pill--active {
  background: rgba(167, 139, 250, 0.25);
  border-color: rgba(167, 139, 250, 0.6);
  color: #a78bfa;
}

.donut-wrap {
  max-width: 400px;
  margin: 0 auto;
}

.breakdown-toggle {
  margin-top: 0.5rem;
  background: none;
  border: none;
  color: rgba(167, 139, 250, 0.8);
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
  color: rgba(255, 255, 255, 0.6);
}

.breakdown-label {
  flex: 1;
}

.breakdown-amount {
  color: rgba(255, 255, 255, 0.85);
}

.breakdown-date {
  color: rgba(255, 255, 255, 0.35);
}
</style>

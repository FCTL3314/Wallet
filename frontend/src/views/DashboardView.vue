<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { analyticsApi, type SummaryEntry, type GroupBy } from '../api/analytics'
import { fmtAmount, fmtPeriod } from '../utils/format'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Filler,
} from 'chart.js'
import BaseCard from '../components/BaseCard.vue'
import BaseDataTable from '../components/BaseDataTable.vue'
import BaseStatCard from '../components/BaseStatCard.vue'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Filler)

const groupBy = ref<GroupBy>('month')
const year = ref(new Date().getFullYear())
const data = ref<SummaryEntry[]>([])
const loading = ref(false)

const dateFrom = ref(`${year.value}-01-01`)
const dateTo = ref(`${year.value}-12-31`)

watch(year, (y) => {
  dateFrom.value = `${y}-01-01`
  dateTo.value = `${y}-12-31`
})

async function load() {
  loading.value = true
  try {
    const { data: d } = await analyticsApi.summary({
      date_from: dateFrom.value,
      date_to: dateTo.value,
      group_by: groupBy.value,
    })
    data.value = d
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch([dateFrom, dateTo, groupBy], load)

const lastEntry = computed(() => data.value[data.value.length - 1] ?? null)

const avgIncome = computed(() => lastEntry.value?.avg_income ?? 0)
const avgProfit = computed(() => lastEntry.value?.avg_profit ?? 0)

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

const chartOptions = {
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
    },
    x: {
      grid: { color: 'rgba(255,255,255,0.07)' },
      ticks: { color: 'rgba(255,255,255,0.50)' },
    },
  },
}
</script>

<template>
  <h1 class="page-title">Dashboard</h1>

  <div class="toolbar">
    <input v-model="dateFrom" type="date" />
    <span class="text-muted">—</span>
    <input v-model="dateTo" type="date" />
    <select v-model="groupBy">
      <option value="month">Month</option>
      <option value="quarter">Quarter</option>
      <option value="year">Year</option>
    </select>
  </div>

  <div v-if="data.length" class="stats-grid">
    <BaseStatCard v-if="lastEntry?.balances" label="Current Balance">
      <div v-for="(val, cur) in lastEntry!.balances" :key="cur" class="stat-value">
        {{ cur }}: {{ fmtAmount(val) }}
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
          <span v-for="(val, cur) in row.balances" :key="cur">{{ cur }} {{ fmtAmount(val) }}&nbsp;</span>
          <span v-if="!row.balances || !Object.keys(row.balances).length">—</span>
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

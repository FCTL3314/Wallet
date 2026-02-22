<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { analyticsApi, type SummaryEntry, type GroupBy } from '../api/analytics'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Filler,
} from 'chart.js'

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
  } catch { /* empty */ }
  loading.value = false
}

onMounted(load)
watch([dateFrom, dateTo, groupBy], load)

function formatPeriod(iso: string) {
  const d = new Date(iso)
  return d.toLocaleDateString('ru-RU', { year: 'numeric', month: 'short' })
}

function fmt(n: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n)
}

function chartData() {
  return {
    labels: data.value.map((e) => formatPeriod(e.period)),
    datasets: [
      {
        label: 'Income',
        data: data.value.map((e) => e.income),
        borderColor: '#22c55e',
        backgroundColor: 'rgba(34,197,94,0.1)',
        fill: true,
        tension: 0.3,
      },
      {
        label: 'Expenses',
        data: data.value.map((e) => e.expenses),
        borderColor: '#ef4444',
        backgroundColor: 'rgba(239,68,68,0.1)',
        fill: true,
        tension: 0.3,
      },
      {
        label: 'Profit',
        data: data.value.map((e) => e.profit),
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59,130,246,0.1)',
        fill: true,
        tension: 0.3,
      },
    ],
  }
}

const chartOptions = {
  responsive: true,
  plugins: { legend: { position: 'top' as const } },
  scales: { y: { beginAtZero: true } },
}
</script>

<template>
  <h1 class="page-title">Dashboard</h1>

  <div class="toolbar">
    <input v-model="dateFrom" type="date" />
    <span>—</span>
    <input v-model="dateTo" type="date" />
    <select v-model="groupBy">
      <option value="month">Month</option>
      <option value="quarter">Quarter</option>
      <option value="year">Year</option>
    </select>
  </div>

  <div v-if="data.length" class="stats-grid">
    <div class="stat-card">
      <div class="stat-label">Total Income</div>
      <div class="stat-value amount-positive">{{ fmt(data.reduce((s, e) => s + e.income, 0)) }}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Total Expenses</div>
      <div class="stat-value amount-negative">{{ fmt(data.reduce((s, e) => s + e.expenses, 0)) }}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Total Profit</div>
      <div class="stat-value" :class="data.reduce((s, e) => s + e.profit, 0) >= 0 ? 'amount-positive' : 'amount-negative'">
        {{ fmt(data.reduce((s, e) => s + e.profit, 0)) }}
      </div>
    </div>
    <div class="stat-card" v-if="data[data.length - 1]?.balances">
      <div class="stat-label">Latest Balance</div>
      <div v-for="(val, cur) in data[data.length - 1]!.balances" :key="cur" class="stat-value">
        {{ cur }}: {{ fmt(val) }}
      </div>
    </div>
  </div>

  <div class="card" v-if="data.length">
    <div class="card-title">Trends</div>
    <Line :data="chartData()" :options="chartOptions" />
  </div>

  <div class="card">
    <div class="card-title">Summary Table</div>
    <p v-if="loading">Loading...</p>
    <p v-else-if="!data.length" style="color: #94a3b8">No data for selected period.</p>
    <table v-else class="data-table">
      <thead>
        <tr>
          <th>Period</th>
          <th>Balance</th>
          <th>Income</th>
          <th>Profit</th>
          <th>Expenses</th>
          <th>Avg Income</th>
          <th>Avg Profit</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in data" :key="row.period">
          <td>{{ formatPeriod(row.period) }}</td>
          <td>
            <span v-for="(val, cur) in row.balances" :key="cur">{{ cur }} {{ fmt(val) }}&nbsp;</span>
            <span v-if="!row.balances || !Object.keys(row.balances).length">—</span>
          </td>
          <td class="amount-positive">{{ fmt(row.income) }}</td>
          <td :class="row.profit >= 0 ? 'amount-positive' : 'amount-negative'">{{ fmt(row.profit) }}</td>
          <td class="amount-negative">{{ fmt(row.expenses) }}</td>
          <td>{{ fmt(row.avg_income) }}</td>
          <td>{{ fmt(row.avg_profit) }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

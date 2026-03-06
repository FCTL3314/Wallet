<script setup lang="ts">
import type { GroupBy } from '../api/analytics'

type Preset = 'All' | 'YTD' | '3M' | '6M' | '12M' | 'custom'

const props = defineProps<{
  dateFrom: string
  dateTo: string
  groupBy?: GroupBy
  activePreset: string
  showGroupBy?: boolean
  allRange?: { from: string; to: string } | null
}>()

const emit = defineEmits<{
  'update:dateFrom': [string]
  'update:dateTo': [string]
  'update:groupBy': [GroupBy]
  'update:activePreset': [string]
}>()

function getPresetDates(preset: Preset): { from: string; to: string } | null {
  const today = new Date()
  const todayStr = today.toISOString().slice(0, 10)
  const yyyy = today.getFullYear()
  if (preset === 'All') return props.allRange ?? { from: '2000-01-01', to: todayStr }
  if (preset === 'YTD') return { from: `${yyyy}-01-01`, to: todayStr }
  const d = new Date(today)
  if (preset === '3M') d.setMonth(d.getMonth() - 3)
  else if (preset === '6M') d.setMonth(d.getMonth() - 6)
  else if (preset === '12M') d.setMonth(d.getMonth() - 12)
  else return null
  return { from: d.toISOString().slice(0, 10), to: todayStr }
}

function setPreset(preset: Preset) {
  const dates = getPresetDates(preset)
  if (dates) {
    emit('update:dateFrom', dates.from)
    emit('update:dateTo', dates.to)
  }
  emit('update:activePreset', preset)
}

function handleDateInput(field: 'dateFrom' | 'dateTo', value: string) {
  if (field === 'dateFrom') emit('update:dateFrom', value)
  else emit('update:dateTo', value)
  emit('update:activePreset', 'custom')
}
</script>

<template>
  <div class="toolbar">
    <div class="preset-pills">
      <button
        v-for="p in (['All', 'YTD', '3M', '6M', '12M'] as const)"
        :key="p"
        class="tab-pill"
        :class="{ 'tab-pill--active': activePreset === p }"
        @click="setPreset(p)"
      >{{ p }}</button>
      <button class="tab-pill" :class="{ 'tab-pill--active': activePreset === 'custom' }" disabled>Custom</button>
    </div>
    <div class="date-range-group">
      <input
        :value="dateFrom"
        type="date"
        @input="handleDateInput('dateFrom', ($event.target as HTMLInputElement).value)"
      />
      <span class="text-muted">—</span>
      <input
        :value="dateTo"
        type="date"
        @input="handleDateInput('dateTo', ($event.target as HTMLInputElement).value)"
      />
    </div>
    <select
      v-if="showGroupBy !== false"
      :value="groupBy"
      @change="emit('update:groupBy', ($event.target as HTMLSelectElement).value as GroupBy)"
    >
      <option value="month">Month</option>
      <option value="quarter">Quarter</option>
      <option value="year">Year</option>
    </select>
    <div v-if="$slots.default" style="margin-left: auto;">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.preset-pills {
  display: flex;
  gap: 0.25rem;
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
  .preset-pills {
    flex-wrap: wrap;
  }

  .date-range-group {
    flex-basis: 100%;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .date-range-group input[type="date"] {
    flex: 1;
    min-width: 0;
  }
}
</style>

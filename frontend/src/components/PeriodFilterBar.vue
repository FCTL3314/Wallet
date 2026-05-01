<script setup lang="ts">
import type { GroupBy } from '../api/analytics'
import { localDateStr } from '../utils/format'
import { PhCalendar } from '@phosphor-icons/vue'

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
  const todayStr = localDateStr(today)
  const yyyy = today.getFullYear()
  if (preset === 'All') return props.allRange ?? { from: '2000-01-01', to: todayStr }
  if (preset === 'YTD') return { from: `${yyyy}-01-01`, to: todayStr }
  let months: number
  if (preset === '3M') months = 3
  else if (preset === '6M') months = 6
  else if (preset === '12M') months = 12
  else return null
  const from = new Date(yyyy, today.getMonth() - (months - 1), 1)
  return { from: localDateStr(from), to: todayStr }
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
  <div class="filter-bar-row">
    <div class="segmented">
      <button
        v-for="p in (['All', 'YTD', '3M', '6M', '12M'] as const)"
        :key="p"
        :class="{ on: activePreset === p }"
        @click="setPreset(p)"
      >{{ p }}</button>
    </div>
    <div class="date-range">
      <PhCalendar :size="14" weight="bold" />
      <input
        :value="dateFrom"
        type="date"
        class="form-input-sm"
        @input="handleDateInput('dateFrom', ($event.target as HTMLInputElement).value)"
      />
      <span class="muted">—</span>
      <input
        :value="dateTo"
        type="date"
        class="form-input-sm"
        @input="handleDateInput('dateTo', ($event.target as HTMLInputElement).value)"
      />
    </div>
    <div v-if="showGroupBy !== false" class="group-select">
      <span class="label">Group</span>
      <div class="segmented segmented--mini">
        <button
          v-for="g in (['month', 'quarter', 'year'] as const)"
          :key="g"
          :class="{ on: groupBy === g }"
          @click="emit('update:groupBy', g)"
        >{{ g[0]!.toUpperCase() }}{{ g.slice(1) }}</button>
      </div>
    </div>
    <slot name="middle" />
    <div v-if="$slots.default" class="filter-actions">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.filter-bar-row {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}
.date-range {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--ink-3);
  font-size: 12px;
}
.date-range input[type="date"] {
  font-size: 12px;
  padding: 4px 8px;
}
.group-select {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.filter-actions {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
@media (max-width: 640px) {
  .filter-actions { margin-left: 0; }
  .date-range { flex-wrap: wrap; }
}
</style>

<script lang="ts">
export type PeriodPreset = 'All' | 'YTD' | '3M' | '6M' | '12M' | 'custom'
export type PeriodDateField = 'dateFrom' | 'dateTo'
</script>

<script setup lang="ts">
import { useId, type VNode } from 'vue'
import { PhCalendar } from '@phosphor-icons/vue'
import type { GroupBy } from '../api/analytics'

const PERIOD_PRESETS = ['All', 'YTD', '3M', '6M', '12M'] as const
const GROUP_BY_OPTIONS = ['month', 'quarter', 'year'] as const

defineProps<{
  dateFrom: string
  dateTo: string
  groupBy?: GroupBy
  activePreset: string
  showGroupBy?: boolean
  stacked?: boolean
}>()

const emit = defineEmits<{
  'select-preset': [PeriodPreset]
  'change-date': [PeriodDateField, string]
  'select-group': [GroupBy]
}>()

defineSlots<{ middle?: () => VNode[] }>()

const periodLabelId = useId()
const rangeLabelId = useId()
const groupLabelId = useId()

function onDateInput(field: PeriodDateField, event: Event) {
  emit('change-date', field, (event.target as HTMLInputElement).value)
}

function groupLabel(value: GroupBy): string {
  return `${value[0]!.toUpperCase()}${value.slice(1)}`
}
</script>

<template>
  <div class="period-controls" :class="{ 'period-controls--stacked': stacked }">
    <div class="pc-passthrough">
      <span :id="periodLabelId" class="label pc-label">Period</span>
      <div class="segmented" role="group" :aria-labelledby="periodLabelId">
        <button
          v-for="p in PERIOD_PRESETS"
          :key="p"
          type="button"
          :class="{ on: activePreset === p }"
          :aria-pressed="activePreset === p"
          @click="emit('select-preset', p)"
        >{{ p }}</button>
      </div>
    </div>

    <div class="pc-passthrough">
      <span :id="rangeLabelId" class="label pc-label">Custom range</span>
      <div class="date-range" role="group" :aria-labelledby="rangeLabelId">
        <PhCalendar :size="14" weight="bold" class="date-icon" aria-hidden="true" />
        <input
          :value="dateFrom"
          type="date"
          class="form-input-sm date-input"
          aria-label="From date"
          @input="onDateInput('dateFrom', $event)"
        />
        <span class="muted date-sep" aria-hidden="true">—</span>
        <input
          :value="dateTo"
          type="date"
          class="form-input-sm date-input"
          aria-label="To date"
          @input="onDateInput('dateTo', $event)"
        />
      </div>
    </div>

    <div v-if="showGroupBy !== false" class="group-select">
      <span :id="groupLabelId" class="label">Group</span>
      <div class="segmented segmented--mini" role="group" :aria-labelledby="groupLabelId">
        <button
          v-for="g in GROUP_BY_OPTIONS"
          :key="g"
          type="button"
          :class="{ on: groupBy === g }"
          :aria-pressed="groupBy === g"
          @click="emit('select-group', g)"
        >{{ groupLabel(g) }}</button>
      </div>
    </div>

    <div v-if="$slots.middle" class="pc-passthrough pc-middle">
      <slot name="middle" />
    </div>
  </div>
</template>

<style scoped>
.period-controls,
.pc-passthrough {
  display: contents;
}

.pc-label {
  display: none;
}

.date-range {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--ink-3);
  font-size: 12px;
}

.group-select {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.date-range .date-input {
  font-size: 12px;
  padding: 4px 8px;
}

@media (max-width: 640px) {
  .date-range .date-input {
    font-size: 16px;
    padding: 8px 10px;
  }
}

/* ── Stacked layout (bottom sheet) ──────────────────────── */

.period-controls--stacked {
  display: flex;
  flex-direction: column;
  gap: 18px;
  min-width: 0;
}

.period-controls--stacked .pc-passthrough,
.period-controls--stacked .group-select {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 8px;
  min-width: 0;
}

.period-controls--stacked .pc-label {
  display: block;
}

.period-controls--stacked .segmented {
  display: flex;
  width: 100%;
  min-width: 0;
}

.period-controls--stacked .segmented button {
  flex: 1 1 0;
  min-width: 0;
  justify-content: center;
  padding: 9px 4px;
  font-size: 13px;
}

.period-controls--stacked .segmented--mini button {
  padding: 8px 4px;
  font-size: 12px;
}

.period-controls--stacked .date-range {
  display: flex;
  width: 100%;
  gap: 8px;
  font-size: 14px;
}

.period-controls--stacked .date-icon {
  display: none;
}

.period-controls--stacked .date-input {
  flex: 1 1 0;
  width: 100%;
  min-width: 0;
  font-size: 16px;
  padding: 10px 12px;
}

.period-controls--stacked .pc-middle {
  flex-direction: row;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.period-controls--stacked .pc-middle :deep(.segmented) {
  flex-wrap: wrap;
  max-width: 100%;
}

.period-controls--stacked .pc-middle :deep(select),
.period-controls--stacked .pc-middle :deep(input) {
  font-size: 16px;
  padding: 9px 12px;
  max-width: 100%;
  min-width: 0;
}
</style>

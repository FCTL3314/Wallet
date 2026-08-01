<script lang="ts">
const COMPACT_QUERY = '(max-width: 640px)'
const MAX_SUMMARY_CHIPS = 2
const ALL_TIME_LABEL = 'All time'

const dayMonthFmt = new Intl.DateTimeFormat('en-US', { day: 'numeric', month: 'short' })
const dayMonthYearFmt = new Intl.DateTimeFormat('en-US', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
})

function parseLocalDate(iso: string): Date | null {
  const [year, month, day] = iso.split('-').map(Number)
  if (!year || !month || !day) return null
  const date = new Date(year, month - 1, day)
  return Number.isNaN(date.getTime()) ? null : date
}
</script>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { PhCalendar, PhSlidersHorizontal } from '@phosphor-icons/vue'
import type { GroupBy } from '../api/analytics'
import { localDateStr } from '../utils/format'
import BaseBottomSheet from './BaseBottomSheet.vue'
import PeriodFilterControls from './PeriodFilterControls.vue'
import type { PeriodDateField, PeriodPreset } from './PeriodFilterControls.vue'

const props = defineProps<{
  dateFrom: string
  dateTo: string
  groupBy?: GroupBy
  activePreset: string
  showGroupBy?: boolean
  allRange?: { from: string; to: string } | null
  extraFilters?: string[]
}>()

const emit = defineEmits<{
  'update:dateFrom': [string]
  'update:dateTo': [string]
  'update:groupBy': [GroupBy]
  'update:activePreset': [string]
}>()

const sheetOpen = ref(false)

let media: MediaQueryList | null = null
const compact = ref(false)

function onMediaChange(event: MediaQueryListEvent) {
  compact.value = event.matches
}

if (typeof window !== 'undefined') {
  media = window.matchMedia(COMPACT_QUERY)
  compact.value = media.matches
}

onMounted(() => media?.addEventListener('change', onMediaChange))
onBeforeUnmount(() => media?.removeEventListener('change', onMediaChange))

watch(compact, (isCompact) => {
  if (!isCompact) sheetOpen.value = false
})

function getPresetDates(preset: PeriodPreset): { from: string; to: string } | null {
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

function setPreset(preset: PeriodPreset) {
  const dates = getPresetDates(preset)
  if (dates) {
    emit('update:dateFrom', dates.from)
    emit('update:dateTo', dates.to)
  }
  emit('update:activePreset', preset)
}

function handleDateInput(field: PeriodDateField, value: string) {
  if (field === 'dateFrom') emit('update:dateFrom', value)
  else emit('update:dateTo', value)
  emit('update:activePreset', 'custom')
}

function selectGroup(value: GroupBy) {
  emit('update:groupBy', value)
}

const presetLabel = computed(() =>
  props.activePreset === 'custom' ? 'Custom' : props.activePreset,
)

const rangeLabel = computed(() => {
  const from = parseLocalDate(props.dateFrom)
  const to = parseLocalDate(props.dateTo)
  if (!from || !to) return `${props.dateFrom} — ${props.dateTo}`
  const currentYear = new Date().getFullYear()
  const spansYears =
    from.getFullYear() !== to.getFullYear() ||
    from.getFullYear() !== currentYear ||
    to.getFullYear() !== currentYear
  const fmt = spansYears ? dayMonthYearFmt : dayMonthFmt
  return `${fmt.format(from)} — ${fmt.format(to)}`
})

const periodLabel = computed(() =>
  props.activePreset === 'All' && !props.allRange ? ALL_TIME_LABEL : rangeLabel.value,
)

const summaryChips = computed<string[]>(() => {
  const chips: string[] = []
  if (props.showGroupBy !== false && props.groupBy) {
    chips.push(`${props.groupBy[0]!.toUpperCase()}${props.groupBy.slice(1)}`)
  }
  chips.push(...(props.extraFilters ?? []))
  return chips
})

const visibleChips = computed(() => summaryChips.value.slice(0, MAX_SUMMARY_CHIPS))
const hiddenChipCount = computed(() => summaryChips.value.length - visibleChips.value.length)

const summaryAriaLabel = computed(() => {
  const parts = [presetLabel.value, periodLabel.value, ...summaryChips.value]
  return `Filters: ${parts.join(', ')}. Open filter options`
})
</script>

<template>
  <div class="filter-bar-row" :class="{ 'filter-bar-row--compact': compact }">
    <PeriodFilterControls
      v-if="!compact"
      :date-from="dateFrom"
      :date-to="dateTo"
      :group-by="groupBy"
      :active-preset="activePreset"
      :show-group-by="showGroupBy"
      @select-preset="setPreset"
      @change-date="handleDateInput"
      @select-group="selectGroup"
    >
      <template v-if="$slots.middle" #middle>
        <slot name="middle" />
      </template>
    </PeriodFilterControls>

    <button
      v-else
      type="button"
      class="filter-summary"
      aria-haspopup="dialog"
      :aria-expanded="sheetOpen"
      :aria-label="summaryAriaLabel"
      @click="sheetOpen = true"
    >
      <PhCalendar :size="15" weight="bold" class="summary-icon" aria-hidden="true" />
      <span class="summary-text" aria-hidden="true">
        <span class="summary-preset">{{ presetLabel }}</span>
        <span class="summary-dot">·</span>
        <span class="summary-period">{{ periodLabel }}</span>
      </span>
      <span v-if="visibleChips.length" class="summary-chips" aria-hidden="true">
        <span v-for="chip in visibleChips" :key="chip" class="summary-chip">{{ chip }}</span>
        <span v-if="hiddenChipCount > 0" class="summary-chip">+{{ hiddenChipCount }}</span>
      </span>
      <PhSlidersHorizontal :size="16" weight="bold" class="summary-caret" aria-hidden="true" />
    </button>

    <div v-if="$slots.default" class="filter-actions">
      <slot />
    </div>

    <BaseBottomSheet v-model="sheetOpen" title="Filters" close-label="Done">
      <PeriodFilterControls
        stacked
        :date-from="dateFrom"
        :date-to="dateTo"
        :group-by="groupBy"
        :active-preset="activePreset"
        :show-group-by="showGroupBy"
        @select-preset="setPreset"
        @change-date="handleDateInput"
        @select-group="selectGroup"
      >
        <template v-if="$slots.middle" #middle>
          <slot name="middle" />
        </template>
      </PeriodFilterControls>
    </BaseBottomSheet>
  </div>
</template>

<style scoped>
.filter-bar-row {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
  min-width: 0;
}

.filter-actions {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

/* ── Compact summary (mobile) ───────────────────────────── */

.filter-bar-row--compact {
  flex-wrap: nowrap;
  gap: 10px;
  max-width: 100%;
}

.filter-summary {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 12px;
  border: 1px solid var(--hairline);
  border-radius: var(--r-pill);
  background: var(--surface-2);
  color: var(--ink);
  font-family: var(--font-sans);
  font-size: 13px;
  text-align: left;
  cursor: pointer;
  touch-action: manipulation;
  transition: background var(--t-fast) var(--ease), border-color var(--t-fast) var(--ease);
}

.filter-summary:active {
  transform: scale(0.99);
}

.filter-summary:focus-visible {
  outline: none;
  box-shadow: var(--focus-ring);
}

.summary-icon,
.summary-caret {
  flex: 0 0 auto;
  color: var(--ink-3);
}

.summary-text {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  align-items: baseline;
  gap: 5px;
  overflow: hidden;
  white-space: nowrap;
}

.summary-preset {
  flex: 0 0 auto;
  font-weight: 600;
  color: var(--accent-ink);
}

.summary-dot {
  flex: 0 0 auto;
  color: var(--ink-4);
}

.summary-period {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--ink-2);
}

.summary-chips {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.summary-chip {
  padding: 2px 8px;
  border-radius: var(--r-pill);
  background: var(--surface);
  border: 1px solid var(--hairline);
  color: var(--ink-3);
  font-size: 11px;
  font-weight: 500;
  white-space: nowrap;
}

.filter-bar-row--compact .filter-actions {
  flex: 0 0 auto;
  margin-left: 0;
}

@media (hover: hover) {
  .filter-summary:hover {
    background: var(--surface-hover);
    border-color: var(--hairline-strong);
  }
}

@media (max-width: 640px) {
  .filter-actions {
    margin-left: 0;
  }
}
</style>

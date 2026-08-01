<script setup lang="ts" generic="TData">
import { computed, onUnmounted, ref, useId, useTemplateRef, watch } from 'vue'
import { FlexRender, type Table, type Row, type Column } from '@tanstack/vue-table'
import BaseCard from './BaseCard.vue'

const SKELETON_WIDTHS = [62, 78, 55, 85, 70]
const SKELETON_ROWS = 5
const SKELETON_CARDS = 4
const LEGACY_EMPTY_COLSPAN = 99
const FALLBACK_COLUMN_COUNT = 5
const SCROLL_EPSILON = 1
const MOBILE_QUERY = '(max-width: 640px)'

const props = withDefaults(
  defineProps<{
    loading?: boolean
    empty?: boolean
    emptyMessage?: string
    title?: string
    /** TanStack Table instance — enables new table-driven mode */
    table?: Table<TData>
    /** Show a global search input above the table (only relevant in table-prop mode) */
    searchable?: boolean
    /** Render rows as stacked cards below 640px — requires the `card` slot */
    mobileCards?: boolean
    /** Pin the first column while scrolling horizontally below 640px */
    stickyFirstColumn?: boolean
  }>(),
  {
    stickyFirstColumn: true,
  },
)

defineSlots<{
  /**
   * In managed mode (table prop provided): receives typed rows from TanStack.
   * In legacy slot mode: called with an empty rows array.
   */
  body(props: { rows: Row<TData>[] }): unknown
  /** Mobile card layout rows — must render <li> elements. Same payload as `body`. */
  card(props: { rows: Row<TData>[] }): unknown
  /** Legacy slot mode: plain table head slot */
  head(props: Record<string, never>): unknown
  /** Card actions slot (both modes) */
  actions(props: Record<string, never>): unknown
}>()

const sortSelectId = useId()

/** True when a TanStack table instance is provided */
const isManagedMode = computed(() => !!props.table)

/** Number of columns to use for skeleton / empty colspan */
const columnCount = computed(
  () => props.table?.getAllLeafColumns().length ?? FALLBACK_COLUMN_COUNT,
)

const emptyColspan = computed(() =>
  isManagedMode.value ? columnCount.value : LEGACY_EMPTY_COLSPAN,
)

const rows = computed<Row<TData>[]>(() => props.table?.getRowModel().rows ?? [])

const isEmpty = computed(() => props.empty || (isManagedMode.value && rows.value.length === 0))

/* ── Mobile card mode ─────────────────────────────────── */

const isMobile = ref(false)
const cardMode = computed(() => props.mobileCards && isMobile.value)

let mediaQuery: MediaQueryList | null = null

function syncMedia(event: MediaQueryList | MediaQueryListEvent) {
  isMobile.value = event.matches
}

if (typeof window !== 'undefined' && 'matchMedia' in window) {
  mediaQuery = window.matchMedia(MOBILE_QUERY)
  syncMedia(mediaQuery)
  mediaQuery.addEventListener('change', syncMedia)
}

onUnmounted(() => mediaQuery?.removeEventListener('change', syncMedia))

/* ── Sorting (shared by header cells and the card sort bar) ── */

const sortableColumns = computed<Column<TData, unknown>[]>(
  () => props.table?.getAllLeafColumns().filter((column) => column.getCanSort()) ?? [],
)

const activeSort = computed(() => props.table?.getState().sorting[0] ?? null)
const activeSortId = computed(() => activeSort.value?.id ?? '')
const activeSortDesc = computed(() => activeSort.value?.desc ?? false)

const sortDirectionLabel = computed(() =>
  activeSortDesc.value ? 'Sort ascending' : 'Sort descending',
)

function columnLabel(column: Column<TData, unknown>): string {
  const header = column.columnDef.header
  return typeof header === 'string' && header ? header : column.id
}

function getSortIcon(direction: 'asc' | 'desc' | false): string {
  if (direction === 'asc') return '↑'
  if (direction === 'desc') return '↓'
  return '↕'
}

function getAriaSort(column: Column<TData, unknown>): 'ascending' | 'descending' | 'none' | undefined {
  if (!column.getCanSort()) return undefined
  const direction = column.getIsSorted()
  if (direction === 'asc') return 'ascending'
  if (direction === 'desc') return 'descending'
  return 'none'
}

function onSortColumnChange(event: Event) {
  const id = (event.target as HTMLSelectElement).value
  props.table?.setSorting(id ? [{ id, desc: activeSortDesc.value }] : [])
}

function toggleSortDirection() {
  const current = activeSort.value
  if (!current) return
  props.table?.setSorting([{ id: current.id, desc: !current.desc }])
}

function onSearchInput(e: Event) {
  props.table?.setGlobalFilter((e.target as HTMLInputElement).value)
}

/* ── Horizontal scroll affordance ─────────────────────── */

const scroller = useTemplateRef<HTMLElement>('scroller')
const canScrollStart = ref(false)
const canScrollEnd = ref(false)

const isScrollable = computed(() => canScrollStart.value || canScrollEnd.value)

let resizeObserver: ResizeObserver | null = null

function updateScrollState() {
  const el = scroller.value
  if (!el) {
    canScrollStart.value = false
    canScrollEnd.value = false
    return
  }
  const maxScroll = el.scrollWidth - el.clientWidth
  canScrollStart.value = el.scrollLeft > SCROLL_EPSILON
  canScrollEnd.value = el.scrollLeft < maxScroll - SCROLL_EPSILON
}

watch(
  scroller,
  (el) => {
    resizeObserver?.disconnect()
    resizeObserver = null
    if (!el) {
      updateScrollState()
      return
    }
    resizeObserver = new ResizeObserver(updateScrollState)
    resizeObserver.observe(el)
    if (el.firstElementChild) resizeObserver.observe(el.firstElementChild)
    updateScrollState()
  },
  { immediate: true, flush: 'post' },
)

onUnmounted(() => resizeObserver?.disconnect())
</script>

<template>
  <BaseCard :title="title" flush class="table-card">
    <template v-if="isManagedMode && searchable" #left>
      <div class="table-search-wrap">
        <span class="table-search-icon" aria-hidden="true">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
        </span>
        <input
          class="table-search-input"
          type="search"
          placeholder="Search…"
          :value="table!.getState().globalFilter ?? ''"
          @input="onSearchInput"
          aria-label="Search table"
        />
      </div>
    </template>

    <template v-if="$slots.actions" #actions>
      <slot name="actions" />
    </template>

    <!-- ── MOBILE CARD MODE ───────────────────────────── -->
    <div v-if="cardMode" class="table-cards">
      <div v-if="sortableColumns.length" class="cards-sortbar">
        <label class="cards-sort-label" :for="sortSelectId">Sort by</label>
        <select
          :id="sortSelectId"
          class="form-input-sm cards-sort-select"
          :value="activeSortId"
          @change="onSortColumnChange"
        >
          <option value="">Default</option>
          <option v-for="column in sortableColumns" :key="column.id" :value="column.id">
            {{ columnLabel(column) }}
          </option>
        </select>
        <button
          type="button"
          class="cards-sort-dir"
          :disabled="!activeSortId"
          :aria-label="sortDirectionLabel"
          @click="toggleSortDirection"
        >
          <span aria-hidden="true">{{ activeSortDesc ? '↓' : '↑' }}</span>
        </button>
      </div>

      <ul v-if="loading" class="row-card-list">
        <li v-for="i in SKELETON_CARDS" :key="i" class="row-card row-card--skeleton">
          <div class="row-card-body">
            <div
              class="skeleton-cell"
              :style="{ width: SKELETON_WIDTHS[i % SKELETON_WIDTHS.length] + '%' }"
            />
            <div
              class="skeleton-cell"
              :style="{ width: SKELETON_WIDTHS[(i + 2) % SKELETON_WIDTHS.length] + '%' }"
            />
          </div>
        </li>
      </ul>

      <div v-else-if="isEmpty" class="table-empty table-empty--cards">
        <svg class="table-empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 01-1.125-1.125M3.375 19.5h7.5c.621 0 1.125-.504 1.125-1.125m-9.75 0V5.625m0 12.75v-1.5c0-.621.504-1.125 1.125-1.125m18.375 2.625V5.625m0 12.75c0 .621-.504 1.125-1.125 1.125m1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125m0 3.75h-7.5A1.125 1.125 0 0112 18.375m9.75-12.75c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125m19.5 0v1.5c0 .621-.504 1.125-1.125 1.125M2.25 5.625v1.5c0 .621.504 1.125 1.125 1.125m0 0h17.25m-17.25 0h7.5c.621 0 1.125.504 1.125 1.125M3.375 8.25c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125m17.25-3.75h-7.5c-.621 0-1.125.504-1.125 1.125m8.625-1.125c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125m-17.25 0h7.5m-7.5 0c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125M12 10.875v-1.5m0 1.5c0 .621-.504 1.125-1.125 1.125M12 10.875c0 .621.504 1.125 1.125 1.125m-2.25 0c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125m2.25-2.25h-2.25m0 0h-7.5m7.5 0v1.5" />
        </svg>
        <p class="table-empty-msg">{{ emptyMessage ?? 'No items yet.' }}</p>
      </div>

      <ul v-else class="row-card-list">
        <slot name="card" :rows="rows" />
      </ul>
    </div>

    <!-- ── TABLE MODE ─────────────────────────────────── -->
    <div
      v-else
      class="table-scroll-wrap"
      :class="{
        'table-scroll-wrap--sticky': stickyFirstColumn,
        'can-scroll-start': canScrollStart,
        'can-scroll-end': canScrollEnd,
      }"
    >
      <div
        ref="scroller"
        class="table-scroll"
        :tabindex="isScrollable ? 0 : undefined"
        :role="isScrollable ? 'region' : undefined"
        :aria-label="isScrollable ? `${title ?? 'Table'} — scrollable` : undefined"
        @scroll.passive="updateScrollState"
      >
        <table class="data-table">
          <thead>
            <tr v-if="isManagedMode && table">
              <th
                v-for="header in table.getFlatHeaders()"
                :key="header.id"
                :class="[
                  header.column.columnDef.meta?.class,
                  { 'th-sortable': header.column.getCanSort() },
                ]"
                :style="header.column.columnDef.meta?.style"
                :aria-sort="getAriaSort(header.column)"
                @click="header.column.getToggleSortingHandler()?.($event)"
              >
                <span class="th-content">
                  <FlexRender
                    v-if="!header.isPlaceholder"
                    :render="header.column.columnDef.header"
                    :props="header.getContext()"
                  />
                  <span
                    v-if="header.column.getCanSort()"
                    class="sort-icon"
                    :class="{
                      'sort-icon--active': header.column.getIsSorted() !== false,
                    }"
                    aria-hidden="true"
                  >{{ getSortIcon(header.column.getIsSorted()) }}</span>
                </span>
              </th>
            </tr>
            <slot v-else name="head" />
          </thead>

          <tbody v-if="loading">
            <tr v-for="i in SKELETON_ROWS" :key="i" class="skeleton-tr">
              <td v-for="j in columnCount" :key="j">
                <div
                  class="skeleton-cell"
                  :style="{ width: SKELETON_WIDTHS[(i + j) % SKELETON_WIDTHS.length] + '%' }"
                />
              </td>
            </tr>
          </tbody>

          <tbody v-else-if="isEmpty">
            <tr>
              <td :colspan="emptyColspan" class="table-empty-cell">
                <div class="table-empty">
                  <svg class="table-empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 01-1.125-1.125M3.375 19.5h7.5c.621 0 1.125-.504 1.125-1.125m-9.75 0V5.625m0 12.75v-1.5c0-.621.504-1.125 1.125-1.125m18.375 2.625V5.625m0 12.75c0 .621-.504 1.125-1.125 1.125m1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125m0 3.75h-7.5A1.125 1.125 0 0112 18.375m9.75-12.75c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125m19.5 0v1.5c0 .621-.504 1.125-1.125 1.125M2.25 5.625v1.5c0 .621.504 1.125 1.125 1.125m0 0h17.25m-17.25 0h7.5c.621 0 1.125.504 1.125 1.125M3.375 8.25c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125m17.25-3.75h-7.5c-.621 0-1.125.504-1.125 1.125m8.625-1.125c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125m-17.25 0h7.5m-7.5 0c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125M12 10.875v-1.5m0 1.5c0 .621-.504 1.125-1.125 1.125M12 10.875c0 .621.504 1.125 1.125 1.125m-2.25 0c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125m2.25-2.25h-2.25m0 0h-7.5m7.5 0v1.5" />
                  </svg>
                  <p class="table-empty-msg">{{ emptyMessage ?? 'No items yet.' }}</p>
                </div>
              </td>
            </tr>
          </tbody>

          <tbody v-else>
            <slot name="body" :rows="rows" />
          </tbody>
        </table>
      </div>

      <span class="table-scroll-fade table-scroll-fade--start" aria-hidden="true" />
      <span class="table-scroll-fade table-scroll-fade--end" aria-hidden="true" />
    </div>
  </BaseCard>
</template>

<style scoped>
/* Search input — lives in the card header row */
.table-search-wrap {
  position: relative;
  display: flex;
  align-items: center;
}

.table-search-icon {
  position: absolute;
  left: 9px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-placeholder);
  pointer-events: none;
  display: flex;
  align-items: center;
}

.table-search-input {
  width: 200px;
  padding: 6px 10px 6px 30px;
  background: rgba(0, 0, 0, 0.04);
  border: 1px solid var(--card-border);
  border-radius: var(--radius-input);
  font-family: var(--font-body);
  font-size: 0.8125rem;
  color: var(--text-primary);
  outline: none;
  transition: width 0.2s ease, border-color 0.18s, box-shadow 0.18s;
}

.table-search-input:focus {
  width: 260px;
  border-color: rgba(var(--color-accent-rgb), 0.55);
  box-shadow: 0 0 0 2px rgba(var(--color-accent-rgb), 0.12);
}

[data-theme="dark"] .table-search-input {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.10);
}

/* Sortable th styles */
.th-sortable {
  cursor: pointer;
  user-select: none;
}

@media (hover: hover) {
  .th-sortable:hover {
    background: rgba(var(--color-accent-rgb), 0.07);
  }
}

.th-content {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.sort-icon {
  font-size: 0.75em;
  opacity: 0.35;
  transition: opacity 0.15s, color 0.15s;
  line-height: 1;
  display: inline-block;
}

.sort-icon--active {
  opacity: 1;
  color: var(--color-accent);
}

/* On phones the search takes the full header width instead of growing on focus */
@media (max-width: 640px) {
  .table-search-wrap {
    flex: 1 1 100%;
    min-width: 0;
  }

  .table-search-input,
  .table-search-input:focus {
    width: 100%;
  }
}
</style>

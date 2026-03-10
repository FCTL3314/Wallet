<script setup lang="ts" generic="TData">
import { computed } from 'vue'
import { FlexRender, type Table, type Row } from '@tanstack/vue-table'
import BaseCard from './BaseCard.vue'

const SKELETON_WIDTHS = [62, 78, 55, 85, 70]

const props = defineProps<{
  loading?: boolean
  empty?: boolean
  emptyMessage?: string
  title?: string
  columns?: number
  /** TanStack Table instance — enables new table-driven mode */
  table?: Table<TData>
  /** Show a global search input above the table (only relevant in table-prop mode) */
  searchable?: boolean
}>()

const emit = defineEmits<{
  'update:search': [value: string]
}>()

defineSlots<{
  /**
   * In managed mode (table prop provided): receives typed rows from TanStack.
   * In legacy slot mode: called with no props (rows will be undefined).
   */
  body(props: { rows: Row<TData>[] }): unknown
  /** Legacy slot mode: plain table head slot */
  head(props: Record<string, never>): unknown
  /** Card actions slot (both modes) */
  actions(props: Record<string, never>): unknown
}>()

/** True when a TanStack table instance is provided */
const isManagedMode = computed(() => !!props.table)

/** Number of columns to use for skeleton / empty colspan */
const columnCount = computed(() => {
  if (props.table) return props.table.getAllLeafColumns().length
  return props.columns ?? 5
})

function getSortIcon(direction: 'asc' | 'desc' | false): string {
  if (direction === 'asc') return '↑'
  if (direction === 'desc') return '↓'
  return '↕'
}

function onSearchInput(e: Event) {
  const value = (e.target as HTMLInputElement).value
  props.table?.setGlobalFilter(value)
  emit('update:search', value)
}
</script>

<template>
  <BaseCard :title="title" flush>
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

    <div style="overflow-x: auto;">
      <table class="data-table">

        <!-- ── MANAGED MODE (TanStack table prop) ─────────── -->
        <template v-if="isManagedMode && table">
          <thead>
            <tr>
              <th
                v-for="header in table.getFlatHeaders()"
                :key="header.id"
                :class="[
                  header.column.columnDef.meta?.class,
                  { 'th-sortable': header.column.getCanSort() },
                ]"
                :style="header.column.columnDef.meta?.style"
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
          </thead>

          <tbody v-if="loading">
            <tr v-for="i in 5" :key="i" class="skeleton-tr">
              <td v-for="j in columnCount" :key="j">
                <div
                  class="skeleton-cell"
                  :style="{ width: SKELETON_WIDTHS[(i + j) % SKELETON_WIDTHS.length] + '%' }"
                />
              </td>
            </tr>
          </tbody>

          <tbody v-else-if="empty || table.getRowModel().rows.length === 0">
            <tr>
              <td :colspan="columnCount" class="table-empty-cell">
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
            <slot name="body" :rows="table.getRowModel().rows" />
          </tbody>
        </template>

        <!-- ── LEGACY SLOT MODE ────────────────────────────── -->
        <template v-else>
          <thead><slot name="head" /></thead>

          <tbody v-if="loading">
            <tr v-for="i in 5" :key="i" class="skeleton-tr">
              <td v-for="j in columnCount" :key="j">
                <div
                  class="skeleton-cell"
                  :style="{ width: SKELETON_WIDTHS[(i + j) % SKELETON_WIDTHS.length] + '%' }"
                />
              </td>
            </tr>
          </tbody>

          <tbody v-else-if="empty">
            <tr>
              <td colspan="99" class="table-empty-cell">
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
            <slot name="body" :rows="([] as never)" />
          </tbody>
        </template>

      </table>
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

.th-sortable:hover {
  background: rgba(var(--color-accent-rgb), 0.07);
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
</style>

import {
  useVueTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  type ColumnDef,
  type SortingState,
  type ColumnFiltersState,
  type Table,
  type RowData,
} from '@tanstack/vue-table'
import { ref, type Ref } from 'vue'

export { createColumnHelper } from '@tanstack/vue-table'
export type { ColumnDef, SortingState, Table, RowData }

// Augment ColumnMeta to support per-column CSS class and inline style for th/td
declare module '@tanstack/table-core' {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  interface ColumnMeta<TData extends RowData, TValue> {
    /** Extra CSS class string applied to <th> and consumer <td> elements */
    class?: string
    /** Inline style applied to <th> */
    style?: string | Record<string, string>
  }
}

export interface UseTableOptions {
  /** Enable global text filter (client-side). Default: false */
  globalFilter?: boolean
  /** Enable column-level filters (client-side). Default: false */
  columnFilters?: boolean
  /**
   * When true, sorting is handled externally (server-side).
   * The table instance will still expose sortingState but will NOT
   * re-order rows itself. Default: false
   */
  manualSorting?: boolean
}

export interface UseTableReturn<TData extends RowData> {
  table: Table<TData>
  sortingState: Ref<SortingState>
  globalFilterValue: Ref<string>
  columnFiltersState: Ref<ColumnFiltersState>
}

export function useTable<TData extends RowData>(
  columns: ColumnDef<TData>[],
  data: Ref<TData[]>,
  options: UseTableOptions = {},
): UseTableReturn<TData> {
  const sortingState = ref<SortingState>([])
  const globalFilterValue = ref('')
  const columnFiltersState = ref<ColumnFiltersState>([])

  const table = useVueTable({
    get data() {
      return data.value
    },
    columns,
    state: {
      get sorting() {
        return sortingState.value
      },
      get globalFilter() {
        return globalFilterValue.value
      },
      get columnFilters() {
        return columnFiltersState.value
      },
    },
    onSortingChange: (updater) => {
      sortingState.value =
        typeof updater === 'function' ? updater(sortingState.value) : updater
    },
    onGlobalFilterChange: (updater) => {
      globalFilterValue.value =
        typeof updater === 'function' ? updater(globalFilterValue.value) : updater
    },
    onColumnFiltersChange: (updater) => {
      columnFiltersState.value =
        typeof updater === 'function' ? updater(columnFiltersState.value) : updater
    },
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: options.manualSorting ? undefined : getSortedRowModel(),
    getFilteredRowModel:
      options.globalFilter || options.columnFilters ? getFilteredRowModel() : undefined,
    manualSorting: options.manualSorting ?? false,
    // Single-column sort only (no multi-sort on shift-click)
    enableMultiSort: false,
  })

  return {
    table,
    sortingState,
    globalFilterValue,
    columnFiltersState,
  }
}

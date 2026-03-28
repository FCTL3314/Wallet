import { ref } from 'vue'
import { analyticsApi } from '../api/analytics'
import { localDateStr } from '../utils/format'

export function useDateRange(defaultPreset: string = 'YTD') {
  const today = new Date()
  const currentYear = today.getFullYear()

  const dateFrom = ref(
    defaultPreset === 'All' ? '2000-01-01' : `${currentYear}-01-01`,
  )
  const dateTo = ref(localDateStr(today))
  const activePreset = ref(defaultPreset)
  const allRange = ref<{ from: string; to: string } | null>(null)

  async function initRange() {
    const { data: dr } = await analyticsApi.dateRange()
    if (dr.min_date && dr.max_date) {
      allRange.value = { from: dr.min_date, to: dr.max_date }
      if (activePreset.value === 'All') {
        dateFrom.value = dr.min_date
        dateTo.value = dr.max_date
      }
    }
  }

  return {
    dateFrom,
    dateTo,
    activePreset,
    allRange,
    initRange,
  }
}

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  currenciesApi, storageLocationsApi, storageAccountsApi, incomeSourcesApi, expenseCategoriesApi,
  type Currency, type StorageLocation, type StorageAccount, type IncomeSource, type ExpenseCategory,
} from '../api/references'

export const useReferencesStore = defineStore('references', () => {
  const currencies = ref<Currency[]>([])
  const storageLocations = ref<StorageLocation[]>([])
  const storageAccounts = ref<StorageAccount[]>([])
  const incomeSources = ref<IncomeSource[]>([])
  const expenseCategories = ref<ExpenseCategory[]>([])
  const loaded = ref(false)

  // O(1) lookup maps — recomputed only when source arrays change
  const _currencyById = computed(() => new Map(currencies.value.map((c) => [c.id, c])))
  const _currencyByCode = computed(() => new Map(currencies.value.map((c) => [c.code, c])))
  const _locationById = computed(() => new Map(storageLocations.value.map((l) => [l.id, l])))
  const _accountById = computed(() => new Map(storageAccounts.value.map((a) => [a.id, a])))

  async function fetchAll() {
    const [c, sl, sa, is_, ec] = await Promise.all([
      currenciesApi.list(),
      storageLocationsApi.list(),
      storageAccountsApi.list(),
      incomeSourcesApi.list(),
      expenseCategoriesApi.list(),
    ])
    currencies.value = c.data
    storageLocations.value = sl.data
    storageAccounts.value = sa.data
    incomeSources.value = is_.data
    expenseCategories.value = ec.data
    loaded.value = true
  }

  function currencyById(id: number) {
    return _currencyById.value.get(id)
  }

  function currencyByCode(code: string) {
    return _currencyByCode.value.get(code)
  }

  function storageAccountLabel(acc: StorageAccount) {
    const loc = _locationById.value.get(acc.storage_location_id)
    const cur = _currencyById.value.get(acc.currency_id)
    return `${loc?.name ?? '?'} ${cur?.code ?? '?'}`
  }

  function storageAccountLabelById(id: number): string {
    const acc = _accountById.value.get(id)
    return acc ? storageAccountLabel(acc) : '?'
  }

  return {
    currencies, storageLocations, storageAccounts, incomeSources, expenseCategories,
    loaded, fetchAll, currencyById, currencyByCode, storageAccountLabel, storageAccountLabelById,
  }
})

import { defineStore } from 'pinia'
import { ref } from 'vue'
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
    return currencies.value.find((c) => c.id === id)
  }

  function storageAccountLabel(acc: StorageAccount) {
    const loc = storageLocations.value.find((l) => l.id === acc.storage_location_id)
    const cur = currencies.value.find((c) => c.id === acc.currency_id)
    return `${loc?.name ?? '?'} ${cur?.code ?? '?'}`
  }

  function storageAccountLabelById(id: number): string {
    const acc = storageAccounts.value.find((a) => a.id === id)
    return acc ? storageAccountLabel(acc) : '?'
  }

  return {
    currencies, storageLocations, storageAccounts, incomeSources, expenseCategories,
    loaded, fetchAll, currencyById, storageAccountLabel, storageAccountLabelById,
  }
})

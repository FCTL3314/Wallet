<script setup lang="ts">
import { ref } from 'vue'
import { useReferencesStore } from '../stores/references'
import {
  currenciesApi, storageLocationsApi, storageAccountsApi, incomeSourcesApi,
  type Currency, type StorageLocation, type IncomeSource,
} from '../api/references'
import { useCrudSection } from '../composables/useCrudSection'
import BaseButton from '../components/BaseButton.vue'
import BaseConfirmButton from '../components/BaseConfirmButton.vue'
import SettingsSection from '../components/SettingsSection.vue'

const refs = useReferencesStore()
const fetchAll = () => refs.fetchAll()

const currencyCrud = useCrudSection(currenciesApi, fetchAll)
const locationCrud = useCrudSection(storageLocationsApi, fetchAll)
const accountCrud = useCrudSection(storageAccountsApi, fetchAll)
const sourceCrud = useCrudSection(incomeSourcesApi, fetchAll)

// Currency
const newCurrency = ref({ code: '', symbol: '' })
async function addCurrency() {
  if (!newCurrency.value.code) return
  await currencyCrud.add(newCurrency.value)
  newCurrency.value = { code: '', symbol: '' }
}
const deleteCurrency = (id: number) => currencyCrud.remove(id)
const editingCurrency = ref<Currency | null>(null)
const editCurrencyForm = ref({ code: '', symbol: '' })
function openEditCurrency(c: Currency) {
  editingCurrency.value = c
  editCurrencyForm.value = { code: c.code, symbol: c.symbol }
}
async function saveEditCurrency() {
  if (!editingCurrency.value) return
  await currenciesApi.update(editingCurrency.value.id, editCurrencyForm.value)
  editingCurrency.value = null
  await refs.fetchAll()
}

// Storage Location
const newLocation = ref('')
async function addLocation() {
  if (!newLocation.value) return
  await locationCrud.add({ name: newLocation.value })
  newLocation.value = ''
}
const deleteLocation = (id: number) => locationCrud.remove(id)
const editingLocation = ref<StorageLocation | null>(null)
const editLocationForm = ref({ name: '' })
function openEditLocation(l: StorageLocation) {
  editingLocation.value = l
  editLocationForm.value = { name: l.name }
}
async function saveEditLocation() {
  if (!editingLocation.value) return
  await storageLocationsApi.update(editingLocation.value.id, editLocationForm.value)
  editingLocation.value = null
  await refs.fetchAll()
}

// Storage Account
const newAccount = ref({ storage_location_id: 0, currency_id: 0 })
async function addAccount() {
  if (!newAccount.value.storage_location_id || !newAccount.value.currency_id) return
  await accountCrud.add(newAccount.value)
  newAccount.value = { storage_location_id: 0, currency_id: 0 }
}
const deleteAccount = (id: number) => accountCrud.remove(id)

// Income Source
const newSource = ref('')
async function addSource() {
  if (!newSource.value) return
  await sourceCrud.add({ name: newSource.value })
  newSource.value = ''
}
const deleteSource = (id: number) => sourceCrud.remove(id)
const editingSource = ref<IncomeSource | null>(null)
const editSourceForm = ref({ name: '' })
function openEditSource(s: IncomeSource) {
  editingSource.value = s
  editSourceForm.value = { name: s.name }
}
async function saveEditSource() {
  if (!editingSource.value) return
  await incomeSourcesApi.update(editingSource.value.id, editSourceForm.value)
  editingSource.value = null
  await refs.fetchAll()
}
</script>

<template>
  <h1 class="page-title">Settings</h1>

  <div class="settings-grid">
    <!-- Currencies -->
    <SettingsSection title="Currencies" :items="refs.currencies" @add="addCurrency">
      <template #add-form>
        <input v-model="newCurrency.code" placeholder="Code (USD)" class="form-input-sm" style="flex: 1" />
        <input v-model="newCurrency.symbol" placeholder="Symbol ($)" class="form-input-sm" style="flex: 1" />
      </template>
      <template #default="{ item: c }">
        <template v-if="editingCurrency?.id === c.id">
          <div style="display: flex; gap: 8px">
            <input v-model="editCurrencyForm.code" class="form-input-sm" style="width: 80px" />
            <input v-model="editCurrencyForm.symbol" class="form-input-sm" style="width: 60px" />
          </div>
          <div style="display: flex; gap: 8px">
            <BaseButton variant="primary" size="sm" @click="saveEditCurrency">Save</BaseButton>
            <BaseButton variant="secondary" size="sm" @click="editingCurrency = null">Cancel</BaseButton>
          </div>
        </template>
        <template v-else>
          <span>{{ c.code }} ({{ c.symbol }})</span>
          <div style="display: flex; gap: 8px">
            <BaseButton variant="secondary" size="sm" @click="openEditCurrency(c)">Edit</BaseButton>
            <BaseConfirmButton @confirm="deleteCurrency(c.id)" />
          </div>
        </template>
      </template>
    </SettingsSection>

    <!-- Storage Locations -->
    <SettingsSection title="Storage Locations" :items="refs.storageLocations" @add="addLocation">
      <template #add-form>
        <input v-model="newLocation" placeholder="Name" class="form-input-sm" style="flex: 1" />
      </template>
      <template #default="{ item: l }">
        <template v-if="editingLocation?.id === l.id">
          <input v-model="editLocationForm.name" class="form-input-sm" style="flex: 1" />
          <div style="display: flex; gap: 8px">
            <BaseButton variant="primary" size="sm" @click="saveEditLocation">Save</BaseButton>
            <BaseButton variant="secondary" size="sm" @click="editingLocation = null">Cancel</BaseButton>
          </div>
        </template>
        <template v-else>
          <span>{{ l.name }}</span>
          <div style="display: flex; gap: 8px">
            <BaseButton variant="secondary" size="sm" @click="openEditLocation(l)">Edit</BaseButton>
            <BaseConfirmButton @confirm="deleteLocation(l.id)" />
          </div>
        </template>
      </template>
    </SettingsSection>

    <!-- Storage Accounts -->
    <SettingsSection title="Storage Accounts" :items="refs.storageAccounts" @add="addAccount">
      <template #add-form>
        <select v-model.number="newAccount.storage_location_id" class="form-input-sm" style="flex: 1">
          <option :value="0" disabled>Location</option>
          <option v-for="l in refs.storageLocations" :key="l.id" :value="l.id">{{ l.name }}</option>
        </select>
        <select v-model.number="newAccount.currency_id" class="form-input-sm" style="flex: 1">
          <option :value="0" disabled>Currency</option>
          <option v-for="c in refs.currencies" :key="c.id" :value="c.id">{{ c.code }}</option>
        </select>
      </template>
      <template #default="{ item: a }">
        <span>{{ refs.storageAccountLabel(a) }}</span>
        <BaseConfirmButton @confirm="deleteAccount(a.id)" />
      </template>
    </SettingsSection>

    <!-- Income Sources -->
    <SettingsSection title="Income Sources" :items="refs.incomeSources" @add="addSource">
      <template #add-form>
        <input v-model="newSource" placeholder="Name" class="form-input-sm" style="flex: 1" />
      </template>
      <template #default="{ item: s }">
        <template v-if="editingSource?.id === s.id">
          <input v-model="editSourceForm.name" class="form-input-sm" style="flex: 1" />
          <div style="display: flex; gap: 8px">
            <BaseButton variant="primary" size="sm" @click="saveEditSource">Save</BaseButton>
            <BaseButton variant="secondary" size="sm" @click="editingSource = null">Cancel</BaseButton>
          </div>
        </template>
        <template v-else>
          <span>{{ s.name }}</span>
          <div style="display: flex; gap: 8px">
            <BaseButton variant="secondary" size="sm" @click="openEditSource(s)">Edit</BaseButton>
            <BaseConfirmButton @confirm="deleteSource(s.id)" />
          </div>
        </template>
      </template>
    </SettingsSection>
  </div>
</template>

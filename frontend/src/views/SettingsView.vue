<script setup lang="ts">
import { ref } from 'vue'
import { useReferencesStore } from '../stores/references'
import {
  currenciesApi, storageLocationsApi, storageAccountsApi, incomeSourcesApi,
  type StorageAccount,
} from '../api/references'
import { useCrudSection } from '../composables/useCrudSection'

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
const deleteCurrency = (id: number) => currencyCrud.remove(id, 'Delete currency?')

// Storage Location
const newLocation = ref('')
async function addLocation() {
  if (!newLocation.value) return
  await locationCrud.add({ name: newLocation.value })
  newLocation.value = ''
}
const deleteLocation = (id: number) => locationCrud.remove(id, 'Delete storage location?')

// Storage Account
const newAccount = ref({ storage_location_id: 0, currency_id: 0 })
async function addAccount() {
  if (!newAccount.value.storage_location_id || !newAccount.value.currency_id) return
  await accountCrud.add(newAccount.value)
  newAccount.value = { storage_location_id: 0, currency_id: 0 }
}
const deleteAccount = (id: number) => accountCrud.remove(id, 'Delete storage account?')
const editingAccount = ref<StorageAccount | null>(null)
const editAccountForm = ref({ storage_location_id: 0 })
function openEditAccount(acc: StorageAccount) {
  editingAccount.value = acc
  editAccountForm.value = { storage_location_id: acc.storage_location_id }
}
async function saveEditAccount() {
  if (!editingAccount.value) return
  await storageAccountsApi.update(editingAccount.value.id, editAccountForm.value)
  editingAccount.value = null
  await refs.fetchAll()
}

// Income Source
const newSource = ref('')
async function addSource() {
  if (!newSource.value) return
  await sourceCrud.add({ name: newSource.value })
  newSource.value = ''
}
const deleteSource = (id: number) => sourceCrud.remove(id, 'Delete income source?')
</script>

<template>
  <h1 class="page-title">Settings</h1>

  <div class="settings-grid">
    <!-- Currencies -->
    <div class="card">
      <div class="card-title">Currencies</div>
      <div class="settings-item-row">
        <input v-model="newCurrency.code" placeholder="Code (USD)" class="form-input-sm" style="width: 80px" />
        <input v-model="newCurrency.symbol" placeholder="Symbol ($)" class="form-input-sm" style="width: 60px" />
        <button class="btn btn-primary btn-sm" @click="addCurrency">Add</button>
      </div>
      <div v-for="c in refs.currencies" :key="c.id" class="settings-item">
        <span>{{ c.code }} ({{ c.symbol }})</span>
        <button class="btn btn-danger btn-sm" @click="deleteCurrency(c.id)">Del</button>
      </div>
    </div>

    <!-- Storage Locations -->
    <div class="card">
      <div class="card-title">Storage Locations</div>
      <div class="settings-item-row">
        <input v-model="newLocation" placeholder="Name" class="form-input-sm" style="flex: 1" />
        <button class="btn btn-primary btn-sm" @click="addLocation">Add</button>
      </div>
      <div v-for="l in refs.storageLocations" :key="l.id" class="settings-item">
        <span>{{ l.name }}</span>
        <button class="btn btn-danger btn-sm" @click="deleteLocation(l.id)">Del</button>
      </div>
    </div>

    <!-- Storage Accounts -->
    <div class="card">
      <div class="card-title">Storage Accounts</div>
      <div class="settings-item-row">
        <select v-model.number="newAccount.storage_location_id" class="form-input-sm" style="flex: 1">
          <option :value="0" disabled>Location</option>
          <option v-for="l in refs.storageLocations" :key="l.id" :value="l.id">{{ l.name }}</option>
        </select>
        <select v-model.number="newAccount.currency_id" class="form-input-sm" style="flex: 1">
          <option :value="0" disabled>Currency</option>
          <option v-for="c in refs.currencies" :key="c.id" :value="c.id">{{ c.code }}</option>
        </select>
        <button class="btn btn-primary btn-sm" @click="addAccount">Add</button>
      </div>
      <div v-for="a in refs.storageAccounts" :key="a.id" class="settings-item">
        <template v-if="editingAccount?.id === a.id">
          <select v-model.number="editAccountForm.storage_location_id" class="form-input-sm" style="flex: 1">
            <option v-for="l in refs.storageLocations" :key="l.id" :value="l.id">{{ l.name }}</option>
          </select>
          <button class="btn btn-primary btn-sm" @click="saveEditAccount">Save</button>
          <button class="btn btn-secondary btn-sm" @click="editingAccount = null">Cancel</button>
        </template>
        <template v-else>
          <span>{{ refs.storageAccountLabel(a) }}</span>
          <button class="btn btn-secondary btn-sm" @click="openEditAccount(a)">Edit</button>
          <button class="btn btn-danger btn-sm" @click="deleteAccount(a.id)">Del</button>
        </template>
      </div>
    </div>

    <!-- Income Sources -->
    <div class="card">
      <div class="card-title">Income Sources</div>
      <div class="settings-item-row">
        <input v-model="newSource" placeholder="Name" class="form-input-sm" style="flex: 1" />
        <button class="btn btn-primary btn-sm" @click="addSource">Add</button>
      </div>
      <div v-for="s in refs.incomeSources" :key="s.id" class="settings-item">
        <span>{{ s.name }}</span>
        <button class="btn btn-danger btn-sm" @click="deleteSource(s.id)">Del</button>
      </div>
    </div>
  </div>
</template>

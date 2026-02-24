<script setup lang="ts">
import { ref } from 'vue'
import { useReferencesStore } from '../stores/references'
import {
  currenciesApi, storageLocationsApi, storageAccountsApi, incomeSourcesApi,
} from '../api/references'

const refs = useReferencesStore()

// Currency
const newCurrency = ref({ code: '', symbol: '' })
async function addCurrency() {
  if (!newCurrency.value.code) return
  await currenciesApi.create(newCurrency.value)
  newCurrency.value = { code: '', symbol: '' }
  await refs.fetchAll()
}
async function deleteCurrency(id: number) {
  if (!confirm('Delete currency?')) return
  await currenciesApi.delete(id)
  await refs.fetchAll()
}

// Storage Location
const newLocation = ref('')
async function addLocation() {
  if (!newLocation.value) return
  await storageLocationsApi.create({ name: newLocation.value })
  newLocation.value = ''
  await refs.fetchAll()
}
async function deleteLocation(id: number) {
  if (!confirm('Delete storage location?')) return
  await storageLocationsApi.delete(id)
  await refs.fetchAll()
}

// Storage Account
const newAccount = ref({ storage_location_id: 0, currency_id: 0 })
async function addAccount() {
  if (!newAccount.value.storage_location_id || !newAccount.value.currency_id) return
  await storageAccountsApi.create(newAccount.value)
  newAccount.value = { storage_location_id: 0, currency_id: 0 }
  await refs.fetchAll()
}
async function deleteAccount(id: number) {
  if (!confirm('Delete storage account?')) return
  await storageAccountsApi.delete(id)
  await refs.fetchAll()
}

// Income Source
const newSource = ref('')
async function addSource() {
  if (!newSource.value) return
  await incomeSourcesApi.create({ name: newSource.value })
  newSource.value = ''
  await refs.fetchAll()
}
async function deleteSource(id: number) {
  if (!confirm('Delete income source?')) return
  await incomeSourcesApi.delete(id)
  await refs.fetchAll()
}
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
        <span>{{ refs.storageAccountLabel(a) }}</span>
        <button class="btn btn-danger btn-sm" @click="deleteAccount(a.id)">Del</button>
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

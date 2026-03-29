<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useReferencesStore } from '../stores/references'
import { useAuthStore } from '../stores/auth'
import {
  currenciesApi, storageLocationsApi, storageAccountsApi, incomeSourcesApi,
  type Currency, type StorageLocation, type IncomeSource, type CatalogCurrency,
  type RateInfo, type UserManualRate,
} from '../api/references'
import { fmtAmount } from '../utils/format'
import { useCrudSection } from '../composables/useCrudSection'
import BaseButton from '../components/BaseButton.vue'
import BaseCard from '../components/BaseCard.vue'
import BaseConfirmButton from '../components/BaseConfirmButton.vue'
import BaseModal from '../components/BaseModal.vue'
import EditDeleteActions from '../components/EditDeleteActions.vue'
import SettingsSection from '../components/SettingsSection.vue'

const route = useRoute()
const refs = useReferencesStore()
const authStore = useAuthStore()
const { user } = storeToRefs(authStore)
const fetchAll = () => refs.fetchAll()

const baseCurrencyCode = computed(() => user.value?.base_currency_code ?? 'USD')

async function updateBaseCurrency(code: string) {
  await authStore.updateBaseCurrency(code)
  await loadAllRates()
}

const locationCrud = useCrudSection(storageLocationsApi, fetchAll)
const accountCrud = useCrudSection(storageAccountsApi, fetchAll)
const sourceCrud = useCrudSection(incomeSourcesApi, fetchAll)

// ── Currency catalog & add form ─────────────────────────────────────────────

const catalogLoading = ref(false)
const filteredCatalog = ref<CatalogCurrency[]>([])

// Mode: 'catalog' | 'custom'
const addMode = ref<'catalog' | 'custom'>('catalog')

// Catalog mode state
const catalogSearch = ref('')
const selectedCatalog = ref<CatalogCurrency | null>(null)

const addedCatalogIds = computed(() =>
  new Set(refs.currencies.map((c) => c.catalog_id).filter((id) => id !== null))
)

const showCatalogDropdown = ref(false)

let catalogDebounce: ReturnType<typeof setTimeout> | null = null

async function fetchCatalog(search: string) {
  catalogLoading.value = true
  try {
    const { data } = await currenciesApi.catalog(
      search.trim()
        ? { search: search.trim(), limit: 20 }
        : { limit: 50 }
    )
    filteredCatalog.value = data.filter((c) => !addedCatalogIds.value.has(c.id))
  } finally {
    catalogLoading.value = false
  }
}

watch(catalogSearch, (val) => {
  if (catalogDebounce) clearTimeout(catalogDebounce)
  catalogDebounce = setTimeout(() => fetchCatalog(val), 200)
})

function onCatalogInputFocus() {
  showCatalogDropdown.value = true
  if (!filteredCatalog.value.length) fetchCatalog(catalogSearch.value)
}

function onCatalogInputBlur() {
  // Delay to allow click on dropdown item
  setTimeout(() => { showCatalogDropdown.value = false }, 150)
}

function selectCatalogItem(item: CatalogCurrency) {
  selectedCatalog.value = item
  catalogSearch.value = `${item.code} — ${item.name}`
  showCatalogDropdown.value = false
}

// Custom mode state
const newCustom = ref({ code: '', symbol: '', name: '' })

function switchToCustom() {
  addMode.value = 'custom'
  selectedCatalog.value = null
  catalogSearch.value = ''
}

function switchToCatalog() {
  addMode.value = 'catalog'
  newCustom.value = { code: '', symbol: '', name: '' }
}

async function addCurrency() {
  if (addMode.value === 'catalog') {
    if (!selectedCatalog.value) return
    await currenciesApi.create({ catalog_id: selectedCatalog.value.id })
    selectedCatalog.value = null
    catalogSearch.value = ''
  } else {
    if (!newCustom.value.code || !newCustom.value.symbol) return
    await currenciesApi.create({
      code: newCustom.value.code,
      symbol: newCustom.value.symbol,
      name: newCustom.value.name || undefined,
    })
    newCustom.value = { code: '', symbol: '', name: '' }
  }
  await refs.fetchAll()
  // Refresh rate info for new currency
  await loadAllRates()
  // Refresh catalog to exclude newly added currency
  await fetchCatalog(catalogSearch.value)
}

const deleteCurrency = async (id: number) => {
  await currenciesApi.delete(id)
  await refs.fetchAll()
  rateInfoMap.value.delete(id)
}

// Edit currency
const editingCurrency = ref<Currency | null>(null)
const editCurrencyForm = ref({ code: '', symbol: '', name: '' })

function openEditCurrency(c: Currency) {
  editingCurrency.value = c
  editCurrencyForm.value = { code: c.code, symbol: c.symbol, name: c.name ?? '' }
}

async function saveEditCurrency() {
  if (!editingCurrency.value) return
  await currenciesApi.update(editingCurrency.value.id, {
    code: editCurrencyForm.value.code,
    symbol: editCurrencyForm.value.symbol,
    name: editCurrencyForm.value.name || undefined,
  })
  editingCurrency.value = null
  await refs.fetchAll()
}

// ── Rate info per currency ──────────────────────────────────────────────────

const rateInfoMap = ref<Map<number, RateInfo>>(new Map())

async function loadAllRates() {
  const { data } = await currenciesApi.ratesAll(baseCurrencyCode.value)
  rateInfoMap.value = new Map(
    Object.entries(data).map(([id, info]) => [Number(id), info])
  )
}

// Load rate info after currencies are available; auto-open rates modal if query param present
function tryAutoOpenRates() {
  const openRatesId = Number(route.query.openRates)
  if (openRatesId) {
    const currency = refs.currencies.find((c) => c.id === openRatesId)
    if (currency) openManualRatesModal(currency)
  }
}

onMounted(async () => {
  // Load initial catalog results
  await fetchCatalog('')

  // Load rate info (after currencies are available)
  if (refs.currencies.length) {
    await loadAllRates()
    tryAutoOpenRates()
  } else {
    const unwatch = refs.$subscribe(() => {
      if (refs.currencies.length) {
        unwatch()
        loadAllRates()
        tryAutoOpenRates()
      }
    })
  }
})

// ── Manual rates modal ──────────────────────────────────────────────────────

const manualRateModalCurrency = ref<Currency | null>(null)
const manualRates = ref<UserManualRate[]>([])
const manualRatesLoading = ref(false)
const manualRateForm = ref({
  to_code: 'USD',
  rate: '',
  valid_from: '',
  valid_to: '',
})

async function openManualRatesModal(c: Currency) {
  manualRateModalCurrency.value = c
  manualRateForm.value = {
    to_code: baseCurrencyCode.value,
    rate: '',
    valid_from: new Date().toISOString().slice(0, 10),
    valid_to: '',
  }
  showRateHistory.value = false
  rateHistory.value = []
  await loadManualRates(c.id)
}

async function loadManualRates(currencyId: number) {
  manualRatesLoading.value = true
  try {
    const { data } = await currenciesApi.getManualRates(currencyId)
    manualRates.value = data
  } finally {
    manualRatesLoading.value = false
  }
}

async function saveManualRate() {
  if (!manualRateModalCurrency.value) return
  const rateVal = parseFloat(manualRateForm.value.rate)
  if (!manualRateForm.value.to_code || !rateVal || !manualRateForm.value.valid_from) return
  await currenciesApi.createManualRate(manualRateModalCurrency.value.id, {
    to_code: manualRateForm.value.to_code,
    rate: rateVal,
    valid_from: manualRateForm.value.valid_from,
    valid_to: manualRateForm.value.valid_to || null,
  })
  manualRateForm.value.rate = ''
  manualRateForm.value.valid_from = ''
  manualRateForm.value.valid_to = ''
  await loadManualRates(manualRateModalCurrency.value.id)
  // Refresh rate info badge
  const { data: ri } = await currenciesApi.getRate(manualRateModalCurrency.value.id)
  rateInfoMap.value.set(manualRateModalCurrency.value.id, ri)
}

async function deleteManualRate(rateId: number) {
  if (!manualRateModalCurrency.value) return
  await currenciesApi.deleteManualRate(manualRateModalCurrency.value.id, rateId)
  await loadManualRates(manualRateModalCurrency.value.id)
}

// ── Rate history (system rates) ─────────────────────────────────────────────

const rateHistory = ref<RateInfo[]>([])
const rateHistoryLoading = ref(false)
const showRateHistory = ref(false)

async function loadRateHistory(currencyId: number) {
  rateHistoryLoading.value = true
  try {
    const { data } = await currenciesApi.rateHistory(currencyId, 30)
    rateHistory.value = data
  } finally {
    rateHistoryLoading.value = false
  }
}

function toggleRateHistory() {
  if (!showRateHistory.value && manualRateModalCurrency.value && rateHistory.value.length === 0) {
    loadRateHistory(manualRateModalCurrency.value.id)
  }
  showRateHistory.value = !showRateHistory.value
}

function closeManualRatesModal() {
  manualRateModalCurrency.value = null
  manualRates.value = []
  rateHistory.value = []
  showRateHistory.value = false
}

// ── Storage Location ────────────────────────────────────────────────────────

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

// ── Storage Account ─────────────────────────────────────────────────────────

const newAccount = ref({ storage_location_id: 0, currency_id: 0 })
async function addAccount() {
  if (!newAccount.value.storage_location_id || !newAccount.value.currency_id) return
  await accountCrud.add(newAccount.value)
  newAccount.value = { storage_location_id: 0, currency_id: 0 }
}
const deleteAccount = (id: number) => accountCrud.remove(id)

// ── Income Source ───────────────────────────────────────────────────────────

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
  <div class="page-sections page-narrow">
  <div class="settings-grid">

    <!-- Currencies -->
    <BaseCard data-onboarding="currencies-section" title="Currencies">
      <!-- Base currency picker -->
      <div class="base-currency-row">
        <span class="base-currency-label">Base currency</span>
        <select
          class="form-input-sm base-currency-select"
          :value="baseCurrencyCode"
          @change="updateBaseCurrency(($event.target as HTMLSelectElement).value)"
        >
          <option v-for="c in refs.currencies" :key="c.code" :value="c.code">
            {{ c.code }}<template v-if="c.name"> — {{ c.name }}</template>
          </option>
        </select>
      </div>

      <!-- Add form -->
      <div class="settings-item-row">
        <template v-if="addMode === 'catalog'">
          <div class="catalog-autocomplete">
            <input
              v-model="catalogSearch"
              class="form-input-sm"
              placeholder="Search currency (e.g. USD, Euro)"
              :disabled="catalogLoading"
              @focus="onCatalogInputFocus"
              @blur="onCatalogInputBlur"
              @input="selectedCatalog = null"
            />
            <div v-if="showCatalogDropdown && filteredCatalog.length" class="catalog-dropdown">
              <button
                v-for="item in filteredCatalog"
                :key="item.id"
                type="button"
                class="catalog-dropdown-item"
                @mousedown.prevent="selectCatalogItem(item)"
              >
                <span class="catalog-item-code">{{ item.code }}</span>
                <span class="catalog-item-name">{{ item.name }}</span>
                <span class="currency-type-badge" :class="`currency-type-badge--${item.currency_type}`">
                  {{ item.currency_type }}
                </span>
                <span v-if="item.has_rates" class="rate-available-dot" title="Exchange rates available" />
              </button>
            </div>
          </div>
          <BaseButton variant="primary" size="sm" :disabled="!selectedCatalog" @click="addCurrency">Add</BaseButton>
        </template>
        <template v-else>
          <input v-model="newCustom.code" placeholder="Code (USD)" class="form-input-sm" style="flex: 1; min-width: 0" />
          <input v-model="newCustom.symbol" placeholder="Symbol ($)" class="form-input-sm" style="width: 64px" />
          <input v-model="newCustom.name" placeholder="Name (optional)" class="form-input-sm" style="flex: 1; min-width: 0" />
          <BaseButton variant="primary" size="sm" :disabled="!newCustom.code || !newCustom.symbol" @click="addCurrency">Add</BaseButton>
        </template>
      </div>

      <div class="add-mode-toggle">
        <button v-if="addMode === 'catalog'" type="button" class="mode-link" @click="switchToCustom">
          Add custom currency instead
        </button>
        <button v-else type="button" class="mode-link" @click="switchToCatalog">
          Search catalog instead
        </button>
      </div>

      <!-- Currency list -->
      <TransitionGroup tag="div" name="settings-item">
        <div v-for="c in refs.currencies" :key="c.id" class="settings-item">
          <template v-if="editingCurrency?.id === c.id">
            <div style="display: flex; gap: 8px; flex-wrap: wrap">
              <input v-model="editCurrencyForm.code" class="form-input-sm" style="width: 80px" />
              <input v-model="editCurrencyForm.symbol" class="form-input-sm" style="width: 60px" />
              <input v-if="c.is_custom" v-model="editCurrencyForm.name" placeholder="Name (optional)" class="form-input-sm" style="flex: 1; min-width: 80px" />
            </div>
            <div style="display: flex; gap: 8px">
              <BaseButton variant="primary" size="sm" @click="saveEditCurrency">Save</BaseButton>
              <BaseButton variant="secondary" size="sm" @click="editingCurrency = null">Cancel</BaseButton>
            </div>
          </template>
          <template v-else>
            <div class="currency-item-info">
              <div class="currency-item-main">
                <span class="currency-item-code">{{ c.code }}</span>
                <span class="currency-item-symbol">({{ c.symbol }})</span>
                <span v-if="c.name" class="currency-item-name">{{ c.name }}</span>
                <span class="currency-type-badge" :class="c.is_custom ? 'currency-type-badge--custom' : 'currency-type-badge--catalog'">
                  {{ c.is_custom ? 'Custom' : (c.catalog_id ? 'Catalog' : 'Catalog') }}
                </span>
              </div>
              <span
                v-if="rateInfoMap.has(c.id) && rateInfoMap.get(c.id)!.rate && c.code !== baseCurrencyCode"
                class="currency-rate-inline"
                :class="{ 'currency-rate-inline--stale': rateInfoMap.get(c.id)!.status === 'stale' }"
              >
                1 {{ c.code }} = {{ Number(rateInfoMap.get(c.id)!.rate).toFixed(4) }} {{ baseCurrencyCode }}
              </span>
              <span
                v-else-if="rateInfoMap.has(c.id) && rateInfoMap.get(c.id)!.status === 'missing' && c.code !== baseCurrencyCode"
                class="currency-rate-inline currency-rate-inline--missing"
              >
                no rate
              </span>
            </div>
            <div class="currency-item-actions">
              <button
                type="button"
                class="rates-btn"
                title="Manage manual exchange rates"
                @click="openManualRatesModal(c)"
              >Rates</button>
              <EditDeleteActions @edit="openEditCurrency(c)" @confirm="deleteCurrency(c.id)" />
            </div>
          </template>
        </div>
      </TransitionGroup>
    </BaseCard>

    <!-- Storage Locations -->
    <SettingsSection data-onboarding="storage-locations-section" title="Storage Locations" :items="refs.storageLocations" @add="addLocation">
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
          <EditDeleteActions @edit="openEditLocation(l)" @confirm="deleteLocation(l.id)" />
        </template>
      </template>
    </SettingsSection>

    <!-- Storage Accounts -->
    <SettingsSection data-onboarding="storage-accounts-section" title="Storage Accounts" :items="refs.storageAccounts" @add="addAccount">
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
    <SettingsSection data-onboarding="income-sources-section" title="Income Sources" :items="refs.incomeSources" @add="addSource">
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
          <EditDeleteActions @edit="openEditSource(s)" @confirm="deleteSource(s.id)" />
        </template>
      </template>
    </SettingsSection>

  </div>
  </div>

  <!-- Manual Rates Modal -->
  <BaseModal
    :show="!!manualRateModalCurrency"
    :title="`Manual Exchange Rates — ${manualRateModalCurrency?.code ?? ''}`"
    @close="closeManualRatesModal"
    @submit="saveManualRate"
  >
    <div class="manual-rate-form">
      <div class="form-row">
        <div class="form-field">
          <label class="form-label">From</label>
          <input
            :value="manualRateModalCurrency?.code"
            class="form-input-sm"
            readonly
          />
        </div>
        <div class="form-field">
          <label class="form-label">To</label>
          <select v-model="manualRateForm.to_code" class="form-input-sm">
            <option v-for="c in refs.currencies.filter(c => c.id !== manualRateModalCurrency?.id)" :key="c.code" :value="c.code">
              {{ c.code }}<template v-if="c.name"> — {{ c.name }}</template>
            </option>
          </select>
        </div>
        <div class="form-field">
          <label class="form-label">Rate</label>
          <input
            v-model="manualRateForm.rate"
            type="number"
            step="any"
            min="0"
            class="form-input-sm"
            placeholder="1.00"
          />
        </div>
      </div>
      <div class="form-row">
        <div class="form-field">
          <label class="form-label">Valid From</label>
          <input v-model="manualRateForm.valid_from" type="date" class="form-input-sm" />
        </div>
        <div class="form-field">
          <label class="form-label">Valid To (optional)</label>
          <input v-model="manualRateForm.valid_to" type="date" class="form-input-sm" />
        </div>
      </div>
    </div>

    <!-- Existing manual rates list -->
    <div v-if="manualRatesLoading" class="manual-rates-loading">Loading rates...</div>
    <div v-else-if="manualRates.length" class="manual-rates-list">
      <div class="manual-rates-list-title">Existing rates</div>
      <div
        v-for="mr in manualRates"
        :key="mr.id"
        class="manual-rate-row"
      >
        <span class="manual-rate-pair">{{ mr.from_code }} → {{ mr.to_code }}</span>
        <span class="manual-rate-value">{{ mr.rate }}</span>
        <span class="manual-rate-dates">{{ mr.valid_from }}<template v-if="mr.valid_to"> – {{ mr.valid_to }}</template></span>
        <BaseConfirmButton @confirm="deleteManualRate(mr.id)" />
      </div>
    </div>
    <div v-else class="manual-rates-empty">No manual rates yet.</div>

    <!-- Rate History (system rates) -->
    <div class="rate-history-section">
      <button type="button" class="rate-history-toggle" @click="toggleRateHistory">
        {{ showRateHistory ? 'Hide' : 'Show' }} system rate history (last 30 days)
      </button>
      <div v-if="showRateHistory" class="rate-history-list">
        <div v-if="rateHistoryLoading" class="manual-rates-loading">Loading history...</div>
        <template v-else-if="rateHistory.length">
          <div class="rate-history-row" v-for="(entry, i) in rateHistory" :key="i">
            <span class="rate-history-date">{{ entry.valid_date }}</span>
            <span class="rate-history-value">{{ entry.rate ? fmtAmount(Number(entry.rate)) : '—' }}</span>
          </div>
        </template>
        <div v-else class="manual-rates-empty">No system rate history available.</div>
      </div>
    </div>
  </BaseModal>
</template>

<style scoped>
/* ── Catalog autocomplete ── */

.catalog-autocomplete {
  position: relative;
  flex: 1;
  min-width: 0;
}

.catalog-autocomplete .form-input-sm {
  width: 100%;
}

.catalog-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: 10px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.10);
  z-index: 100;
  max-height: 240px;
  overflow-y: auto;
}

.catalog-dropdown-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.45rem 0.75rem;
  background: none;
  border: none;
  cursor: pointer;
  text-align: left;
  font-size: 0.82rem;
  color: var(--text-primary);
  transition: background 0.1s;
}

.catalog-dropdown-item:hover {
  background: rgba(var(--color-accent-rgb), 0.07);
}

.catalog-item-code {
  font-weight: 600;
  min-width: 2.8rem;
  color: var(--text-primary);
}

.catalog-item-name {
  flex: 1;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.rate-available-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-income);
  flex-shrink: 0;
}

/* ── Currency type badges ── */

.currency-type-badge {
  display: inline-block;
  padding: 0.1rem 0.45rem;
  border-radius: 9999px;
  font-size: 0.65rem;
  font-weight: 600;
  letter-spacing: 0.03em;
  text-transform: lowercase;
  flex-shrink: 0;
}

.currency-type-badge--fiat {
  background: rgba(var(--color-accent-rgb), 0.12);
  color: var(--color-accent);
  border: 1px solid rgba(var(--color-accent-rgb), 0.30);
}

.currency-type-badge--crypto {
  background: rgba(76, 190, 203, 0.12);
  color: var(--color-cyan);
  border: 1px solid rgba(76, 190, 203, 0.30);
}

.currency-type-badge--custom {
  background: rgba(224, 184, 74, 0.12);
  color: #b45309;
  border: 1px solid rgba(224, 184, 74, 0.30);
}

.currency-type-badge--catalog {
  background: rgba(74, 170, 128, 0.10);
  color: var(--color-income);
  border: 1px solid rgba(74, 170, 128, 0.25);
}

/* ── Rate status icons ── */

.rate-status-icon {
  font-size: 0.9rem;
  flex-shrink: 0;
  cursor: default;
}

.rate-status-icon--stale {
  color: var(--color-warning);
}

.rate-status-icon--missing {
  color: var(--color-expense);
}

/* ── Base currency picker ── */

.base-currency-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding-bottom: 0.75rem;
  margin-bottom: 0.25rem;
  border-bottom: 1px solid var(--card-border);
}

.base-currency-label {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-secondary);
  white-space: nowrap;
}

.base-currency-select {
  min-width: 120px;
}

/* ── Inline rate display ── */

.currency-rate-inline {
  font-size: 0.72rem;
  font-variant-numeric: tabular-nums;
  color: var(--text-placeholder);
  white-space: nowrap;
  letter-spacing: 0.01em;
}

.currency-rate-inline--stale {
  color: var(--color-warning);
}

.currency-rate-inline--missing {
  color: var(--color-expense);
}

/* ── Currency item layout ── */

.currency-item-info {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 3px;
  flex: 1;
  min-width: 0;
}

.currency-item-main {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-wrap: wrap;
}

.currency-item-code {
  font-weight: 600;
  color: var(--text-primary);
}

.currency-item-symbol {
  color: var(--text-secondary);
  font-size: 0.85rem;
}

.currency-item-name {
  color: var(--text-label);
  font-size: 0.8rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.currency-item-actions {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-shrink: 0;
}

/* ── Rates button ── */

.rates-btn {
  padding: 0.2rem 0.6rem;
  font-size: 0.75rem;
  font-weight: 500;
  border-radius: 6px;
  border: 1px solid var(--card-border);
  background: rgba(var(--color-accent-rgb), 0.08);
  color: var(--color-accent);
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}

.rates-btn:hover {
  background: rgba(var(--color-accent-rgb), 0.15);
  border-color: rgba(var(--color-accent-rgb), 0.40);
}

/* ── Add mode toggle ── */

.add-mode-toggle {
  margin-top: 0.4rem;
  margin-bottom: 0.5rem;
}

.mode-link {
  background: none;
  border: none;
  padding: 0;
  font-size: 0.78rem;
  color: var(--color-accent);
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.mode-link:hover {
  color: var(--color-accent-light);
}

/* ── Manual rate modal form ── */

.manual-rate-form {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.form-row {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  flex: 1;
  min-width: 100px;
}

.form-label {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--text-secondary);
}

.manual-rates-list {
  margin-top: 0.5rem;
  border-top: 1px solid var(--card-border);
  padding-top: 0.75rem;
}

.manual-rates-list-title {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-label);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.5rem;
}

.manual-rate-row {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding: 0.35rem 0;
  font-size: 0.82rem;
  border-bottom: 1px solid var(--card-border);
}

.manual-rate-row:last-child {
  border-bottom: none;
}

.manual-rate-pair {
  font-weight: 600;
  color: var(--text-primary);
  min-width: 5rem;
}

.manual-rate-value {
  font-variant-numeric: tabular-nums;
  color: var(--text-primary);
  min-width: 4rem;
}

.manual-rate-dates {
  flex: 1;
  color: var(--text-label);
  font-size: 0.78rem;
}

.manual-rates-loading,
.manual-rates-empty {
  font-size: 0.82rem;
  color: var(--text-placeholder);
  margin-top: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--card-border);
}

/* ── Rate history ── */

.rate-history-section {
  margin-top: 1rem;
  border-top: 1px solid var(--card-border);
  padding-top: 0.75rem;
}

.rate-history-toggle {
  background: none;
  border: none;
  padding: 0;
  font-size: 0.78rem;
  color: var(--color-accent);
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.rate-history-toggle:hover {
  color: var(--color-accent-light);
}

.rate-history-list {
  margin-top: 0.5rem;
}

.rate-history-row {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding: 0.3rem 0;
  font-size: 0.8rem;
  border-bottom: 1px solid var(--card-border);
}

.rate-history-row:last-child {
  border-bottom: none;
}

.rate-history-date {
  color: var(--text-secondary);
  min-width: 5.5rem;
  font-variant-numeric: tabular-nums;
}

.rate-history-value {
  font-weight: 600;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
  min-width: 4rem;
}

</style>

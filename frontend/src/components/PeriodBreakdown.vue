<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { PhWarning } from '@phosphor-icons/vue'
import { analyticsApi, type ExplainParams, type PeriodExplain } from '../api/analytics'
import { useAsync } from '../composables/useAsync'
import { fmtMoney, fmtSignedMoney } from '../utils/format'

const props = defineProps<{ params: ExplainParams }>()

const { data, loading, error, execute } = useAsync<PeriodExplain>(async () => {
  const { data: payload } = await analyticsApi.summaryExplain(props.params)
  return payload
})

onMounted(execute)

const detail = computed(() => data.value)

// Without conversion the backend reports no currency, but the figures are still
// denominated in something: when every account and transaction shares one code,
// that code is the answer. Only a genuinely mixed, unconverted period has none.
const ccy = computed<string | null>(() => {
  const d = detail.value
  if (!d) return null
  if (d.currency) return d.currency
  const codes = new Set([
    ...Object.keys(d.balances),
    ...Object.keys(d.balance_change),
    ...Object.keys(d.income_by_currency),
  ])
  return codes.size === 1 ? ([...codes][0] ?? null) : null
})

function fmtDate(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number)
  if (!y || !m || !d) return iso
  return new Date(y, m - 1, d).toLocaleDateString('en-US', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

function daysBetween(from: string, to: string): number {
  const a = new Date(from).getTime()
  const b = new Date(to).getTime()
  return Math.round((b - a) / 86_400_000)
}

/**
 * How stale the closing measurement is. A snapshot taken well before the period
 * ended means the row describes a window that does not match its label, which is
 * the single most confusing thing a balance-derived profit can do.
 */
function staleness(closingDate: string): number {
  const end = detail.value?.period_end
  return end ? daysBetween(closingDate, end) : 0
}

const STALE_DAYS = 5

const hasStaleClosing = computed(() =>
  (detail.value?.accounts ?? []).some(
    (a) => a.closing && staleness(a.closing.date) > STALE_DAYS,
  ),
)

// Reported per currency rather than as one sum: the transactions behind a period
// can be denominated in several currencies, and adding those together would
// produce a total in no currency at all.
const incomeTotals = computed(() =>
  Object.entries(detail.value?.income_by_currency ?? {})
    .map(([code, amount]) => ({ code, amount }))
    .sort((a, b) => a.code.localeCompare(b.code)),
)
</script>

<template>
  <div class="breakdown">
    <p v-if="loading" class="muted bd-note">Loading breakdown…</p>
    <p v-else-if="error" class="bd-error">{{ error }}</p>

    <template v-else-if="detail">
      <p class="muted bd-note">
        Covers {{ fmtDate(detail.period_start) }} — {{ fmtDate(detail.period_end) }}.
      </p>

      <div v-if="hasStaleClosing" class="bd-warn">
        <PhWarning :size="16" weight="fill" class="bd-warn-icon" />
        <span>
          The closing balance below comes from a snapshot taken before this period ended, so
          this row's profit describes the window between the two snapshot dates — not the
          calendar period in its label.
        </span>
      </div>

      <section class="bd-section">
        <div class="label">Balance movement</div>
        <div class="bd-scroll">
          <table class="bd-table">
            <thead>
              <tr>
                <th>Account</th>
                <th class="col-num">Opening</th>
                <th class="col-num">Closing</th>
                <th class="col-num">Change</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="acct in detail.accounts" :key="acct.account_id">
                <td>
                  {{ acct.label }}
                  <span
                    v-if="!acct.remeasured_in_period"
                    class="bd-chip"
                    title="No snapshot inside this period — the previous balance was carried forward."
                  >carried forward</span>
                </td>
                <td class="col-num">
                  <template v-if="acct.opening">
                    <span class="num">{{ fmtMoney(acct.opening.amount, acct.currency) }}</span>
                    <span class="muted bd-asof">as of {{ fmtDate(acct.opening.date) }}</span>
                  </template>
                  <span v-else class="muted">not tracked yet</span>
                </td>
                <td class="col-num">
                  <template v-if="acct.closing">
                    <span class="num">{{ fmtMoney(acct.closing.amount, acct.currency) }}</span>
                    <span
                      class="muted bd-asof"
                      :class="{ 'bd-asof--stale': staleness(acct.closing.date) > STALE_DAYS }"
                    >
                      as of {{ fmtDate(acct.closing.date) }}
                      <template v-if="staleness(acct.closing.date) > STALE_DAYS">
                        · {{ staleness(acct.closing.date) }}d before period end
                      </template>
                    </span>
                  </template>
                  <span v-else class="muted">—</span>
                </td>
                <td class="col-num">
                  <span v-if="acct.is_opening_capital" class="muted bd-opening">
                    opening capital, not profit
                  </span>
                  <span v-else class="num" :class="acct.delta >= 0 ? 'up' : 'down'">
                    {{ fmtSignedMoney(acct.delta, acct.currency) }}
                  </span>
                </td>
              </tr>
              <tr v-if="!detail.accounts.length">
                <td colspan="4" class="muted">No tracked accounts in this period.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="bd-section">
        <div class="label">
          Income · {{ detail.income_transactions.length }} transaction<span
            v-if="detail.income_transactions.length !== 1"
          >s</span>
        </div>
        <div v-if="detail.income_transactions.length" class="bd-scroll">
          <table class="bd-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Source</th>
                <th>Account</th>
                <th class="col-num">Amount</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="tx in detail.income_transactions" :key="tx.id">
                <td>{{ fmtDate(tx.date) }}</td>
                <td>{{ tx.source }}</td>
                <td class="muted">{{ tx.account }}</td>
                <td class="col-num num up">
                  {{ fmtMoney(tx.amount, tx.currency) }}
                </td>
              </tr>
              <tr class="bd-total-row">
                <td colspan="3">Total received</td>
                <td class="col-num num">
                  <span v-for="total in incomeTotals" :key="total.code" class="bd-total-line">
                    {{ fmtMoney(total.amount, total.code) }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-else class="muted bd-note">No income recorded in this period.</p>
      </section>

      <section class="bd-section">
        <div class="label">How the row is computed</div>
        <dl class="bd-math">
          <div class="bd-math-row">
            <dt>Income received</dt>
            <dd class="num">{{ fmtMoney(detail.income, ccy) }}</dd>
          </div>
          <div class="bd-math-row">
            <dt>Profit (change in tracked balances)</dt>
            <dd class="num" :class="detail.profit >= 0 ? 'up' : 'down'">
              {{ fmtMoney(detail.profit, ccy) }}
            </dd>
          </div>
          <div class="bd-math-row bd-math-row--result">
            <dt>Expense = income − profit</dt>
            <dd class="num">
              <template v-if="detail.is_measured">{{ fmtMoney(detail.derived_expense, ccy) }}</template>
              <span v-else class="muted">not derived</span>
            </dd>
          </div>
        </dl>

        <p v-if="detail.is_bootstrap" class="muted bd-note">
          First period with any tracked balance. The opening amount is capital you already
          had, so no profit or expense is derived from it.
        </p>
        <p v-else-if="!detail.is_measured" class="muted bd-note">
          No already-tracked account was re-counted inside this period, so the balance was
          only carried forward. Profit is unknown rather than zero, and no expense is derived.
        </p>
        <p v-if="detail.conversion_missing.length" class="bd-note down">
          No exchange rate for {{ detail.conversion_missing.join(', ') }} — those amounts are
          missing from the totals above.
        </p>
      </section>

      <section v-if="Object.keys(detail.rates).length > 1" class="bd-section">
        <div class="label">Rates used at {{ fmtDate(detail.period_end) }}</div>
        <div class="bd-rates">
          <span v-for="(rate, code) in detail.rates" :key="code" class="bd-rate">
            <span class="num">1 {{ code }}</span>
            =
            <span class="num">{{ rate.rate ? fmtMoney(rate.rate, ccy) : `? ${ccy ?? ''}` }}</span>
            <span v-if="rate.status !== 'ok'" class="bd-chip">{{ rate.status }}</span>
          </span>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.breakdown {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 16px 4px 8px;
}

.bd-note {
  font-size: 12px;
  line-height: 1.6;
  margin: 0;
}

.bd-error {
  font-size: 13px;
  color: var(--expense-ink, #d46878);
  margin: 0;
}

.bd-warn {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--r-inner);
  background: var(--warning-soft);
  font-size: 12px;
  line-height: 1.6;
}

.bd-warn-icon {
  flex-shrink: 0;
  color: var(--warning-ink);
  margin-top: 1px;
}

.bd-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.bd-scroll {
  overflow-x: auto;
}

.bd-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12.5px;
}

.bd-table th {
  text-align: left;
  font-weight: 500;
  color: var(--ink-3);
  padding: 6px 10px 6px 0;
  border-bottom: 1px solid var(--hairline);
  white-space: nowrap;
}

.bd-table td {
  padding: 7px 10px 7px 0;
  border-bottom: 1px solid var(--hairline);
  vertical-align: top;
}

.bd-table .col-num {
  text-align: right;
  padding-right: 0;
}

.bd-asof {
  display: block;
  font-size: 11px;
  margin-top: 2px;
  white-space: nowrap;
}

.bd-asof--stale {
  color: var(--warning-ink);
}

.bd-opening {
  font-size: 11px;
}

.bd-chip {
  display: inline-block;
  margin-left: 6px;
  padding: 1px 7px;
  border-radius: var(--r-pill);
  background: var(--surface-2);
  border: 1px solid var(--hairline);
  font-size: 10px;
  color: var(--ink-3);
  white-space: nowrap;
}

.bd-total-row td {
  border-bottom: none;
  font-weight: 600;
  padding-top: 9px;
}

.bd-total-line {
  display: block;
}

.bd-math {
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.bd-math-row {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 6px 0;
  font-size: 12.5px;
}

.bd-math-row dt,
.bd-math-row dd {
  margin: 0;
}

.bd-math-row--result {
  border-top: 1px solid var(--hairline);
  margin-top: 4px;
  padding-top: 9px;
  font-weight: 600;
}

.bd-rates {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  font-size: 12px;
}

.bd-rate {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
</style>

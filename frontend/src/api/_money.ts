// Coerce monetary fields returned by the backend (Pydantic Decimal → JSON string)
// from string to number, recursively. Run inside the global Axios response interceptor
// so views can trust the TS interfaces that say `amount: number`.
//
// Two categories of fields:
//  - direct money keys: the value at the key is a string number → Number(...)
//  - record-of-money keys: the value is { [k]: stringNumber } → coerce values

const MONEY_KEYS = new Set([
  'amount',
  'budgeted_amount',
  'budgeted',
  'actual',
  'remaining',
  'total',
  'latest_snapshot_amount',
  'income',
  'profit',
  'derived_expense',
  'avg_income',
  'avg_profit',
  'converted_balance',
  'delta',
  'pct',
  'total_income',
  'total_profit',
])

const RECORD_OF_MONEY_KEYS = new Set([
  'balances',
  'balance_change',
  'totals',
  'sources',
])

function toNum(v: unknown): unknown {
  if (typeof v === 'string' && v !== '') {
    const n = Number(v)
    return Number.isFinite(n) ? n : v
  }
  return v
}

export function coerceMoney<T>(value: T): T {
  if (Array.isArray(value)) {
    for (let i = 0; i < value.length; i++) value[i] = coerceMoney(value[i])
    return value
  }
  if (value !== null && typeof value === 'object') {
    const obj = value as Record<string, unknown>
    for (const k of Object.keys(obj)) {
      const v = obj[k]
      if (MONEY_KEYS.has(k)) {
        obj[k] = toNum(v)
      } else if (
        RECORD_OF_MONEY_KEYS.has(k) &&
        v !== null &&
        typeof v === 'object' &&
        !Array.isArray(v)
      ) {
        const inner = v as Record<string, unknown>
        for (const ik of Object.keys(inner)) inner[ik] = toNum(inner[ik])
      } else if (v !== null && typeof v === 'object') {
        coerceMoney(v)
      }
    }
  }
  return value
}

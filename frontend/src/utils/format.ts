export type PeriodGrouping = 'month' | 'quarter' | 'year'

const numberFmt = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
// Crypto balances live below one unit, where two decimals renders every holding as
// "0.00". Amounts at or above 1 keep the fixed two-decimal money format.
const preciseFmt = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 8 })
const monthFmt = new Intl.DateTimeFormat('en-US', { year: 'numeric', month: 'short' })

export function localDateStr(d: Date = new Date()): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

export function fmtAmount(n: number): string {
  const abs = Math.abs(n)
  if (abs > 0 && abs < 1) return preciseFmt.format(n)
  return numberFmt.format(n)
}

export function fmtPeriod(iso: string, groupBy: PeriodGrouping = 'month'): string {
  const [yearPart, monthPart] = iso.split('-')
  const year = Number(yearPart)
  if (!yearPart || !Number.isFinite(year)) return iso
  if (groupBy === 'year') return String(year)
  const month = Number(monthPart) || 1
  if (groupBy === 'quarter') return `Q${Math.floor((month - 1) / 3) + 1} ${year}`
  return monthFmt.format(new Date(year, month - 1, 1))
}

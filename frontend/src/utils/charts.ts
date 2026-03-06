import type { SummaryEntry } from '../types/index'

export const DONUT_COLORS = ['#fbbf24', '#34d399', '#06b6d4', '#a78bfa', '#fb7185', '#f97316']

export function buildLineChartOptions(
  currencyCode: string | null,
  onHover: (period: string | null) => void,
  data: SummaryEntry[],
) {
  return {
    responsive: true,
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    onHover: (_event: unknown, elements: Array<{ index: number }>) => {
      if (elements.length > 0) {
        onHover(data[elements[0]!.index]?.period ?? null)
      } else {
        onHover(null)
      }
    },
    plugins: {
      legend: {
        position: 'top' as const,
        labels: {
          color: 'rgba(0,0,0,0.55)',
          font: { family: 'DM Sans', size: 12 },
        },
      },
      tooltip: {
        mode: 'index' as const,
        intersect: false,
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        grid: { color: 'rgba(0,0,0,0.06)' },
        ticks: { color: 'rgba(0,0,0,0.45)' },
        title: currencyCode
          ? { display: true, text: currencyCode, color: 'rgba(0,0,0,0.45)' }
          : { display: false },
      },
      x: {
        grid: { color: 'rgba(0,0,0,0.06)' },
        ticks: { color: 'rgba(0,0,0,0.45)' },
      },
    },
  }
}

export const donutOptions = {
  responsive: true,
  plugins: {
    legend: {
      position: 'right' as const,
      labels: {
        color: 'rgba(0,0,0,0.55)',
        font: { family: 'DM Sans', size: 12 },
      },
    },
  },
}

export const DONUT_COLORS = ['#5585c5', '#4aaa80', '#e0b84a', '#d46878', '#4cbecb', '#78a8e0']

export interface TooltipBreakdownRow {
  label: string
  value: number
  prefix?: string
}

export function buildLineChartOption(
  periods: string[],
  values: number[],
  label: string,
  color: string,
  areaColor: string,
  currencyCode: string | null,
  onHover: (dataIndex: number | null) => void,
  isDark = false,
  breakdownByIndex?: (TooltipBreakdownRow[] | null)[],
) {
  const textMuted = isDark ? 'rgba(255,255,255,0.45)' : 'rgba(0,0,0,0.45)'
  const lineColor = isDark ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.12)'
  const splitColor = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)'
  const crossColor = isDark ? 'rgba(255,255,255,0.20)' : 'rgba(0,0,0,0.15)'
  const tooltipBg = isDark ? 'rgba(30,30,34,0.96)' : '#ffffff'
  const tooltipBorder = isDark ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.08)'
  const tooltipText = isDark ? 'rgba(255,255,255,0.92)' : 'rgba(0,0,0,0.85)'
  const fmt = (v: number) =>
    Number(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  return {
    grid: { left: 16, right: 24, bottom: 8, top: 36, containLabel: true },
    tooltip: {
      trigger: 'axis',
      confine: true,
      backgroundColor: tooltipBg,
      borderColor: tooltipBorder,
      textStyle: { color: tooltipText },
      axisPointer: { type: 'cross', crossStyle: { color: crossColor } },
      formatter: (params: Array<{ dataIndex: number; axisValue: string; marker: string; seriesName: string; value: number }>) => {
        const idx = params[0]?.dataIndex ?? null
        onHover(idx)
        const p = params[0]
        if (!p) return ''
        const val = fmt(Number(p.value))
        let html = `<span style="font-size:11px;color:${textMuted}">${p.axisValue}</span><br/>${p.marker}${p.seriesName}: <b>${val}</b>`
        const rows = idx !== null && breakdownByIndex ? breakdownByIndex[idx] : null
        if (rows && rows.length) {
          html += `<div style="margin-top:6px;padding-top:6px;border-top:1px solid ${lineColor};font-size:11px;">`
          for (const row of rows) {
            const prefix = row.prefix ?? ''
            html += `<div style="display:flex;justify-content:space-between;gap:12px;"><span style="color:${textMuted}">${row.label}</span><span style="font-variant-numeric:tabular-nums;">${prefix}${fmt(row.value)}</span></div>`
          }
          html += `</div>`
        }
        return html
      },
    },
    xAxis: {
      type: 'category',
      data: periods,
      boundaryGap: false,
      axisLabel: { color: textMuted, fontSize: 11 },
      axisLine: { lineStyle: { color: lineColor } },
      axisTick: { lineStyle: { color: lineColor } },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      name: currencyCode ?? '',
      nameTextStyle: { color: textMuted, fontSize: 11 },
      axisLabel: { color: textMuted, fontSize: 11 },
      splitLine: { lineStyle: { color: splitColor } },
    },
    series: [
      {
        name: label,
        type: 'line',
        smooth: 0.4,
        data: values,
        areaStyle: { color: areaColor, opacity: 1 },
        lineStyle: { color, width: 2 },
        itemStyle: { color },
        symbol: 'circle',
        symbolSize: 5,
        emphasis: { focus: 'series' },
      },
    ],
  }
}

export function buildDonutChartOption(labels: string[], values: number[], colors: string[], isDark = false) {
  const tooltipBg = isDark ? 'rgba(30,30,34,0.96)' : '#ffffff'
  const tooltipBorder = isDark ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.08)'
  const tooltipText = isDark ? 'rgba(255,255,255,0.92)' : 'rgba(0,0,0,0.85)'
  return {
    tooltip: {
      trigger: 'item',
      confine: true,
      backgroundColor: tooltipBg,
      borderColor: tooltipBorder,
      textStyle: { color: tooltipText },
      formatter: '{b}: <b>{c}</b> ({d}%)',
    },
    legend: { show: false },
    series: [
      {
        type: 'pie',
        radius: ['44%', '70%'],
        center: ['50%', '50%'],
        data: labels.map((name, i) => ({
          name,
          value: values[i],
          itemStyle: { color: colors[i] },
        })),
        label: { show: false },
        emphasis: {
          label: { show: true, fontSize: 13, fontWeight: 'bold' },
          itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.15)' },
        },
      },
    ],
  }
}

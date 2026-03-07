export const DONUT_COLORS = ['#5585c5', '#4aaa80', '#e0b84a', '#d46878', '#4cbecb', '#78a8e0']

export function buildLineChartOption(
  periods: string[],
  values: number[],
  label: string,
  color: string,
  areaColor: string,
  currencyCode: string | null,
  onHover: (dataIndex: number | null) => void,
  isDark = false,
) {
  const textMuted = isDark ? 'rgba(255,255,255,0.45)' : 'rgba(0,0,0,0.45)'
  const lineColor = isDark ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.12)'
  const splitColor = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)'
  const crossColor = isDark ? 'rgba(255,255,255,0.20)' : 'rgba(0,0,0,0.15)'
  return {
    grid: { left: 16, right: 24, bottom: 8, top: 36, containLabel: true },
    tooltip: {
      trigger: 'axis',
      confine: true,
      axisPointer: { type: 'cross', crossStyle: { color: crossColor } },
      formatter: (params: Array<{ dataIndex: number; axisValue: string; marker: string; seriesName: string; value: number }>) => {
        const idx = params[0]?.dataIndex ?? null
        onHover(idx)
        const p = params[0]
        if (!p) return ''
        const val = Number(p.value).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
        return `<span style="font-size:11px;color:${textMuted}">${p.axisValue}</span><br/>${p.marker}${p.seriesName}: <b>${val}</b>`
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

export function buildDonutChartOption(labels: string[], values: number[], colors: string[]) {
  return {
    tooltip: {
      trigger: 'item',
      confine: true,
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

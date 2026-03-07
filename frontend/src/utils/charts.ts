export const DONUT_COLORS = ['#5585c5', '#4aaa80', '#e0b84a', '#d46878', '#4cbecb', '#78a8e0']

export function buildLineChartOption(
  periods: string[],
  values: number[],
  label: string,
  color: string,
  areaColor: string,
  currencyCode: string | null,
  onHover: (dataIndex: number | null) => void,
) {
  return {
    grid: { left: 16, right: 24, bottom: 8, top: 36, containLabel: true },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross', crossStyle: { color: 'rgba(0,0,0,0.15)' } },
      formatter: (params: Array<{ dataIndex: number; axisValue: string; marker: string; seriesName: string; value: number }>) => {
        const idx = params[0]?.dataIndex ?? null
        onHover(idx)
        const p = params[0]
        const val = Number(p.value).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
        return `<span style="font-size:11px;color:rgba(0,0,0,0.45)">${p.axisValue}</span><br/>${p.marker}${p.seriesName}: <b>${val}</b>`
      },
    },
    xAxis: {
      type: 'category',
      data: periods,
      boundaryGap: false,
      axisLabel: { color: 'rgba(0,0,0,0.45)', fontSize: 11 },
      axisLine: { lineStyle: { color: 'rgba(0,0,0,0.12)' } },
      axisTick: { lineStyle: { color: 'rgba(0,0,0,0.12)' } },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      name: currencyCode ?? '',
      nameTextStyle: { color: 'rgba(0,0,0,0.45)', fontSize: 11 },
      axisLabel: { color: 'rgba(0,0,0,0.45)', fontSize: 11 },
      splitLine: { lineStyle: { color: 'rgba(0,0,0,0.06)' } },
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

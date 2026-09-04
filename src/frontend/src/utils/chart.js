import * as echarts from 'echarts'

export function initChart(el, opts) {
  return echarts.init(el, 'glass', opts)
}

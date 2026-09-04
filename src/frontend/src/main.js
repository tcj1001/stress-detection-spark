import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import './assets/glass.css'
import * as ElIcons from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import $ from 'jquery'
import App from './App.vue'
import router from './router'

window.$ = window.jQuery = $

echarts.registerTheme('glass', {
  backgroundColor: 'transparent',
  textStyle: { color: 'rgba(255,255,255,0.85)' },
  title: { textStyle: { color: '#fff' }, subtextStyle: { color: 'rgba(255,255,255,0.6)' } },
  legend: { textStyle: { color: 'rgba(255,255,255,0.8)' } },
  categoryAxis: {
    axisLine: { lineStyle: { color: 'rgba(255,255,255,0.2)' } },
    axisTick: { lineStyle: { color: 'rgba(255,255,255,0.15)' } },
    axisLabel: { color: 'rgba(255,255,255,0.7)' },
    splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
    nameTextStyle: { color: 'rgba(255,255,255,0.7)' },
  },
  valueAxis: {
    axisLine: { lineStyle: { color: 'rgba(255,255,255,0.2)' } },
    axisTick: { lineStyle: { color: 'rgba(255,255,255,0.15)' } },
    axisLabel: { color: 'rgba(255,255,255,0.7)' },
    splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
    nameTextStyle: { color: 'rgba(255,255,255,0.7)' },
  },
  radar: {
    axisLine: { lineStyle: { color: 'rgba(255,255,255,0.15)' } },
    splitLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
    splitArea: { areaStyle: { color: ['rgba(255,255,255,0.02)', 'rgba(255,255,255,0.05)'] } },
    axisName: { color: 'rgba(255,255,255,0.7)' },
  },
  tooltip: {
    backgroundColor: 'rgba(15,23,42,0.85)',
    borderColor: 'rgba(255,255,255,0.15)',
    textStyle: { color: '#e8edf3' },
  },
  visualMap: { textStyle: { color: 'rgba(255,255,255,0.7)' } },
})

const app = createApp(App)

app.use(ElementPlus)
app.use(router)

Object.keys(ElIcons).forEach(key => {
  app.component(key, ElIcons[key])
})

app.mount('#app')

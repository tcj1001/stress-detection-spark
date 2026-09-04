<template>
  <div>
    <h2 style="margin:0 0 20px;">趋势分析</h2>
    <el-card shadow="never" style="border-radius:10px;margin-bottom:16px;">
      <el-form inline>
        <el-form-item label="选择用户">
          <el-select v-model="userId" placeholder="请选择用户" style="width:220px;" @change="load">
            <el-option v-for="id in users" :key="id" :label="`用户 ${id}`" :value="id" />
          </el-select>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" style="border-radius:10px;margin-bottom:16px;">
      <template #header><b>压力变化趋势</b></template>
      <div ref="lineRef" style="height:320px;"></div>
    </el-card>

    <el-card shadow="never" style="border-radius:10px;margin-bottom:16px;">
      <template #header><b>日环比变化率</b></template>
      <div ref="rateRef" style="height:260px;"></div>
    </el-card>

    <!-- 未来趋势预测 -->
    <h2 style="margin:30px 0 20px;">未来趋势预测</h2>

    <template v-if="forecast">
      <!-- 摘要卡片 -->
      <el-row :gutter="16" style="margin-bottom:16px;">
        <el-col :span="6">
          <el-card shadow="hover" style="border-radius:10px;">
            <div style="text-align:center;">
              <div style="font-size:13px;color:rgba(255,255,255,0.5);margin-bottom:6px;">当前压力分</div>
              <div style="font-size:28px;font-weight:bold;">{{ forecast.summary.last_score }}</div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" style="border-radius:10px;">
            <div style="text-align:center;">
              <div style="font-size:13px;color:rgba(255,255,255,0.5);margin-bottom:6px;">预测均值</div>
              <div style="font-size:28px;font-weight:bold;">{{ forecast.summary.avg_forecast }}</div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" style="border-radius:10px;">
            <div style="text-align:center;">
              <div style="font-size:13px;color:rgba(255,255,255,0.5);margin-bottom:6px;">趋势方向</div>
              <div :style="{ fontSize:'28px', fontWeight:'bold', color: dirColor }">
                {{ dirArrow }} {{ forecast.summary.direction }}
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" style="border-radius:10px;">
            <div style="text-align:center;">
              <div style="font-size:13px;color:rgba(255,255,255,0.5);margin-bottom:6px;">日均变化率</div>
              <div :style="{ fontSize:'28px', fontWeight:'bold', color: dirColor }">
                {{ forecast.summary.slope > 0 ? '+' : '' }}{{ forecast.summary.slope }}
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 预测图表 -->
      <el-card shadow="never" style="border-radius:10px;margin-bottom:16px;">
        <template #header><b>历史趋势 + 未来7天预测（含置信区间）</b></template>
        <div ref="forecastRef" style="height:400px;"></div>
      </el-card>

      <!-- 预测明细 -->
      <el-card shadow="never" style="border-radius:10px;">
        <template #header><b>逐日预测明细</b></template>
        <el-table :data="forecastTable" size="small" stripe border style="width:100%;">
          <el-table-column prop="date" label="预测日期" width="140" />
          <el-table-column prop="score" label="预测压力分" width="120">
            <template #default="{ row }">
              <span style="font-weight:bold;">{{ row.score }}</span>
            </template>
          </el-table-column>
          <el-table-column label="置信区间" width="140">
            <template #default="{ row }">
              {{ row.lower }} ~ {{ row.upper }}
            </template>
          </el-table-column>
          <el-table-column prop="risk" label="预测风险等级" width="130">
            <template #default="{ row }">
              <el-tag :type="riskTag(row.risk)" size="small">{{ row.risk }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="较当前变化" width="130">
            <template #default="{ row }">
              <span :style="{ color: row.delta > 0 ? '#f56c6c' : '#67c23a', fontWeight:'bold' }">
                {{ row.delta > 0 ? '+' : '' }}{{ row.delta }}
              </span>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>
    <el-empty v-else description="加载中..." />
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { initChart } from '@/utils/chart'
import { getUsers, getTrendChart, getTrendForecast } from '../api/index.js'

const users = ref([])
const userId = ref('')
const lineRef = ref()
const rateRef = ref()
const forecastRef = ref()
let lineChart, rateChart, forecastChart

const forecast = ref(null)
const forecastTable = ref([])

function riskTag(level) {
  if (level === '高风险') return 'danger'
  if (level === '中风险') return 'warning'
  return 'success'
}

const dirColor = computed(() => {
  if (!forecast.value) return '#909399'
  const d = forecast.value.summary.direction
  if (d === '上升') return '#f56c6c'
  if (d === '下降') return '#67c23a'
  return '#409eff'
})

const dirArrow = computed(() => {
  if (!forecast.value) return ''
  const d = forecast.value.summary.direction
  if (d === '上升') return '↗'
  if (d === '下降') return '↘'
  return '→'
})

onMounted(async () => {
  const res = await getUsers()
  users.value = res.data
  userId.value = res.data[0]
  await load()
})

async function load() {
  const [trendRes, fcRes] = await Promise.all([
    getTrendChart(userId.value),
    getTrendForecast(userId.value),
  ])
  renderLine(trendRes.data)
  renderRate(trendRes.data)

  const fc = fcRes.data
  forecast.value = fc

  forecastTable.value = fc.forecast.dates.map((date, i) => ({
    date,
    score: fc.forecast.scores[i],
    upper: fc.forecast.upper[i],
    lower: fc.forecast.lower[i],
    risk: fc.forecast.risk_levels[i],
    delta: (fc.forecast.scores[i] - fc.summary.last_score).toFixed(2),
  }))

  setTimeout(() => renderForecast(fc), 100)
}

function renderLine(d) {
  if (!lineChart) lineChart = initChart(lineRef.value)
  lineChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['压力评分', '7日均线'] },
    xAxis: { type: 'category', data: d.dates, axisLabel: { rotate: 45, fontSize: 11 } },
    yAxis: { type: 'value', name: '分值', min: 0, max: 100 },
    series: [
      { name: '压力评分', type: 'line', data: d.stress_score, smooth: true, symbol: 'none', color: '#409eff' },
      { name: '7日均线', type: 'line', data: d.score_7day_avg, smooth: true, symbol: 'none',
        lineStyle: { type: 'dashed' }, color: '#e6a23c' },
    ],
  })
}

function renderRate(d) {
  if (!rateChart) rateChart = initChart(rateRef.value)
  const colors = d.score_change_rate.map(v => v > 0 ? '#f56c6c' : '#67c23a')
  rateChart.setOption({
    tooltip: { trigger: 'axis', formatter: p => `${p[0].name}<br/>变化率：${(p[0].value * 100).toFixed(1)}%` },
    xAxis: { type: 'category', data: d.dates, axisLabel: { rotate: 45, fontSize: 11 } },
    yAxis: { type: 'value', name: '变化率' },
    series: [{
      type: 'bar',
      data: d.score_change_rate.map((v, i) => ({ value: v, itemStyle: { color: colors[i] } })),
    }],
  })
}

function renderForecast(fc) {
  if (!forecastRef.value) return
  if (!forecastChart) forecastChart = initChart(forecastRef.value)

  const histDates = fc.history.dates
  const histScores = fc.history.scores
  const fcDates = fc.forecast.dates
  const fcScores = fc.forecast.scores
  const allDates = [...histDates, ...fcDates]
  const pad = new Array(histDates.length - 1).fill(null)
  const bridge = histScores[histScores.length - 1]

  const histLine = [...histScores, ...new Array(fcDates.length).fill(null)]
  const fcLine = [...pad, bridge, ...fcScores]
  const upperLine = [...pad, bridge, ...fc.forecast.upper]
  const lowerLine = [...pad, bridge, ...fc.forecast.lower]

  forecastChart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: params => {
        let tip = `<b>${params[0].axisValue}</b><br/>`
        params.forEach(p => {
          if (p.value != null && !p.seriesName.startsWith('_')) {
            tip += `${p.marker} ${p.seriesName}: ${p.value}<br/>`
          }
        })
        return tip
      }
    },
    legend: { data: ['历史压力分', '预测压力分', '置信上界', '置信下界'], top: 5 },
    xAxis: {
      type: 'category',
      data: allDates,
      axisLabel: { rotate: 45, fontSize: 10 },
    },
    yAxis: { type: 'value', name: '压力分', min: 0, max: 100 },
    series: [
      {
        name: '历史压力分',
        type: 'line',
        data: histLine,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2, color: '#409eff' },
        itemStyle: { color: '#409eff' },
        areaStyle: { opacity: 0.08, color: '#409eff' },
      },
      {
        name: '预测压力分',
        type: 'line',
        data: fcLine,
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        lineStyle: { width: 3, type: 'dashed', color: '#e6a23c' },
        itemStyle: {
          color: p => {
            const v = typeof p === 'number' ? p : (p.value ?? 0)
            if (v >= 65) return '#f56c6c'
            if (v >= 40) return '#e6a23c'
            return '#67c23a'
          },
        },
        label: {
          show: true,
          position: 'top',
          fontSize: 10,
          formatter: p => {
            const idx = p.dataIndex - histDates.length + 1
            if (idx >= 0 && idx < fc.forecast.risk_levels.length) {
              return fc.forecast.risk_levels[idx]
            }
            return ''
          },
        },
        markLine: {
          data: [{ xAxis: histDates[histDates.length - 1] }],
          label: { formatter: '预测起点', fontSize: 11 },
          lineStyle: { type: 'dashed', color: '#909399' },
        },
      },
      {
        name: '置信上界',
        type: 'line',
        data: upperLine,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 1, type: 'dotted', color: '#c0c4cc' },
        itemStyle: { color: '#c0c4cc' },
      },
      {
        name: '置信下界',
        type: 'line',
        data: lowerLine,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 1, type: 'dotted', color: '#c0c4cc' },
        itemStyle: { color: '#c0c4cc' },
      },
    ],
    grid: { top: 60, bottom: 60, right: 30 },
  }, true)
}
</script>

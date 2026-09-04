<template>
  <div>
    <h2 style="margin:0 0 20px;">每日压力分析</h2>
    <el-card shadow="never" style="border-radius:10px;margin-bottom:16px;">
      <el-form inline>
        <el-form-item label="选择用户">
          <el-select v-model="userId" placeholder="请选择用户" style="width:220px;" @change="load">
            <el-option v-for="id in users" :key="id" :label="`用户 ${id}`" :value="id" />
          </el-select>
        </el-form-item>
      </el-form>
    </el-card>

    <el-row :gutter="16">
      <el-col :span="24">
        <el-card shadow="never" style="border-radius:10px;margin-bottom:16px;">
          <template #header><b>压力评分趋势（含7日滑动均线）</b></template>
          <div ref="lineRef" style="height:350px;"></div>
        </el-card>
      </el-col>
      <el-col :span="24">
        <el-card shadow="never" style="border-radius:10px;margin-bottom:16px;">
          <template #header><b>各维度压力分明细</b></template>
          <div ref="barRef" style="height:300px;"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 四模型预测对比 -->
    <h2 style="margin:30px 0 20px;">四模型风险预测对比</h2>

    <el-card shadow="never" style="border-radius:10px;margin-bottom:16px;">
      <el-form inline>
        <el-form-item label="选择用户">
          <el-select v-model="predUserId" placeholder="请选择用户" style="width:220px;" @change="loadPrediction">
            <el-option v-for="id in predUsers" :key="id" :label="`用户 ${id}`" :value="id" />
          </el-select>
        </el-form-item>
      </el-form>
    </el-card>

    <template v-if="predData">
      <!-- 准确率卡片 -->
      <el-row :gutter="16" style="margin-bottom:16px;">
        <el-col :span="6" v-for="m in modelList" :key="m.key">
          <el-card shadow="hover" style="border-radius:10px;">
            <div style="text-align:center;">
              <div :style="{ fontSize:'13px', color: m.color, fontWeight:'bold', marginBottom:'6px' }">{{ m.label }}</div>
              <div style="font-size:28px;font-weight:bold;">{{ m.accuracy }}</div>
              <div style="color:rgba(255,255,255,0.5);font-size:12px;margin-top:4px;">该用户准确率</div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" style="margin-bottom:16px;">
        <!-- 预测对比时间线 -->
        <el-col :span="16">
          <el-card shadow="never" style="border-radius:10px;">
            <template #header><b>每日预测结果对比</b></template>
            <div ref="predChartRef" style="height:380px;"></div>
          </el-card>
        </el-col>
        <!-- 预测分布饼图 -->
        <el-col :span="8">
          <el-card shadow="never" style="border-radius:10px;">
            <template #header><b>预测正误分布</b></template>
            <div ref="pieChartRef" style="height:380px;"></div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 预测明细表格 -->
      <el-card shadow="never" style="border-radius:10px;">
        <template #header><b>逐日预测明细表</b></template>
        <el-table :data="predTable" size="small" stripe border max-height="400" style="width:100%;">
          <el-table-column prop="date" label="日期" width="120" />
          <el-table-column prop="actual" label="实际风险" width="100">
            <template #default="{ row }">
              <el-tag :type="riskTag(row.actual)" size="small">{{ row.actual }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column v-for="m in modelList" :key="m.key" :label="m.label" width="130">
            <template #default="{ row }">
              <el-tag :type="riskTag(row[m.key])" size="small" :effect="row[m.key] === row.actual ? 'dark' : 'plain'">
                {{ row[m.key] }}
              </el-tag>
              <el-icon v-if="row[m.key] !== row.actual" style="color:#f56c6c;margin-left:4px;"><CloseBold /></el-icon>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>
    <el-empty v-else-if="predUserId" description="该用户暂无预测数据" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { initChart } from '@/utils/chart'
import { CloseBold } from '@element-plus/icons-vue'
import {
  getUsers, getStressChart, getStressList,
  getPredictionUsers, getPrediction
} from '../api/index.js'

const users = ref([])
const userId = ref('')
const lineRef = ref()
const barRef = ref()
let lineChart, barChart

const predUsers = ref([])
const predUserId = ref('')
const predData = ref(null)
const predTable = ref([])
const predChartRef = ref()
const pieChartRef = ref()
let predChart, pieChart

const MODEL_CONFIG = {
  WeightedScoring:     { label: '综合压力评估', color: '#409EFF' },
  TrendAnalysis:       { label: '趋势分析',     color: '#67C23A' },
  CorrelationAnalysis: { label: '相关性分析',   color: '#E6A23C' },
  KMeansClustering:    { label: 'K-Means聚类',  color: '#F56C6C' },
}
const modelList = ref([])

function riskTag(level) {
  if (level === '高风险') return 'danger'
  if (level === '中风险') return 'warning'
  return 'success'
}

onMounted(async () => {
  const [usersRes, predUsersRes] = await Promise.all([getUsers(), getPredictionUsers()])
  users.value = usersRes.data
  userId.value = usersRes.data[0]
  predUsers.value = predUsersRes.data
  predUserId.value = predUsersRes.data[0]
  await Promise.all([load(), loadPrediction()])
})

async function load() {
  const [chartRes, listRes] = await Promise.all([
    getStressChart(userId.value),
    getStressList(userId.value),
  ])
  renderLine(chartRes.data)
  renderBar(listRes.data.results || listRes.data)
}

async function loadPrediction() {
  if (!predUserId.value) return
  const res = await getPrediction(predUserId.value)
  const d = res.data
  if (!d.dates.length) { predData.value = null; return }
  predData.value = d

  modelList.value = Object.keys(MODEL_CONFIG).map(k => ({
    key: k,
    label: MODEL_CONFIG[k].label,
    color: MODEL_CONFIG[k].color,
    accuracy: d.accuracy[k] != null ? (d.accuracy[k] * 100).toFixed(1) + '%' : '-',
  }))

  predTable.value = d.dates.map((date, i) => {
    const row = { date, actual: d.actual_risk[i] }
    for (const m of Object.keys(MODEL_CONFIG)) {
      row[m] = d.predictions[m][i]
    }
    return row
  })

  setTimeout(() => {
    renderPredChart(d)
    renderPieChart(d)
  }, 100)
}

function renderLine(data) {
  if (!lineChart) lineChart = initChart(lineRef.value)
  lineChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['压力评分', '7日均线'] },
    xAxis: { type: 'category', data: data.dates, axisLabel: { rotate: 45, fontSize: 11 } },
    yAxis: { type: 'value', name: '分值', min: 0, max: 100 },
    series: [
      { name: '压力评分', type: 'line', data: data.stress_score, smooth: true, symbol: 'none',
        lineStyle: { width: 2 }, areaStyle: { opacity: 0.15 }, color: '#409eff' },
      { name: '7日均线', type: 'line', data: data.score_7day_avg, smooth: true, symbol: 'none',
        lineStyle: { width: 2, type: 'dashed' }, color: '#f56c6c' },
    ],
  })
}

function renderBar(records) {
  if (!barChart) barChart = initChart(barRef.value)
  const dates = records.map(r => r.activity_date)
  barChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['心率压力分', '久坐压力分', '睡眠压力分', '活动压力分'] },
    xAxis: { type: 'category', data: dates, axisLabel: { rotate: 45, fontSize: 11 } },
    yAxis: { type: 'value', name: '分值' },
    series: [
      { name: '心率压力分', type: 'bar', stack: 'score', data: records.map(r => r.hr_score) },
      { name: '久坐压力分', type: 'bar', stack: 'score', data: records.map(r => r.sedentary_score) },
      { name: '睡眠压力分', type: 'bar', stack: 'score', data: records.map(r => r.sleep_score) },
      { name: '活动压力分', type: 'bar', stack: 'score', data: records.map(r => r.active_score) },
    ],
  })
}

function renderPredChart(d) {
  if (!predChartRef.value) return
  if (!predChart) predChart = initChart(predChartRef.value)

  const riskMap = { '低风险': 0, '中风险': 1, '高风险': 2 }
  const series = [
    {
      name: '实际风险',
      type: 'line',
      data: d.actual_risk.map(r => riskMap[r]),
      lineStyle: { width: 3, color: '#303133' },
      itemStyle: { color: '#303133' },
      symbol: 'circle',
      symbolSize: 10,
      z: 10,
    },
    ...Object.keys(MODEL_CONFIG).map(k => ({
      name: MODEL_CONFIG[k].label,
      type: 'scatter',
      data: d.predictions[k].map(r => riskMap[r]),
      itemStyle: { color: MODEL_CONFIG[k].color },
      symbolSize: (val, params) => {
        return d.predictions[k][params.dataIndex] === d.actual_risk[params.dataIndex] ? 12 : 16
      },
      symbol: (val, params) => {
        return d.predictions[k][params.dataIndex] === d.actual_risk[params.dataIndex] ? 'circle' : 'triangle'
      },
    })),
  ]

  predChart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: params => {
        const date = d.dates[params[0].dataIndex]
        const labels = ['低风险', '中风险', '高风险']
        return `<b>${date}</b><br/>` +
          params.map(p => `${p.marker} ${p.seriesName}: ${labels[p.value]}`).join('<br/>')
      }
    },
    legend: { top: 5 },
    xAxis: { type: 'category', data: d.dates, axisLabel: { rotate: 45, fontSize: 10 } },
    yAxis: {
      type: 'value', name: '风险等级', min: -0.3, max: 2.3,
      axisLabel: { formatter: v => ['低风险', '中风险', '高风险'][Math.round(v)] || '' },
      splitNumber: 2,
    },
    series,
    grid: { top: 60, bottom: 60 },
  }, true)
}

function renderPieChart(d) {
  if (!pieChartRef.value) return
  if (!pieChart) pieChart = initChart(pieChartRef.value)

  const pieData = Object.keys(MODEL_CONFIG).map(k => {
    const correct = d.predictions[k].filter((p, i) => p === d.actual_risk[i]).length
    const wrong = d.predictions[k].length - correct
    return { name: MODEL_CONFIG[k].label, correct, wrong }
  })

  pieChart.setOption({
    tooltip: { formatter: '{b}: 正确{c}次' },
    legend: { bottom: 0, textStyle: { fontSize: 11 } },
    series: [{
      type: 'pie',
      radius: ['30%', '55%'],
      center: ['50%', '45%'],
      data: pieData.map(p => ({
        name: p.name,
        value: p.correct,
        itemStyle: { color: MODEL_CONFIG[Object.keys(MODEL_CONFIG)[pieData.indexOf(p)]].color },
      })),
      label: { formatter: '{b}\n{d}%', fontSize: 11 },
    }],
  }, true)
}
</script>

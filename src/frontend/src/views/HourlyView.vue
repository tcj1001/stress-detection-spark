<template>
  <div>
    <h2 style="margin:0 0 20px;">24小时时段规律</h2>
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
      <template #header><b>各时段平均步数与卡路里</b></template>
      <div ref="barRef" style="height:320px;"></div>
    </el-card>
    <el-card shadow="never" style="border-radius:10px;">
      <template #header><b>各时段平均活动强度</b></template>
      <div ref="lineRef" style="height:280px;"></div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { initChart } from '@/utils/chart'
import { getHourlyUsers, getHourlyChart } from '../api/index.js'

const users = ref([])
const userId = ref('')
const barRef = ref()
const lineRef = ref()
let barChart, lineChart

onMounted(async () => {
  const res = await getHourlyUsers()
  users.value = res.data
  userId.value = res.data[0]
  await load()
})

async function load() {
  const res = await getHourlyChart(userId.value)
  const d = res.data
  const hours = d.hours.map(h => `${String(h).padStart(2, '0')}:00`)
  renderBar(d, hours)
  renderLine(d, hours)
}

function renderBar(d, hours) {
  if (!barChart) barChart = initChart(barRef.value)
  barChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['平均步数', '平均卡路里'] },
    xAxis: { type: 'category', data: hours },
    yAxis: [
      { type: 'value', name: '步数', position: 'left' },
      { type: 'value', name: '卡路里', position: 'right' },
    ],
    series: [
      { name: '平均步数', type: 'bar', data: d.avg_steps, color: '#409eff' },
      { name: '平均卡路里', type: 'bar', yAxisIndex: 1, data: d.avg_calories, color: '#e6a23c' },
    ],
  })
}

function renderLine(d, hours) {
  if (!lineChart) lineChart = initChart(lineRef.value)
  lineChart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: hours },
    yAxis: { type: 'value', name: '活动强度' },
    series: [{
      type: 'line', data: d.avg_intensity, smooth: true, symbol: 'none',
      areaStyle: { opacity: 0.2 }, color: '#67c23a',
    }],
  })
}
</script>

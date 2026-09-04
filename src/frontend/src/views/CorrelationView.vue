<template>
  <div>
    <h2 style="margin:0 0 20px;">相关性分析</h2>
    <el-card shadow="never" style="border-radius:10px;margin-bottom:16px;">
      <template #header><b>压力特征 Pearson 相关系数热力图</b></template>
      <div ref="heatRef" style="height:500px;"></div>
    </el-card>

    <!-- 三角热力图 -->
    <el-card shadow="never" style="border-radius:10px;margin-bottom:16px;">
      <template #header><b>上三角相关系数矩阵</b></template>
      <div ref="triRef" style="height:500px;"></div>
    </el-card>

    <!-- 关键发现 -->
    <el-row :gutter="16" style="margin-bottom:16px;">
      <el-col :span="12">
        <el-card shadow="never" style="border-radius:10px;">
          <template #header><b>与压力评分的关联强度</b></template>
          <div ref="stressBarRef" style="height:280px;"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never" style="border-radius:10px;">
          <template #header><b>最显著相关特征对</b></template>
          <div ref="topBarRef" style="height:280px;"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" style="border-radius:10px;">
      <template #header><b>关键发现摘要</b></template>
      <div v-for="(finding, i) in findings" :key="i" style="margin-bottom:14px;">
        <el-tag :type="finding.type" size="small" style="margin-right:8px;">{{ finding.tag }}</el-tag>
        <span style="font-size:14px;line-height:1.8;">{{ finding.text }}</span>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { initChart } from '@/utils/chart'
import { getCorrelationHeatmap } from '../api/index.js'

const heatRef = ref()
const triRef = ref()
const stressBarRef = ref()
const topBarRef = ref()
const findings = ref([])

const labelMap = {
  stress_score: '压力评分',
  resting_hr: '静息心率',
  sleep_efficiency: '睡眠效率',
  sedentary_ratio: '久坐比例',
  active_minutes: '活动时长',
  total_steps: '总步数',
  calories: '卡路里',
}

function label(f) { return labelMap[f] || f }

function strengthText(v) {
  const a = Math.abs(v)
  if (a >= 0.7) return '强'
  if (a >= 0.4) return '中等'
  if (a >= 0.2) return '弱'
  return '极弱'
}

onMounted(async () => {
  const res = await getCorrelationHeatmap()
  const { features, data } = res.data

  renderHeatmap(features, data)
  renderTriangle(features, data)

  const corrMap = {}
  data.forEach(([x, y, v]) => { corrMap[`${x}__${y}`] = +v.toFixed(4) })

  analyzeStressCorrelations(features, corrMap)
  analyzeTopPairs(features, corrMap)
  generateFindings(features, corrMap)
})

function renderHeatmap(features, data) {
  const labels = features.map(f => label(f))
  const chartData = data.map(([x, y, v]) => [features.indexOf(x), features.indexOf(y), +v.toFixed(3)])
  const chart = initChart(heatRef.value)
  chart.setOption({
    tooltip: {
      formatter: p => `${label(features[p.data[1]])} — ${label(features[p.data[0]])}<br/>相关系数：${p.data[2]}`,
    },
    grid: { top: 20, right: 120, bottom: 80, left: 100 },
    xAxis: { type: 'category', data: labels, axisLabel: { rotate: 30 } },
    yAxis: { type: 'category', data: labels },
    visualMap: {
      min: -1, max: 1, calculable: true, orient: 'vertical', right: 10, top: 'center',
      inRange: { color: ['#5470c6', '#ffffff', '#ee6666'] },
    },
    series: [{
      type: 'heatmap', data: chartData,
      label: { show: true, fontSize: 11 },
      emphasis: { itemStyle: { shadowBlur: 10 } },
    }],
  })
}

function renderTriangle(features, data) {
  const labels = features.map(f => label(f))
  const chartData = []
  data.forEach(([x, y, v]) => {
    const xi = features.indexOf(x), yi = features.indexOf(y)
    if (yi >= xi) {
      chartData.push([xi, yi, +v.toFixed(3)])
    }
  })

  const chart = initChart(triRef.value)
  chart.setOption({
    tooltip: {
      formatter: p => {
        const d = p.data
        return `${label(features[d[1]])} — ${label(features[d[0]])}<br/>相关系数：${d[2]}`
      },
    },
    grid: { top: 20, right: 120, bottom: 80, left: 100 },
    xAxis: { type: 'category', data: labels, axisLabel: { rotate: 30 } },
    yAxis: { type: 'category', data: labels },
    visualMap: {
      min: -1, max: 1, calculable: true, orient: 'vertical', right: 10, top: 'center',
      inRange: { color: ['#304d77', '#5470c6', '#c2d4f0', '#ffffff', '#f0c2c2', '#ee6666', '#a73030'] },
    },
    series: [{
      type: 'heatmap',
      data: chartData,
      label: {
        show: true, fontSize: 12, fontWeight: 'bold',
        formatter: p => p.data[2].toFixed(2),
      },
      itemStyle: { borderColor: '#fff', borderWidth: 2, borderRadius: 4 },
      emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.3)' } },
    }],
  })
}

function analyzeStressCorrelations(features, corrMap) {
  const stressCorrs = features
    .filter(f => f !== 'stress_score')
    .map(f => ({
      feature: f,
      value: corrMap[`stress_score__${f}`] ?? corrMap[`${f}__stress_score`] ?? 0,
    }))
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))

  const chart = initChart(stressBarRef.value)
  chart.setOption({
    tooltip: { formatter: p => `${p.name}: ${p.value}` },
    xAxis: { type: 'value', name: '相关系数', min: -1, max: 1 },
    yAxis: { type: 'category', data: stressCorrs.map(c => label(c.feature)).reverse() },
    series: [{
      type: 'bar',
      data: stressCorrs.map(c => ({
        value: c.value,
        itemStyle: { color: c.value > 0 ? '#ee6666' : '#5470c6' },
        label: { show: true, position: c.value > 0 ? 'right' : 'left', fontSize: 11, formatter: '{c}' },
      })).reverse(),
    }],
    grid: { left: 90, right: 60, top: 10, bottom: 30 },
  })
}

function analyzeTopPairs(features, corrMap) {
  const pairs = []
  for (let i = 0; i < features.length; i++) {
    for (let j = i + 1; j < features.length; j++) {
      const a = features[i], b = features[j]
      if (a === 'stress_score' || b === 'stress_score') continue
      const v = corrMap[`${a}__${b}`] ?? corrMap[`${b}__${a}`] ?? 0
      pairs.push({ a, b, value: v })
    }
  }
  pairs.sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
  const top = pairs.slice(0, 6)

  const chart = initChart(topBarRef.value)
  chart.setOption({
    tooltip: { formatter: p => `${p.name}: ${p.value}` },
    xAxis: { type: 'value', name: '相关系数', min: -1, max: 1 },
    yAxis: {
      type: 'category',
      data: top.map(p => `${label(p.a)} ↔ ${label(p.b)}`).reverse(),
      axisLabel: { fontSize: 11 },
    },
    series: [{
      type: 'bar',
      data: top.map(p => ({
        value: p.value,
        itemStyle: { color: p.value > 0 ? '#ee6666' : '#5470c6' },
        label: { show: true, position: p.value > 0 ? 'right' : 'left', fontSize: 11, formatter: '{c}' },
      })).reverse(),
    }],
    grid: { left: 150, right: 60, top: 10, bottom: 30 },
  })
}

function generateFindings(features, corrMap) {
  const result = []

  const stressCorrs = features
    .filter(f => f !== 'stress_score')
    .map(f => ({
      feature: f,
      value: corrMap[`stress_score__${f}`] ?? corrMap[`${f}__stress_score`] ?? 0,
    }))
    .sort((a, b) => b.value - a.value)

  const strongest = stressCorrs.reduce((a, b) => Math.abs(a.value) > Math.abs(b.value) ? a : b)
  result.push({
    tag: '核心发现',
    type: 'danger',
    text: `"${label(strongest.feature)}"与压力评分的相关性最强（r = ${strongest.value.toFixed(3)}），`
      + `属于${strengthText(strongest.value)}${strongest.value > 0 ? '正' : '负'}相关，`
      + `是影响压力水平的最关键指标。`,
  })

  const positives = stressCorrs.filter(c => c.value > 0.2)
  if (positives.length) {
    result.push({
      tag: '正相关',
      type: 'warning',
      text: `${positives.map(c => `"${label(c.feature)}"(${c.value.toFixed(3)})`).join('、')}`
        + `与压力评分呈正相关——数值越高，压力越大。`,
    })
  }

  const negatives = stressCorrs.filter(c => c.value < -0.2)
  if (negatives.length) {
    result.push({
      tag: '负相关',
      type: 'success',
      text: `${negatives.map(c => `"${label(c.feature)}"(${c.value.toFixed(3)})`).join('、')}`
        + `与压力评分呈负相关——数值越高，压力反而越低，是缓解压力的保护因素。`,
    })
  }

  const allPairs = []
  for (let i = 0; i < features.length; i++) {
    for (let j = i + 1; j < features.length; j++) {
      const a = features[i], b = features[j]
      if (a === 'stress_score' || b === 'stress_score') continue
      const v = corrMap[`${a}__${b}`] ?? corrMap[`${b}__${a}`] ?? 0
      allPairs.push({ a, b, value: v })
    }
  }

  const strongPair = allPairs.reduce((a, b) => Math.abs(a.value) > Math.abs(b.value) ? a : b)
  if (Math.abs(strongPair.value) > 0.3) {
    result.push({
      tag: '特征联动',
      type: '',
      text: `"${label(strongPair.a)}"与"${label(strongPair.b)}"之间存在${strengthText(strongPair.value)}`
        + `${strongPair.value > 0 ? '正' : '负'}相关（r = ${strongPair.value.toFixed(3)}），`
        + `表明两者在生理机制上存在联动效应。`,
    })
  }

  const weakStress = stressCorrs.filter(c => Math.abs(c.value) < 0.15)
  if (weakStress.length) {
    result.push({
      tag: '独立因素',
      type: 'info',
      text: `${weakStress.map(c => `"${label(c.feature)}"`).join('、')}`
        + `与压力评分几乎无线性关系（|r| < 0.15），`
        + `说明这些指标受个体差异影响较大，不宜作为通用压力判断依据。`,
    })
  }

  const sedSleep = corrMap['sedentary_ratio__sleep_efficiency'] ?? corrMap['sleep_efficiency__sedentary_ratio']
  if (sedSleep != null) {
    const desc = sedSleep > 0 ? '久坐多的人反而睡眠效率更高（可能与低活动量导致的疲劳有关）'
      : '久坐比例越高，睡眠效率越差，形成"久坐→睡差→高压"的恶性循环'
    result.push({
      tag: '健康启示',
      type: 'danger',
      text: `久坐比例与睡眠效率的相关系数为 ${sedSleep.toFixed(3)}：${desc}。`
        + `建议关注久坐与睡眠的综合干预。`,
    })
  }

  findings.value = result
}
</script>

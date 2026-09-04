<template>
  <div>
    <h2 style="margin-bottom:20px;">四模型性能对比分析</h2>

    <!-- Metric cards -->
    <el-row :gutter="16" style="margin-bottom:20px;">
      <el-col :span="6" v-for="m in modelList" :key="m.key">
        <el-card shadow="hover">
          <div style="text-align:center;">
            <div :style="{ fontSize:'13px', color: m.color, fontWeight:'bold', marginBottom:'8px' }">{{ m.label }}</div>
            <div style="font-size:26px;font-weight:bold;">{{ m.accuracy }}</div>
            <div style="color:rgba(255,255,255,0.5);font-size:12px;margin-top:4px;">Accuracy</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Main comparison charts -->
    <el-row :gutter="20" style="margin-bottom:20px;">
      <el-col :span="12">
        <el-card header="分类性能指标对比">
          <div ref="metricsChart" style="height:420px;"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card header="学习曲线（收敛性对比）">
          <div ref="learningChart" style="height:420px;"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Confusion matrix heatmaps -->
    <el-row :gutter="20" style="margin-bottom:20px;">
      <el-col :span="6" v-for="m in modelKeys" :key="'cm_'+m">
        <el-card :header="MODEL_CONFIG[m].label + ' 混淆矩阵'">
          <div :ref="el => cmRefs[m] = el" style="height:300px;"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Prediction distribution -->
    <el-row :gutter="20" style="margin-bottom:20px;">
      <el-col :span="12">
        <el-card header="各模型预测分布 vs 实际分布">
          <div ref="distChart" style="height:380px;"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card header="各模型预测正误统计">
          <div ref="correctChart" style="height:380px;"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Per-class metrics -->
    <el-row :gutter="20" style="margin-bottom:20px;">
      <el-col :span="12">
        <el-card header="各风险等级 F1 分数对比">
          <div ref="f1ClassChart" style="height:380px;"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card header="各风险等级召回率对比">
          <div ref="recallClassChart" style="height:380px;"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Feature importance -->
    <el-row :gutter="16">
      <el-col :span="12" v-for="m in modelKeys" :key="'fi_'+m">
        <el-card :header="MODEL_CONFIG[m].label + ' — 特征重要性'" style="margin-bottom:16px;">
          <div :ref="el => fiRefs[m] = el" style="height:300px;"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'
import { initChart as _initChart } from '@/utils/chart'
import {
  getModelMetrics, getModelLearningCurve,
  getModelFeatureImportance, getModelConfusionMatrix
} from '@/api'

const metricsChart = ref(null)
const learningChart = ref(null)
const f1ClassChart = ref(null)
const recallClassChart = ref(null)
const fiRefs = reactive({})
const distChart = ref(null)
const correctChart = ref(null)
const cmRefs = reactive({})

const modelList = ref([])

const MODEL_CONFIG = {
  WeightedScoring:     { label: '综合压力评估', color: '#409EFF', lineType: 'solid',  symbol: 'circle' },
  TrendAnalysis:       { label: '趋势分析',     color: '#67C23A', lineType: 'dashed', symbol: 'rect' },
  CorrelationAnalysis: { label: '相关性分析',   color: '#E6A23C', lineType: 'dotted', symbol: 'triangle' },
  KMeansClustering:    { label: 'K-Means聚类',  color: '#F56C6C', lineType: [5,3,1,3], symbol: 'diamond' },
}

const modelKeys = Object.keys(MODEL_CONFIG)

const featureLabel = {
  total_steps: '总步数', sedentary_min: '久坐时间', calories: '卡路里',
  active_minutes: '活动时间', sedentary_ratio: '久坐比例', resting_hr: '静息心率',
  avg_hr: '平均心率', hrv_proxy: 'HRV代理', sleep_efficiency: '睡眠效率',
  avg_mets: '平均METs', low_mets_ratio: '低METs比例', total_sleep_min: '总睡眠时间',
  score_change_rate: '评分变化率', score_7day_avg: '7日均分', prev_score: '前日评分',
}

function initChart(el) {
  return _initChart(el, { renderer: 'canvas', devicePixelRatio: window.devicePixelRatio * 2 })
}

onMounted(async () => {
  const [metricsRes, lcRes, fiRes, cmRes] = await Promise.all([
    getModelMetrics(),
    getModelLearningCurve(),
    getModelFeatureImportance(),
    getModelConfusionMatrix(),
  ])

  const metrics = metricsRes.data
  const lc = lcRes.data
  const fi = fiRes.data
  const cm = cmRes.data

  modelList.value = modelKeys.map(k => ({
    key: k,
    label: MODEL_CONFIG[k].label,
    color: MODEL_CONFIG[k].color,
    accuracy: metrics[k]?.accuracy != null ? (metrics[k].accuracy * 100).toFixed(1) + '%' : '-',
  }))

  await nextTick()
  renderMetricsComparison(metrics)
  renderLearningCurves(lc)
  renderPerClassF1(metrics)
  renderPerClassRecall(metrics)
  renderFeatureImportance(fi)
  renderConfusionMatrices(cm)
  renderDistribution(cm)
  renderCorrectness(cm)
})

function renderMetricsComparison(metrics) {
  const metricNames = ['accuracy', 'precision', 'recall', 'f1']
  const metricLabels = ['准确率', '精确率', '召回率', 'F1分数']

  const series = modelKeys.map(k => ({
    name: MODEL_CONFIG[k].label,
    type: 'bar',
    barGap: '10%',
    data: metricNames.map(m => {
      const v = metrics[k]?.[m]
      return v != null ? +(v * 100).toFixed(2) : 0
    }),
    itemStyle: { color: MODEL_CONFIG[k].color },
    label: { show: true, position: 'top', fontSize: 11, formatter: '{c}%' }
  }))

  initChart(metricsChart.value).setOption({
    tooltip: { trigger: 'axis', formatter: params => params.map(p => `${p.seriesName}: ${p.value}%`).join('<br>') },
    legend: { top: 5 },
    xAxis: { type: 'category', data: metricLabels, axisLabel: { fontSize: 13 } },
    yAxis: { type: 'value', name: '%', max: 100, min: 50 },
    series,
    grid: { top: 60, bottom: 30 }
  })
}

function renderLearningCurves(lc) {
  const series = []
  modelKeys.forEach(k => {
    const cfg = MODEL_CONFIG[k]
    const data = lc[k]
    if (!data || !data.train_size.length) return
    series.push({
      name: cfg.label + ' (Test)',
      type: 'line',
      data: data.train_size.map((s, i) => [s, +(data.test_score[i] * 100).toFixed(2)]),
      lineStyle: { type: cfg.lineType, width: 2.5 },
      symbol: cfg.symbol, symbolSize: 8,
      itemStyle: { color: cfg.color },
    })
  })

  initChart(learningChart.value).setOption({
    tooltip: { trigger: 'axis', formatter: params => params.map(p => `${p.seriesName}: ${p.value[1]}%`).join('<br>') },
    legend: { top: 5, textStyle: { fontSize: 11 } },
    xAxis: { type: 'value', name: '训练样本数', nameLocation: 'center', nameGap: 30 },
    yAxis: { type: 'value', name: '准确率 (%)', min: v => Math.floor(v.min / 5) * 5 },
    series,
    grid: { top: 60, bottom: 45 }
  })
}

function renderPerClassF1(metrics) {
  const riskLevels = ['高风险', '中风险', '低风险']
  const series = modelKeys.map(k => ({
    name: MODEL_CONFIG[k].label,
    type: 'line',
    data: riskLevels.map(r => {
      const v = metrics[k]?.[`f1_${r}`]
      return v != null ? +(v * 100).toFixed(2) : 0
    }),
    lineStyle: { type: MODEL_CONFIG[k].lineType, width: 2.5 },
    symbol: MODEL_CONFIG[k].symbol, symbolSize: 10,
    itemStyle: { color: MODEL_CONFIG[k].color },
  }))

  initChart(f1ClassChart.value).setOption({
    tooltip: { trigger: 'axis', formatter: params => params.map(p => `${p.seriesName}: ${p.value}%`).join('<br>') },
    legend: { top: 5 },
    xAxis: { type: 'category', data: riskLevels, axisLabel: { fontSize: 13 } },
    yAxis: { type: 'value', name: 'F1 (%)', max: 100 },
    series,
    grid: { top: 55, bottom: 30 }
  })
}

function renderPerClassRecall(metrics) {
  const riskLevels = ['高风险', '中风险', '低风险']
  const series = modelKeys.map(k => ({
    name: MODEL_CONFIG[k].label,
    type: 'line',
    data: riskLevels.map(r => {
      const v = metrics[k]?.[`recall_${r}`]
      return v != null ? +(v * 100).toFixed(2) : 0
    }),
    lineStyle: { type: MODEL_CONFIG[k].lineType, width: 2.5 },
    symbol: MODEL_CONFIG[k].symbol, symbolSize: 10,
    itemStyle: { color: MODEL_CONFIG[k].color },
  }))

  initChart(recallClassChart.value).setOption({
    tooltip: { trigger: 'axis', formatter: params => params.map(p => `${p.seriesName}: ${p.value}%`).join('<br>') },
    legend: { top: 5 },
    xAxis: { type: 'category', data: riskLevels, axisLabel: { fontSize: 13 } },
    yAxis: { type: 'value', name: '召回率 (%)', max: 100 },
    series,
    grid: { top: 55, bottom: 30 }
  })
}

function renderFeatureImportance(fi) {
  modelKeys.forEach(k => {
    const el = fiRefs[k]
    if (!el || !fi[k] || !fi[k].length) return
    const cfg = MODEL_CONFIG[k]
    const items = fi[k].sort((a, b) => a.rank - b.rank)
    const names = items.map(i => featureLabel[i.feature] || i.feature)
    const values = items.map(i => +(i.importance * 100).toFixed(2))

    initChart(el).setOption({
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'value', name: '重要性 (%)' },
      yAxis: { type: 'category', data: names.slice().reverse(), axisLabel: { fontSize: 12 } },
      series: [{
        type: 'bar',
        data: values.slice().reverse(),
        itemStyle: { color: cfg.color },
        label: { show: true, position: 'right', fontSize: 11, formatter: '{c}%' },
      }],
      grid: { left: 100, top: 10, bottom: 20, right: 60 },
    })
  })
}

function renderConfusionMatrices(cm) {
  const risks = cm.risk_levels

  modelKeys.forEach(k => {
    const el = cmRefs[k]
    if (!el) return
    const matrix = cm.models[k].matrix
    const data = []
    for (let i = 0; i < risks.length; i++) {
      for (let j = 0; j < risks.length; j++) {
        data.push([j, i, matrix[i][j]])
      }
    }
    const maxVal = Math.max(...data.map(d => d[2]))

    initChart(el).setOption({
      tooltip: {
        formatter: p => `实际: ${risks[p.data[1]]}<br/>预测: ${risks[p.data[0]]}<br/>数量: ${p.data[2]}`
      },
      xAxis: { type: 'category', data: risks, name: '预测', nameLocation: 'center', nameGap: 30, axisLabel: { fontSize: 11 } },
      yAxis: { type: 'category', data: risks, name: '实际', axisLabel: { fontSize: 11 } },
      visualMap: {
        min: 0, max: maxVal, show: false,
        inRange: { color: ['#ffffff', MODEL_CONFIG[k].color] },
      },
      series: [{
        type: 'heatmap',
        data,
        label: { show: true, fontSize: 16, fontWeight: 'bold' },
        itemStyle: { borderColor: '#fff', borderWidth: 2 },
      }],
      grid: { top: 10, bottom: 45, left: 60, right: 10 },
    })
  })
}

function renderDistribution(cm) {
  const risks = cm.risk_levels
  const actualTotal = {}
  risks.forEach(r => { actualTotal[r] = cm.models[modelKeys[0]].actual_dist[r] || 0 })

  const categories = ['实际分布', ...modelKeys.map(k => MODEL_CONFIG[k].label)]
  const series = risks.map(r => ({
    name: r,
    type: 'bar',
    stack: 'total',
    data: [
      actualTotal[r],
      ...modelKeys.map(k => cm.models[k].pred_dist[r] || 0),
    ],
    itemStyle: { color: r === '高风险' ? '#f56c6c' : r === '中风险' ? '#e6a23c' : '#67c23a' },
    label: { show: true, position: 'inside', fontSize: 11 },
  }))

  initChart(distChart.value).setOption({
    tooltip: { trigger: 'axis' },
    legend: { top: 5 },
    xAxis: { type: 'category', data: categories, axisLabel: { rotate: 15, fontSize: 11 } },
    yAxis: { type: 'value', name: '样本数' },
    series,
    grid: { top: 50, bottom: 50 },
  })
}

function renderCorrectness(cm) {
  const labels = modelKeys.map(k => MODEL_CONFIG[k].label)
  const correct = modelKeys.map(k => {
    const m = cm.models[k].matrix
    let c = 0
    for (let i = 0; i < m.length; i++) c += m[i][i]
    return c
  })
  const total = modelKeys.map(k => {
    const m = cm.models[k].matrix
    let t = 0
    m.forEach(row => row.forEach(v => { t += v }))
    return t
  })
  const wrong = total.map((t, i) => t - correct[i])

  initChart(correctChart.value).setOption({
    tooltip: { trigger: 'axis', formatter: params => {
      const c = params[0].value, w = params[1].value
      return `${params[0].name}<br/>正确: ${c}<br/>错误: ${w}<br/>准确率: ${(c / (c + w) * 100).toFixed(1)}%`
    }},
    legend: { top: 5 },
    xAxis: { type: 'category', data: labels, axisLabel: { fontSize: 11 } },
    yAxis: { type: 'value', name: '样本数' },
    series: [
      {
        name: '预测正确',
        type: 'bar',
        stack: 'result',
        data: correct,
        itemStyle: { color: '#67c23a' },
        label: { show: true, position: 'inside', fontSize: 12 },
      },
      {
        name: '预测错误',
        type: 'bar',
        stack: 'result',
        data: wrong,
        itemStyle: { color: '#f56c6c' },
        label: { show: true, position: 'inside', fontSize: 12, formatter: p => p.value > 0 ? p.value : '' },
      },
    ],
    grid: { top: 50, bottom: 30 },
  })
}
</script>

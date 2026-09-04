<template>
  <div>
    <h2 style="margin:0 0 20px;">总览仪表盘</h2>

    <!-- 统计卡片 -->
    <el-row :gutter="16" style="margin-bottom:20px;">
      <el-col :span="6" v-for="c in cards" :key="c.label">
        <el-card shadow="never" style="border-radius:10px;">
          <div style="display:flex;align-items:center;gap:12px;">
            <el-icon :size="36" :style="{color: c.color}"><component :is="c.icon" /></el-icon>
            <div>
              <div style="font-size:24px;font-weight:bold;">{{ c.value }}</div>
              <div style="font-size:13px;color:rgba(255,255,255,0.5);">{{ c.label }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <!-- 风险等级饼图 -->
      <el-col :span="12">
        <el-card shadow="never" style="border-radius:10px;">
          <template #header><b>风险等级分布</b></template>
          <div ref="pieRef" style="height:300px;"></div>
        </el-card>
      </el-col>
      <!-- 聚类分布 -->
      <el-col :span="12">
        <el-card shadow="never" style="border-radius:10px;">
          <template #header><b>用户聚类分布</b></template>
          <div ref="clusterRef" style="height:300px;"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { initChart } from '@/utils/chart'
import { getRiskSummary, getUsers, getClusterSummary } from '../api/index.js'

const pieRef = ref()
const clusterRef = ref()
const cards = ref([
  { label: '监测用户数', value: '-', icon: 'User', color: '#409eff' },
  { label: '高风险人次', value: '-', icon: 'Warning', color: '#f56c6c' },
  { label: '中风险人次', value: '-', icon: 'Bell', color: '#e6a23c' },
  { label: '低风险人次', value: '-', icon: 'CircleCheck', color: '#67c23a' },
])

onMounted(async () => {
  const [usersRes, riskRes, clusterRes] = await Promise.all([
    getUsers(), getRiskSummary(), getClusterSummary()
  ])

  cards.value[0].value = usersRes.data.length

  const riskMap = {}
  riskRes.data.forEach(r => { riskMap[r.risk_level] = r.count })
  cards.value[1].value = riskMap['高风险'] ?? 0
  cards.value[2].value = riskMap['中风险'] ?? 0
  cards.value[3].value = riskMap['低风险'] ?? 0

  // 饼图
  const pie = initChart(pieRef.value)
  pie.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c}次 ({d}%)' },
    legend: { bottom: 0 },
    color: ['#f56c6c', '#e6a23c', '#67c23a'],
    series: [{
      type: 'pie',
      radius: ['40%', '65%'],
      data: riskRes.data.map(r => ({ name: r.risk_level, value: r.count })),
      label: { formatter: '{b}\n{d}%' },
    }],
  })

  // 聚类柱图
  const cluster = initChart(clusterRef.value)
  const clusterData = clusterRes.data
  cluster.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: clusterData.map(c => c.cluster_label), axisLabel: { interval: 0 } },
    yAxis: { type: 'value', name: '平均压力分' },
    color: ['#409eff'],
    series: [{
      type: 'bar',
      data: clusterData.map(c => (+c.avg_stress).toFixed(1)),
      barWidth: '40%',
      label: { show: true, position: 'top' },
    }],
  })
})
</script>

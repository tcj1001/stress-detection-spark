<template>
  <div>
    <h2 style="margin:0 0 20px;">用户画像</h2>
    <el-row :gutter="16">
      <el-col :span="14">
        <el-card shadow="never" style="border-radius:10px;">
          <template #header><b>聚类雷达图</b></template>
          <div ref="radarRef" style="height:380px;"></div>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card shadow="never" style="border-radius:10px;">
          <template #header><b>用户列表</b></template>
          <el-table :data="profiles" size="small" stripe>
            <el-table-column prop="user_id" label="用户ID" width="120" />
            <el-table-column prop="cluster_label" label="类型" />
            <el-table-column prop="avg_stress_score" label="平均压力" />
            <el-table-column prop="risk_level" label="风险等级">
              <template #default="{ row }">
                <el-tag :type="riskTag(row.risk_level)" size="small">{{ row.risk_level }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { initChart } from '@/utils/chart'
import { getClusterSummary, getUserProfiles } from '../api/index.js'

const radarRef = ref()
const profiles = ref([])

function riskTag(level) {
  if (level === '高风险') return 'danger'
  if (level === '中风险') return 'warning'
  return 'success'
}

onMounted(async () => {
  const [clusterRes, profileRes] = await Promise.all([getClusterSummary(), getUserProfiles()])
  profiles.value = profileRes.data.results || profileRes.data

  const clusterData = clusterRes.data
  const chart = initChart(radarRef.value)
  chart.setOption({
    tooltip: {},
    legend: { data: clusterData.map(c => c.cluster_label), bottom: 0 },
    radar: {
      indicator: [
        { name: '平均压力分', max: 100 },
        { name: '睡眠效率', max: 1 },
        { name: '活动时长(分钟)', max: 200 },
        { name: '静息心率', max: 100 },
        { name: '久坐比例', max: 1 },
      ],
    },
    series: [{
      type: 'radar',
      data: clusterData.map(c => ({
        name: c.cluster_label,
        value: [
          +c.avg_stress,
          +c.avg_sleep,
          +c.avg_active,
          +c.avg_hr,
          +c.avg_sedentary,
        ],
      })),
    }],
  })
})
</script>

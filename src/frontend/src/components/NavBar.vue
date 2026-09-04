<template>
  <el-container class="glass-layout">
    <el-aside width="220px" class="glass-sidebar">
      <div class="sidebar-title">压力检测系统</div>
      <el-menu
        :default-active="$route.path"
        router
      >
        <el-menu-item index="/">
          <el-icon><DataAnalysis /></el-icon>
          <span>总览仪表盘</span>
        </el-menu-item>
        <el-menu-item index="/stress">
          <el-icon><TrendCharts /></el-icon>
          <span>每日压力分析</span>
        </el-menu-item>
        <el-menu-item index="/trend">
          <el-icon><Histogram /></el-icon>
          <span>趋势分析</span>
        </el-menu-item>
        <el-menu-item index="/correlation">
          <el-icon><Grid /></el-icon>
          <span>相关性分析</span>
        </el-menu-item>
        <el-menu-item index="/profile">
          <el-icon><User /></el-icon>
          <span>用户画像</span>
        </el-menu-item>
        <el-menu-item index="/hourly">
          <el-icon><Clock /></el-icon>
          <span>时段规律</span>
        </el-menu-item>
        <el-menu-item index="/model-comparison">
          <el-icon><DataLine /></el-icon>
          <span>模型性能对比</span>
        </el-menu-item>
        <el-menu-item v-if="isAdmin" index="/user-manage">
          <el-icon><Setting /></el-icon>
          <span>用户管理</span>
        </el-menu-item>
      </el-menu>
      <div class="logout-btn">
        <span style="font-size:13px;color:rgba(255,255,255,0.7);margin-right:10px;">{{ displayName }}</span>
        <el-button type="danger" link @click="logout">
          <el-icon><SwitchButton /></el-icon> 退出登录
        </el-button>
      </div>
    </el-aside>
    <el-main class="glass-main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
const router = useRouter()
const isAdmin = computed(() => localStorage.getItem('role') === 'ADMIN')
const displayName = computed(() => localStorage.getItem('nickname') || localStorage.getItem('username') || '')
function logout() {
  localStorage.removeItem('token')
  localStorage.removeItem('username')
  localStorage.removeItem('nickname')
  localStorage.removeItem('role')
  router.push('/login')
}
</script>

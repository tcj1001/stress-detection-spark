<template>
  <div class="glass-auth-wrap">
    <el-card class="glass-auth-card">
      <div style="text-align:center;margin-bottom:28px;">
        <h2>注册账号</h2>
      </div>
      <el-form :model="form" :rules="rules" ref="formRef">
        <el-form-item prop="nickname">
          <el-input v-model="form.nickname" placeholder="用户名" :prefix-icon="User" size="large" />
        </el-form-item>
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="账号（3-50位，用于登录）" :prefix-icon="Postcard" size="large" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" placeholder="密码（至少6位）" :prefix-icon="Lock" size="large" show-password />
        </el-form-item>
        <el-button type="primary" style="width:100%;" size="large" :loading="loading" @click="onRegister">
          注册
        </el-button>
      </el-form>
      <div style="text-align:center;margin-top:18px;font-size:14px;">
        已有账号？<el-link type="primary" @click="$router.push('/login')">返回登录</el-link>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock, Postcard } from '@element-plus/icons-vue'
import { register } from '../api/index.js'

const router = useRouter()
const formRef = ref()
const loading = ref(false)
const form = ref({ nickname: '', username: '', password: '' })
const rules = {
  nickname: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  username: [{ required: true, min: 3, message: '账号至少3位', trigger: 'blur' }],
  password: [{ required: true, min: 6, message: '密码至少6位', trigger: 'blur' }],
}

async function onRegister() {
  await formRef.value.validate()
  loading.value = true
  try {
    await register(form.value)
    ElMessage.success('注册成功，请登录')
    router.push('/login')
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '注册失败')
  } finally {
    loading.value = false
  }
}
</script>

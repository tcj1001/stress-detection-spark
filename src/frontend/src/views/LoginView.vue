<template>
  <div class="glass-auth-wrap">
    <el-card class="glass-auth-card">
      <div style="text-align:center;margin-bottom:28px;">
        <h2>压力检测数据分析系统</h2>
        <p style="margin:10px 0 0;font-size:14px;">用户登录</p>
      </div>
      <el-form :model="form" :rules="rules" ref="formRef" @submit.prevent="onLogin">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="账号" :prefix-icon="User" size="large" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" placeholder="密码" :prefix-icon="Lock" size="large" show-password />
        </el-form-item>
        <el-button type="primary" style="width:100%;" size="large" :loading="loading" @click="onLogin">
          登录
        </el-button>
      </el-form>
      <div style="display:flex;justify-content:space-between;margin-top:18px;font-size:14px;">
        <el-link type="info" @click="showChangePwd = true">修改密码</el-link>
        <span>没有账号？<el-link type="primary" @click="$router.push('/register')">立即注册</el-link></span>
      </div>
    </el-card>

    <el-dialog v-model="showChangePwd" title="修改密码" width="400px" :close-on-click-modal="false">
      <el-form :model="pwdForm" :rules="pwdRules" ref="pwdFormRef" label-width="80px">
        <el-form-item label="账号" prop="username">
          <el-input v-model="pwdForm.username" placeholder="请输入账号" />
        </el-form-item>
        <el-form-item label="原密码" prop="oldPassword">
          <el-input v-model="pwdForm.oldPassword" type="password" placeholder="请输入原密码" show-password />
        </el-form-item>
        <el-form-item label="新密码" prop="newPassword">
          <el-input v-model="pwdForm.newPassword" type="password" placeholder="新密码至少6位" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showChangePwd = false">取消</el-button>
        <el-button type="primary" :loading="pwdLoading" @click="onChangePwd">确认修改</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { login, changePassword } from '../api/index.js'

const router = useRouter()
const formRef = ref()
const loading = ref(false)
const form = ref({ username: '', password: '' })
const rules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function onLogin() {
  await formRef.value.validate()
  loading.value = true
  try {
    const res = await login(form.value)
    const { token, username, nickname, role } = res.data.data
    localStorage.setItem('token', token)
    localStorage.setItem('username', username)
    localStorage.setItem('nickname', nickname || username)
    localStorage.setItem('role', role)
    ElMessage.success('登录成功')
    router.push('/')
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '登录失败')
  } finally {
    loading.value = false
  }
}

const showChangePwd = ref(false)
const pwdLoading = ref(false)
const pwdFormRef = ref()
const pwdForm = ref({ username: '', oldPassword: '', newPassword: '' })
const pwdRules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  oldPassword: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  newPassword: [{ required: true, message: '请输入新密码', trigger: 'blur' }, { min: 6, message: '新密码至少6位', trigger: 'blur' }],
}

async function onChangePwd() {
  await pwdFormRef.value.validate()
  pwdLoading.value = true
  try {
    await changePassword(pwdForm.value)
    ElMessage.success('密码修改成功，请重新登录')
    showChangePwd.value = false
    pwdForm.value = { username: '', oldPassword: '', newPassword: '' }
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '修改失败')
  } finally {
    pwdLoading.value = false
  }
}
</script>

<template>
  <div>
    <h2 style="margin-top:0;">用户管理</h2>

    <el-card>
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
        <el-input
          v-model="keyword"
          placeholder="搜索账号或用户名"
          :prefix-icon="Search"
          style="width:280px;"
          clearable
          @clear="loadUsers"
          @keyup.enter="loadUsers"
        />
        <el-button type="primary" @click="showAddDialog">添加用户</el-button>
      </div>

      <el-table :data="users" stripe style="width:100%;">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="nickname" label="用户名" min-width="120" />
        <el-table-column prop="username" label="账号" min-width="120" />
        <el-table-column prop="role" label="角色" width="100">
          <template #default="{ row }">
            <el-tag :type="row.role === 'ADMIN' ? 'danger' : 'info'" size="small">
              {{ row.role === 'ADMIN' ? '管理员' : '普通用户' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" label="注册时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.createdAt) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="warning" link @click="showPwdDialog(row)" :disabled="row.role === 'ADMIN'">
              修改密码
            </el-button>
            <el-button size="small" type="danger" link @click="handleDelete(row)" :disabled="row.role === 'ADMIN'">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div style="display:flex;justify-content:flex-end;margin-top:16px;">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="loadUsers"
        />
      </div>
    </el-card>

    <el-dialog v-model="addVisible" title="添加用户" width="420px" :close-on-click-modal="false">
      <el-form :model="addForm" :rules="addRules" ref="addFormRef" label-width="80px">
        <el-form-item label="用户名" prop="nickname">
          <el-input v-model="addForm.nickname" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="账号" prop="username">
          <el-input v-model="addForm.username" placeholder="请输入账号（3-50位）" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="addForm.password" type="password" placeholder="请输入密码（至少6位）" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addVisible = false">取消</el-button>
        <el-button type="primary" :loading="addLoading" @click="handleAdd">确认添加</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="pwdVisible" title="修改密码" width="420px" :close-on-click-modal="false">
      <el-form :model="pwdForm" :rules="pwdRules" ref="pwdFormRef" label-width="80px">
        <el-form-item label="账号">
          <el-input :model-value="pwdForm.username" disabled />
        </el-form-item>
        <el-form-item label="新密码" prop="newPassword">
          <el-input v-model="pwdForm.newPassword" type="password" placeholder="请输入新密码（至少6位）" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pwdVisible = false">取消</el-button>
        <el-button type="primary" :loading="pwdLoading" @click="handleChangePwd">确认修改</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { getAdminUsers, adminCreateUser, adminChangePassword, adminDeleteUser } from '../api/index.js'

const keyword = ref('')
const users = ref([])
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

function formatDate(dt) {
  if (!dt) return ''
  if (Array.isArray(dt)) {
    const [y, m, d, h, min, s] = dt
    return `${y}-${String(m).padStart(2,'0')}-${String(d).padStart(2,'0')} ${String(h||0).padStart(2,'0')}:${String(min||0).padStart(2,'0')}:${String(s||0).padStart(2,'0')}`
  }
  return String(dt).replace('T', ' ').substring(0, 19)
}

async function loadUsers() {
  try {
    const res = await getAdminUsers(currentPage.value - 1, pageSize.value, keyword.value)
    const page = res.data.data
    users.value = page.content || []
    total.value = page.totalElements || 0
  } catch (e) {
    ElMessage.error('加载用户列表失败')
  }
}

onMounted(loadUsers)

const addVisible = ref(false)
const addLoading = ref(false)
const addFormRef = ref()
const addForm = ref({ nickname: '', username: '', password: '' })
const addRules = {
  nickname: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  username: [{ required: true, min: 3, message: '账号至少3位', trigger: 'blur' }],
  password: [{ required: true, min: 6, message: '密码至少6位', trigger: 'blur' }],
}

function showAddDialog() {
  addForm.value = { nickname: '', username: '', password: '' }
  addVisible.value = true
}

async function handleAdd() {
  await addFormRef.value.validate()
  addLoading.value = true
  try {
    const res = await adminCreateUser(addForm.value)
    if (res.data.code === 200) {
      ElMessage.success('添加成功')
      addVisible.value = false
      loadUsers()
    } else {
      ElMessage.error(res.data.message)
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '添加失败')
  } finally {
    addLoading.value = false
  }
}

const pwdVisible = ref(false)
const pwdLoading = ref(false)
const pwdFormRef = ref()
const pwdForm = ref({ id: null, username: '', newPassword: '' })
const pwdRules = {
  newPassword: [{ required: true, min: 6, message: '新密码至少6位', trigger: 'blur' }],
}

function showPwdDialog(row) {
  pwdForm.value = { id: row.id, username: row.username, newPassword: '' }
  pwdVisible.value = true
}

async function handleChangePwd() {
  await pwdFormRef.value.validate()
  pwdLoading.value = true
  try {
    await adminChangePassword(pwdForm.value.id, pwdForm.value.newPassword)
    ElMessage.success('密码修改成功')
    pwdVisible.value = false
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '修改失败')
  } finally {
    pwdLoading.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除用户「${row.nickname || row.username}」吗？`, '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    const res = await adminDeleteUser(row.id)
    if (res.data.code === 200) {
      ElMessage.success('删除成功')
      loadUsers()
    } else {
      ElMessage.error(res.data.message)
    }
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.message || '删除失败')
  }
}
</script>

import axios from 'axios'

const djangoApi = axios.create({
  baseURL: import.meta.env.VITE_DJANGO_API_URL || 'http://127.0.0.1:8000/api',
  timeout: 10000,
})

djangoApi.interceptors.response.use(res => {
  res.data = JSON.parse(JSON.stringify(res.data).replace(/2016-/g, '2026-'))
  return res
})

const springApi = axios.create({
  baseURL: import.meta.env.VITE_SPRING_API_URL || 'http://127.0.0.1:8080/api',
  timeout: 10000,
})

springApi.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// 数据分析接口（Django）
export const getUsers = () => djangoApi.get('/stress/users/')
export const getRiskSummary = () => djangoApi.get('/stress/risk-summary/')
export const getStressChart = (userId) => djangoApi.get('/stress/chart/', { params: { user_id: userId } })
export const getStressList = (userId) => djangoApi.get('/stress/', { params: { user_id: userId, page_size: 100 } })
export const getTrendChart = (userId) => djangoApi.get('/trend/chart/', { params: { user_id: userId } })
export const getTrendForecast = (userId) => djangoApi.get('/trend/forecast/', { params: { user_id: userId } })
export const getCorrelationHeatmap = () => djangoApi.get('/correlation/heatmap/')
export const getClusterSummary = () => djangoApi.get('/profile/cluster-summary/')
export const getUserProfiles = () => djangoApi.get('/profile/')
export const getHourlyUsers = () => djangoApi.get('/hourly/users/')
export const getHourlyChart = (userId) => djangoApi.get('/hourly/chart/', { params: { user_id: userId } })
export const getPredictionUsers = () => djangoApi.get('/stress/prediction-users/')
export const getPrediction = (userId) => djangoApi.get('/stress/prediction/', { params: { user_id: userId } })

// ML模型对比接口（Django）
export const getModelMetrics = () => djangoApi.get('/model/metrics/')
export const getModelLearningCurve = () => djangoApi.get('/model/learning-curve/')
export const getModelFeatureImportance = () => djangoApi.get('/model/feature-importance/')
export const getModelConfusionMatrix = () => djangoApi.get('/model/confusion-matrix/')

// 用户管理接口（Spring Boot）
export const register = (data) => springApi.post('/auth/register', data)
export const login = (data) => springApi.post('/auth/login', data)
export const changePassword = (data) => springApi.put('/auth/change-password', data)
export const getAdminUsers = (page = 0, size = 10, keyword = '') =>
  springApi.get('/admin/users', { params: { page, size, keyword: keyword || undefined } })
export const adminCreateUser = (data) => springApi.post('/admin/users', data)
export const adminChangePassword = (id, newPassword) =>
  springApi.put(`/admin/users/${id}/password`, { newPassword })
export const adminDeleteUser = (id) => springApi.delete(`/admin/users/${id}`)

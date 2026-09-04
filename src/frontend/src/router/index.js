import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/login', component: () => import('../views/LoginView.vue'), meta: { public: true } },
    { path: '/register', component: () => import('../views/RegisterView.vue'), meta: { public: true } },
    {
      path: '/',
      component: () => import('../components/NavBar.vue'),
      children: [
        { path: '', component: () => import('../views/DashboardView.vue') },
        { path: 'stress', component: () => import('../views/StressView.vue') },
        { path: 'trend', component: () => import('../views/TrendView.vue') },
        { path: 'correlation', component: () => import('../views/CorrelationView.vue') },
        { path: 'profile', component: () => import('../views/ProfileView.vue') },
        { path: 'hourly', component: () => import('../views/HourlyView.vue') },
        { path: 'model-comparison', component: () => import('../views/ModelComparisonView.vue') },
        { path: 'user-manage', component: () => import('../views/UserManageView.vue'), meta: { admin: true } },
      ],
    },
  ],
})

router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  if (!to.meta.public && !token) return '/login'
  if (to.meta.admin && localStorage.getItem('role') !== 'ADMIN') return '/'
})

export default router

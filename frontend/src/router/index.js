import { createRouter, createWebHistory } from 'vue-router'
import Layout from '@/components/Layout.vue'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { public: true, title: '登录' },
  },
  {
    path: '/',
    component: Layout,
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: '综合看板', icon: 'Odometer' },
      },
      {
        path: 'granaries',
        name: 'Granaries',
        component: () => import('@/views/Granaries.vue'),
        meta: { title: '仓房管理', icon: 'House' },
      },
      {
        path: 'batches',
        name: 'Batches',
        component: () => import('@/views/Batches.vue'),
        meta: { title: '库存粮情', icon: 'Wheat' },
      },
      {
        path: 'monitors',
        name: 'Monitors',
        component: () => import('@/views/Monitors.vue'),
        meta: { title: '温湿度监测', icon: 'Sunny' },
      },
      {
        path: 'stock-records',
        name: 'StockRecords',
        component: () => import('@/views/StockRecords.vue'),
        meta: { title: '出入库记录', icon: 'Switch' },
      },
      {
        path: 'fumigations',
        name: 'Fumigations',
        component: () => import('@/views/Fumigations.vue'),
        meta: { title: '熏蒸作业', icon: 'MagicStick' },
      },
      {
        path: 'stocktakes',
        name: 'Stocktakes',
        component: () => import('@/views/Stocktakes.vue'),
        meta: { title: '库存盘点', icon: 'DocumentChecked' },
      },
      {
        path: 'operation-logs',
        name: 'OperationLogs',
        component: () => import('@/views/OperationLogs.vue'),
        meta: { title: '操作日志', icon: 'List', manager: true },
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('@/views/Users.vue'),
        meta: { title: '账号岗位', icon: 'UserFilled', manager: true },
      },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.public) {
    if (auth.isLoggedIn && to.name === 'Login') return '/dashboard'
    return true
  }
  if (!auth.isLoggedIn) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.meta.manager && !auth.isManager) {
    return { path: '/dashboard' }
  }
  return true
})

export default router

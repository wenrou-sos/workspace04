import { createRouter, createWebHistory } from 'vue-router'
import Layout from '@/components/Layout.vue'

const routes = [
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
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router

import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

// 请求自动携带登录令牌
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('gd_token')
  if (token) config.headers.Authorization = `Token ${token}`
  return config
})

api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const resp = error.response
    let msg = '网络异常，请检查后端服务是否启动（http://localhost:8000）'
    if (resp) {
      const contentType = resp.headers?.['content-type'] || ''
      if (resp.status === 401) {
        msg = '登录已失效，请重新登录'
        localStorage.removeItem('gd_token')
        localStorage.removeItem('gd_user')
        // 避免在登录页重复跳转
        if (!location.hash.startsWith('#/login') && location.pathname !== '/login') {
          location.href = '/login'
        }
      } else if (resp.status === 403) {
        if (contentType.includes('application/json')) {
          msg = resp.data?.detail || '当前岗位无权执行该操作'
        } else {
          msg = '当前岗位无权执行该操作（403）'
        }
      } else if (contentType.includes('application/json')) {
        const detail = resp.data
        if (typeof detail === 'string') msg = detail
        else if (detail.detail) msg = detail.detail
        else if (Array.isArray(detail) && detail[0]) msg = String(detail[0])
        else msg = Object.entries(detail).map(([k, v]) => `${k}: ${v}`).join('；')
      } else if (resp.status >= 500) {
        msg = `服务器内部错误（${resp.status}），请查看后端日志 /tmp/django.log`
      } else {
        msg = `请求失败（HTTP ${resp.status}）`
      }
    } else if (error.code === 'ERR_NETWORK') {
      msg = '无法连接后端（:8000），请先启动 Django 服务'
    }
    ElMessage.error(msg)
    return Promise.reject(error)
  }
)

export default api

// ---- 仓房 ----
export const granaryApi = {
  list: (params) => api.get('/granaries/', { params }),
  retrieve: (id) => api.get(`/granaries/${id}/`),
  create: (data) => api.post('/granaries/', data),
  update: (id, data) => api.put(`/granaries/${id}/`, data),
  patch: (id, data) => api.patch(`/granaries/${id}/`, data),
  remove: (id) => api.delete(`/granaries/${id}/`),
  tempSeries: (id) => api.get(`/granaries/${id}/temperature_series/`),
}

// ---- 库存批次 ----
export const batchApi = {
  list: (params) => api.get('/batches/', { params }),
  create: (data) => api.post('/batches/', data),
  update: (id, data) => api.put(`/batches/${id}/`, data),
  remove: (id) => api.delete(`/batches/${id}/`),
}

// ---- 温湿度监测 ----
export const monitorApi = {
  list: (params) => api.get('/monitors/', { params }),
  create: (data) => api.post('/monitors/', data),
  remove: (id) => api.delete(`/monitors/${id}/`),
  latest: () => api.get('/monitors/latest/'),
}

// ---- 出入库 ----
export const stockApi = {
  list: (params) => api.get('/stock-records/', { params }),
  create: (data) => api.post('/stock-records/', data),
  update: (id, data) => api.put(`/stock-records/${id}/`, data),
  remove: (id) => api.delete(`/stock-records/${id}/`),
  void: (id, reason) => api.post(`/stock-records/${id}/void/`, { reason }),
}

// ---- 熏蒸 ----
export const fumigationApi = {
  list: (params) => api.get('/fumigations/', { params }),
  create: (data) => api.post('/fumigations/', data),
  update: (id, data) => api.put(`/fumigations/${id}/`, data),
  remove: (id) => api.delete(`/fumigations/${id}/`),
  advance: (id) => api.post(`/fumigations/${id}/advance/`),
}

// ---- 盘点 ----
export const stocktakeApi = {
  list: (params) => api.get('/stocktakes/', { params }),
  retrieve: (id) => api.get(`/stocktakes/${id}/`),
  create: (data) => api.post('/stocktakes/', data),
  update: (id, data) => api.put(`/stocktakes/${id}/`, data),
  remove: (id) => api.delete(`/stocktakes/${id}/`),
  generateItems: (id) => api.post(`/stocktakes/${id}/generate_items/`),
  finish: (id) => api.post(`/stocktakes/${id}/finish/`),
}

export const stocktakeItemApi = {
  list: (params) => api.get('/stocktake-items/', { params }),
  update: (id, data) => api.patch(`/stocktake-items/${id}/`, data),
}

// ---- 仪表盘 ----
export const dashboardApi = {
  summary: () => api.get('/dashboard/'),
  trend: () => api.get('/dashboard/trend/'),
  tempMonitor: () => api.get('/dashboard/temp_monitor/'),
}

// ---- 当前身份 / 操作日志 / 账号岗位 ----
export const authApi = {
  me: () => api.get('/auth/me/'),
}

export const operationLogApi = {
  list: (params) => api.get('/operation-logs/', { params }),
}

export const userApi = {
  list: (params) => api.get('/users/', { params }),
  retrieve: (id) => api.get(`/users/${id}/`),
  create: (data) => api.post('/users/', data),
  update: (id, data) => api.put(`/users/${id}/`, data),
  patch: (id, data) => api.patch(`/users/${id}/`, data),
  remove: (id) => api.delete(`/users/${id}/`),
}

import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const detail = error.response?.data
    let msg = '请求失败'
    if (detail) {
      if (typeof detail === 'string') msg = detail
      else if (detail.detail) msg = detail.detail
      else if (Array.isArray(detail) && detail[0]) msg = String(detail[0])
      else msg = Object.entries(detail).map(([k, v]) => `${k}: ${v}`).join('；')
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

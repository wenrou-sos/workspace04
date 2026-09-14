import { defineStore } from 'pinia'
import axios from 'axios'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('gd_token') || '',
    user: JSON.parse(localStorage.getItem('gd_user') || 'null'),
  }),
  getters: {
    isLoggedIn: (s) => !!s.token,
    role: (s) => s.user?.role || '',
    isManager: (s) => !!s.user?.is_manager,
    isKeeper: (s) => s.user?.role === 'keeper',
    isViewer: (s) => s.user?.role === 'viewer',
    displayName: (s) => s.user?.name || s.user?.username || '',
  },
  actions: {
    /** 是否可在界面上执行写操作（viewer 只读） */
    canWrite() {
      return ['admin', 'director', 'keeper'].includes(this.user?.role)
    },
    /** 是否可安排熏蒸（仅主任/管理员） */
    canArrangeFumigation() {
      return this.isManager
    },
    /** 是否可盘点调账 / 删除（仅主任/管理员） */
    canApproveOrDelete() {
      return this.isManager
    },
    /** 仓房是否在当前用户管辖范围内（主任/管理员/只读为全部） */
    canAccessGranary(gid) {
      if (this.isManager || this.user?.role === 'viewer') return true
      return (this.user?.granary_ids || []).includes(gid)
    },
    async login(username, password) {
      const { data } = await axios.post('/api/auth/login/', { username, password })
      this.token = data.token
      this.user = data.user
      localStorage.setItem('gd_token', data.token)
      localStorage.setItem('gd_user', JSON.stringify(data.user))
      return data.user
    },
    async logout() {
      try {
        await axios.post('/api/auth/logout/', {}, {
          headers: { Authorization: `Token ${this.token}` },
        })
      } catch (e) {
        // 即使后端注销失败也清理本地凭证
      }
      this.clear()
    },
    clear() {
      this.token = ''
      this.user = null
      localStorage.removeItem('gd_token')
      localStorage.removeItem('gd_user')
    },
  },
})

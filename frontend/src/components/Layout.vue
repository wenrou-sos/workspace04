<template>
  <el-container class="app-wrapper">
    <el-aside width="230px" class="sidebar">
      <div class="logo">
        <el-icon :size="26"><Wheat /></el-icon>
        <div>
          <div class="logo-title">智慧粮库</div>
          <div class="logo-sub">粮食储备库管理系统</div>
        </div>
      </div>
      <el-menu
        :default-active="$route.path"
        router
        background-color="#20322b"
        text-color="#c4d3cb"
        active-text-color="#f5c542"
      >
        <template v-for="item in visibleMenus" :key="item.path">
          <el-menu-item :index="item.path">
            <el-icon><component :is="item.icon" /></el-icon>
            <span>{{ item.title }}</span>
          </el-menu-item>
        </template>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-title">{{ $route.meta.title }}</div>
        <div class="header-right">
          <el-icon><Location /></el-icon>
          <span class="depot-name">中央储备粮 XX 直属库</span>
          <el-divider direction="vertical" />
          <el-tag size="small" :type="roleTagType" effect="dark">{{ auth.user?.role_display }}</el-tag>
          <el-avatar :size="30" style="background: #b8860b">{{ auth.displayName.slice(0, 1) }}</el-avatar>
          <el-dropdown @command="onCommand">
            <span class="user-name">
              {{ auth.displayName }}
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout" :icon="SwitchButton">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { SwitchButton } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

const allMenus = [
  { path: '/dashboard', title: '综合看板', icon: 'Odometer' },
  { path: '/granaries', title: '仓房管理', icon: 'House' },
  { path: '/batches', title: '库存粮情', icon: 'Wheat' },
  { path: '/monitors', title: '温湿度监测', icon: 'Sunny' },
  { path: '/stock-records', title: '出入库记录', icon: 'Switch' },
  { path: '/fumigations', title: '熏蒸作业', icon: 'MagicStick' },
  { path: '/stocktakes', title: '库存盘点', icon: 'DocumentChecked' },
  { path: '/operation-logs', title: '操作日志', icon: 'List', manager: true },
  { path: '/users', title: '账号岗位', icon: 'UserFilled', manager: true },
]
const visibleMenus = computed(() =>
  allMenus.filter((m) => !m.manager || auth.isManager)
)

const roleTagType = computed(() => {
  return { admin: 'danger', director: 'warning', keeper: 'success', viewer: 'info' }[auth.role] || 'info'
})

async function onCommand(cmd) {
  if (cmd === 'logout') {
    await ElMessageBox.confirm('确认退出登录？', '提示', { type: 'warning' })
    await auth.logout()
    router.replace('/login')
  }
}
</script>

<style scoped>
.app-wrapper {
  height: 100vh;
}

.sidebar {
  background: #20322b;
  overflow-x: hidden;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 18px 16px;
  color: #f5c542;
}

.logo-title {
  font-size: 18px;
  font-weight: 700;
  color: #fff;
  white-space: nowrap;
}

.logo-sub {
  font-size: 11px;
  color: #9fb8ac;
  white-space: nowrap;
}

:deep(.el-menu) {
  border-right: none;
}

.header {
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
}

.header-title {
  font-size: 17px;
  font-weight: 600;
  color: #1f2d3d;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #5a6b62;
  font-size: 14px;
}

.depot-name {
  color: #5a6b62;
}

.user-name {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  color: #1f2d3d;
  outline: none;
}

.main-content {
  background: #f0f2f5;
  padding: 20px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>

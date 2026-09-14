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
        <el-menu-item
          v-for="item in menus"
          :key="item.path"
          :index="item.path"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.title }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-title">{{ $route.meta.title }}</div>
        <div class="header-right">
          <el-icon><Location /></el-icon>
          <span>中央储备粮 XX 直属库</span>
          <el-divider direction="vertical" />
          <el-avatar :size="30" style="background: #b8860b">管</el-avatar>
          <span>库管员</span>
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
const menus = [
  { path: '/dashboard', title: '综合看板', icon: 'Odometer' },
  { path: '/granaries', title: '仓房管理', icon: 'House' },
  { path: '/batches', title: '库存粮情', icon: 'Wheat' },
  { path: '/monitors', title: '温湿度监测', icon: 'Sunny' },
  { path: '/stock-records', title: '出入库记录', icon: 'Switch' },
  { path: '/fumigations', title: '熏蒸作业', icon: 'MagicStick' },
  { path: '/stocktakes', title: '库存盘点', icon: 'DocumentChecked' },
]
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

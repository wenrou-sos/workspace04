<template>
  <router-view />
</template>

<script setup></script>

<style>
html,
body,
#app {
  height: 100%;
  margin: 0;
}

body {
  font-family:
    'PingFang SC', 'Microsoft YaHei', 'Helvetica Neue', Arial, sans-serif;
  background: #f0f2f5;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #1f2d3d;
}

.filter-bar {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 14px;
  align-items: center;
}

.stat-number {
  font-size: 26px;
  font-weight: 700;
  color: #b8860b;
}
</style>

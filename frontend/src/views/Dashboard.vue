<template>
  <div class="dashboard" v-loading="loading">
    <!-- 顶部指标卡 -->
    <el-row :gutter="16">
      <el-col :span="6" v-for="card in cards" :key="card.label">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-inner">
            <el-icon :size="40" :color="card.color">
              <component :is="card.icon" />
            </el-icon>
            <div>
              <div class="stat-label">{{ card.label }}</div>
              <div class="stat-number">{{ card.value }}</div>
              <div class="stat-extra">{{ card.extra }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :span="16">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>近 7 日出入库趋势（吨）</span>
            </div>
          </template>
          <div ref="trendChart" style="height: 320px"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header"><span>库存品种结构</span></div>
          </template>
          <div ref="pieChart" style="height: 320px"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :span="14">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>各仓实时粮情</span>
              <el-tag size="small" type="info">每仓最新检测值</el-tag>
            </div>
          </template>
          <el-table :data="monitor.granaries" size="small" stripe height="300">
            <el-table-column prop="granary_code" label="仓号" width="70" />
            <el-table-column prop="granary_name" label="仓名" min-width="110" />
            <el-table-column label="平均粮温" width="95">
              <template #default="{ row }">
                <span :class="tempClass(row.avg_temp)">{{ fmt(row.avg_temp) }}℃</span>
              </template>
            </el-table-column>
            <el-table-column label="最高粮温" width="95">
              <template #default="{ row }">
                <span :class="tempClass(row.max_temp)">{{ fmt(row.max_temp) }}℃</span>
              </template>
            </el-table-column>
            <el-table-column label="湿度" width="80">
              <template #default="{ row }">{{ fmt(row.humidity) }}%</template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag size="small" :type="findType(GRANARY_STATUS, row.status)">
                  {{ findLabel(GRANARY_STATUS, row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="告警" width="80">
              <template #default="{ row }">
                <el-tag
                  v-if="row.alert_level && row.alert_level !== 'normal'"
                  size="small"
                  :type="findType(ALERT_LEVEL, row.alert_level)"
                >
                  {{ findLabel(ALERT_LEVEL, row.alert_level) }}
                </el-tag>
                <el-tag v-else size="small" type="success">正常</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>近 12 小时温湿度预警</span>
              <el-badge :value="monitor.alerts.length" :hidden="!monitor.alerts.length" type="danger" />
            </div>
          </template>
          <el-scrollbar height="300px">
            <el-timeline v-if="monitor.alerts.length">
              <el-timeline-item
                v-for="(a, i) in monitor.alerts"
                :key="i"
                :type="a.level === 'critical' ? 'danger' : 'warning'"
                :timestamp="`${a.granary} · ${a.time}`"
              >
                <div>
                  <el-tag size="small" :type="findType(ALERT_LEVEL, a.level)">
                    {{ findLabel(ALERT_LEVEL, a.level) }}
                  </el-tag>
                  平均粮温 {{ a.avg_temp }}℃ / 最高 {{ a.max_temp }}℃ / 湿度 {{ a.humidity }}%
                </div>
                <div v-if="a.note" class="alert-note">{{ a.note }}</div>
              </el-timeline-item>
            </el-timeline>
            <el-empty v-else description="近 12 小时无预警" :image-size="80" />
          </el-scrollbar>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, ref, nextTick } from 'vue'
import * as echarts from 'echarts'
import { dashboardApi } from '@/api'
import { ALERT_LEVEL, GRANARY_STATUS, findLabel, findType } from '@/utils/constants'

const loading = ref(true)
const summary = ref({})
const trendData = ref({ days: [], inbound: [], outbound: [] })
const monitor = ref({ granaries: [], alerts: [] })

const cards = computed(() => [
  {
    label: '在储粮食总量',
    value: `${summary.value.total_stock ?? '-'} 吨`,
    extra: `总仓容 ${summary.value.total_capacity ?? '-'} 吨`,
    icon: 'Wheat',
    color: '#b8860b',
  },
  {
    label: '平均仓容利用率',
    value: `${summary.value.utilization ?? '-'} %`,
    extra: `${summary.value.granary_count ?? 0} 栋仓房`,
    icon: 'DataAnalysis',
    color: '#2f8f6b',
  },
  {
    label: '近 7 日入 / 出库',
    value: `${summary.value.week_inbound ?? 0} / ${summary.value.week_outbound ?? 0} 吨`,
    extra: '收购与轮换动态',
    icon: 'Switch',
    color: '#3b7dd8',
  },
  {
    label: '进行中熏蒸作业',
    value: `${summary.value.active_fumigations ?? 0} 项`,
    extra: `温湿度预警 ${summary.value.warning_count ?? 0} 条`,
    icon: 'MagicStick',
    color: '#d46b08',
  },
])

const trendChart = ref(null)
const pieChart = ref(null)
let chartInstances = []

function tempClass(v) {
  if (v == null) return ''
  if (v >= 28) return 'temp-critical'
  if (v >= 25) return 'temp-warning'
  return 'temp-normal'
}
function fmt(v) {
  return v == null ? '--' : Number(v).toFixed(1)
}

function renderTrend() {
  const chart = echarts.init(trendChart.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['入库', '出库'], right: 0 },
    grid: { left: 50, right: 20, top: 40, bottom: 30 },
    xAxis: { type: 'category', data: trendData.value.days },
    yAxis: { type: 'value', name: '吨' },
    series: [
      {
        name: '入库',
        type: 'bar',
        data: trendData.value.inbound,
        itemStyle: { color: '#2f8f6b' },
        barMaxWidth: 26,
      },
      {
        name: '出库',
        type: 'bar',
        data: trendData.value.outbound,
        itemStyle: { color: '#d48806' },
        barMaxWidth: 26,
      },
    ],
  })
  chartInstances.push(chart)
}

function renderPie() {
  const data = Object.entries(summary.value.stock_by_kind || {}).map(([name, value]) => ({
    name,
    value,
  }))
  const chart = echarts.init(pieChart.value)
  chart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} 吨 ({d}%)' },
    legend: { bottom: 0 },
    color: ['#d4a017', '#e6b422', '#7cb342', '#8d6e63', '#558b2f'],
    series: [
      {
        type: 'pie',
        radius: ['42%', '68%'],
        center: ['50%', '45%'],
        label: { formatter: '{b}\n{d}%' },
        data,
      },
    ],
  })
  chartInstances.push(chart)
}

function onResize() {
  chartInstances.forEach((c) => c.resize())
}

onMounted(async () => {
  const [s, t, m] = await Promise.all([
    dashboardApi.summary(),
    dashboardApi.trend(),
    dashboardApi.tempMonitor(),
  ])
  summary.value = s
  trendData.value = t
  monitor.value = m
  loading.value = false
  await nextTick()
  renderTrend()
  renderPie()
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  chartInstances.forEach((c) => c.dispose())
})
</script>

<style scoped>
.stat-card {
  border-top: 3px solid #b8860b;
}

.stat-inner {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-label {
  color: #7a8a82;
  font-size: 13px;
}

.stat-number {
  font-size: 24px;
  font-weight: 700;
  color: #1f2d3d;
  margin: 4px 0;
}

.stat-extra {
  font-size: 12px;
  color: #9aa7a1;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
}

.alert-note {
  color: #909399;
  font-size: 12px;
  margin-top: 2px;
}

.temp-normal {
  color: #2f8f6b;
}
.temp-warning {
  color: #d48806;
  font-weight: 600;
}
.temp-critical {
  color: #cf1322;
  font-weight: 700;
}
</style>

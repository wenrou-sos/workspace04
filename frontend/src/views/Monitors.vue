<template>
  <div>
    <div class="page-header">
      <h2>温湿度监测</h2>
      <el-button type="primary" :icon="Plus" @click="openDialog()">录入检测记录</el-button>
    </div>

    <el-row :gutter="12" class="mb16">
      <el-col :span="6" v-for="stat in stats" :key="stat.label">
        <el-card shadow="hover" body-style="padding: 14px">
          <div class="mini-stat">
            <span>{{ stat.label }}</span>
            <strong :style="{ color: stat.color }">{{ stat.value }}</strong>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="mb16">
      <template #header>
        <div class="card-header">
          <span>粮温趋势对比（近 7 天，按日均值）</span>
          <el-radio-group v-model="chartMetric" size="small">
            <el-radio-button value="avg_temp">平均粮温</el-radio-button>
            <el-radio-button value="humidity">相对湿度</el-radio-button>
          </el-radio-group>
        </div>
      </template>
      <div ref="chartRef" style="height: 330px"></div>
    </el-card>

    <el-card>
      <div class="filter-bar">
        <el-select v-model="filters.granary" placeholder="仓房" clearable style="width: 160px">
          <el-option v-for="g in granaries" :key="g.id" :label="g.code" :value="g.id" />
        </el-select>
        <el-select v-model="filters.alert_level" placeholder="告警级别" clearable style="width: 130px">
          <el-option v-for="a in ALERT_LEVEL" :key="a.value" :label="a.label" :value="a.value" />
        </el-select>
        <el-date-picker
          v-model="dateRange"
          type="datetimerange"
          range-separator="至"
          start-placeholder="开始时间"
          end-placeholder="结束时间"
          value-format="YYYY-MM-DDTHH:mm:ss"
          style="width: 340px"
        />
        <el-button type="primary" :icon="Search" @click="loadData">查询</el-button>
      </div>

      <el-table :data="list" v-loading="loading" border stripe height="420">
        <el-table-column prop="granary_code" label="仓号" width="80" />
        <el-table-column prop="recorded_at" label="检测时间" width="160">
          <template #default="{ row }">{{ formatTime(row.recorded_at) }}</template>
        </el-table-column>
        <el-table-column prop="avg_temp" label="平均粮温(℃)" width="110" align="right">
          <template #default="{ row }">
            <span :class="tempClass(row.avg_temp)">{{ row.avg_temp }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="max_temp" label="最高粮温(℃)" width="110" align="right">
          <template #default="{ row }">
            <span :class="tempClass(row.max_temp)">{{ row.max_temp }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="min_temp" label="最低粮温(℃)" width="110" align="right" />
        <el-table-column prop="ambient_temp" label="仓温(℃)" width="90" align="right" />
        <el-table-column prop="humidity" label="仓湿(%)" width="90" align="right">
          <template #default="{ row }">
            <span :class="row.humidity >= 70 ? 'warn-text' : ''">{{ row.humidity }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="sensor_layer" label="检测层点" width="90" align="center" />
        <el-table-column prop="inspector" label="检测人" width="90" />
        <el-table-column label="告警级别" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="findType(ALERT_LEVEL, row.alert_level)">
              {{ row.alert_level_display }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="note" label="情况说明" min-width="160" />
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" title="录入检测记录" width="560px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
        <el-form-item label="仓房" prop="granary">
          <el-select v-model="form.granary" style="width: 100%">
            <el-option v-for="g in granaries" :key="g.id" :label="`${g.code} ${g.name}`" :value="g.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="检测时间" prop="recorded_at">
          <el-date-picker v-model="form.recorded_at" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="平均粮温" prop="avg_temp">
              <el-input-number v-model="form.avg_temp" :precision="2" :step="0.1" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="最高粮温" prop="max_temp">
              <el-input-number v-model="form.max_temp" :precision="2" :step="0.1" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="最低粮温" prop="min_temp">
              <el-input-number v-model="form.min_temp" :precision="2" :step="0.1" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="仓温(℃)">
              <el-input-number v-model="form.ambient_temp" :precision="2" :step="0.1" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="仓内湿度(%)" prop="humidity">
              <el-input-number v-model="form.humidity" :precision="1" :min="0" :max="100" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="检测层点">
              <el-select v-model="form.sensor_layer" style="width: 100%">
                <el-option label="上层" value="上层" />
                <el-option label="中层" value="中层" />
                <el-option label="下层" value="下层" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="检测人">
          <el-input v-model="form.inspector" />
        </el-form-item>
        <el-form-item label="情况说明">
          <el-input v-model="form.note" type="textarea" :rows="2" />
        </el-form-item>
        <el-alert
          type="info"
          :closable="false"
          title="系统将按仓房温湿度阈值自动判定告警级别（正常 / 预警 / 告警）"
        />
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, reactive, ref, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import { granaryApi, monitorApi } from '@/api'
import { ALERT_LEVEL, findType } from '@/utils/constants'

const list = ref([])
const granaries = ref([])
const loading = ref(false)
const filters = reactive({ granary: '', alert_level: '' })
const dateRange = ref(null)

const stats = computed(() => {
  const latest = new Map()
  for (const r of list.value) {
    if (!latest.has(r.granary)) latest.set(r.granary, r)
  }
  const latestRows = [...latest.values()]
  const avg = latestRows.length
    ? (latestRows.reduce((s, r) => s + Number(r.avg_temp), 0) / latestRows.length).toFixed(1)
    : '--'
  const warn = list.value.filter((r) => r.alert_level === 'warning').length
  const crit = list.value.filter((r) => r.alert_level === 'critical').length
  return [
    { label: '检测记录（筛选范围）', value: `${list.value.length} 条`, color: '#3b7dd8' },
    { label: '平均粮温', value: `${avg} ℃`, color: '#2f8f6b' },
    { label: '预警记录', value: `${warn} 条`, color: '#d48806' },
    { label: '告警记录', value: `${crit} 条`, color: '#cf1322' },
  ]
})

function formatTime(t) {
  return t?.replace('T', ' ').slice(0, 16)
}
function tempClass(v) {
  v = Number(v)
  if (v >= 28) return 'temp-critical'
  if (v >= 25) return 'temp-warning'
  return 'temp-normal'
}

async function loadData() {
  loading.value = true
  try {
    const params = { page_size: 500, ordering: '-recorded_at' }
    if (filters.granary) params.granary = filters.granary
    if (filters.alert_level) params.alert_level = filters.alert_level
    if (dateRange.value) {
      params.recorded_at__gte = dateRange.value[0]
      params.recorded_at__lte = dateRange.value[1]
    }
    const res = await monitorApi.list(params)
    list.value = res.results ?? res
  } finally {
    loading.value = false
  }
}

// ---- 录入 ----
const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref()
const emptyForm = () => ({
  granary: null,
  recorded_at: new Date().toISOString().slice(0, 19),
  avg_temp: 20, max_temp: 22, min_temp: 19,
  ambient_temp: 22, humidity: 60,
  sensor_layer: '中层', inspector: '', note: '',
  outside_temp: 20, outside_humidity: 60,
})
const form = reactive(emptyForm())
const rules = {
  granary: [{ required: true, message: '请选择仓房', trigger: 'change' }],
  recorded_at: [{ required: true, message: '请选择时间', trigger: 'change' }],
  avg_temp: [{ required: true, message: '请输入', trigger: 'blur' }],
  max_temp: [{ required: true, message: '请输入', trigger: 'blur' }],
  min_temp: [{ required: true, message: '请输入', trigger: 'blur' }],
  humidity: [{ required: true, message: '请输入湿度', trigger: 'blur' }],
}
function openDialog() {
  Object.assign(form, emptyForm())
  dialogVisible.value = true
}
async function save() {
  await formRef.value.validate()
  saving.value = true
  try {
    await monitorApi.create({ ...form })
    ElMessage.success('录入成功')
    dialogVisible.value = false
    loadData()
  } finally {
    saving.value = false
  }
}

// ---- 趋势图（近 7 天按仓房按日聚合） ----
const chartRef = ref(null)
const chartMetric = ref('avg_temp')
let chart = null

async function renderChart() {
  // 拉全量近 7 天数据后前端按日聚合
  const since = new Date(Date.now() - 7 * 86400000).toISOString().slice(0, 19)
  const res = await monitorApi.list({ page_size: 2000, recorded_at__gte: since })
  const rows = res.results ?? res
  const dayMap = {}
  for (const r of rows) {
    const day = r.recorded_at.slice(5, 10)
    const code = r.granary_code
    if (!dayMap[code]) dayMap[code] = {}
    if (!dayMap[code][day]) dayMap[code][day] = []
    dayMap[code][day].push(Number(r[chartMetric.value]))
  }
  const days = []
  for (let i = 6; i >= 0; i--) {
    days.push(new Date(Date.now() - i * 86400000).toISOString().slice(5, 10))
  }
  const palette = ['#2f8f6b', '#d48806', '#3b7dd8', '#cf1322', '#722ed1', '#8d6e63', '#13a8a8', '#eb2f96']
  const series = Object.keys(dayMap).map((code, idx) => ({
    name: code,
    type: 'line',
    smooth: true,
    symbol: 'circle',
    symbolSize: 5,
    itemStyle: { color: palette[idx % palette.length] },
    data: days.map((d) => {
      const arr = dayMap[code][d]
      if (!arr || !arr.length) return null
      return Number((arr.reduce((s, v) => s + v, 0) / arr.length).toFixed(2))
    }),
    connectNulls: true,
  }))
  if (!chart) chart = echarts.init(chartRef.value)
  chart.setOption(
    {
      tooltip: { trigger: 'axis' },
      legend: { top: 0, type: 'scroll' },
      grid: { left: 45, right: 25, top: 38, bottom: 30 },
      xAxis: { type: 'category', data: days },
      yAxis: { type: 'value', name: chartMetric.value === 'humidity' ? '%' : '℃' },
      series,
    },
    true
  )
}

function onResize() {
  chart?.resize()
}
watch(chartMetric, () => renderChart())

onMounted(async () => {
  const gres = await granaryApi.list({ page_size: 100 })
  granaries.value = gres.results ?? gres
  await loadData()
  await nextTick()
  renderChart()
  window.addEventListener('resize', onResize)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  chart?.dispose()
})
</script>

<style scoped>
.mb16 {
  margin-bottom: 16px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}
.mini-stat {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #7a8a82;
  font-size: 13px;
}
.mini-stat strong {
  font-size: 17px;
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
.warn-text {
  color: #d48806;
  font-weight: 600;
}
</style>

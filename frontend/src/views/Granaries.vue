<template>
  <div>
    <div class="page-header">
      <h2>仓房管理</h2>
      <el-button v-if="auth.isManager" type="primary" :icon="Plus" @click="openDialog()">新增仓房</el-button>
    </div>

    <el-card>
      <div class="filter-bar">
        <el-input
          v-model="filters.search"
          placeholder="搜索仓号 / 名称 / 保管员"
          clearable
          style="width: 240px"
          @keyup.enter="loadData"
          @clear="loadData"
        />
        <el-select v-model="filters.status" placeholder="仓房状态" clearable style="width: 140px">
          <el-option v-for="s in GRANARY_STATUS" :key="s.value" :label="s.label" :value="s.value" />
        </el-select>
        <el-select v-model="filters.granary_type" placeholder="仓型" clearable style="width: 140px">
          <el-option v-for="t in GRANARY_TYPE" :key="t.value" :label="t.label" :value="t.value" />
        </el-select>
        <el-button type="primary" :icon="Search" @click="loadData">查询</el-button>
      </div>

      <el-table :data="list" v-loading="loading" border stripe>
        <el-table-column prop="code" label="仓号" width="80" />
        <el-table-column prop="name" label="仓房名称" min-width="120" />
        <el-table-column label="仓型" width="90">
          <template #default="{ row }">{{ row.granary_type_display }}</template>
        </el-table-column>
        <el-table-column label="设计仓容(吨)" width="120" align="right">
          <template #default="{ row }">{{ row.capacity }}</template>
        </el-table-column>
        <el-table-column label="当前结存(吨)" width="120" align="right">
          <template #default="{ row }">
            <span style="font-weight: 600; color: #b8860b">{{ row.current_stock }}</span>
          </template>
        </el-table-column>
        <el-table-column label="仓容利用率" width="170">
          <template #default="{ row }">
            <el-progress
              :percentage="row.utilization"
              :color="utilColor(row.utilization)"
              :stroke-width="14"
            />
          </template>
        </el-table-column>
        <el-table-column prop="manager" label="保管员" width="90" />
        <el-table-column prop="location" label="位置" min-width="110" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="findType(GRANARY_STATUS, row.status)">
              {{ row.status_display }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="showDetail(row)">粮情</el-button>
            <el-button v-if="auth.isManager" link type="primary" size="small" @click="openDialog(row)">编辑</el-button>
            <el-popconfirm v-if="auth.canApproveOrDelete()" title="确认删除该仓房？" @confirm="remove(row)">
              <template #reference>
                <el-button link type="danger" size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑仓房' : '新增仓房'" width="640px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="仓号" prop="code">
              <el-input v-model="form.code" placeholder="如 P05" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="仓房名称" prop="name">
              <el-input v-model="form.name" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="仓型" prop="granary_type">
              <el-select v-model="form.granary_type" style="width: 100%">
                <el-option v-for="t in GRANARY_TYPE" :key="t.value" :label="t.label" :value="t.value" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="保管员" prop="manager">
              <el-input v-model="form.manager" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="设计仓容(吨)" prop="capacity">
              <el-input-number v-model="form.capacity" :min="0" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="建筑面积(㎡)">
              <el-input-number v-model="form.area" :min="0" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="库区位置">
              <el-input v-model="form.location" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="建成年份">
              <el-input-number v-model="form.build_year" :min="1980" :max="2100" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="温度阈值(℃)">
              <el-input-number v-model="form.temperature_threshold" :min="0" :max="60" :precision="1" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="湿度阈值(%)">
              <el-input-number v-model="form.humidity_threshold" :min="0" :max="100" :precision="1" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="备注">
              <el-input v-model="form.remark" type="textarea" :rows="2" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <!-- 仓房粮情详情 -->
    <el-drawer v-model="detailVisible" size="62%" :title="`${detail?.code} ${detail?.name} · 粮情详情`">
      <template v-if="detail">
        <el-descriptions :column="3" border size="small" class="mb16">
          <el-descriptions-item label="仓型">{{ detail.granary_type_display }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag size="small" :type="findType(GRANARY_STATUS, detail.status)">{{ detail.status_display }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="保管员">{{ detail.manager }}</el-descriptions-item>
          <el-descriptions-item label="设计仓容">{{ detail.capacity }} 吨</el-descriptions-item>
          <el-descriptions-item label="当前结存">{{ detail.current_stock }} 吨</el-descriptions-item>
          <el-descriptions-item label="利用率">{{ detail.utilization }}%</el-descriptions-item>
        </el-descriptions>

        <h4>在储粮批次</h4>
        <el-table :data="detailBatches" size="small" border class="mb16">
          <el-table-column prop="batch_no" label="批次号" min-width="130" />
          <el-table-column label="品种">
            <template #default="{ row }">{{ row.grain_kind_display }}</template>
          </el-table-column>
          <el-table-column label="等级">
            <template #default="{ row }">{{ row.grade_display }}</template>
          </el-table-column>
          <el-table-column prop="quantity" label="结存(吨)" align="right" />
          <el-table-column prop="origin" label="产地" />
          <el-table-column prop="moisture" label="水分%" align="center" />
          <el-table-column prop="stored_at" label="入库日期" width="110" />
        </el-table>

        <h4>近 24 小时温湿度趋势</h4>
        <div ref="detailChart" style="height: 300px"></div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, nextTick } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import { batchApi, granaryApi } from '@/api'
import { GRANARY_STATUS, GRANARY_TYPE, findType } from '@/utils/constants'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const list = ref([])
const loading = ref(false)
const filters = reactive({ search: '', status: '', granary_type: '' })

async function loadData() {
  loading.value = true
  try {
    const params = {}
    if (filters.search) params.search = filters.search
    if (filters.status) params.status = filters.status
    if (filters.granary_type) params.granary_type = filters.granary_type
    const res = await granaryApi.list(params)
    list.value = res.results ?? res
  } finally {
    loading.value = false
  }
}

function utilColor(p) {
  if (p >= 95) return '#cf1322'
  if (p >= 70) return '#2f8f6b'
  return '#d48806'
}

// ---- 新增/编辑 ----
const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref()
const emptyForm = () => ({
  id: null, code: '', name: '', granary_type: 'square', capacity: 1000,
  area: 0, manager: '', location: '', build_year: null,
  temperature_threshold: 25, humidity_threshold: 70, remark: '',
})
const form = reactive(emptyForm())
const rules = {
  code: [{ required: true, message: '请输入仓号', trigger: 'blur' }],
  name: [{ required: true, message: '请输入仓房名称', trigger: 'blur' }],
  granary_type: [{ required: true, message: '请选择仓型', trigger: 'change' }],
  capacity: [{ required: true, message: '请输入仓容', trigger: 'blur' }],
  manager: [{ required: true, message: '请输入保管员', trigger: 'blur' }],
}

function openDialog(row) {
  Object.assign(form, emptyForm())
  if (row) Object.assign(form, row)
  dialogVisible.value = true
  nextTick(() => formRef.value?.clearValidate())
}

async function save() {
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) await granaryApi.update(form.id, form)
    else await granaryApi.create(form)
    ElMessage.success('保存成功')
    dialogVisible.value = false
    loadData()
  } finally {
    saving.value = false
  }
}

async function remove(row) {
  await granaryApi.remove(row.id)
  ElMessage.success('删除成功')
  loadData()
}

// ---- 详情抽屉 ----
const detailVisible = ref(false)
const detail = ref(null)
const detailBatches = ref([])
const detailChart = ref(null)
let chart = null

async function showDetail(row) {
  detail.value = row
  detailVisible.value = true
  detailBatches.value = []
  const [batches, series] = await Promise.all([
    batchApi.list({ granary: row.id }),
    granaryApi.tempSeries(row.id),
  ])
  detailBatches.value = batches.results ?? batches
  await nextTick()
  chart?.dispose()
  chart = echarts.init(detailChart.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['平均粮温', '最高粮温', '湿度'], right: 0 },
    grid: { left: 45, right: 45, top: 40, bottom: 30 },
    xAxis: { type: 'category', data: series.map((s) => s.time) },
    yAxis: [
      { type: 'value', name: '温度℃', min: 10 },
      { type: 'value', name: '湿度%', min: 30, max: 100 },
    ],
    series: [
      {
        name: '平均粮温', type: 'line', smooth: true,
        data: series.map((s) => s.avg_temp), itemStyle: { color: '#2f8f6b' },
      },
      {
        name: '最高粮温', type: 'line', smooth: true,
        data: series.map((s) => s.max_temp), itemStyle: { color: '#cf1322' },
      },
      {
        name: '湿度', type: 'line', smooth: true, yAxisIndex: 1,
        data: series.map((s) => s.humidity), itemStyle: { color: '#3b7dd8' },
      },
    ],
  })
}

onMounted(loadData)
</script>

<style scoped>
.mb16 {
  margin-bottom: 16px;
}
h4 {
  margin: 12px 0 8px;
  color: #1f2d3d;
}
</style>

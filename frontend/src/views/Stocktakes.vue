<template>
  <div>
    <div class="page-header">
      <h2>库存盘点</h2>
      <el-button v-if="auth.isManager" type="primary" :icon="Plus" @click="openDialog()">新建盘点单</el-button>
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

    <el-card>
      <el-table :data="list" v-loading="loading" border stripe>
        <el-table-column prop="stocktake_no" label="盘点单号" width="160" />
        <el-table-column prop="name" label="盘点名称" min-width="180" />
        <el-table-column prop="plan_date" label="盘点日期" width="120" />
        <el-table-column prop="leader" label="负责人" width="100" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="findType(STOCKTAKE_STATUS, row.status)">
              {{ row.status_display }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="账存(吨)" width="110" align="right">
          <template #default="{ row }">{{ row.total_book }}</template>
        </el-table-column>
        <el-table-column label="实盘(吨)" width="110" align="right">
          <template #default="{ row }">
            {{ row.status === 'draft' ? '--' : row.total_actual }}
          </template>
        </el-table-column>
        <el-table-column label="差异(吨)" width="110" align="right">
          <template #default="{ row }">
            <span v-if="row.status !== 'draft'" :class="diffClass(row.total_diff)">
              {{ row.total_diff > 0 ? '+' : '' }}{{ row.total_diff }}
            </span>
            <span v-else>--</span>
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="140" />
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="showDetail(row)">盘点明细</el-button>
            <el-popconfirm
              v-if="auth.canApproveOrDelete() && row.status === 'draft'"
              title="确认删除该盘点单？"
              @confirm="remove(row)"
            >
              <template #reference>
                <el-button link type="danger" size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新建盘点单 -->
    <el-dialog v-model="dialogVisible" title="新建盘点单" width="520px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="盘点单号" prop="stocktake_no">
          <el-input v-model="form.stocktake_no" />
        </el-form-item>
        <el-form-item label="盘点名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="盘点日期" prop="plan_date">
          <el-date-picker v-model="form.plan_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="负责人">
          <el-input :model-value="auth.displayName" disabled />
        </el-form-item>
        <el-form-item label="参加人员">
          <el-input v-model="form.members" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">创建</el-button>
      </template>
    </el-dialog>

    <!-- 盘点明细抽屉 -->
    <el-drawer v-model="detailVisible" size="72%" :title="`${detail?.stocktake_no} · ${detail?.name}`">
      <template v-if="detail">
        <div class="detail-toolbar">
          <el-descriptions :column="4" border size="small">
            <el-descriptions-item label="状态">
              <el-tag size="small" :type="findType(STOCKTAKE_STATUS, detail.status)">
                {{ detail.status_display }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="账面合计">{{ detail.total_book }} 吨</el-descriptions-item>
            <el-descriptions-item label="实盘合计">{{ detail.total_actual }} 吨</el-descriptions-item>
            <el-descriptions-item label="差异合计">
              <span :class="diffClass(detail.total_diff)">
                {{ detail.total_diff > 0 ? '+' : '' }}{{ detail.total_diff }} 吨
              </span>
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <div class="detail-actions">
          <el-button
            type="primary"
            :icon="Refresh"
            :disabled="detail.status !== 'draft' || !auth.canWrite()"
            :loading="generating"
            @click="generateItems"
          >
            按在储批次生成盘点明细
          </el-button>
          <el-button
            type="success"
            :icon="Check"
            :disabled="detail.status !== 'counting' || !auth.canApproveOrDelete()"
            @click="finish"
          >
            完成盘点并调账
          </el-button>
          <el-tag v-if="!auth.canApproveOrDelete()" size="small" type="info">
            保管员录入实盘，调账由库管主任完成
          </el-tag>
          <span class="tip" v-if="detail.status === 'draft'">先生成明细，再逐仓录入实盘数量</span>
          <span class="tip" v-else-if="detail.status === 'counting'">录入全部实盘数量后完成盘点</span>
          <span class="tip done" v-else>盘点已结束，批次结存已按实盘调整</span>
        </div>

        <el-table :data="items" border size="small">
          <el-table-column type="index" label="序号" width="55" align="center" />
          <el-table-column prop="granary_code" label="仓号" width="80" />
          <el-table-column prop="batch_no" label="批次号" min-width="130" />
          <el-table-column prop="book_quantity" label="账面数量(吨)" width="120" align="right" />
          <el-table-column label="实盘数量(吨)" width="150">
            <template #default="{ row }">
              <el-input-number
                v-if="detail.status === 'counting' && auth.canWrite()"
                :model-value="row.actual_quantity"
                :min="0"
                :precision="2"
                size="small"
                style="width: 135px"
                @change="(v) => updateItem(row, v)"
              />
              <span v-else>{{ row.actual_quantity ?? '--' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="差异(吨)" width="100" align="right">
            <template #default="{ row }">
              <span v-if="row.actual_quantity != null" :class="diffClass(row.diff)">
                {{ row.diff > 0 ? '+' : '' }}{{ row.diff }}
              </span>
              <span v-else>--</span>
            </template>
          </el-table-column>
          <el-table-column prop="loss_quantity" label="损耗(吨)" width="100" align="right" />
          <el-table-column prop="gain_quantity" label="溢余(吨)" width="100" align="right" />
          <el-table-column label="差异原因" min-width="160">
            <template #default="{ row }">
              <el-input
                v-if="detail.status === 'counting' && auth.canWrite()"
                :model-value="row.reason"
                size="small"
                @change="(v) => updateReason(row, v)"
                placeholder="如：水分减量"
              />
              <span v-else>{{ row.reason }}</span>
            </template>
          </el-table-column>
        </el-table>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Check } from '@element-plus/icons-vue'
import { stocktakeApi, stocktakeItemApi } from '@/api'
import { STOCKTAKE_STATUS, findType } from '@/utils/constants'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const list = ref([])
const loading = ref(false)

const stats = computed(() => {
  const counting = list.value.filter((s) => s.status === 'counting').length
  const adjusted = list.value.filter((s) => s.status === 'adjusted').length
  const totalLoss = list.value.reduce((sum, s) => sum + (s.total_diff < 0 ? Math.abs(s.total_diff) : 0), 0)
  const totalGain = list.value.reduce((sum, s) => sum + (s.total_diff > 0 ? s.total_diff : 0), 0)
  return [
    { label: '盘点单总数', value: `${list.value.length} 张`, color: '#3b7dd8' },
    { label: '盘点中', value: `${counting} 张`, color: '#d48806' },
    { label: '已调账', value: `${adjusted} 张`, color: '#2f8f6b' },
    { label: '累计损 / 溢', value: `${totalLoss.toFixed(2)} / ${totalGain.toFixed(2)} 吨`, color: '#b8860b' },
  ]
})

async function loadData() {
  loading.value = true
  try {
    const res = await stocktakeApi.list({ page_size: 100 })
    list.value = res.results ?? res
  } finally {
    loading.value = false
  }
}

function diffClass(v) {
  if (v == null || Number(v) === 0) return 'diff-zero'
  return Number(v) < 0 ? 'diff-loss' : 'diff-gain'
}

// ---- 新建 ----
const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref()
const today = () => new Date().toISOString().slice(0, 10)
function genNo() {
  const d = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  return `PD${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}${pad(d.getHours())}${pad(d.getMinutes())}`
}
const form = reactive({
  stocktake_no: genNo(),
  name: '',
  plan_date: today(),
  members: '',
  remark: '',
})
const rules = {
  stocktake_no: [{ required: true, message: '请输入盘点单号', trigger: 'blur' }],
  name: [{ required: true, message: '请输入盘点名称', trigger: 'blur' }],
  plan_date: [{ required: true, message: '请选择日期', trigger: 'change' }],
}
function openDialog() {
  Object.assign(form, {
    stocktake_no: genNo(), name: '', plan_date: today(),
    members: '', remark: '',
  })
  dialogVisible.value = true
}
async function save() {
  await formRef.value.validate()
  saving.value = true
  try {
    await stocktakeApi.create({ ...form, status: 'draft' })
    ElMessage.success('盘点单已创建')
    dialogVisible.value = false
    loadData()
  } finally {
    saving.value = false
  }
}
async function remove(row) {
  await stocktakeApi.remove(row.id)
  ElMessage.success('删除成功')
  loadData()
}

// ---- 明细抽屉 ----
const detailVisible = ref(false)
const detail = ref(null)
const items = ref([])
const generating = ref(false)

async function showDetail(row) {
  detailVisible.value = true
  await refreshDetail(row.id)
}

async function refreshDetail(id) {
  const data = await stocktakeApi.retrieve(id)
  detail.value = data
  const res = await stocktakeItemApi.list({ stocktake: id, page_size: 500 })
  items.value = res.results ?? res
}

async function generateItems() {
  generating.value = true
  try {
    const data = await stocktakeApi.generateItems(detail.value.id)
    detail.value = data
    const res = await stocktakeItemApi.list({ stocktake: detail.value.id, page_size: 500 })
    items.value = res.results ?? res
    ElMessage.success(`已按 ${items.value.length} 个在储批次生成明细，可录入实盘数`)
  } finally {
    generating.value = false
  }
}

async function updateItem(row, value) {
  await stocktakeItemApi.update(row.id, { actual_quantity: value })
  row.actual_quantity = value
  row.diff = value == null ? null : Number((value - Number(row.book_quantity)).toFixed(2))
}

async function updateReason(row, value) {
  await stocktakeItemApi.update(row.id, { reason: value || '' })
  row.reason = value || ''
}

async function finish() {
  await ElMessageBox.confirm(
    '完成盘点后系统将按实盘数量自动调整批次结存（产生损/溢记录），是否继续？',
    '盘点调账确认',
    { type: 'warning' }
  )
  const data = await stocktakeApi.finish(detail.value.id)
  detail.value = data
  await refreshDetail(detail.value.id)
  ElMessage.success('盘点完成，结存已调账')
  loadData()
}

onMounted(loadData)
</script>

<style scoped>
.mb16 {
  margin-bottom: 16px;
}
.mini-stat {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #7a8a82;
  font-size: 13px;
}
.mini-stat strong {
  font-size: 16px;
}
.detail-toolbar {
  margin-bottom: 14px;
}
.detail-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}
.tip {
  color: #909399;
  font-size: 13px;
}
.tip.done {
  color: #2f8f6b;
}
.diff-zero {
  color: #909399;
}
.diff-loss {
  color: #cf1322;
  font-weight: 600;
}
.diff-gain {
  color: #2f8f6b;
  font-weight: 600;
}
</style>

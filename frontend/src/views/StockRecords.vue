<template>
  <div>
    <div class="page-header">
      <h2>出入库记录</h2>
      <el-button v-if="auth.canWrite()" type="primary" :icon="Plus" @click="openDialog()">新增出入库单</el-button>
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
      <div class="filter-bar">
        <el-radio-group v-model="filters.direction" @change="reload">
          <el-radio-button value="">全部</el-radio-button>
          <el-radio-button value="in">入库</el-radio-button>
          <el-radio-button value="out">出库</el-radio-button>
        </el-radio-group>
        <el-select v-model="filters.granary" placeholder="仓房" clearable style="width: 150px" @change="reload">
          <el-option v-for="g in granaries" :key="g.id" :label="g.code" :value="g.id" />
        </el-select>
        <el-select v-model="filters.biz_type" placeholder="业务类型" clearable style="width: 140px" @change="reload">
          <el-option v-for="b in manualBizTypes" :key="b.value" :label="b.label" :value="b.value" />
        </el-select>
        <el-checkbox v-model="hideVoid" @change="reload">隐藏已作废</el-checkbox>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          style="width: 280px"
        />
        <el-input
          v-model="filters.search"
          placeholder="单据号 / 对方单位 / 经办人"
          clearable
          style="width: 220px"
          @keyup.enter="reload"
          @clear="reload"
        />
        <el-button type="primary" :icon="Search" @click="reload">查询</el-button>
      </div>

      <el-table
        :data="hideVoid ? list.filter((r) => !r.is_void) : list"
        v-loading="loading" border stripe height="520"
        :row-class-name="rowClass"
      >
        <el-table-column label="状态" width="78">
          <template #default="{ row }">
            <el-tag v-if="row.is_void" type="danger" size="small">已作废</el-tag>
            <el-tag v-else size="small" :type="findType(DIRECTION, row.direction)">
              {{ row.direction_display }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="record_no" label="单据编号" width="150" />
        <el-table-column label="业务类型" width="100">
          <template #default="{ row }">{{ row.biz_type_display }}</template>
        </el-table-column>
        <el-table-column prop="granary_code" label="仓号" width="72" />
        <el-table-column prop="batch_no" label="批次号" width="130" />
        <el-table-column prop="quantity" label="数量(吨)" width="100" align="right">
          <template #default="{ row }">
            <strong :class="row.is_void ? 'void-text' : (row.direction === 'in' ? 'qty-in' : 'qty-out')">
              {{ row.direction === 'in' ? '+' : '-' }}{{ row.quantity }}
            </strong>
          </template>
        </el-table-column>
        <el-table-column prop="unit_price" label="单价" width="90" align="right" />
        <el-table-column label="金额(元)" width="120" align="right">
          <template #default="{ row }">{{ row.amount?.toLocaleString() }}</template>
        </el-table-column>
        <el-table-column prop="counterparty" label="对方单位" min-width="150" show-overflow-tooltip />
        <el-table-column prop="operator" label="经办人" width="90" />
        <el-table-column prop="occurred_at" label="时间" width="148">
          <template #default="{ row }">{{ row.occurred_at.replace('T', ' ').slice(0, 16) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-tooltip v-if="!editable(row)" :content="lockReason(row)" placement="top">
              <span>
                <el-button link type="primary" size="small" disabled>更正</el-button>
              </span>
            </el-tooltip>
            <el-button
              v-else link type="primary" size="small"
              @click="openDialog(row)"
            >更正</el-button>

            <el-tooltip v-if="!editable(row)" :content="lockReason(row)" placement="top">
              <span>
                <el-button link type="danger" size="small" disabled>作废</el-button>
              </span>
            </el-tooltip>
            <el-button
              v-else link type="danger" size="small"
              @click="askVoidReason(row)"
            >作废</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        class="pager"
        background
        layout="total, prev, pager, next"
        :total="total"
        :page-size="pageSize"
        :current-page="page"
        @current-change="onPage"
      />
    </el-card>

    <!-- 作废原因弹窗 -->
    <el-dialog v-model="voidDialog" title="单据红冲作废" width="480px">
      <el-alert
        type="warning" :closable="false" class="mb16"
        title="作废后原单保留并标记「已作废」，系统自动反向冲销批次结存与仓房状态，此操作不可撤销。"
      />
      <el-descriptions :column="1" border size="small" class="mb16">
        <el-descriptions-item label="单据编号">{{ voidRow?.record_no }}</el-descriptions-item>
        <el-descriptions-item label="内容">
          {{ voidRow?.direction_display }}{{ voidRow?.quantity }}吨 · {{ voidRow?.granary_code }}
        </el-descriptions-item>
      </el-descriptions>
      <el-input v-model="voidReason" type="textarea" :rows="3" maxlength="200" show-word-limit
                placeholder="必须填写作废原因，将随原单永久保留" />
      <template #footer>
        <el-button @click="voidDialog = false">取消</el-button>
        <el-button type="danger" :loading="voiding" :disabled="!voidReason.trim()" @click="confirmVoid">
          确认作废
        </el-button>
      </template>
    </el-dialog>

    <!-- 新增/更正弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '更正出入库单' : '新增出入库单'" width="640px">
      <el-alert
        v-if="editingId"
        type="info" :closable="false" class="mb16"
        title="更正保存后，系统将按「新单影响 − 原单影响」的差额自动调整批次结存与仓房状态；原经办人保持不变，更正动作记入操作日志。"
      />
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <el-form-item label="出入库方向" prop="direction">
          <el-radio-group v-model="form.direction" @change="onDirectionChange">
            <el-radio-button value="in">入库</el-radio-button>
            <el-radio-button value="out">出库</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="单据编号" prop="record_no">
              <el-input v-model="form.record_no" :disabled="!!editingId" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="业务类型" prop="biz_type">
              <el-select v-model="form.biz_type" style="width: 100%">
                <el-option v-for="b in availableBizTypes" :key="b.value" :label="b.label" :value="b.value" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="仓房" prop="granary">
              <el-select v-model="form.granary" style="width: 100%" @change="loadBatches"
                         :disabled="!!editingId">
                <el-option v-for="g in selectableGranaries" :key="g.id"
                           :label="`${g.code} ${g.name}`" :value="g.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="粮油批次" prop="batch">
              <el-select v-model="form.batch" style="width: 100%">
                <el-option v-for="b in batches" :key="b.id"
                           :label="`${b.batch_no} ${b.grain_kind_display} 结存${b.quantity}吨`"
                           :value="b.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="数量(吨)" prop="quantity">
              <el-input-number v-model="form.quantity" :min="0.01" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="单价(元/吨)">
              <el-input-number v-model="form.unit_price" :min="0" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="对方单位">
              <el-input v-model="form.counterparty" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="经办人">
              <el-input :model-value="editingId ? editingOperator : auth.displayName" disabled />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="出入库时间" prop="occurred_at">
              <el-date-picker v-model="form.occurred_at" type="datetime"
                              value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="备注">
              <el-input v-model="form.remark" type="textarea" :rows="2" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-alert
          v-if="selectedBatch && form.direction === 'out' && form.quantity > Number(selectedBatch.quantity)"
          type="error" :closable="false"
          :title="`出库数量超过批次当前结存 ${selectedBatch.quantity} 吨，无法保存`"
          class="mb16"
        />
        <el-alert type="info" :closable="false"
                  title="熏蒸作业期间及已完成盘点结账期间的单据不能更正或作废（后端强制校验）" />
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">
          {{ editingId ? '保存更正' : '保存' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import { batchApi, granaryApi, stockApi } from '@/api'
import { BIZ_TYPE, DIRECTION, findType } from '@/utils/constants'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const list = ref([])
const granaries = ref([])
const batches = ref([])
const loading = ref(false)
const filters = reactive({ direction: '', granary: '', biz_type: '', search: '' })
const dateRange = ref(null)
const hideVoid = ref(false)
const page = ref(1)
const pageSize = 50
const total = ref(0)

// 盘盈/盘亏调账单由盘点流程生成，不在手工业务类型下拉中出现
const ADJUST_TYPES = ['adjust_gain', 'adjust_loss']
const manualBizTypes = BIZ_TYPE.filter((b) => !ADJUST_TYPES.includes(b.value))

const stats = computed(() => {
  const valid = list.value.filter((r) => !r.is_void)
  const inbound = valid.filter((r) => r.direction === 'in').reduce((s, r) => s + Number(r.quantity), 0)
  const outbound = valid.filter((r) => r.direction === 'out').reduce((s, r) => s + Number(r.quantity), 0)
  const voided = list.value.filter((r) => r.is_void).length
  return [
    { label: '有效入库', value: `${inbound.toFixed(1)} 吨`, color: '#2f8f6b' },
    { label: '有效出库', value: `${outbound.toFixed(1)} 吨`, color: '#cf1322' },
    { label: '净变动', value: `${(inbound - outbound).toFixed(1)} 吨`, color: '#b8860b' },
    { label: '已作废单据', value: `${voided} 张`, color: '#909399' },
  ]
})

function rowClass({ row }) {
  return row.is_void ? 'void-row' : ''
}

/** 是否允许更正/作废：有写权限、非调账单、未作废、本仓可操作 */
function editable(row) {
  if (!auth.canWrite() || row.is_void || ADJUST_TYPES.includes(row.biz_type)) return false
  return auth.canAccessGranary(row.granary)
}
/** 不可操作时的原因提示 */
function lockReason(row) {
  if (!auth.canWrite()) return '只读账号无操作权限'
  if (ADJUST_TYPES.includes(row.biz_type)) return '盘点调账单由系统生成，不能更正或作废'
  if (row.is_void) return '该单据已作废'
  if (!auth.canAccessGranary(row.granary)) return '非本人管辖仓房'
  return '该单据已进入盘点结账或熏蒸作业期间'
}

async function loadData() {
  loading.value = true
  try {
    const params = { page: page.value }
    if (filters.direction) params.direction = filters.direction
    if (filters.granary) params.granary = filters.granary
    if (filters.biz_type) params.biz_type = filters.biz_type
    if (filters.search) params.search = filters.search
    if (dateRange.value) {
      params.occurred_at__gte = `${dateRange.value[0]}T00:00:00`
      params.occurred_at__lte = `${dateRange.value[1]}T23:59:59`
    }
    const res = await stockApi.list(params)
    if (res.results) {
      list.value = res.results
      total.value = res.count
    } else {
      list.value = res
      total.value = res.length
    }
  } finally {
    loading.value = false
  }
}
function reload() {
  page.value = 1
  loadData()
}
function onPage(p) {
  page.value = p
  loadData()
}

// ---- 新增 / 更正 ----
const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref()
const editingId = ref(null)
const editingOperator = ref('')
const emptyForm = () => ({
  direction: 'in', record_no: '', biz_type: 'purchase', granary: null, batch: null,
  quantity: 50, unit_price: 0, counterparty: '',
  occurred_at: new Date().toISOString().slice(0, 19), remark: '',
})
const form = reactive(emptyForm())
const rules = {
  record_no: [{ required: true, message: '请输入单据编号', trigger: 'blur' }],
  biz_type: [{ required: true, message: '请选择业务类型', trigger: 'change' }],
  granary: [{ required: true, message: '请选择仓房', trigger: 'change' }],
  batch: [{ required: true, message: '请选择批次', trigger: 'change' }],
  quantity: [{ required: true, message: '请输入数量', trigger: 'blur' }],
  occurred_at: [{ required: true, message: '请选择时间', trigger: 'change' }],
}
const IN_BIZ = ['purchase', 'transfer_in', 'return']
const OUT_BIZ = ['sale', 'transfer_out', 'loss', 'process']
const availableBizTypes = computed(() =>
  manualBizTypes.filter((b) => (form.direction === 'in' ? IN_BIZ.includes(b.value) : OUT_BIZ.includes(b.value)))
)
const selectableGranaries = computed(() => granaries.value.filter((g) => auth.canAccessGranary(g.id)))
const selectedBatch = computed(() => batches.value.find((b) => b.id === form.batch))

function genRecordNo() {
  const d = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  const prefix = form.direction === 'in' ? 'RK' : 'CK'
  return `${prefix}${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}${pad(d.getHours())}${pad(d.getMinutes())}`
}
function onDirectionChange() {
  form.biz_type = form.direction === 'in' ? 'purchase' : 'sale'
  form.batch = null
  batches.value = []
  if (!editingId.value) form.record_no = genRecordNo()
}
async function loadBatches() {
  form.batch = null
  if (!form.granary) return
  const res = await batchApi.list({ granary: form.granary, page_size: 100 })
  batches.value = res.results ?? res
}

function openDialog(row) {
  Object.assign(form, emptyForm())
  batches.value = []
  editingId.value = null
  if (row) {
    // 更正：回填原单
    editingId.value = row.id
    editingOperator.value = row.operator
    Object.assign(form, {
      direction: row.direction, record_no: row.record_no, biz_type: row.biz_type,
      granary: row.granary, batch: row.batch, quantity: Number(row.quantity),
      unit_price: Number(row.unit_price), counterparty: row.counterparty,
      occurred_at: row.occurred_at, remark: row.remark || '',
    })
    loadBatches().then(() => { form.batch = row.batch })
  } else {
    form.record_no = genRecordNo()
  }
  dialogVisible.value = true
}

async function save() {
  await formRef.value.validate()
  saving.value = true
  try {
    const payload = { ...form }
    if (editingId.value) {
      await stockApi.update(editingId.value, payload)
      ElMessage.success('单据已更正，批次结存与仓房状态已按差额联动')
    } else {
      await stockApi.create(payload)
      ElMessage.success('出入库单已保存，结存已联动更新')
    }
    dialogVisible.value = false
    loadData()
  } finally {
    saving.value = false
  }
}

// ---- 红冲作废 ----
const voidDialog = ref(false)
const voidRow = ref(null)
const voidReason = ref('')
const voiding = ref(false)
// el-popconfirm 不便收原因，改为打开原因弹窗
function askVoidReason(row) {
  voidRow.value = row
  voidReason.value = ''
  voidDialog.value = true
}
async function confirmVoid() {
  if (!voidReason.value.trim()) return
  voiding.value = true
  try {
    await stockApi.void(voidRow.value.id, voidReason.value.trim())
    ElMessage.success('单据已红冲作废，结存已反向冲销')
    voidDialog.value = false
    loadData()
  } finally {
    voiding.value = false
  }
}

onMounted(async () => {
  const gres = await granaryApi.list({ page_size: 100 })
  granaries.value = gres.results ?? gres
  loadData()
})
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
.pager {
  margin-top: 14px;
  justify-content: flex-end;
}
.qty-in {
  color: #2f8f6b;
}
.qty-out {
  color: #cf1322;
}
.void-text {
  color: #909399;
  text-decoration: line-through;
}
:deep(.void-row) {
  background: #fafafa !important;
  color: #909399;
}
:deep(.void-row td) {
  text-decoration: line-through;
}
:deep(.void-row .el-tag) {
  text-decoration: none;
}
</style>

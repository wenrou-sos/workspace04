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
        <el-radio-group v-model="filters.direction" @change="loadData">
          <el-radio-button value="">全部</el-radio-button>
          <el-radio-button value="in">入库</el-radio-button>
          <el-radio-button value="out">出库</el-radio-button>
        </el-radio-group>
        <el-select v-model="filters.granary" placeholder="仓房" clearable style="width: 150px" @change="loadData">
          <el-option v-for="g in granaries" :key="g.id" :label="g.code" :value="g.id" />
        </el-select>
        <el-select v-model="filters.biz_type" placeholder="业务类型" clearable style="width: 140px" @change="loadData">
          <el-option v-for="b in BIZ_TYPE" :key="b.value" :label="b.label" :value="b.value" />
        </el-select>
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
          @keyup.enter="loadData"
          @clear="loadData"
        />
        <el-button type="primary" :icon="Search" @click="loadData">查询</el-button>
      </div>

      <el-table :data="list" v-loading="loading" border stripe height="520">
        <el-table-column prop="record_no" label="单据编号" width="150" />
        <el-table-column label="方向" width="80">
          <template #default="{ row }">
            <el-tag size="small" :type="findType(DIRECTION, row.direction)">
              {{ row.direction_display }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="业务类型" width="100">
          <template #default="{ row }">{{ row.biz_type_display }}</template>
        </el-table-column>
        <el-table-column prop="granary_code" label="仓号" width="80" />
        <el-table-column prop="batch_no" label="批次号" width="130" />
        <el-table-column prop="quantity" label="数量(吨)" width="110" align="right">
          <template #default="{ row }">
            <strong :style="{ color: row.direction === 'in' ? '#2f8f6b' : '#cf1322' }">
              {{ row.direction === 'in' ? '+' : '-' }}{{ row.quantity }}
            </strong>
          </template>
        </el-table-column>
        <el-table-column prop="unit_price" label="单价(元/吨)" width="110" align="right" />
        <el-table-column label="金额(元)" width="130" align="right">
          <template #default="{ row }">{{ row.amount?.toLocaleString() }}</template>
        </el-table-column>
        <el-table-column prop="counterparty" label="对方单位" min-width="160" />
        <el-table-column prop="operator" label="经办人" width="90" />
        <el-table-column prop="occurred_at" label="时间" width="150">
          <template #default="{ row }">{{ row.occurred_at.replace('T', ' ').slice(0, 16) }}</template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="120" />
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

    <el-dialog v-model="dialogVisible" title="新增出入库单" width="640px">
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
              <el-input v-model="form.record_no" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="业务类型" prop="biz_type">
              <el-select v-model="form.biz_type" style="width: 100%">
                <el-option
                  v-for="b in availableBizTypes"
                  :key="b.value"
                  :label="b.label"
                  :value="b.value"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="仓房" prop="granary">
              <el-select v-model="form.granary" style="width: 100%" @change="loadBatches">
                <el-option v-for="g in selectableGranaries" :key="g.id" :label="`${g.code} ${g.name}`" :value="g.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="粮油批次" prop="batch">
              <el-select v-model="form.batch" style="width: 100%" placeholder="请选择批次（新粮请先在库存粮情中登记批次）">
                <el-option
                  v-for="b in batches"
                  :key="b.id"
                  :label="`${b.batch_no} ${b.grain_kind_display} 结存${b.quantity}吨`"
                  :value="b.id"
                />
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
              <el-input :model-value="auth.displayName" disabled />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="出入库时间">
              <el-date-picker v-model="form.occurred_at" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%" />
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
          type="error"
          :closable="false"
          :title="`出库数量超过批次结存 ${selectedBatch.quantity} 吨，无法提交`"
          class="mb16"
        />
        <el-alert
          type="info"
          :closable="false"
          title="保存后系统自动更新批次结存数量与仓房状态"
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
const page = ref(1)
const pageSize = 50
const total = ref(0)

const stats = computed(() => {
  const inbound = list.value.filter((r) => r.direction === 'in').reduce((s, r) => s + Number(r.quantity), 0)
  const outbound = list.value.filter((r) => r.direction === 'out').reduce((s, r) => s + Number(r.quantity), 0)
  const inCount = list.value.filter((r) => r.direction === 'in').length
  const outCount = list.value.filter((r) => r.direction === 'out').length
  return [
    { label: '本页入库', value: `${inCount} 单 / ${inbound.toFixed(1)} 吨`, color: '#2f8f6b' },
    { label: '本页出库', value: `${outCount} 单 / ${outbound.toFixed(1)} 吨`, color: '#cf1322' },
    { label: '净变动', value: `${(inbound - outbound).toFixed(1)} 吨`, color: '#b8860b' },
    { label: '记录总数', value: `${total.value} 条`, color: '#3b7dd8' },
  ]
})

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

function onPage(p) {
  page.value = p
  loadData()
}

// ---- 新增 ----
const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref()
const emptyForm = () => ({
  direction: 'in',
  record_no: '',
  biz_type: 'purchase',
  granary: null,
  batch: null,
  quantity: 50,
  unit_price: 0,
  counterparty: '',
  operator: '',
  occurred_at: new Date().toISOString().slice(0, 19),
  remark: '',
})
const form = reactive(emptyForm())
const rules = {
  direction: [{ required: true }],
  record_no: [{ required: true, message: '请输入单据编号', trigger: 'blur' }],
  biz_type: [{ required: true, message: '请选择业务类型', trigger: 'change' }],
  granary: [{ required: true, message: '请选择仓房', trigger: 'change' }],
  batch: [{ required: true, message: '请选择批次', trigger: 'change' }],
  quantity: [{ required: true, message: '请输入数量', trigger: 'blur' }],
}

const selectableGranaries = computed(() =>
  granaries.value.filter((g) => auth.canAccessGranary(g.id))
)

const IN_BIZ = ['purchase', 'transfer_in', 'return']
const OUT_BIZ = ['sale', 'transfer_out', 'loss', 'process']
const availableBizTypes = computed(() =>
  BIZ_TYPE.filter((b) => (form.direction === 'in' ? IN_BIZ.includes(b.value) : OUT_BIZ.includes(b.value)))
)
const selectedBatch = computed(() => batches.value.find((b) => b.id === form.batch))

function onDirectionChange() {
  form.biz_type = form.direction === 'in' ? 'purchase' : 'sale'
  form.batch = null
  batches.value = []
}

async function loadBatches() {
  form.batch = null
  if (!form.granary) return
  const res = await batchApi.list({ granary: form.granary, page_size: 100 })
  batches.value = res.results ?? res
}

function genRecordNo() {
  const d = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  const prefix = form.direction === 'in' ? 'RK' : 'CK'
  return `${prefix}${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}${pad(d.getHours())}${pad(d.getMinutes())}`
}

function openDialog() {
  Object.assign(form, emptyForm())
  form.record_no = genRecordNo()
  dialogVisible.value = true
  batches.value = []
}

async function save() {
  await formRef.value.validate()
  saving.value = true
  try {
    await stockApi.create({ ...form })
    ElMessage.success('出入库单已保存，结存已联动更新')
    dialogVisible.value = false
    loadData()
  } finally {
    saving.value = false
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
</style>

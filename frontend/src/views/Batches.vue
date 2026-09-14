<template>
  <div>
    <div class="page-header">
      <h2>库存粮情</h2>
      <el-button type="primary" :icon="Plus" @click="openDialog()">登记批次</el-button>
    </div>

    <el-row :gutter="12" class="mb16">
      <el-col :span="6" v-for="stat in stats" :key="stat.label">
        <el-card shadow="hover" body-style="padding: 14px">
          <div class="mini-stat">
            <span>{{ stat.label }}</span>
            <strong>{{ stat.value }}</strong>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card>
      <div class="filter-bar">
        <el-select v-model="filters.granary" placeholder="仓房" clearable style="width: 160px" @change="loadData">
          <el-option v-for="g in granaries" :key="g.id" :label="`${g.code} ${g.name}`" :value="g.id" />
        </el-select>
        <el-select v-model="filters.grain_kind" placeholder="品种" clearable style="width: 130px" @change="loadData">
          <el-option v-for="k in GRAIN_KIND" :key="k.value" :label="k.label" :value="k.value" />
        </el-select>
        <el-input
          v-model="filters.search"
          placeholder="批次号 / 产地"
          clearable
          style="width: 200px"
          @keyup.enter="loadData"
          @clear="loadData"
        />
        <el-button type="primary" :icon="Search" @click="loadData">查询</el-button>
      </div>

      <el-table :data="list" v-loading="loading" border stripe>
        <el-table-column prop="batch_no" label="批次号" min-width="130" />
        <el-table-column label="仓房" width="130">
          <template #default="{ row }">{{ row.granary_code }}</template>
        </el-table-column>
        <el-table-column label="品种" width="80">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ row.grain_kind_display }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="等级" width="70" align="center">
          <template #default="{ row }">{{ row.grade_display }}</template>
        </el-table-column>
        <el-table-column prop="quantity" label="结存(吨)" width="120" align="right">
          <template #default="{ row }">
            <strong style="color: #b8860b">{{ Number(row.quantity).toLocaleString() }}</strong>
          </template>
        </el-table-column>
        <el-table-column prop="origin" label="产地" min-width="140" />
        <el-table-column prop="production_year" label="产年" width="70" align="center" />
        <el-table-column label="水分" width="75" align="center">
          <template #default="{ row }">
            <span :class="row.moisture > 13.5 ? 'warn-text' : ''">{{ row.moisture }}%</span>
          </template>
        </el-table-column>
        <el-table-column label="杂质" width="75" align="center">
          <template #default="{ row }">{{ row.impurity }}%</template>
        </el-table-column>
        <el-table-column prop="inbound_price" label="单价(元/吨)" width="110" align="right" />
        <el-table-column prop="stored_at" label="入库日期" width="110" />
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openDialog(row)">编辑</el-button>
            <el-popconfirm title="确认删除该批次？" @confirm="remove(row)">
              <template #reference>
                <el-button link type="danger" size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑批次' : '登记批次'" width="640px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="批次号" prop="batch_no">
              <el-input v-model="form.batch_no" placeholder="如 PC202609P05" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="所在仓房" prop="granary">
              <el-select v-model="form.granary" style="width: 100%">
                <el-option v-for="g in granaries" :key="g.id" :label="`${g.code} ${g.name}`" :value="g.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="粮食品种" prop="grain_kind">
              <el-select v-model="form.grain_kind" style="width: 100%">
                <el-option v-for="k in GRAIN_KIND" :key="k.value" :label="k.label" :value="k.value" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="质量等级" prop="grade">
              <el-select v-model="form.grade" style="width: 100%">
                <el-option v-for="g in GRADE" :key="g.value" :label="g.label" :value="g.value" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="结存数量(吨)">
              <el-input-number v-model="form.quantity" :min="0" :precision="2" style="width: 100%" disabled />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="入库单价(元/吨)">
              <el-input-number v-model="form.inbound_price" :min="0" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="产地">
              <el-input v-model="form.origin" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="生产年份">
              <el-input-number v-model="form.production_year" :min="2000" :max="2100" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="水分(%)">
              <el-input-number v-model="form.moisture" :min="0" :max="30" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="杂质(%)">
              <el-input-number v-model="form.impurity" :min="0" :max="10" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="入库日期">
              <el-date-picker v-model="form.stored_at" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
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
import { batchApi, granaryApi } from '@/api'
import { GRADE, GRAIN_KIND } from '@/utils/constants'

const list = ref([])
const granaries = ref([])
const loading = ref(false)
const filters = reactive({ granary: '', grain_kind: '', search: '' })

const stats = computed(() => {
  const totalQty = list.value.reduce((s, b) => s + Number(b.quantity), 0)
  const kinds = new Set(list.value.map((b) => b.grain_kind_display))
  const value = list.value.reduce((s, b) => s + Number(b.quantity) * Number(b.inbound_price), 0)
  return [
    { label: '在储批次', value: `${list.value.length} 个` },
    { label: '库存总量', value: `${Math.round(totalQty).toLocaleString()} 吨` },
    { label: '库存品种', value: `${kinds.size} 种` },
    { label: '库存货值（约）', value: `${(value / 10000).toFixed(1)} 万元` },
  ]
})

async function loadData() {
  loading.value = true
  try {
    const params = { page_size: 100 }
    if (filters.granary) params.granary = filters.granary
    if (filters.grain_kind) params.grain_kind = filters.grain_kind
    if (filters.search) params.search = filters.search
    const res = await batchApi.list(params)
    list.value = res.results ?? res
  } finally {
    loading.value = false
  }
}

const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref()
const emptyForm = () => ({
  id: null, batch_no: '', granary: null, grain_kind: 'wheat', grade: '3',
  quantity: 0, inbound_price: 0, origin: '', production_year: 2026,
  moisture: 12.5, impurity: 0.8, stored_at: new Date().toISOString().slice(0, 10),
  remark: '',
})
const form = reactive(emptyForm())
const rules = {
  batch_no: [{ required: true, message: '请输入批次号', trigger: 'blur' }],
  granary: [{ required: true, message: '请选择仓房', trigger: 'change' }],
  grain_kind: [{ required: true, message: '请选择品种', trigger: 'change' }],
}

function openDialog(row) {
  Object.assign(form, emptyForm())
  if (row) Object.assign(form, row)
  dialogVisible.value = true
}

async function save() {
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) await batchApi.update(form.id, form)
    else await batchApi.create(form)
    ElMessage.success('保存成功（结存数量由出入库流水自动更新）')
    dialogVisible.value = false
    loadData()
  } finally {
    saving.value = false
  }
}

async function remove(row) {
  await batchApi.remove(row.id)
  ElMessage.success('删除成功')
  loadData()
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
  color: #b8860b;
  font-size: 17px;
}
.warn-text {
  color: #d48806;
  font-weight: 600;
}
</style>

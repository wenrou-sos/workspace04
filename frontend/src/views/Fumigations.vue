<template>
  <div>
    <div class="page-header">
      <h2>熏蒸作业安排</h2>
      <el-button v-if="auth.canArrangeFumigation()" type="primary" :icon="Plus" @click="openDialog()">安排熏蒸</el-button>
    </div>

    <el-row :gutter="12" class="mb16">
      <el-col :span="4" v-for="stat in stats" :key="stat.label">
        <el-card shadow="hover" body-style="padding: 12px">
          <div class="mini-stat">
            <span>{{ stat.label }}</span>
            <strong :style="{ color: stat.color }">{{ stat.value }}</strong>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card>
      <div class="filter-bar">
        <el-select v-model="filters.status" placeholder="作业状态" clearable style="width: 140px" @change="loadData">
          <el-option v-for="s in FUMIGATION_STATUS" :key="s.value" :label="s.label" :value="s.value" />
        </el-select>
        <el-select v-model="filters.granary" placeholder="仓房" clearable style="width: 150px" @change="loadData">
          <el-option v-for="g in granaries" :key="g.id" :label="g.code" :value="g.id" />
        </el-select>
        <el-input
          v-model="filters.search"
          placeholder="作业单号 / 负责人 / 仓号"
          clearable
          style="width: 230px"
          @keyup.enter="loadData"
          @clear="loadData"
        />
        <el-button type="primary" :icon="Search" @click="loadData">查询</el-button>
      </div>

      <el-table :data="list" v-loading="loading" border stripe>
        <el-table-column prop="task_no" label="作业单号" width="140" />
        <el-table-column prop="granary_code" label="熏蒸仓房" width="100" />
        <el-table-column label="药剂" min-width="150">
          <template #default="{ row }">{{ row.agent_display }}</template>
        </el-table-column>
        <el-table-column prop="dose" label="用药量(kg)" width="100" align="right" />
        <el-table-column label="计划时段" min-width="270">
          <template #default="{ row }">
            {{ fmt(row.plan_start) }}<br />
            <span class="text-muted">至 {{ fmt(row.plan_end) }}（密闭 {{ row.seal_days }} 天）</span>
          </template>
        </el-table-column>
        <el-table-column prop="leader" label="负责人" width="90" />
        <el-table-column prop="target_pest" label="防治对象" min-width="130" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="findType(FUMIGATION_STATUS, row.status)">
              {{ row.status_display }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="auth.canWrite() && canAdvance(row.status)"
              link
              type="warning"
              size="small"
              @click="advance(row)"
            >
              {{ nextAction(row.status) }}
            </el-button>
            <el-button v-if="auth.canArrangeFumigation()" link type="primary" size="small" @click="openDialog(row)">编辑</el-button>
            <el-popconfirm
              v-if="auth.canApproveOrDelete() && (row.status === 'planned' || row.status === 'canceled' || row.status === 'done')"
              title="确认删除该作业单？"
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

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑熏蒸作业' : '安排熏蒸作业'" width="680px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="作业单号" prop="task_no">
              <el-input v-model="form.task_no" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="熏蒸仓房" prop="granary">
              <el-select v-model="form.granary" style="width: 100%">
                <el-option v-for="g in selectableGranaries" :key="g.id" :label="`${g.code} ${g.name}`" :value="g.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="熏蒸药剂" prop="agent">
              <el-select v-model="form.agent" style="width: 100%">
                <el-option v-for="a in FUMIGATION_AGENT" :key="a.value" :label="a.label" :value="a.value" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="用药量(kg)" prop="dose">
              <el-input-number v-model="form.dose" :min="0" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="计划开始" prop="plan_start">
              <el-date-picker v-model="form.plan_start" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="计划结束" prop="plan_end">
              <el-date-picker v-model="form.plan_end" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="密闭天数">
              <el-input-number v-model="form.seal_days" :min="1" :max="60" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="作业状态">
              <el-select v-model="form.status" style="width: 100%">
                <el-option v-for="s in FUMIGATION_STATUS" :key="s.value" :label="s.label" :value="s.value" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="负责人">
              <el-input :model-value="auth.displayName" disabled />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="防治对象">
              <el-input v-model="form.target_pest" placeholder="如：玉米象、赤拟谷盗" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="作业人员">
              <el-input v-model="form.team" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="安全措施">
              <el-input v-model="form.safety_note" type="textarea" :rows="3"
                placeholder="佩戴防毒面具、设置警戒区、散气后检测药剂残留浓度合格方可入仓" />
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
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import { fumigationApi, granaryApi } from '@/api'
import { FUMIGATION_AGENT, FUMIGATION_STATUS, findType } from '@/utils/constants'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const list = ref([])
const granaries = ref([])
const loading = ref(false)
const filters = reactive({ status: '', granary: '', search: '' })

const stats = computed(() => {
  const count = (s) => list.value.filter((t) => t.status === s).length
  return [
    { label: '已安排', value: count('planned'), color: '#909399' },
    { label: '施药中', value: count('running'), color: '#d48806' },
    { label: '密闭中', value: count('sealed'), color: '#3b7dd8' },
    { label: '通风散气', value: count('ventilating'), color: '#d46b08' },
    { label: '已完成', value: count('done'), color: '#2f8f6b' },
    { label: '作业合计', value: list.value.length, color: '#1f2d3d' },
  ]
})

async function loadData() {
  loading.value = true
  try {
    const params = { page_size: 200 }
    if (filters.status) params.status = filters.status
    if (filters.granary) params.granary = filters.granary
    if (filters.search) params.search = filters.search
    const res = await fumigationApi.list(params)
    list.value = res.results ?? res
  } finally {
    loading.value = false
  }
}

function fmt(t) {
  return t ? t.replace('T', ' ').slice(0, 16) : '--'
}
function canAdvance(status) {
  return ['planned', 'running', 'sealed', 'ventilating'].includes(status)
}
function nextAction(status) {
  return {
    planned: '开始施药',
    running: '转入密闭',
    sealed: '通风散气',
    ventilating: '完成作业',
  }[status]
}

async function advance(row) {
  await ElMessageBox.confirm(
    `确认将作业单 ${row.task_no} 状态推进为「${nextAction(row.status)}」？`,
    '作业状态推进',
    { type: 'warning' }
  )
  await fumigationApi.advance(row.id)
  ElMessage.success('状态已更新')
  loadData()
}

// ---- 新增/编辑 ----
const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref()

function nextDay(days) {
  return new Date(Date.now() + days * 86400000).toISOString().slice(0, 19)
}
function genNo() {
  const d = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  return `XZ${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}${pad(d.getHours())}${pad(d.getMinutes())}`
}
const emptyForm = () => ({
  id: null, task_no: genNo(), granary: null,
  agent: 'ph3', dose: 20,
  plan_start: nextDay(1), plan_end: nextDay(11),
  seal_days: 9, status: 'planned',
  leader: '', team: '', target_pest: '', safety_note: '', remark: '',
})
const form = reactive(emptyForm())
const rules = {
  task_no: [{ required: true, message: '请输入作业单号', trigger: 'blur' }],
  granary: [{ required: true, message: '请选择仓房', trigger: 'change' }],
  agent: [{ required: true, message: '请选择药剂', trigger: 'change' }],
  dose: [{ required: true, message: '请输入用药量', trigger: 'blur' }],
  plan_start: [{ required: true, message: '请选择开始时间', trigger: 'change' }],
  plan_end: [{ required: true, message: '请选择结束时间', trigger: 'change' }],
}

const selectableGranaries = computed(() =>
  granaries.value.filter((g) => auth.canAccessGranary(g.id))
)

function openDialog(row) {
  Object.assign(form, emptyForm())
  if (row) Object.assign(form, row)
  dialogVisible.value = true
}

async function save() {
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) await fumigationApi.update(form.id, form)
    else await fumigationApi.create(form)
    ElMessage.success('保存成功')
    dialogVisible.value = false
    loadData()
  } finally {
    saving.value = false
  }
}

async function remove(row) {
  await fumigationApi.remove(row.id)
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
  flex-direction: column;
  gap: 4px;
  color: #7a8a82;
  font-size: 13px;
}
.mini-stat strong {
  font-size: 20px;
}
.text-muted {
  color: #909399;
  font-size: 12px;
}
</style>

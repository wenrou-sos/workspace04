<template>
  <div>
    <div class="page-header">
      <h2>操作日志</h2>
      <span class="sub">{{ scopeTip }}</span>
    </div>

    <el-card>
      <div class="filter-bar">
        <el-select v-model="filters.module" placeholder="业务模块" clearable style="width: 150px" @change="reload">
          <el-option v-for="m in MODULES" :key="m" :label="m" :value="m" />
        </el-select>
        <el-select v-model="filters.action" placeholder="动作类型" clearable style="width: 150px" @change="reload">
          <el-option v-for="a in ACTIONS" :key="a.value" :label="a.label" :value="a.value" />
        </el-select>
        <el-button type="primary" :icon="Search" @click="reload">查询</el-button>
      </div>

      <el-table :data="list" v-loading="loading" border stripe height="560">
        <el-table-column prop="created_at" label="操作时间" width="170">
          <template #default="{ row }">{{ fmt(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="actor_name" label="操作人" width="110">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ row.actor_name || '—' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="动作" width="110">
          <template #default="{ row }">
            <el-tag size="small" :type="actionType(row.action)">{{ row.action_display }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="module" label="模块" width="110" />
        <el-table-column prop="target" label="操作对象" min-width="220" show-overflow-tooltip />
        <el-table-column prop="detail" label="详情" min-width="240" show-overflow-tooltip />
        <el-table-column prop="ip" label="IP" width="140" />
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
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { operationLogApi } from '@/api'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const scopeTip = computed(() =>
  auth.isKeeper ? '仅显示本人的操作记录' : '全部人员的关键操作记录（不可篡改）'
)

const list = ref([])
const loading = ref(false)
const filters = reactive({ module: '', action: '' })
const page = ref(1)
const pageSize = 50
const total = ref(0)

const MODULES = ['出入库', '库存盘点', '熏蒸作业', '温湿度监测', '库存批次', '仓房档案', '盘点明细', '账号岗位', '认证']
const ACTIONS = [
  { value: 'login', label: '登录' },
  { value: 'login_fail', label: '登录失败' },
  { value: 'logout', label: '登出' },
  { value: 'create', label: '新增' },
  { value: 'update', label: '修改' },
  { value: 'delete', label: '删除' },
  { value: 'stock_in', label: '入库' },
  { value: 'stock_out', label: '出库' },
  { value: 'stock_correct', label: '单据更正' },
  { value: 'stock_void', label: '单据作废' },
  { value: 'fumigation_advance', label: '熏蒸状态推进' },
  { value: 'stocktake_generate', label: '生成盘点明细' },
  { value: 'stocktake_adjust', label: '盘点调账' },
]

function actionType(a) {
  if (['delete', 'stock_out', 'stocktake_adjust', 'login_fail', 'stock_void'].includes(a)) return 'danger'
  if (['stock_in', 'create', 'stocktake_generate'].includes(a)) return 'success'
  if (['login', 'logout'].includes(a)) return 'info'
  if (['stock_correct'].includes(a)) return 'primary'
  return 'warning'
}
function fmt(t) {
  return t ? t.replace('T', ' ').slice(0, 19) : ''
}

async function load() {
  loading.value = true
  try {
    const params = { page: page.value }
    if (filters.module) params.module = filters.module
    if (filters.action) params.action = filters.action
    const res = await operationLogApi.list(params)
    list.value = res.results ?? []
    total.value = res.count ?? list.value.length
  } finally {
    loading.value = false
  }
}
function reload() {
  page.value = 1
  load()
}
function onPage(p) {
  page.value = p
  load()
}
onMounted(load)
</script>

<style scoped>
.sub {
  color: #909399;
  font-size: 13px;
}
.pager {
  margin-top: 14px;
  justify-content: flex-end;
}
</style>

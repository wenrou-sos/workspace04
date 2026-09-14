<template>
  <div>
    <div class="page-header">
      <h2>账号岗位管理</h2>
      <el-button type="primary" :icon="Plus" @click="openDialog()">新建账号</el-button>
    </div>

    <el-alert
      class="mb16"
      type="info"
      :closable="false"
      title="岗位说明：系统管理员全权；库管主任负责全仓业务与删除、盘点调账（审核）；保管员只能操作本人管辖仓房的日常业务；只读用户可看全部数据与看板但不能修改。"
    />

    <el-card>
      <el-table :data="list" v-loading="loading" border stripe>
        <el-table-column prop="username" label="登录账号" width="130" />
        <el-table-column prop="display_name" label="姓名" width="120" />
        <el-table-column label="岗位" width="130">
          <template #default="{ row }">
            <el-tag :type="roleTag(row.role)" effect="dark">{{ row.role_display }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="phone" label="电话" width="140" />
        <el-table-column label="管辖仓房" min-width="220">
          <template #default="{ row }">
            <span v-if="row.role === 'keeper'">
              <el-tag v-for="c in row.granary_codes" :key="c" size="small" class="g-tag">{{ c }}</el-tag>
              <span v-if="!row.granary_codes.length" class="muted">未分配</span>
            </span>
            <span v-else class="muted">全部仓房{{ row.role === 'viewer' ? '（只读）' : '' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openDialog(row)">编辑/授权</el-button>
            <el-popconfirm
              :title="`确认删除账号 ${row.username}？`"
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

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑账号与授权' : '新建账号'" width="560px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="登录账号" prop="username">
          <el-input v-model="form.username" :disabled="!!form.id" />
        </el-form-item>
        <el-form-item :label="form.id ? '重置密码' : '初始密码'" :prop="form.id ? '' : 'password'">
          <el-input v-model="form.password" type="password" show-password
                    :placeholder="form.id ? '留空表示不修改密码' : '请输入初始密码'" />
        </el-form-item>
        <el-form-item label="姓名" prop="display_name">
          <el-input v-model="form.display_name" />
        </el-form-item>
        <el-form-item label="岗位角色" prop="role">
          <el-select v-model="form.role" style="width: 100%">
            <el-option v-for="r in ROLES" :key="r.value" :label="r.label" :value="r.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model="form.phone" />
        </el-form-item>
        <el-form-item v-if="form.role === 'keeper'" label="管辖仓房">
          <el-select v-model="form.granary_ids" multiple filterable style="width: 100%"
                     placeholder="选择该保管员负责的仓房（可多选）">
            <el-option v-for="g in granaries" :key="g.id"
                       :label="`${g.code} ${g.name}`" :value="g.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { granaryApi, userApi } from '@/api'

const list = ref([])
const granaries = ref([])
const loading = ref(false)

const ROLES = [
  { value: 'admin', label: '系统管理员' },
  { value: 'director', label: '库管主任' },
  { value: 'keeper', label: '保管员' },
  { value: 'viewer', label: '只读用户' },
]
const roleTag = (r) => ({ admin: 'danger', director: 'warning', keeper: 'success', viewer: 'info' }[r])

async function loadData() {
  loading.value = true
  try {
    const res = await userApi.list({ page_size: 200 })
    list.value = res.results ?? res
  } finally {
    loading.value = false
  }
}

const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref()
const emptyForm = () => ({
  id: null, username: '', password: '', display_name: '',
  role: 'keeper', phone: '', granary_ids: [],
})
const form = reactive(emptyForm())
const rules = {
  username: [{ required: true, message: '请输入登录账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入初始密码', trigger: 'blur' }],
  display_name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  role: [{ required: true, message: '请选择岗位', trigger: 'change' }],
}

async function openDialog(row) {
  Object.assign(form, emptyForm())
  if (row) {
    const detail = await userApi.retrieve(row.id)
    // 编辑时需要仓房 ID，列表只给了 code
    const gmap = Object.fromEntries(granaries.value.map((g) => [g.code, g.id]))
    form.id = detail.id
    form.username = detail.username
    form.display_name = detail.display_name
    form.role = detail.role
    form.phone = detail.phone
    form.granary_ids = (detail.granary_codes || []).map((c) => gmap[c]).filter(Boolean)
  }
  dialogVisible.value = true
}

async function save() {
  await formRef.value.validate()
  saving.value = true
  try {
    const payload = { ...form }
    if (form.id) delete payload.id
    if (form.id) await userApi.update(form.id, payload)
    else await userApi.create(payload)
    ElMessage.success('保存成功')
    dialogVisible.value = false
    loadData()
  } finally {
    saving.value = false
  }
}

async function remove(row) {
  await userApi.remove(row.id)
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
.g-tag {
  margin-right: 6px;
}
.muted {
  color: #909399;
  font-size: 13px;
}
</style>

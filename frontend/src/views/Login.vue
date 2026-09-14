<template>
  <div class="login-wrapper">
    <div class="login-card">
      <div class="brand">
        <el-icon :size="40" color="#b8860b"><Wheat /></el-icon>
        <div>
          <h1>智慧粮库</h1>
          <p>粮食储备库管理系统</p>
        </div>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" @keyup.enter="submit">
        <el-form-item prop="username">
          <el-input v-model="form.username" size="large" placeholder="账号" :prefix-icon="User" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" size="large"
                    placeholder="密码" :prefix-icon="Lock" show-password />
        </el-form-item>
        <el-button type="primary" size="large" style="width: 100%" :loading="loading" @click="submit">
          登 录
        </el-button>
      </el-form>

      <el-divider>演示账号</el-divider>
      <div class="demo-accounts">
        <el-tag v-for="a in demoAccounts" :key="a.username" class="acc-tag"
                :type="a.type" effect="plain" @click="fill(a)">
          {{ a.label }}（{{ a.username }}）
        </el-tag>
      </div>
      <p class="hint">点击标签自动填充，密码：admin123 / director123 / keeper123 / viewer123</p>
    </div>
    <div class="footer">中央储备粮 XX 直属库 · 岗位化访问控制</div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const formRef = ref()
const loading = ref(false)
const form = reactive({ username: '', password: '' })
const rules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

const demoAccounts = [
  { username: 'admin', password: 'admin123', label: '系统管理员', type: 'danger' },
  { username: 'director', password: 'director123', label: '库管主任', type: 'warning' },
  { username: 'zhangjg', password: 'keeper123', label: '保管员(张建国/P01)', type: 'success' },
  { username: 'viewer', password: 'viewer123', label: '只读用户', type: 'info' },
]
function fill(a) {
  form.username = a.username
  form.password = a.password
}

async function submit() {
  await formRef.value.validate()
  loading.value = true
  try {
    const user = await auth.login(form.username, form.password)
    ElMessage.success(`欢迎，${user.name}（${user.role_display}）`)
    router.replace(route.query.redirect || '/dashboard')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrapper {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #20322b 0%, #2f5d4f 60%, #b8860b 140%);
}
.login-card {
  width: 420px;
  background: #fff;
  border-radius: 10px;
  padding: 36px 40px 28px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.25);
}
.brand {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 26px;
}
.brand h1 {
  margin: 0;
  font-size: 24px;
  color: #1f2d3d;
}
.brand p {
  margin: 4px 0 0;
  color: #7a8a82;
  font-size: 13px;
}
.demo-accounts {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}
.acc-tag {
  cursor: pointer;
}
.hint {
  text-align: center;
  color: #9aa7a1;
  font-size: 12px;
  margin-top: 14px;
}
.footer {
  margin-top: 24px;
  color: rgba(255, 255, 255, 0.75);
  font-size: 13px;
}
</style>

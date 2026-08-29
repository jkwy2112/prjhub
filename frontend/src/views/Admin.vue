<template>
  <div v-loading="loading">
    <el-tabs v-model="tab">
      <el-tab-pane label="系统概览" name="overview">
        <el-row :gutter="16" class="stat-row">
          <el-col :span="4" v-for="c in statCards" :key="c.label">
            <div class="stat-card" :style="{ borderTop: `3px solid ${c.color}` }">
              <div class="stat-value" :style="{ color: c.color }">{{ c.value }}</div>
              <div class="stat-label">{{ c.label }}</div>
            </div>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-card shadow="never">
              <template #header><b>认证方式</b></template>
              <div class="auth-row">
                <span>本地账号</span>
                <el-tag type="success" size="small">已启用</el-tag>
              </div>
              <div class="auth-row">
                <span>LDAP 域账号</span>
                <el-tag :type="stats.auth_options?.ldap_enabled ? 'success' : 'info'" size="small">
                  {{ stats.auth_options?.ldap_enabled ? '已启用' : '未配置' }}
                </el-tag>
              </div>
              <div class="auth-row">
                <span>企业微信</span>
                <el-tag :type="stats.auth_options?.wecom_enabled ? 'success' : 'info'" size="small">
                  {{ stats.auth_options?.wecom_enabled ? '已启用' : '未配置' }}
                </el-tag>
              </div>
              <p class="hint">在 backend/.env 中配置 LDAP_* / WECOM_* 并重启后端即可启用</p>
            </el-card>
          </el-col>
          <el-col :span="8">
            <el-card shadow="never">
              <template #header><b>任务状态分布 (全系统)</b></template>
              <div v-for="(meta, key) in STATUS_META" :key="key" class="dist-row">
                <el-tag :color="meta.color" style="border: none; color: #fff" size="small">{{ meta.label }}</el-tag>
                <el-progress :percentage="pct(stats.task_status_distribution?.[key] || 0)"
                  :color="meta.color" style="flex: 1; margin: 0 10px" />
                <span class="dist-count">{{ stats.task_status_distribution?.[key] || 0 }}</span>
              </div>
            </el-card>
          </el-col>
          <el-col :span="8">
            <el-card shadow="never">
              <template #header><b>最近注册用户</b></template>
              <div v-for="u in stats.recent_users || []" :key="u.id" class="user-row">
                <el-avatar :size="28" style="background: #409EFF">{{ (u.name || u.username).slice(0, 1) }}</el-avatar>
                <div style="flex: 1">
                  <div>{{ u.name || u.username }}</div>
                  <div style="font-size: 12px; color: #909399">{{ u.username }}</div>
                </div>
                <el-tag size="small" :type="{ local: 'info', ldap: 'warning', wecom: 'success' }[u.auth_type]">
                  {{ { local: '本地', ldap: 'LDAP', wecom: '企业微信' }[u.auth_type] }}
                </el-tag>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>

      <el-tab-pane :label="`用户管理 (${users.length})`" name="users">
        <div class="toolbar">
          <el-input v-model="query" placeholder="搜索用户名/姓名/邮箱" clearable style="width: 240px"
            :prefix-icon="Search" @input="loadUsers" />
          <el-select v-model="authFilter" placeholder="全部来源" clearable style="width: 140px" @change="loadUsers">
            <el-option value="local" label="本地" />
            <el-option value="ldap" label="LDAP" />
            <el-option value="wecom" label="企业微信" />
          </el-select>
          <el-button type="primary" :icon="Plus" @click="openCreate">新建用户</el-button>
        </div>
        <el-table :data="users" style="background: #fff; border-radius: 8px">
          <el-table-column label="用户" min-width="180">
            <template #default="{ row }">
              <div style="display: flex; align-items: center; gap: 8px">
                <el-avatar :size="30" style="background: #409EFF">{{ (row.name || row.username).slice(0, 1) }}</el-avatar>
                <div>
                  <div>{{ row.name || row.username }}
                    <el-tag v-if="row.is_superuser" type="danger" size="small" style="margin-left: 4px">超管</el-tag>
                  </div>
                  <div style="font-size: 12px; color: #909399">{{ row.username }}</div>
                </div>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="email" label="邮箱" min-width="160" show-overflow-tooltip />
          <el-table-column label="来源" width="100">
            <template #default="{ row }">
              <el-tag size="small" :type="{ local: 'info', ldap: 'warning', wecom: 'success' }[row.auth_type]">
                {{ { local: '本地', ldap: 'LDAP', wecom: '企业微信' }[row.auth_type] }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="参与项目" width="90" prop="project_count" />
          <el-table-column label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
                {{ row.is_active ? '正常' : '已禁用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="注册时间" width="110">
            <template #default="{ row }">{{ fmtDate(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="130" fixed="right">
            <template #default="{ row }">
              <el-button text type="primary" size="small" @click="openEdit(row)">编辑</el-button>
              <el-button v-if="row.id !== me.id" text :type="row.is_active ? 'danger' : 'success'" size="small"
                @click="toggleActive(row)">{{ row.is_active ? '禁用' : '启用' }}</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="createDialog" title="新建用户" width="480px">
      <el-form :model="createForm" label-width="90px">
        <el-form-item label="用户名" required>
          <el-input v-model="createForm.username" placeholder="字母/数字/._- , 登录账号" maxlength="64" />
        </el-form-item>
        <el-form-item label="姓名"><el-input v-model="createForm.name" maxlength="128" /></el-form-item>
        <el-form-item label="邮箱"><el-input v-model="createForm.email" maxlength="255" /></el-form-item>
        <el-form-item label="初始密码" required>
          <el-input v-model="createForm.password" type="password" show-password placeholder="至少 6 位" />
        </el-form-item>
        <el-form-item label="超级管理员">
          <el-switch v-model="createForm.is_superuser" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="createUser">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editDialog" :title="`编辑用户 ${editing?.username || ''}`" width="480px">
      <el-form :model="editForm" label-width="110px">
        <el-form-item label="姓名"><el-input v-model="editForm.name" maxlength="128" /></el-form-item>
        <el-form-item label="邮箱"><el-input v-model="editForm.email" maxlength="255" /></el-form-item>
        <el-form-item label="重置密码">
          <el-input v-model="editForm.password" type="password" show-password placeholder="留空则不修改" />
        </el-form-item>
        <el-form-item v-if="editing?.id !== me.id" label="超级管理员">
          <el-switch v-model="editForm.is_superuser" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveUser">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus } from '@element-plus/icons-vue'
import api from '../api'
import { STATUS_META, fmtDate } from '../constants'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const me = computed(() => auth.user || {})
const loading = ref(false)
const saving = ref(false)
const tab = ref('overview')
const stats = reactive({})
const users = ref([])
const query = ref('')
const authFilter = ref('')

const createDialog = ref(false)
const createForm = reactive({ username: '', name: '', email: '', password: '', is_superuser: false })
const editDialog = ref(false)
const editing = ref(null)
const editForm = reactive({ name: '', email: '', password: '', is_superuser: false })

const statCards = computed(() => [
  { label: '用户', value: stats.user_count ?? '-', color: '#409EFF' },
  { label: '活跃用户', value: stats.active_user_count ?? '-', color: '#67C23A' },
  { label: '项目', value: stats.project_count ?? '-', color: '#E6A23C' },
  { label: '归档项目', value: stats.archived_project_count ?? '-', color: '#909399' },
  { label: '任务', value: stats.task_count ?? '-', color: '#F56C6C' },
  { label: 'Git 仓库', value: stats.repo_count ?? '-', color: '#9254de' },
])

function pct(v) {
  const total = Object.values(stats.task_status_distribution || {}).reduce((a, b) => a + b, 0) || 1
  return Math.round((v / total) * 100)
}

async function loadStats() {
  const { data } = await api.get('/admin/stats')
  Object.assign(stats, data)
}

async function loadUsers() {
  const params = {}
  if (query.value) params.q = query.value
  if (authFilter.value) params.auth_type = authFilter.value
  const { data } = await api.get('/admin/users', { params })
  users.value = data
}

function openCreate() {
  Object.assign(createForm, { username: '', name: '', email: '', password: '', is_superuser: false })
  createDialog.value = true
}

async function createUser() {
  if (!createForm.username || createForm.password.length < 6) {
    return ElMessage.warning('请填写用户名和至少 6 位的初始密码')
  }
  saving.value = true
  try {
    await api.post('/admin/users', createForm)
    ElMessage.success('用户创建成功')
    createDialog.value = false
    loadUsers()
  } catch { /* interceptor */ } finally {
    saving.value = false
  }
}

function openEdit(row) {
  editing.value = row
  Object.assign(editForm, { name: row.name, email: row.email, password: '', is_superuser: row.is_superuser })
  editDialog.value = true
}

async function saveUser() {
  saving.value = true
  const payload = { name: editForm.name, email: editForm.email }
  if (editForm.password) {
    if (editForm.password.length < 6) {
      saving.value = false
      return ElMessage.warning('密码至少 6 位')
    }
    payload.password = editForm.password
  }
  if (editing.value.id !== me.value.id) payload.is_superuser = editForm.is_superuser
  try {
    await api.put(`/admin/users/${editing.value.id}`, payload)
    ElMessage.success('已保存')
    editDialog.value = false
    loadUsers()
  } catch { /* interceptor */ } finally {
    saving.value = false
  }
}

async function toggleActive(row) {
  const disabling = row.is_active
  if (disabling) {
    await ElMessageBox.confirm(
      `禁用后「${row.name || row.username}」将无法登录, 再次启用需重置密码`, '禁用用户', { type: 'warning' }
    )
  }
  await api.put(`/admin/users/${row.id}`, { is_active: !disabling })
  ElMessage.success(disabling ? '已禁用' : '已启用, 请为其重置密码')
  loadUsers()
}

onMounted(async () => {
  loading.value = true
  try {
    await Promise.all([loadStats(), loadUsers()])
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.stat-row { margin-bottom: 16px; }
.stat-card { background: #fff; border-radius: 8px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
.stat-value { font-size: 26px; font-weight: 700; }
.stat-label { color: #909399; font-size: 12px; margin-top: 4px; }
.auth-row { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; }
.hint { color: #c0c4cc; font-size: 12px; margin-top: 12px; }
.dist-row { display: flex; align-items: center; margin-bottom: 12px; }
.dist-count { color: #909399; font-size: 13px; width: 28px; text-align: right; }
.user-row { display: flex; align-items: center; gap: 10px; padding: 6px 0; }
.toolbar { display: flex; gap: 10px; margin-bottom: 12px; }
</style>

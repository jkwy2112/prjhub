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
              <div v-for="s in wf.statuses" :key="s.key" class="dist-row">
                <el-tag :color="s.color" style="border: none; color: #fff" size="small">{{ s.name }}</el-tag>
                <el-progress :percentage="pct(stats.task_status_distribution?.[s.key] || 0)"
                  :color="s.color" style="flex: 1; margin: 0 10px" />
                <span class="dist-count">{{ stats.task_status_distribution?.[s.key] || 0 }}</span>
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
      <el-tab-pane label="工作流" name="workflow">
        <el-alert type="info" :closable="false" style="margin-bottom: 12px"
          title="任务状态与流转规则, 保存后立即对全部项目的看板/列表生效; 删除仍有任务的状态时, 这些任务会自动迁移到初始状态" />
        <el-card shadow="never" v-loading="wfLoading">
          <div v-for="(s, idx) in wfEditable" :key="idx" class="wf-row">
            <div class="wf-main">
              <el-color-picker v-model="s.color" size="small" />
              <el-input v-model="s.name" size="small" style="width: 120px" maxlength="32" placeholder="状态名" />
              <el-radio-group :model-value="wfInitialKey" size="small" @update:model-value="setInitial(idx)">
                <el-radio-button :value="s.key" :disabled="!s.is_initial && wfHasInitial !== idx">
                  <span v-if="s.is_initial">初始状态</span>
                  <span v-else>设为初始</span>
                </el-radio-button>
              </el-radio-group>
              <el-checkbox v-model="s.is_done" size="small">完成态</el-checkbox>
              <el-select v-model="s.next_keys" multiple size="small" placeholder="可流转到" style="min-width: 220px">
                <el-option v-for="o in wfEditable" :key="o.key" :value="o.key" :label="o.name"
                  :disabled="o.key === s.key" />
              </el-select>
              <span v-if="wf.usedKeys.includes(s.key)" class="wf-used">有任务使用</span>
            </div>
            <div class="wf-ops">
              <el-button text size="small" :disabled="idx === 0" @click="moveWf(idx, -1)">上移</el-button>
              <el-button text size="small" :disabled="idx === wfEditable.length - 1" @click="moveWf(idx, 1)">下移</el-button>
              <el-button text type="danger" size="small" @click="removeWf(idx)">删除</el-button>
            </div>
          </div>
          <div style="margin-top: 14px; display: flex; gap: 10px">
            <el-button :icon="Plus" @click="addWf">新增状态</el-button>
            <el-button type="primary" :loading="wfSaving" @click="saveWf">保存工作流</el-button>
            <el-button @click="resetWf" :loading="wfSaving">恢复默认</el-button>
          </div>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="认证配置" name="authconfig">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-card shadow="never">
              <template #header>
                <div style="display: flex; justify-content: space-between; align-items: center">
                  <b>LDAP 域认证</b>
                  <el-switch v-model="ldapForm.enabled" active-text="启用" />
                </div>
              </template>
              <el-form :model="ldapForm" label-width="110px" size="small">
                <el-form-item label="服务器">
                  <el-input v-model="ldapForm.server" placeholder="ldap://ldap.corp.com:389" />
                </el-form-item>
                <el-form-item label="启用 SSL">
                  <el-switch v-model="ldapForm.use_ssl" />
                </el-form-item>
                <el-form-item label="Bind DN">
                  <el-input v-model="ldapForm.bind_dn" placeholder="cn=admin,dc=corp,dc=com" />
                </el-form-item>
                <el-form-item label="Bind 密码">
                  <el-input v-model="ldapForm.bind_password" type="password" show-password placeholder="服务账号密码" />
                </el-form-item>
                <el-form-item label="搜索基准">
                  <el-input v-model="ldapForm.search_base" placeholder="ou=people,dc=corp,dc=com" />
                </el-form-item>
                <el-form-item label="搜索过滤器">
                  <el-input v-model="ldapForm.search_filter" placeholder="(uid={login})" />
                </el-form-item>
                <el-form-item label="用户名属性">
                  <el-input v-model="ldapForm.attr_username" style="width: 130px" placeholder="uid" />
                </el-form-item>
                <el-form-item label="姓名属性">
                  <el-input v-model="ldapForm.attr_display_name" style="width: 130px" placeholder="cn" />
                </el-form-item>
                <el-form-item label="邮箱属性">
                  <el-input v-model="ldapForm.attr_email" style="width: 130px" placeholder="mail" />
                </el-form-item>
                <div style="display: flex; gap: 10px">
                  <el-button type="primary" size="small" :loading="ldapSaving" @click="saveLdap">保存</el-button>
                  <el-button size="small" :loading="ldapTesting" @click="testLdap">测试连接</el-button>
                </div>
              </el-form>
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card shadow="never">
              <template #header>
                <div style="display: flex; justify-content: space-between; align-items: center">
                  <b>企业微信</b>
                  <el-switch v-model="wecomForm.enabled" active-text="启用" />
                </div>
              </template>
              <el-form :model="wecomForm" label-width="110px" size="small">
                <el-form-item label="Corp ID">
                  <el-input v-model="wecomForm.corp_id" placeholder="ww1234567890abcdef" />
                </el-form-item>
                <el-form-item label="Corp Secret">
                  <el-input v-model="wecomForm.corp_secret" type="password" show-password />
                </el-form-item>
                <el-form-item label="Agent ID">
                  <el-input v-model="wecomForm.agent_id" placeholder="1000002" />
                </el-form-item>
                <div style="display: flex; gap: 10px">
                  <el-button type="primary" size="small" :loading="wecomSaving" @click="saveWecom">保存</el-button>
                  <el-button size="small" :loading="wecomTesting" @click="testWecom">测试连接</el-button>
                </div>
              </el-form>
              <el-alert style="margin-top: 14px" type="info" :closable="false"
                title="保存启用后, 登录页将出现「企业微信登录」按钮, 授权回调地址需配置为 {站点地址}/login" />
            </el-card>
          </el-col>
        </el-row>
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
import { TYPE_META, PRIORITY_META, fmtDate } from '../constants'
import { useAuthStore } from '../stores/auth'
import { useWorkflowStore } from '../stores/workflow'

const auth = useAuthStore()
const wf = useWorkflowStore()
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

// ---------- workflow editor ----------

const wfEditable = ref([])
const wfLoading = ref(false)
const wfSaving = ref(false)

const wfInitialKey = computed(() => wfEditable.value.find((s) => s.is_initial)?.key || '')
const wfHasInitial = computed(() => wfEditable.value.findIndex((s) => s.is_initial))

function syncWfEditable() {
  wfEditable.value = wf.statuses.map((s) => ({ ...s, next_keys: [...(s.next_keys || [])] }))
}

function setInitial(idx) {
  wfEditable.value.forEach((s, i) => (s.is_initial = i === idx))
}

function moveWf(idx, delta) {
  const arr = wfEditable.value
  const [item] = arr.splice(idx, 1)
  arr.splice(idx + delta, 0, item)
}

function removeWf(idx) {
  wfEditable.value.splice(idx, 1)
}

function addWf() {
  const n = wfEditable.value.length + 1
  wfEditable.value.push({
    key: `custom_${Date.now().toString(36)}`,
    name: `新状态${n}`,
    color: '#9254de',
    is_initial: false,
    is_done: false,
    next_keys: [],
  })
}

async function saveWf() {
  wfSaving.value = true
  try {
    const payload = wfEditable.value.map((s) => ({
      key: s.key, name: s.name, color: s.color,
      is_initial: !!s.is_initial, is_done: !!s.is_done,
      next_keys: (s.next_keys || []).filter((k) => k !== s.key && wfEditable.value.some((x) => x.key === k)),
    }))
    const { data } = await api.put('/workflow', { statuses: payload })
    if (data.migrated) ElMessage.warning(`已保存, ${data.migrated} 个任务被迁移到初始状态`)
    else ElMessage.success('工作流已保存')
    await wf.fetch(true)
    syncWfEditable()
  } catch { /* interceptor */ } finally {
    wfSaving.value = false
  }
}

async function resetWf() {
  await ElMessageBox.confirm('恢复为默认工作流 (待办/进行中/测试中/已完成)? 自定义状态将被移除, 其任务迁回初始状态',
    '恢复默认', { type: 'warning' })
  wfSaving.value = true
  try {
    await api.post('/workflow/reset')
    ElMessage.success('已恢复默认工作流')
    await wf.fetch(true)
    syncWfEditable()
  } finally {
    wfSaving.value = false
  }
}

// ---------- auth config (LDAP / WeCom) ----------

const ldapForm = reactive({
  enabled: false, server: '', use_ssl: false, bind_dn: '', bind_password: '',
  search_base: '', search_filter: '(uid={login})', attr_username: 'uid',
  attr_display_name: 'cn', attr_email: 'mail',
})
const wecomForm = reactive({ enabled: false, corp_id: '', corp_secret: '', agent_id: '' })
const ldapSaving = ref(false)
const ldapTesting = ref(false)
const wecomSaving = ref(false)
const wecomTesting = ref(false)

async function loadAuthConfig() {
  const { data } = await api.get('/admin/auth-config')
  Object.assign(ldapForm, data.ldap)
  Object.assign(wecomForm, data.wecom)
}

function cleanSecret(v) {
  return v === '******' || v === null ? undefined : v
}

async function saveLdap() {
  ldapSaving.value = true
  try {
    const payload = { ...ldapForm, bind_password: cleanSecret(ldapForm.bind_password) }
    await api.put('/admin/auth-config/ldap', payload)
    ElMessage.success('LDAP 配置已保存')
    await loadAuthConfig()
  } catch { /* interceptor */ } finally {
    ldapSaving.value = false
  }
}

async function testLdap() {
  ldapTesting.value = true
  try {
    const payload = { ...ldapForm, bind_password: cleanSecret(ldapForm.bind_password) }
    const { data } = await api.post('/admin/auth-config/ldap/test', payload)
    data.ok ? ElMessage.success(data.message) : ElMessage.error(data.message)
  } catch { /* interceptor */ } finally {
    ldapTesting.value = false
  }
}

async function saveWecom() {
  wecomSaving.value = true
  try {
    const payload = { ...wecomForm, corp_secret: cleanSecret(wecomForm.corp_secret) }
    await api.put('/admin/auth-config/wecom', payload)
    ElMessage.success('企业微信配置已保存')
    auth.fetchOptions()
    await loadAuthConfig()
  } catch { /* interceptor */ } finally {
    wecomSaving.value = false
  }
}

async function testWecom() {
  wecomTesting.value = true
  try {
    const payload = { ...wecomForm, corp_secret: cleanSecret(wecomForm.corp_secret) }
    const { data } = await api.post('/admin/auth-config/wecom/test', payload)
    data.ok ? ElMessage.success(data.message) : ElMessage.error(data.message)
  } catch { /* interceptor */ } finally {
    wecomTesting.value = false
  }
}

onMounted(async () => {
  loading.value = true
  try {
    await Promise.all([
      wf.fetch().then(syncWfEditable),
      loadStats(),
      loadUsers(),
      loadAuthConfig(),
    ])
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
.wf-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 0; border-bottom: 1px dashed #ebeef5;
}
.wf-main { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.wf-used { color: #e6a23c; font-size: 12px; }
.wf-ops { flex-shrink: 0; }
</style>

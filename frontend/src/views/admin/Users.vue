<template>
  <div>
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
    <el-table :data="users" v-loading="loading" style="background: #fff; border-radius: 8px">
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
      <el-table-column prop="dept" label="部门" width="120" show-overflow-tooltip />
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

    <el-dialog v-model="createDialog" title="新建用户" width="480px">
      <el-form :model="createForm" label-width="90px">
        <el-form-item label="用户名" required>
          <el-input v-model="createForm.username" placeholder="字母/数字/._- , 登录账号" maxlength="64" />
        </el-form-item>
        <el-form-item label="姓名"><el-input v-model="createForm.name" maxlength="128" /></el-form-item>
        <el-form-item label="邮箱"><el-input v-model="createForm.email" maxlength="255" /></el-form-item>
        <el-form-item label="部门"><el-input v-model="createForm.dept" maxlength="128" placeholder="如: 技术部" /></el-form-item>
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
        <el-form-item label="部门"><el-input v-model="editForm.dept" maxlength="128" /></el-form-item>
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
import api from '../../api'
import { fmtDate } from '../../constants'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const me = computed(() => auth.user || {})
const loading = ref(false)
const saving = ref(false)
const users = ref([])
const query = ref('')
const authFilter = ref('')

const createDialog = ref(false)
const createForm = reactive({ username: '', name: '', email: '', dept: '', password: '', is_superuser: false })
const editDialog = ref(false)
const editing = ref(null)
const editForm = reactive({ name: '', dept: '', email: '', password: '', is_superuser: false })

async function loadUsers() {
  loading.value = true
  try {
    const params = {}
    if (query.value) params.q = query.value
    if (authFilter.value) params.auth_type = authFilter.value
    const { data } = await api.get('/admin/users', { params })
    users.value = data
  } finally {
    loading.value = false
  }
}

function openCreate() {
  Object.assign(createForm, { username: '', name: '', email: '', dept: '', password: '', is_superuser: false })
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
  Object.assign(editForm, { name: row.name, dept: row.dept || '', email: row.email, password: '', is_superuser: row.is_superuser })
  editDialog.value = true
}

async function saveUser() {
  saving.value = true
  const payload = { name: editForm.name, dept: editForm.dept, email: editForm.email }
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

onMounted(loadUsers)
</script>

<style scoped>
.toolbar { display: flex; gap: 10px; margin-bottom: 12px; }
</style>

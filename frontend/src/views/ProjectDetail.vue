<template>
  <div v-if="project">
    <div class="pd-head">
      <div class="pd-title">
        <span class="pd-key" :style="{ background: project.color }">{{ project.key }}</span>
        <h2>{{ project.name }}</h2>
        <el-tag v-if="project.is_archived" type="info">已归档</el-tag>
      </div>
      <div>
        <el-button v-if="canAdmin && !project.repo_path" :icon="FolderOpened" @click="initRepo">
          初始化 Git 仓库
        </el-button>
        <el-button type="primary" :icon="Plus" @click="openCreate">新建任务</el-button>
      </div>
    </div>

    <el-tabs v-model="tab">
      <el-tab-pane label="看板" name="kanban">
        <div class="kanban" v-loading="loadingTasks">
          <div v-for="col in STATUS_ORDER" :key="col" class="kanban-col"
            @dragover.prevent @drop="onDrop($event, col)">
            <div class="kanban-col-head">
              <el-tag :color="STATUS_META[col].color" effect="dark" style="border: none" size="small">
                {{ STATUS_META[col].label }}
              </el-tag>
              <span class="kanban-count">{{ byStatus[col.key]?.length || 0 }}</span>
            </div>
            <div v-for="t in byStatus[col.key] || []" :key="t.id" class="kanban-card" draggable="true"
              @dragstart="onDragStart($event, t)" @click="openTask(t)">
              <div class="card-title">
                <el-tag effect="dark" size="small" :color="TYPE_META[t.type].color" style="border: none">
                  {{ TYPE_META[t.type].label }}
                </el-tag>
                <span class="card-key">{{ project.key }}-{{ t.number }}</span>
              </div>
              <div class="card-name">{{ t.title }}</div>
              <div class="card-foot">
                <el-tag size="small" :type="PRIORITY_META[t.priority].type">
                  {{ PRIORITY_META[t.priority].label }}
                </el-tag>
                <span v-if="t.due_date && !isDone(t.status) && isOverdue(t)" class="overdue">已逾期</span>
                <span class="card-meta">
                  <el-icon><ChatDotRound /></el-icon>{{ t.comments_count }}
                  <el-avatar v-if="memberMap[t.assignee_id]" :size="20" style="margin-left: 6px; background: #409EFF">
                    {{ (memberMap[t.assignee_id].user.name || memberMap[t.assignee_id].user.username).slice(0, 1) }}
                  </el-avatar>
                </span>
              </div>
            </div>
            <el-button v-if="col === 'todo'" text size="small" class="add-card" @click="openCreate">
              + 添加任务
            </el-button>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="列表" name="list">
        <div class="list-toolbar">
          <el-input v-model="listQuery" placeholder="搜索标题或编号" clearable style="width: 240px" :prefix-icon="Search" />
          <el-select v-model="listStatus" placeholder="全部状态" clearable style="width: 140px">
            <el-option v-for="(m, k) in STATUS_META" :key="k" :value="k" :label="m.label" />
          </el-select>
          <el-select v-model="listAssignee" placeholder="全部负责人" clearable style="width: 140px">
            <el-option v-for="m in members" :key="m.user_id" :value="m.user_id"
              :label="m.user.name || m.user.username" />
          </el-select>
        </div>
        <el-table :data="filteredTasks" v-loading="loadingTasks" @row-click="openTask" style="cursor: pointer">
          <el-table-column label="编号" width="100">
            <template #default="{ row }">{{ project.key }}-{{ row.number }}</template>
          </el-table-column>
          <el-table-column prop="title" label="标题" min-width="240" show-overflow-tooltip />
          <el-table-column label="类型" width="80">
            <template #default="{ row }">
              <el-tag effect="dark" size="small" :color="TYPE_META[row.type].color" style="border: none">
                {{ TYPE_META[row.type].label }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag size="small" :color="colorOf(row.status)" style="border: none; color: #fff">
                {{ labelOf(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="优先级" width="80">
            <template #default="{ row }">
              <el-tag size="small" :type="PRIORITY_META[row.priority].type">{{ PRIORITY_META[row.priority].label }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="负责人" width="110">
            <template #default="{ row }">{{ memberMap[row.assignee_id]?.user.name || '未指派' }}</template>
          </el-table-column>
          <el-table-column label="截止日期" width="110">
            <template #default="{ row }">
              <span :class="{ overdue: isOverdue(row) }">{{ fmtDate(row.due_date) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="90" fixed="right">
            <template #default="{ row }">
              <el-button text type="danger" size="small" @click.stop="removeTask(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane :label="`成员 (${members.length})`" name="members">
        <div class="list-toolbar" v-if="canAdmin">
          <el-select v-model="addUserId" filterable remote :remote-method="searchUsers" placeholder="搜索用户并添加"
            style="width: 260px" clearable>
            <el-option v-for="u in userOptions" :key="u.id" :value="u.id"
              :label="`${u.name || u.username} (${u.username})`" />
          </el-select>
          <el-select v-model="addRole" style="width: 120px">
            <el-option value="member" label="成员" />
            <el-option value="admin" label="管理员" />
          </el-select>
          <el-button type="primary" :disabled="!addUserId" @click="addMember">添加成员</el-button>
        </div>
        <el-table :data="members" style="background: #fff; border-radius: 8px">
          <el-table-column label="用户" min-width="180">
            <template #default="{ row }">
              <div style="display: flex; align-items: center; gap: 8px">
                <el-avatar :size="30" style="background: #409EFF">
                  {{ (row.user.name || row.user.username).slice(0, 1) }}
                </el-avatar>
                <div>
                  <div>{{ row.user.name || row.user.username }}</div>
                  <div style="font-size: 12px; color: #909399">{{ row.user.username }}</div>
                </div>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="登录方式" width="120">
            <template #default="{ row }">
              <el-tag size="small" :type="{ local: 'info', ldap: 'warning', wecom: 'success' }[row.user.auth_type]">
                {{ { local: '本地', ldap: 'LDAP', wecom: '企业微信' }[row.user.auth_type] }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="角色" width="180">
            <template #default="{ row }">
              <el-select v-if="canAdmin && row.role !== 'owner'" :model-value="row.role" size="small"
                style="width: 120px" @change="(role) => changeRole(row, role)">
                <el-option value="member" label="成员" />
                <el-option value="admin" label="管理员" />
              </el-select>
              <el-tag v-else :type="ROLE_META[row.role].type">{{ ROLE_META[row.role].label }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="加入时间" width="120">
            <template #default="{ row }">{{ fmtDate(row.joined_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="90">
            <template #default="{ row }">
              <el-button v-if="canAdmin && row.role !== 'owner'" text type="danger" size="small"
                @click="removeMember(row)">移除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="动态" name="activity">
        <el-card shadow="never">
          <el-timeline v-if="activities.length">
            <el-timeline-item v-for="a in activities" :key="a.id" :timestamp="fmtDateTime(a.created_at)"
              placement="top" :color="{ create: '#67C23A', delete: '#F56C6C', status: '#409EFF', comment: '#909399' }[a.action] || '#409EFF'">
              <b>{{ a.user?.name || a.user?.username || '系统' }}</b><span style="margin-left: 6px">{{ a.target }}</span>
            </el-timeline-item>
          </el-timeline>
          <el-empty v-else description="暂无动态" :image-size="80" />
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="设置" name="settings" v-if="canAdmin">
        <el-card shadow="never" style="max-width: 640px">
          <el-form :model="settingsForm" label-width="90px">
            <el-form-item label="项目名称"><el-input v-model="settingsForm.name" /></el-form-item>
            <el-form-item label="描述"><el-input v-model="settingsForm.description" type="textarea" :rows="3" /></el-form-item>
            <el-form-item label="颜色"><el-color-picker v-model="settingsForm.color" /></el-form-item>
            <el-form-item label="归档">
              <el-switch v-model="settingsForm.is_archived" active-text="归档后项目只读展示" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="savingSettings" @click="saveSettings">保存设置</el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card shadow="never" style="max-width: 640px; margin-top: 16px">
          <template #header><b>Git 仓库</b></template>
          <template v-if="project.repo_path">
            <el-descriptions :column="1" border size="small">
              <el-descriptions-item label="仓库路径">
                <el-text type="primary" size="small">{{ project.repo_path }}</el-text>
              </el-descriptions-item>
              <el-descriptions-item label="克隆地址">
                <code class="clone-url">git clone {{ project.repo_path.replace(/^.*repos/, 'git@prjhub:repos') }}</code>
              </el-descriptions-item>
            </el-descriptions>
            <p class="repo-hint">服务器端 bare 仓库, 团队成员可 push 首个提交: <code>git push origin {{ project.key.toLowerCase() }}:main</code></p>
          </template>
          <el-empty v-else description="尚未初始化 Git 仓库" :image-size="70">
            <el-button type="primary" :icon="FolderOpened" @click="initRepo">初始化仓库</el-button>
          </el-empty>
        </el-card>

        <el-card shadow="never" style="max-width: 640px; margin-top: 16px">
          <template #header><b style="color: #f56c6c">危险操作</b></template>
          <el-button type="danger" plain :disabled="project.my_role !== 'owner'" @click="deleteProject">
            删除项目 (含全部任务与 Git 仓库)
          </el-button>
          <p v-if="project.my_role !== 'owner'" class="repo-hint">仅项目所有者可删除</p>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <TaskDialog v-model="taskDialog" :project-id="project.id" :members="members" :task="editingTask"
      @saved="loadTasks" />
    <TaskDrawer v-model="taskDrawer" :task-id="drawerTaskId" :project-key="project.key" :members="members"
      :statuses="statuses" @changed="loadTasks" />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, FolderOpened, ChatDotRound } from '@element-plus/icons-vue'
import api from '../api'
import { STATUS_META, STATUS_ORDER, TYPE_META, PRIORITY_META, ROLE_META, fmtDate, fmtDateTime } from '../constants'
import TaskDialog from '../components/TaskDialog.vue'
import TaskDrawer from '../components/TaskDrawer.vue'

const statuses = STATUS_ORDER.map((k) => ({ key: k, ...STATUS_META[k], is_done: k === 'done' }))
const labelOf = (k) => STATUS_META[k]?.label || k
const colorOf = (k) => STATUS_META[k]?.color || '#909399'
const isDone = (k) => k === 'done'

const route = useRoute()
const router = useRouter()
const projectId = Number(route.params.id)

const project = ref(null)
const tasks = ref([])
const members = ref([])
const activities = ref([])
const loadingTasks = ref(false)
const tab = ref('kanban')

const taskDialog = ref(false)
const editingTask = ref(null)
const taskDrawer = ref(false)
const drawerTaskId = ref(null)
let dragTask = null

const listQuery = ref('')
const listStatus = ref('')
const listAssignee = ref(null)

const userOptions = ref([])
const addUserId = ref(null)
const addRole = ref('member')

const settingsForm = reactive({ name: '', description: '', color: '', is_archived: false })
const savingSettings = ref(false)

const canAdmin = computed(() => ['owner', 'admin'].includes(project.value?.my_role))
const memberMap = computed(() => Object.fromEntries(members.value.map((m) => [m.user_id, m])))
const byStatus = computed(() => {
  const map = {}
  for (const s of STATUS_ORDER) map[s] = []
  for (const t of tasks.value) {
    if (map[t.status]) map[t.status].push(t)
    else map.todo.push(t)
  }
  return map
})
const filteredTasks = computed(() =>
  tasks.value.filter((t) => {
    if (listStatus.value && t.status !== listStatus.value) return false
    if (listAssignee.value && t.assignee_id !== listAssignee.value) return false
    if (listQuery.value) {
      const q = listQuery.value.toLowerCase()
      const key = `${project.value.key}-${t.number}`.toLowerCase()
      if (!t.title.toLowerCase().includes(q) && !key.includes(q)) return false
    }
    return true
  })
)

function isOverdue(t) {
  return t.due_date && new Date(t.due_date) < new Date() && !isDone(t.status)
}

async function loadProject() {
  const { data } = await api.get(`/projects/${projectId}`)
  project.value = data
  Object.assign(settingsForm, { name: data.name, description: data.description, color: data.color, is_archived: data.is_archived })
}

async function loadTasks() {
  loadingTasks.value = true
  try {
    const { data } = await api.get(`/projects/${projectId}/tasks`)
    tasks.value = data
  } finally {
    loadingTasks.value = false
  }
}

async function loadMembers() {
  const { data } = await api.get(`/projects/${projectId}/members`)
  members.value = data
}

async function loadActivities() {
  const { data } = await api.get(`/projects/${projectId}/activities`)
  activities.value = data
}

function openCreate() {
  editingTask.value = null
  taskDialog.value = true
}

function openTask(t) {
  drawerTaskId.value = t.id
  taskDrawer.value = true
}

function onDragStart(_, t) {
  dragTask = t
}

async function onDrop(_, status) {
  if (!dragTask || dragTask.status === status) return
  const t = dragTask
  dragTask = null
  try {
    await api.put(`/tasks/${t.id}`, { status })
    await loadTasks()
  } catch {
    await loadTasks()
  }
}

async function removeTask(t) {
  await ElMessageBox.confirm(`确定删除任务「${t.title}」?`, '删除任务', { type: 'warning' })
  await api.delete(`/tasks/${t.id}`)
  ElMessage.success('已删除')
  loadTasks()
}

async function searchUsers(q) {
  if (!q) return (userOptions.value = [])
  const { data } = await api.get('/users', { params: { q } })
  userOptions.value = data.filter((u) => !memberMap.value[u.id])
}

async function addMember() {
  await api.post(`/projects/${projectId}/members`, { user_id: addUserId.value, role: addRole.value })
  ElMessage.success('成员已添加')
  addUserId.value = null
  loadMembers()
}

async function changeRole(row, role) {
  await api.put(`/projects/${projectId}/members/${row.id}`, { role })
  ElMessage.success('角色已更新')
  loadMembers()
}

async function removeMember(row) {
  await ElMessageBox.confirm(`确定将 ${row.user.name || row.user.username} 移出项目?`, '移除成员', { type: 'warning' })
  await api.delete(`/projects/${projectId}/members/${row.id}`)
  ElMessage.success('已移除')
  loadMembers()
}

async function initRepo() {
  const { data } = await api.post(`/projects/${projectId}/init-repo`)
  project.value = data
  ElMessage.success('Git 仓库初始化成功: ' + data.repo_path)
}

async function saveSettings() {
  savingSettings.value = true
  try {
    const { data } = await api.put(`/projects/${projectId}`, settingsForm)
    project.value = { ...project.value, ...data }
    ElMessage.success('已保存')
  } finally {
    savingSettings.value = false
  }
}

async function deleteProject() {
  await ElMessageBox.confirm('此操作将删除项目、全部任务以及 Git 仓库, 不可恢复!', '删除项目',
    { type: 'error', confirmButtonText: '确认删除' })
  await api.delete(`/projects/${projectId}`)
  ElMessage.success('项目已删除')
  router.replace('/projects')
}

onMounted(async () => {
  await Promise.all([loadProject(), loadTasks(), loadMembers(), loadActivities()])
  if (route.query.task) {
    drawerTaskId.value = Number(route.query.task)
    taskDrawer.value = true
  }
})

watch(tab, (v) => {
  if (v === 'activity') loadActivities()
})
</script>

<style scoped>
.pd-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.pd-title { display: flex; align-items: center; gap: 12px; }
.pd-title h2 { font-size: 20px; color: #303133; }
.pd-key { color: #fff; font-weight: 700; font-size: 13px; padding: 4px 10px; border-radius: 8px; }
.wf-bind-row { display: flex; gap: 10px; }
.wf-bind-tip { color: #909399; font-size: 12px; margin-top: 10px; }
.kanban { display: flex; gap: 12px; align-items: flex-start; overflow-x: auto; padding-bottom: 12px; }
.kanban-col {
  flex: 1; min-width: 240px; background: #eceef1; border-radius: 10px;
  padding: 10px; min-height: 400px;
}
.kanban-col-head { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; padding: 0 6px; }
.kb-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.kb-title { font-size: var(--ph-font-sm); color: var(--ph-text-primary); flex: 1; }
.kb-count { background: var(--ph-fill); color: var(--ph-text-secondary); font-size: 11px;
  min-width: 20px; height: 18px; line-height: 18px; text-align: center; border-radius: 9px; padding: 0 6px; }
.kanban-count { color: #909399; font-size: 12px; }
.kanban-card {
  background: var(--ph-fill-blank, #fff); border-radius: var(--ph-radius-md);
  padding: 10px 12px; margin-bottom: 8px; cursor: pointer;
  border: 1px solid var(--ph-border-lighter); border-left: 3px solid var(--card-accent, var(--ph-border));
  box-shadow: var(--ph-shadow-1); transition: box-shadow .15s, transform .15s;
}
.kanban-card:hover { box-shadow: var(--ph-shadow-2); transform: translateY(-1px); }
.card-title { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.card-key { color: #c0c4cc; font-size: 11px; }
.card-name { font-size: 13px; color: #303133; margin-bottom: 8px; }
.card-foot { display: flex; align-items: center; gap: 6px; }
.card-meta { margin-left: auto; display: flex; align-items: center; gap: 3px; color: #909399; font-size: 12px; }
.overdue { color: var(--ph-danger); font-size: 11px; }
.due-chip { font-size: 10px; padding: 1px 6px; border-radius: 4px;
  background: var(--ph-fill-light); color: var(--ph-text-secondary); }
.due-chip.overdue { background: var(--ph-danger-light-9); color: var(--ph-danger); font-weight: 600; }
.add-card { width: 100%; color: #909399; }
.list-toolbar { display: flex; gap: 10px; margin-bottom: 12px; }
.clone-url {
  display: inline-block; background: #f5f7fa; padding: 4px 8px; border-radius: 4px;
  font-size: 12px; color: #409eff;
}
.repo-hint { color: #909399; font-size: 12px; margin-top: 10px; }
</style>

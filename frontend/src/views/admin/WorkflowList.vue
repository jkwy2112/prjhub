<template>
  <div>
    <div class="toolbar">
      <span class="tip">工作流可绑定到项目 (项目设置 → 工作流); 节点支持处理人规则与拖拽式设计</span>
      <el-button type="primary" :icon="Plus" @click="openCreate">新建工作流</el-button>
    </div>
    <el-table :data="workflows" v-loading="loading" style="background: #fff; border-radius: 8px">
      <el-table-column prop="name" label="名称" min-width="160">
        <template #default="{ row }">
          {{ row.name }}
          <el-tag v-if="row.is_default" type="danger" size="small" style="margin-left: 6px">默认</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="描述" min-width="220" show-overflow-tooltip />
      <el-table-column prop="node_count" label="状态数" width="80" />
      <el-table-column prop="project_count" label="绑定项目" width="90" />
      <el-table-column label="操作" width="250" fixed="right">
        <template #default="{ row }">
          <el-button text type="primary" size="small" :icon="Share"
            @click="$router.push(`/admin/workflows/${row.id}`)">设计</el-button>
          <el-button v-if="!row.is_default" text size="small" @click="setDefault(row)">设为默认</el-button>
          <el-button v-if="!row.is_default" text type="danger" size="small" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="createDialog" title="新建工作流" width="480px">
      <el-form :model="createForm" label-width="90px">
        <el-form-item label="名称" required><el-input v-model="createForm.name" maxlength="64" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="createForm.description" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <p class="tip" style="margin: -10px 0 14px 100px">创建后以「默认四状态」为模板, 可在设计器中自由修改</p>
      <template #footer>
        <el-button @click="createDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="create">创建并设计</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Share } from '@element-plus/icons-vue'
import api from '../../api'

const router = useRouter()
const loading = ref(false)
const saving = ref(false)
const workflows = ref([])
const createDialog = ref(false)
const createForm = reactive({ name: '', description: '' })

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/workflows')
    workflows.value = data
  } finally {
    loading.value = false
  }
}

function openCreate() {
  Object.assign(createForm, { name: '', description: '' })
  createDialog.value = true
}

async function create() {
  if (!createForm.name.trim()) return ElMessage.warning('请填写工作流名称')
  saving.value = true
  try {
    const { data } = await api.post('/workflows', createForm)
    createDialog.value = false
    router.push(`/admin/workflows/${data.id}`)
  } catch { /* interceptor */ } finally {
    saving.value = false
  }
}

async function setDefault(row) {
  await api.post(`/workflows/${row.id}/default`)
  ElMessage.success(`「${row.name}」已设为默认工作流`)
  load()
}

async function remove(row) {
  await ElMessageBox.confirm(
    `删除「${row.name}」? 仅未被项目绑定时可删除`, '删除工作流', { type: 'warning' }
  )
  await api.delete(`/workflows/${row.id}`)
  ElMessage.success('已删除')
  load()
}

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.tip { color: #909399; font-size: 12px; }
</style>

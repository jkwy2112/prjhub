<template>
  <div>
    <div class="toolbar">
      <el-radio-group v-model="statusFilter">
        <el-radio-button value="">全部未完成</el-radio-button>
        <el-radio-button v-for="(m, k) in STATUS_META" :key="k" :value="k">{{ m.label }}</el-radio-button>
      </el-radio-group>
    </div>
    <el-table :data="tasks" v-loading="loading" @row-click="open" style="cursor: pointer; background: #fff; border-radius: 8px">
      <el-table-column label="任务" min-width="280">
        <template #default="{ row }">
          <span class="task-title-cell">
            <el-tag effect="dark" size="small" :color="TYPE_META[row.type].color" style="border: none">
              {{ TYPE_META[row.type].label }}
            </el-tag>
            {{ row.title }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="所属项目" width="140">
        <template #default="{ row }">{{ projectMap[row.project_id]?.name || `#${row.project_id}` }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag size="small" :color="STATUS_META[row.status].color" style="border: none; color: #fff">
            {{ STATUS_META[row.status].label }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="优先级" width="80">
        <template #default="{ row }">
          <el-tag size="small" :type="PRIORITY_META[row.priority].type">{{ PRIORITY_META[row.priority].label }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="截止" width="110">
        <template #default="{ row }">{{ fmtDate(row.due_date) }}</template>
      </el-table-column>
      <el-table-column label="更新时间" width="160">
        <template #default="{ row }">{{ fmtDateTime(row.updated_at) }}</template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!loading && !tasks.length" description="没有找到任务" />
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'
import { STATUS_META, TYPE_META, PRIORITY_META, fmtDate, fmtDateTime } from '../constants'

const router = useRouter()
const loading = ref(false)
const tasks = ref([])
const projectMap = ref({})
const statusFilter = ref('')

async function load() {
  loading.value = true
  try {
    const params = statusFilter.value ? { status: statusFilter.value } : {}
    const { data } = await api.get('/my/tasks', { params })
    tasks.value = data
    const missing = [...new Set(data.map((t) => t.project_id))].filter((id) => !projectMap.value[id])
    await Promise.all(missing.map(async (id) => {
      try {
        const p = await api.get(`/projects/${id}`)
        projectMap.value[id] = p.data
      } catch { /* ignore */ }
    }))
  } finally {
    loading.value = false
  }
}

function open(row) {
  router.push(`/projects/${row.project_id}?task=${row.id}`)
}

onMounted(load)
watch(statusFilter, load)
</script>

<style scoped>
.toolbar { margin-bottom: 14px; }
.task-title-cell { display: flex; align-items: center; gap: 8px; }
</style>

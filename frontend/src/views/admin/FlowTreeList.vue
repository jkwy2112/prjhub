<template>
  <div>
    <div class="toolbar">
      <span class="tip">可视化设计的审批流程 (钉钉/WFlow 风格): 审批人 · 条件分支 · 并行分支 · 会签/或签/票签</span>
      <el-button type="primary" :icon="Plus" @click="create">新建流程</el-button>
    </div>
    <el-table :data="list" v-loading="loading" style="background: #fff; border-radius: 8px">
      <el-table-column prop="name" label="名称" min-width="180" />
      <el-table-column prop="key" label="标识" width="180" />
      <el-table-column label="来源" width="120">
        <template #default="{ row }">
          <el-tag size="small" :type="row.has_tree ? 'success' : 'info'">
            {{ row.has_tree ? '可视化设计' : '内置模板' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="version" label="版本" width="70" />
      <el-table-column label="发布时间" width="160">
        <template #default="{ row }">{{ fmtDateTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="170" fixed="right">
        <template #default="{ row }">
          <el-button text type="primary" size="small" :icon="Edit"
            :disabled="!row.has_tree" @click="$router.push(`/admin/flows/${row.id}`)">设计</el-button>
          <el-button text size="small" :icon="View"
            @click="$router.push(`/approvals`)">去发起</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Edit, View } from '@element-plus/icons-vue'
import api from '../../api'
import { fmtDateTime } from '../../constants'

const router = useRouter()
const loading = ref(false)
const list = ref([])

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/approvals/definitions')
    list.value = data
  } finally {
    loading.value = false
  }
}

function create() {
  router.push('/admin/flows/new')
}

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.tip { color: #909399; font-size: 12px; }
</style>

<template>
  <div class="flow-panel">
    <div class="panel-toolbar">
      <span class="tip">审批流程模板: 发起人从此处发起审批; 模板按分组管理</span>
      <div>
        <el-button type="primary" :icon="Plus" @click="create">新建流程</el-button>
      </div>
    </div>

    <div v-for="(group, gname) in grouped" :key="gname" class="flow-group">
      <div class="flow-group-title">
        <span>{{ gname }}</span>
        <span class="cnt">({{ group.length }})</span>
      </div>
      <div class="flow-cards">
        <div v-for="d in group" :key="d.id" class="flow-card">
          <div class="card-head">
            <span class="card-logo" :style="{ background: (d.logo && d.logo.background) || '#409EFF' }">
              <el-icon :size="20" style="color: #fff"><component :is="iconOf(d.logo && d.logo.icon)" /></el-icon>
            </span>
            <b class="card-name">{{ d.name }}</b>
          </div>
          <div class="card-remark">{{ d.remark || '暂无说明' }}</div>
          <div class="card-foot">
            <span>v{{ d.version }} · {{ fmtDate(d.created_at) }}</span>
            <span class="ops">
              <el-button text type="primary" size="small" :disabled="!d.has_tree"
                @click="$router.push(`/admin/flows/${d.id}`)">设计</el-button>
            </span>
          </div>
        </div>
        <div class="flow-card add-card" @click="create">
          <el-icon :size="22"><Plus /></el-icon>
          <span>新建流程</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Document, Tickets, Money, ShoppingCart, Goods, Calendar, User, UserFilled,
         Star, Warning, Setting, Link, Histogram, Promotion } from '@element-plus/icons-vue'
import api from '../../api'
import { fmtDate } from '../../constants'

const router = useRouter()
const loading = ref(false)
const list = ref([])

const ICONS = { Document, Tickets, Money, ShoppingCart, Goods, Calendar, User, UserFilled,
  Star, Warning, Setting, Link, Histogram, Promotion }
const iconOf = (name) => ICONS[name] || Document

const grouped = computed(() => {
  const map = {}
  for (const d of list.value) {
    ;(map[d.group_name || '默认分组'] = map[d.group_name || '默认分组'] || []).push(d)
  }
  return map
})

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
.panel-toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.tip { color: #909399; font-size: 12px; }
.flow-group { margin-bottom: 20px; }
.flow-group-title { font-size: 14px; font-weight: 600; color: #303133; margin-bottom: 10px; }
.flow-group-title .cnt { color: #909399; font-weight: normal; margin-left: 4px; }
.flow-cards { display: flex; flex-wrap: wrap; gap: 14px; }
.flow-card {
  width: 240px; background: #fff; border-radius: 10px; padding: 14px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.07); border: 1px solid transparent;
}
.flow-card:hover { box-shadow: 0 4px 14px rgba(0,0,0,0.12); }
.flow-card.add-card {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 6px; color: #909399; cursor: pointer; border: 1px dashed #dcdfe6; min-height: 120px;
  box-shadow: none;
}
.flow-card.add-card:hover { color: #409eff; border-color: #409eff; }
.card-head { display: flex; align-items: center; gap: 10px; }
.card-logo { width: 38px; height: 38px; border-radius: 9px; display: inline-flex;
  align-items: center; justify-content: center; flex-shrink: 0; }
.card-name { font-size: 14px; color: #303133; }
.card-remark {
  color: #909399; font-size: 12px; margin: 8px 0 10px; height: 32px; overflow: hidden;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
}
.card-foot { display: flex; justify-content: space-between; align-items: center;
  color: #c0c4cc; font-size: 11px; border-top: 1px dashed #f0f0f0; padding-top: 8px; }
</style>

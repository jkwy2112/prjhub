<template>
  <div v-loading="loading">
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
          <p class="hint">
            在「集成配置 → LDAP 认证 / IM 配置」中在线配置, 保存后立即生效
          </p>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="never">
          <template #header><b>任务状态分布 (全系统, 按默认工作流)</b></template>
          <div v-for="s in wf.statuses" :key="s.key" class="dist-row">
            <el-tag :color="s.color" style="border: none; color: #fff" size="small">{{ s.name }}</el-tag>
            <el-progress :percentage="pct(stats.task_status_distribution?.[s.key] || 0)"
              :color="s.color" style="flex: 1; margin: 0 10px" />
            <span class="dist-count">{{ stats.task_status_distribution?.[s.key] || 0 }}</span>
          </div>
          <div v-if="stats.task_status_distribution?.other" class="dist-row">
            <el-tag style="border: none; color: #fff" size="small" :color="'#c0c4cc'">其他</el-tag>
            <el-progress :percentage="pct(stats.task_status_distribution.other)"
              :color="'#c0c4cc'" style="flex: 1; margin: 0 10px" />
            <span class="dist-count">{{ stats.task_status_distribution.other }}</span>
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
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import api from '../../api'
import { STATUS_META } from '../../constants'
const loading = ref(false)
const stats = reactive({})

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

onMounted(async () => {
  loading.value = true
  try {
    api.get('/admin/stats').then(({ data }) => Object.assign(stats, data))
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
</style>

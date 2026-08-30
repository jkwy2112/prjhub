<template>
  <div v-loading="loading">
    <el-row :gutter="16" class="stat-row">
      <el-col :span="6" v-for="card in statCards" :key="card.label">
        <div class="stat-card">
          <span class="stat-icon" :style="{ background: card.bg, color: card.color }">
            <el-icon :size="20"><component :is="card.icon" /></el-icon>
          </span>
          <div class="stat-main">
            <div class="stat-value">{{ card.value }}</div>
            <div class="stat-label">{{ card.label }}</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <el-col :span="14">
        <el-card shadow="never">
          <template #header><b>任务状态分布</b></template>
          <v-chart :option="statusChartOption" class="chart" autoresize />
        </el-card>
        <el-card shadow="never" style="margin-top: 16px">
          <template #header><b>我的待办任务</b></template>
          <el-table :data="dash.my_recent_tasks || []" size="small" @row-click="openTask" style="cursor: pointer">
            <el-table-column label="标题" min-width="200">
              <template #default="{ row }">{{ row.title }}</template>
            </el-table-column>
            <el-table-column label="类型" width="80">
              <template #default="{ row }">
                <el-tag :color="TYPE_META[row.type].color" effect="dark" size="small" style="border: none">
                  {{ TYPE_META[row.type].label }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :color="STATUS_META[row.status].color" effect="light" size="small" style="border: none">
                  {{ STATUS_META[row.status].label }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="优先级" width="80">
              <template #default="{ row }">
                <el-tag :type="PRIORITY_META[row.priority].type" size="small">{{ PRIORITY_META[row.priority].label }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card shadow="never">
          <template #header><b>最新动态</b></template>
          <el-timeline v-if="(dash.recent_activities || []).length">
            <el-timeline-item v-for="a in dash.recent_activities" :key="a.id" :timestamp="fmtDateTime(a.created_at)"
              placement="top" :color="activityColor(a.action)">
              <b>{{ a.user?.name || a.user?.username || '系统' }}</b>
              <span style="margin-left: 6px">{{ a.target }}</span>
            </el-timeline-item>
          </el-timeline>
          <el-empty v-else description="暂无动态" :image-size="80" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, markRaw } from 'vue'
import { Folder, Loading, AlarmClock, CircleCheck } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import api from '../api'
import { STATUS_META, STATUS_ORDER, TYPE_META, PRIORITY_META, fmtDateTime } from '../constants'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import VChart from 'vue-echarts'

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent])

const router = useRouter()
const loading = ref(false)
const dash = reactive({})

const statCards = computed(() => [
  { label: '参与项目', value: dash.project_count ?? '-', color: 'var(--ph-primary)',
    bg: 'var(--ph-primary-light-9)', icon: markRaw(Folder) },
  { label: '进行中任务', value: dash.my_open_task_count ?? '-', color: 'var(--ph-warning)',
    bg: 'var(--ph-warning-light-9)', icon: markRaw(Loading) },
  { label: '已逾期', value: dash.overdue_task_count ?? '-', color: 'var(--ph-danger)',
    bg: 'var(--ph-danger-light-9)', icon: markRaw(AlarmClock) },
  { label: '已完成', value: dash.done_task_count ?? '-', color: 'var(--ph-success)',
    bg: 'var(--ph-success-light-9)', icon: markRaw(CircleCheck) },
])

const statusChartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 40, right: 20, top: 20, bottom: 30 },
  xAxis: { type: 'category', data: STATUS_ORDER.map((k) => STATUS_META[k].label) },
  yAxis: { type: 'value', minInterval: 1 },
  series: [{
    type: 'bar',
    barWidth: 40,
    data: STATUS_ORDER.map((k) => ({
      value: dash.status_distribution?.[k] || 0,
      itemStyle: { color: STATUS_META[k].color, borderRadius: [4, 4, 0, 0] },
    })),
  }],
}))

function activityColor(action) {
  return { create: '#67C23A', delete: '#F56C6C', comment: '#909399', status: '#409EFF' }[action] || '#409EFF'
}

function openTask(row) {
  router.push(`/projects/${row.project_id}?task=${row.id}`)
}

onMounted(async () => {
  loading.value = true
  try {
    api.get('/dashboard').then(({ data }) => Object.assign(dash, data))
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.stat-row { margin-bottom: var(--ph-space-4); }
.stat-card {
  display: flex; align-items: center; gap: var(--ph-space-4);
  background: var(--ph-fill-blank, #fff); border-radius: var(--ph-radius-lg);
  padding: var(--ph-space-4) var(--ph-space-5);
  border: 1px solid var(--ph-border-lighter); box-shadow: var(--ph-shadow-1);
  transition: box-shadow .2s, transform .15s;
}
.stat-card:hover { box-shadow: var(--ph-shadow-2); transform: translateY(-2px); }
.stat-icon { width: 46px; height: 46px; border-radius: 12px; display: flex;
  align-items: center; justify-content: center; flex-shrink: 0; }
.stat-value { font-size: 26px; font-weight: 700; color: var(--ph-text-primary);
  font-variant-numeric: tabular-nums; line-height: 1.15; }
.stat-label { color: var(--ph-text-secondary); font-size: var(--ph-font-xs); margin-top: 2px; }
.chart { height: 260px; }
</style>

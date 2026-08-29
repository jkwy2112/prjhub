<template>
  <el-drawer v-model="visible" size="480px" :with-header="false" @closed="$emit('update:modelValue', false)">
    <div v-if="task" class="drawer-body">
      <div class="task-head">
        <el-tag effect="dark" size="small" :color="TYPE_META[task.type].color" style="border:none">
          {{ TYPE_META[task.type].label }}
        </el-tag>
        <span class="task-key">{{ projectKey }}-{{ task.number }}</span>
        <el-tag size="small" :type="PRIORITY_META[task.priority].type" style="margin-left: auto">
          {{ PRIORITY_META[task.priority].label }}优先级
        </el-tag>
      </div>

      <h3 class="task-title">{{ task.title }}</h3>

      <div class="task-meta">
        <div class="meta-row">
          <span class="meta-label">状态</span>
          <el-select :model-value="task.status" size="small" style="width: 130px" @change="onStatusChange">
            <el-option :value="task.status" :label="STATUS_META[task.status].label + ' (当前)'" disabled />
            <el-option v-for="key in STATUS_FLOW[task.status] || []" :key="key" :value="key"
              :label="STATUS_META[key].label" />
          </el-select>
        </div>
        <div class="meta-row">
          <span class="meta-label">负责人</span>
          <el-select :model-value="task.assignee_id" size="small" style="width: 130px" clearable
            placeholder="未指派" @change="onAssigneeChange">
            <el-option v-for="m in members" :key="m.user_id" :value="m.user_id"
              :label="m.user.name || m.user.username" />
          </el-select>
        </div>
        <div class="meta-row">
          <span class="meta-label">优先级</span>
          <el-select :model-value="task.priority" size="small" style="width: 130px" @change="onField('priority', $event)">
            <el-option v-for="(meta, key) in PRIORITY_META" :key="key" :value="key" :label="meta.label" />
          </el-select>
        </div>
        <div class="meta-row">
          <span class="meta-label">截止日期</span>
          <el-date-picker :model-value="dueDate" type="date" size="small" style="width: 130px"
            value-format="YYYY-MM-DDT00:00:00Z" @update:model-value="onField('due_date', $event)" />
        </div>
        <div class="meta-row">
          <span class="meta-label">创建时间</span>
          <span class="meta-value">{{ fmtDateTime(task.created_at) }}</span>
        </div>
      </div>

      <el-divider content-position="left">描述</el-divider>
      <el-input v-model="draftDesc" type="textarea" :rows="4" placeholder="补充任务描述..."
        @blur="saveDesc" />

      <el-divider content-position="left">评论 ({{ comments.length }})</el-divider>
      <div class="comment-list">
        <div v-for="c in comments" :key="c.id" class="comment-item">
          <el-avatar :size="28" style="background: #409EFF; flex-shrink: 0">
            {{ (c.user.name || c.user.username).slice(0, 1) }}
          </el-avatar>
          <div class="comment-main">
            <div class="comment-head">
              <b>{{ c.user.name || c.user.username }}</b>
              <span>{{ fmtDateTime(c.created_at) }}</span>
            </div>
            <div class="comment-content">{{ c.content }}</div>
          </div>
        </div>
        <el-empty v-if="!comments.length" description="暂无评论" :image-size="60" />
      </div>
      <div class="comment-input">
        <el-input v-model="commentText" type="textarea" :rows="2" placeholder="发表评论..." maxlength="4000" />
        <el-button type="primary" :disabled="!commentText.trim()" :loading="commenting" @click="submitComment">
          发送
        </el-button>
      </div>
    </div>
  </el-drawer>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'
import { STATUS_META, STATUS_FLOW, TYPE_META, PRIORITY_META, fmtDateTime } from '../constants'

const props = defineProps({
  modelValue: Boolean,
  taskId: { type: Number, default: null },
  projectKey: { type: String, default: '' },
  members: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:modelValue', 'changed'])

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const task = ref(null)
const comments = ref([])
const commentText = ref('')
const commenting = ref(false)
const draftDesc = ref('')

const dueDate = computed(() => (task.value?.due_date ? task.value.due_date.slice(0, 10) : null))

watch(() => props.taskId, load, { immediate: true })
watch(() => visible.value, (v) => { if (v && props.taskId) load() })

async function load() {
  if (!props.taskId) return
  const { data } = await api.get(`/tasks/${props.taskId}`)
  task.value = data
  comments.value = data.comments || []
  draftDesc.value = data.description || ''
}

async function patch(payload) {
  await api.put(`/tasks/${props.taskId}`, payload)
  await load()
  emit('changed')
}

async function onStatusChange(status) {
  try {
    await patch({ status })
  } catch { await load() }
}

async function onAssigneeChange(assignee_id) {
  try {
    await patch({ assignee_id: assignee_id || null })
  } catch { await load() }
}

async function onField(field, value) {
  try {
    await patch({ [field]: value })
  } catch { await load() }
}

async function saveDesc() {
  if (draftDesc.value !== (task.value?.description || '')) await patch({ description: draftDesc.value })
}

async function submitComment() {
  commenting.value = true
  try {
    await api.post(`/tasks/${props.taskId}/comments`, { content: commentText.value.trim() })
    commentText.value = ''
    await load()
    emit('changed')
  } finally {
    commenting.value = false
  }
}
</script>

<style scoped>
.drawer-body { display: flex; flex-direction: column; height: 100%; }
.task-head { display: flex; align-items: center; gap: 8px; }
.task-key { color: #909399; font-size: 13px; }
.task-title { font-size: 18px; margin: 12px 0; color: #303133; }
.task-meta { display: grid; grid-template-columns: 1fr 1fr; gap: 10px 24px; }
.meta-row { display: flex; align-items: center; gap: 8px; }
.meta-label { color: #909399; font-size: 12px; width: 52px; flex-shrink: 0; }
.meta-value { font-size: 13px; color: #606266; }
.comment-list { flex: 1; overflow: auto; margin-bottom: 12px; }
.comment-item { display: flex; gap: 10px; margin-bottom: 14px; }
.comment-main { flex: 1; }
.comment-head { display: flex; gap: 10px; align-items: baseline; margin-bottom: 4px; }
.comment-head span { color: #c0c4cc; font-size: 12px; }
.comment-content {
  background: #f5f7fa; border-radius: 8px; padding: 8px 12px;
  font-size: 13px; color: #303133; white-space: pre-wrap;
}
.comment-input { display: flex; gap: 8px; align-items: flex-end; }
</style>

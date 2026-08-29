<template>
  <el-dialog v-model="visible" :title="isEdit ? '编辑任务' : '新建任务'" width="560px" @closed="reset">
    <el-form :model="form" label-width="80px">
      <el-form-item label="标题" required>
        <el-input v-model="form.title" maxlength="255" placeholder="一句话描述这个任务" />
      </el-form-item>
      <el-form-item label="类型">
        <el-radio-group v-model="form.type">
          <el-radio-button value="requirement">需求</el-radio-button>
          <el-radio-button value="task">任务</el-radio-button>
          <el-radio-button value="bug">缺陷</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="优先级">
        <el-radio-group v-model="form.priority">
          <el-radio-button value="low">低</el-radio-button>
          <el-radio-button value="medium">中</el-radio-button>
          <el-radio-button value="high">高</el-radio-button>
          <el-radio-button value="urgent">紧急</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="负责人">
        <el-select v-model="form.assignee_id" clearable placeholder="未指派" style="width: 200px">
          <el-option v-for="m in members" :key="m.user_id" :value="m.user_id"
            :label="m.user.name || m.user.username" />
        </el-select>
      </el-form-item>
      <el-form-item label="截止日期">
        <el-date-picker v-model="dueLocal" type="date" value-format="YYYY-MM-DD" style="width: 200px" />
      </el-form-item>
      <el-form-item label="描述">
        <el-input v-model="form.description" type="textarea" :rows="4" maxlength="10000" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import api from '../api'

const props = defineProps({
  modelValue: Boolean,
  projectId: { type: Number, required: true },
  members: { type: Array, default: () => [] },
  task: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue', 'saved'])

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const isEdit = computed(() => !!props.task)
const saving = ref(false)
const form = reactive({ title: '', type: 'task', priority: 'medium', assignee_id: null, due_date: null, description: '' })
const dueLocal = ref(null)

watch(visible, (v) => {
  if (v && props.task) {
    Object.assign(form, {
      title: props.task.title,
      type: props.task.type,
      priority: props.task.priority,
      assignee_id: props.task.assignee_id,
      due_date: props.task.due_date,
      description: props.task.description,
    })
    dueLocal.value = props.task.due_date ? props.task.due_date.slice(0, 10) : null
  }
})

async function save() {
  if (!form.title.trim()) return ElMessage.warning('请填写任务标题')
  saving.value = true
  const payload = {
    ...form,
    assignee_id: form.assignee_id || null,
    due_date: dueLocal.value ? dayjs(dueLocal.value).toISOString() : null,
  }
  try {
    if (isEdit.value) await api.put(`/tasks/${props.task.id}`, payload)
    else await api.post(`/projects/${props.projectId}/tasks`, payload)
    ElMessage.success(isEdit.value ? '任务已更新' : '任务已创建')
    visible.value = false
    emit('saved')
  } catch { /* interceptor */ } finally {
    saving.value = false
  }
}

function reset() {
  Object.assign(form, { title: '', type: 'task', priority: 'medium', assignee_id: null, due_date: null, description: '' })
  dueLocal.value = null
}
</script>

<template>
  <div class="up-trigger" @click="pickerVisible = true">
    <template v-if="multiple">
      <el-tag v-for="u in inner" :key="u.id" closable size="small" style="margin: 0 6px 6px 0"
        @close.stop="removeOne(u)">{{ u.name || u.username }}</el-tag>
      <el-button v-if="!inner.length" size="small" type="primary" plain round :icon="Plus">选择人员</el-button>
      <el-button v-else size="small" text type="primary" :icon="Plus" style="margin-left: 0" />
    </template>
    <template v-else>
      <el-button v-if="!inner" size="small" type="primary" plain round :icon="Plus">选择人员</el-button>
      <span v-else class="up-single" @click.stop="pickerVisible = true">
        <el-avatar :size="24" style="background: var(--ph-primary)">
          {{ (inner.name || inner.username).slice(0, 1) }}
        </el-avatar>
        <b>{{ inner.name || inner.username }}</b>
        <el-icon class="up-x" @click.stop="clearOne"><CircleCloseFilled /></el-icon>
      </span>
    </template>

    <UserPickerDialog v-model="pickerVisible" :title="title" :multiple="multiple"
      :model-value-selected="dialogValue" @ok="onPicked" />
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { Plus, CircleCloseFilled } from '@element-plus/icons-vue'
import UserPickerDialog from './UserPicker.vue'

const props = defineProps({
  modelValue: { type: [Array, Object], default: () => [] }, // array<user> | user | null
  multiple: { type: Boolean, default: true },
  title: { type: String, default: '选择人员' },
})
const emit = defineEmits(['update:modelValue', 'change'])

const pickerVisible = ref(false)
const inner = computed(() => props.modelValue)
const dialogValue = computed(() =>
  props.multiple ? (props.modelValue || []) : (props.modelValue || null))

function onPicked(value) {
  emit('update:modelValue', value)
  emit('change', value)
}

function removeOne(u) {
  const next = (props.modelValue || []).filter((x) => x.id !== u.id)
  emit('update:modelValue', next)
  emit('change', next)
}

function clearOne() {
  emit('update:modelValue', null)
  emit('change', null)
}
</script>

<style scoped>
.up-trigger { display: inline-flex; flex-wrap: wrap; align-items: center; min-height: 32px; cursor: pointer; }
.up-single { display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px 3px 4px;
  background: var(--ph-primary-light-9); border-radius: 999px; }
.up-single b { font-size: var(--ph-font-sm); color: var(--ph-text-primary); }
.up-x { color: var(--ph-text-secondary); font-size: 15px; }
.up-x:hover { color: var(--ph-danger); }
</style>

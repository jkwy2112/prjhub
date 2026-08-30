<template>
  <el-dialog v-model="visible" :title="title" width="640px" append-to-body destroy-on-close
    class="user-picker-dialog" @closed="$emit('closed')">
    <div class="up-body">
      <!-- search -->
      <el-input v-model="keyword" :prefix-icon="Search" clearable placeholder="搜索用户名 / 姓名 / 邮箱"
        class="up-search" @input="onSearch" />

      <div class="up-main">
        <!-- left: candidates -->
        <div class="up-col">
          <div class="up-col-title">可选人员 <span class="up-cnt">{{ filtered.length }}</span></div>
          <div class="up-list" v-loading="loading">
            <div v-for="u in filtered" :key="u.id" class="up-item"
              :class="{ active: isSelected(u) }" @click="toggle(u)">
              <el-avatar :size="30" style="background: var(--ph-primary); flex-shrink: 0">
                {{ (u.name || u.username).slice(0, 1) }}
              </el-avatar>
              <div class="up-info">
                <b>{{ u.name || u.username }}</b>
                <span class="up-sub">{{ u.username }}<template v-if="u.dept"> · {{ u.dept }}</template></span>
              </div>
              <el-icon v-if="isSelected(u)" class="up-check"><CircleCheckFilled /></el-icon>
            </div>
            <el-empty v-if="!loading && !filtered.length" description="无匹配人员" :image-size="60" />
          </div>
        </div>

        <!-- right: selected -->
        <div class="up-col" v-if="multiple">
          <div class="up-col-title">已选 <span class="up-cnt">{{ selected.length }}</span>
            <el-button v-if="selected.length" text type="danger" size="small" style="margin-left: auto"
              @click="selected = []">清空</el-button>
          </div>
          <div class="up-list">
            <div v-for="u in selected" :key="u.id" class="up-item" @click="remove(u)">
              <el-avatar :size="30" style="background: var(--ph-primary); flex-shrink: 0">
                {{ (u.name || u.username).slice(0, 1) }}
              </el-avatar>
              <div class="up-info">
                <b>{{ u.name || u.username }}</b>
                <span class="up-sub">{{ u.username }}</span>
              </div>
              <el-icon class="up-remove"><CircleCloseFilled /></el-icon>
            </div>
            <el-empty v-if="!selected.length" description="点击左侧人员添加" :image-size="60" />
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <span class="up-hint">{{ multiple ? '可多选' : '单选' }}{{ selected.length ? ` · 已选 ${selected.length} 人` : '' }}</span>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :disabled="!selected.length" @click="confirm">确 定</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { Search, CircleCheckFilled, CircleCloseFilled } from '@element-plus/icons-vue'
import api from '../../api'

const props = defineProps({
  modelValue: Boolean,
  title: { type: String, default: '选择人员' },
  multiple: { type: Boolean, default: true },
  // v-model of selected: multiple → array of user objects; single → user object | null
  modelValueSelected: { type: [Array, Object], default: () => [] },
})
const emit = defineEmits(['update:modelValue', 'update:modelValueSelected', 'ok', 'closed'])

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const keyword = ref('')
const loading = ref(false)
const users = ref([])
const selected = ref([])

watch(visible, (v) => {
  if (v) {
    keyword.value = ''
    selected.value = props.multiple ? [...(props.modelValueSelected || [])]
      : (props.modelValueSelected ? [props.modelValueSelected] : [])
    if (!users.value.length) load()
  }
})

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/users', { params: { q: keyword.value } })
    users.value = data
  } finally {
    loading.value = false
  }
}

let timer = null
function onSearch() {
  clearTimeout(timer)
  timer = setTimeout(load, 300)
}

const filtered = computed(() =>
  users.value.filter((u) => !isSelected(u)))

function isSelected(u) {
  return selected.value.some((x) => x.id === u.id)
}

function toggle(u) {
  if (!props.multiple) {
    selected.value = [u]
    return
  }
  const i = selected.value.findIndex((x) => x.id === u.id)
  if (i >= 0) selected.value.splice(i, 1)
  else selected.value.push(u)
}

function remove(u) {
  selected.value = selected.value.filter((x) => x.id !== u.id)
}

function confirm() {
  const value = props.multiple ? selected.value : (selected.value[0] || null)
  emit('update:modelValueSelected', value)
  emit('ok', value)
  visible.value = false
}
</script>

<style scoped>
.up-search { margin-bottom: var(--ph-space-3); }
.up-main { display: flex; gap: var(--ph-space-3); }
.up-col { flex: 1; min-width: 0; }
.up-col-title { font-size: var(--ph-font-xs); color: var(--ph-text-secondary); font-weight: 600;
  margin-bottom: var(--ph-space-2); display: flex; align-items: center; gap: 4px; }
.up-cnt { background: var(--ph-fill); border-radius: 8px; padding: 0 6px; font-size: 11px; line-height: 16px; }
.up-list { height: 320px; overflow-y: auto; border: 1px solid var(--ph-border-lighter);
  border-radius: var(--ph-radius-md); padding: var(--ph-space-2); }
.up-item { display: flex; align-items: center; gap: 10px; padding: 7px 8px; border-radius: var(--ph-radius-base);
  cursor: pointer; transition: background .12s; }
.up-item:hover { background: var(--ph-fill-light); }
.up-item.active { background: var(--ph-primary-light-9); }
.up-info { flex: 1; min-width: 0; line-height: 1.3; }
.up-info b { display: block; font-size: var(--ph-font-sm); color: var(--ph-text-primary);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.up-sub { font-size: 11px; color: var(--ph-text-secondary); }
.up-check { color: var(--ph-primary); font-size: 17px; }
.up-remove { color: var(--ph-danger); font-size: 17px; opacity: 0; }
.up-item:hover .up-remove { opacity: 1; }
.up-hint { float: left; color: var(--ph-text-secondary); font-size: var(--ph-font-xs);
  line-height: 32px; margin-right: 8px; }
</style>

<template>
  <div class="fd-layout">
    <div class="fd-palette">
      <div v-for="group in grouped" :key="group.name" class="fd-group">
        <p class="fd-group-name">{{ group.name }}</p>
        <draggable :list="group.components" item-key="name"
          :group="{ name: 'form', pull: 'clone', put: false }" :sort="false"
          :clone="cloneComponent">
          <template #item="{ element }">
            <div class="fd-palette-item" @click="clickAdd(element)">
              <el-icon><component :is="iconOf(element.icon)" /></el-icon>
              <span>{{ element.title }}</span>
            </div>
          </template>
        </draggable>
      </div>
      <p class="fd-tip">拖拽控件到中间画布（或点击添加）；点击字段配置属性</p>
    </div>

    <div class="fd-canvas">
      <div class="fd-canvas-toolbar">
        <span class="fd-canvas-tip" v-if="!items.length">请在左侧选择控件拖拽到此处</span>
        <el-button size="small" :icon="View" @click="preview = true">预览表单</el-button>
      </div>
      <draggable :list="items" item-key="id" group="form" :animation="300" class="fd-drag-area"
        @start="selected = null">
        <template #item="{ element, index }">
          <div class="fd-field" :class="{ selected: selected === element }"
            @click="selected = element">
            <div class="fd-field-head">
              <el-tag size="small" effect="plain" :type="typeTag(element)">{{ typeLabel(element) }}</el-tag>
              <span class="fd-field-title"><span v-if="element.props.required" class="req">*</span>{{ element.title }}</span>
              <span class="fd-field-id">{{ element.id }}</span>
              <span class="fd-ops">
                <el-button text size="small" :disabled="index === 0" @click.stop="move(index, -1)">↑</el-button>
                <el-button text size="small" :disabled="index === items.length - 1" @click.stop="move(index, 1)">↓</el-button>
                <el-button text type="danger" size="small" @click.stop="remove(index)">删除</el-button>
              </span>
            </div>
            <div class="fd-field-preview">
              <FormRender :items="[element]" mode="design" />
            </div>
          </div>
        </template>
      </draggable>
      <el-empty v-if="!items.length" description="拖拽或点击左侧组件添加" :image-size="70" />
    </div>

    <div class="fd-props">
      <template v-if="selected">
        <div class="fd-props-head">
          <el-icon><component :is="iconOf(selected.icon || 'Edit')" /></el-icon>
          <b>{{ selected.title }}</b>
          <span class="fd-field-id">{{ selected.id }}</span>
        </div>
        <FormControlConfig :item="selected" />
      </template>
      <el-empty v-else description="选中控件后在此编辑属性" :image-size="60" />
    </div>

    <el-dialog v-model="preview" title="表单预览（填写效果）" width="640px">
      <FormRender :items="items" mode="fill" :model="previewModel"
        :user-options="userOptions"
        @search-users="searchUsers" @upload="doPreviewUpload"
        @upload-error="(m) => ElMessage.warning(m)" />
      <template #footer>
        <el-button @click="preview = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Close, View, Edit, Document, Histogram, Money, CircleCheck, Finished,
         Calendar, Warning, User, Timer, Picture, Paperclip, Grid } from '@element-plus/icons-vue'
import draggable from 'vuedraggable'
import { FORM_COMPONENTS, newFormItem } from './formComponents'
import FormRender from './FormRender.vue'
import FormControlConfig from './FormControlConfig.vue'
import api from '../../api'

const props = defineProps({
  items: { type: Array, required: true },
})
const emit = defineEmits(['changed'])

const selected = ref(null)
const preview = ref(false)
const previewModel = reactive({})
const userOptions = ref([])

const ICONS = { Edit, Document, Histogram, Money, CircleCheck, Finished, Calendar,
                Warning, User, Timer, Picture, Paperclip, Grid }
const iconOf = (name) => ICONS[name] || Edit

const grouped = computed(() => {
  const map = {}
  for (const c of FORM_COMPONENTS) {
    ;(map[c.group] = map[c.group] || []).push(c)
  }
  return Object.entries(map).map(([name, components]) => ({ name, components }))
})

const TYPE_LABELS = {
  TextInput: '单行文本', TextareaInput: '多行文本', NumberInput: '数字', AmountInput: '金额',
  SelectInput: '单选', MultipleSelect: '多选', DateTime: '日期', DateTimeRange: '日期区间',
  UserPicker: '人员', ImageUpload: '图片', FileUpload: '附件', TableList: '明细表', Description: '说明',
}
const typeLabel = (item) => TYPE_LABELS[item.name] || item.name
const typeTag = (item) => ({ Number: 'warning', Array: 'success', Date: 'info', User: 'danger' }[item.valueType] || '')

function cloneComponent(component) {
  return JSON.parse(JSON.stringify(newFormItem(component.name)))
}

function clickAdd(element) {
  props.items.push(cloneComponent(element))
  selected.value = props.items[props.items.length - 1]
  emit('changed')
}

function move(i, delta) {
  const [it] = props.items.splice(i, 1)
  props.items.splice(i + delta, 0, it)
  emit('changed')
}

function remove(index) {
  if (selected.value === props.items[index]) selected.value = null
  props.items.splice(index, 1)
  emit('changed')
}

async function searchUsers(q) {
  if (!q) return (userOptions.value = [])
  const { data } = await api.get('/users', { params: { q } })
  userOptions.value = data
}

async function doPreviewUpload({ opt }) {
  const fd = new FormData()
  fd.append('file', opt.file)
  try {
    const { data } = await api.post('/uploads', fd)
    opt.onSuccess(data)
    if (!previewModel[opt.item.id]) previewModel[opt.item.id] = []
    previewModel[opt.item.id].push(data.url)
  } catch (e) { /* ignore */ }
}
</script>

<style scoped>
.fd-layout { display: flex; gap: 14px; height: 100%; min-height: 560px; }
.fd-palette { width: 200px; flex-shrink: 0; background: var(--ph-fill-blank, #fff);
  border-radius: var(--ph-radius-lg); border: 1px solid var(--ph-border-lighter);
  padding: var(--ph-space-3); overflow-y: auto; }
.fd-group-name { font-size: var(--ph-font-xs); color: var(--ph-text-secondary); font-weight: 600;
  margin: var(--ph-space-3) 0 var(--ph-space-2); display: flex; align-items: center; gap: 6px; }
.fd-group-name::after { content: ''; flex: 1; height: 1px; background: var(--ph-border-lighter); }
.fd-palette-item {
  display: flex; align-items: center; gap: 8px; padding: 8px 10px; margin-bottom: var(--ph-space-2);
  border: 1px solid var(--ph-border-lighter); border-radius: var(--ph-radius-md); cursor: grab;
  font-size: var(--ph-font-xs); color: var(--ph-text-regular); background: var(--ph-fill-blank);
  transition: all .15s; user-select: none;
}
.fd-palette-item:hover { border-color: var(--ph-primary); color: var(--ph-primary);
  background: var(--ph-primary-light-9); transform: translateY(-1px); }
.fd-palette-item:active { cursor: grabbing; }
.fd-tip { font-size: 11px; color: #c0c4cc; margin-top: 10px; line-height: 1.5; }
.fd-canvas { flex: 1; overflow: auto; background: var(--ph-bg-page);
  border: 1px solid var(--ph-border-lighter); border-radius: var(--ph-radius-lg);
  padding: var(--ph-space-4); }
.fd-canvas-toolbar { display: flex; justify-content: flex-end; margin-bottom: 10px; }
.fd-canvas-tip { color: #c0c4cc; font-size: 12px; margin-right: auto; align-self: center; }
.fd-drag-area { min-height: 200px; }
.fd-field { background: var(--ph-fill-blank, #fff); border: 1px solid var(--ph-border-lighter);
  border-left: 3px solid var(--ph-border); border-radius: var(--ph-radius-base);
  padding: var(--ph-space-3) var(--ph-space-3); margin-bottom: var(--ph-space-2); cursor: pointer;
  transition: all .15s; }
.fd-field:hover { border-left-color: var(--ph-primary-light-3); box-shadow: var(--ph-shadow-1); }
.fd-field.selected { border-left-color: var(--ph-primary);
  box-shadow: 0 0 0 1px var(--ph-primary-light-5), var(--ph-shadow-1); }
.fd-field-head { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.fd-field-title { font-size: var(--ph-font-sm); font-weight: 600; color: var(--ph-text-primary); }
.req { color: var(--ph-danger); }
.fd-field-id { font-size: 11px; color: var(--ph-text-disabled); font-family: monospace; }
.fd-ops { margin-left: auto; display: flex; gap: 2px; opacity: 0; transition: opacity .15s; }
.fd-field:hover .fd-ops { opacity: 1; }
.fd-props { width: 300px; flex-shrink: 0; background: #fff; border-radius: 8px; padding: 12px;
  overflow-y: auto; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
.fd-props :deep(.el-form-item) { margin-bottom: 10px; }
.fd-props :deep(.el-form-item__label) { font-weight: 600; color: #303133; }
.fd-props-head { display: flex; align-items: center; gap: 6px; margin-bottom: 12px; color: #409eff; }
.fd-props-head b { color: #303133; }
.fd-col-row { display: flex; gap: 6px; align-items: center; margin-bottom: 6px; }
</style>

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
.fd-layout { display: flex; gap: 14px; height: calc(100vh - 300px); }
.fd-palette { width: 190px; flex-shrink: 0; background: #fff; border-radius: 8px; padding: 12px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06); overflow: auto; }
.fd-group-name { font-size: 12px; color: #909399; font-weight: 600; margin: 8px 0; }
.fd-palette-item {
  display: flex; align-items: center; gap: 6px; padding: 8px 10px; margin-bottom: 6px;
  border: 1px solid #ebeef5; border-radius: 8px; cursor: grab; font-size: 12px; color: #606266;
  background: #fafafa;
}
.fd-palette-item:hover { border-color: #409eff; color: #409eff; background: #fff; }
.fd-tip { font-size: 11px; color: #c0c4cc; margin-top: 10px; line-height: 1.5; }
.fd-canvas { flex: 1; overflow: auto; background: #f7f8fa; border-radius: 8px; padding: 14px; }
.fd-canvas-toolbar { display: flex; justify-content: flex-end; margin-bottom: 10px; }
.fd-canvas-tip { color: #c0c4cc; font-size: 12px; margin-right: auto; align-self: center; }
.fd-drag-area { min-height: 200px; }
.fd-field { background: #fff; border: 1.5px solid #ebeef5; border-left-width: 4px; border-radius: 8px;
  padding: 10px 12px; margin-bottom: 10px; cursor: pointer; }
.fd-field.selected { border-left-color: #409eff; box-shadow: 0 2px 8px rgba(64,158,255,0.12); }
.fd-field-head { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.fd-field-title { font-size: 13px; font-weight: 600; color: #303133; }
.req { color: #f56c6c; }
.fd-field-id { font-size: 11px; color: #c0c4cc; font-family: monospace; }
.fd-ops { margin-left: auto; display: flex; gap: 2px; }
.fd-props { width: 300px; flex-shrink: 0; background: #fff; border-radius: 8px; padding: 12px;
  overflow: auto; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
.fd-props-head { display: flex; align-items: center; gap: 6px; margin-bottom: 12px; color: #409eff; }
.fd-props-head b { color: #303133; }
.fd-col-row { display: flex; gap: 6px; align-items: center; margin-bottom: 6px; }
</style>

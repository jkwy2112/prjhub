<template>
  <div class="fd-layout">
    <!-- left palette -->
    <div class="fd-palette">
      <h5>表单组件</h5>
      <div class="fd-palette-grid">
        <div v-for="c in FORM_COMPONENTS" :key="c.name" class="fd-palette-item" @click="addItem(c.name)">
          <el-icon><component :is="iconOf(c.icon)" /></el-icon>
          <span>{{ c.title }}</span>
        </div>
      </div>
      <p class="fd-tip">点击添加到表单; 字段ID可用于流程条件 (如金额: f_amou_x1)</p>
    </div>

    <!-- center canvas -->
    <div class="fd-canvas">
      <div v-for="(item, i) in items" :key="item.id" class="fd-field"
        :class="{ selected: selected === item }" @click="selected = item">
        <div class="fd-field-head">
          <el-tag size="small" effect="plain" :type="typeTag(item)">{{ typeLabel(item) }}</el-tag>
          <span class="fd-field-title">{{ item.title }}</span>
          <span class="fd-field-id">{{ item.id }}{{ item.props.required ? ' · 必填' : '' }}</span>
          <span class="fd-ops">
            <el-button text size="small" :disabled="i === 0" @click.stop="move(i, -1)">↑</el-button>
            <el-button text size="small" :disabled="i === items.length - 1" @click.stop="move(i, 1)">↓</el-button>
            <el-button text type="danger" size="small" @click.stop="remove(i)">删除</el-button>
          </span>
        </div>
        <div class="fd-field-preview">
          <FormRender :items="[item]" mode="design" />
        </div>
      </div>
      <el-empty v-if="!items.length" description="从左侧点击组件添加表单字段" :image-size="70" />
    </div>

    <!-- right props -->
    <div class="fd-props">
      <el-empty v-if="!selected" description="点击字段配置属性" :image-size="60" />
      <template v-else>
        <h5>字段属性</h5>
        <el-form label-width="70px" size="small">
          <el-form-item label="标题">
            <el-input v-model="selected.title" maxlength="30" />
          </el-form-item>
          <el-form-item label="字段ID">
            <el-input v-model="selected.id" maxlength="40"
              placeholder="条件表达式引用的变量名" />
          </el-form-item>
          <el-form-item v-if="selected.name !== 'Description'" label="必填">
            <el-switch v-model="selected.props.required" />
          </el-form-item>
          <el-form-item v-if="hasPlaceholder(selected)" label="提示">
            <el-input v-model="selected.props.placeholder" maxlength="50" />
          </el-form-item>
          <template v-if="selected.name === 'SelectInput' || selected.name === 'MultipleSelect'">
            <el-form-item label="选项">
              <div class="fd-options">
                <el-input v-for="(o, i) in selected.props.options" :key="i" v-model="selected.props.options[i]"
                  size="small" style="margin-bottom: 6px">
                  <template #append>
                    <el-icon style="cursor: pointer" @click="selected.props.options.splice(i, 1)"><Close /></el-icon>
                  </template>
                </el-input>
                <el-button text size="small" :icon="Plus"
                  @click="selected.props.options.push(`选项${selected.props.options.length + 1}`)">加选项</el-button>
              </div>
            </el-form-item>
          </template>
          <el-form-item v-if="selected.name === 'Description'" label="内容">
            <el-input v-model="selected.props.content" type="textarea" :rows="3" />
          </el-form-item>
        </el-form>
        <el-divider />
        <h5>填写预览</h5>
        <FormRender :items="[selected]" mode="design" />
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Plus, Close, Edit, Document, Histogram, Money, CircleCheck, Finished, Calendar, Warning, User } from '@element-plus/icons-vue'
import { FORM_COMPONENTS, newFormItem } from './formComponents'
import FormRender from './FormRender.vue'

const props = defineProps({
  items: { type: Array, required: true },
})
const emit = defineEmits(['changed'])

const selected = ref(null)

const ICONS = { Edit, Document, Histogram, Money, CircleCheck, Finished, Calendar, Warning, User }
const iconOf = (name) => ICONS[name] || Edit

const TYPE_LABELS = {
  TextInput: '单行文本', TextareaInput: '多行文本', NumberInput: '数字', AmountInput: '金额',
  SelectInput: '单选', MultipleSelect: '多选', DateTime: '日期', UserPicker: '人员', Description: '说明',
}
const typeLabel = (item) => TYPE_LABELS[item.name] || item.name
const typeTag = (item) => ({ Number: 'warning', Array: 'success', Date: 'info' }[item.valueType] || '')

function hasPlaceholder(item) {
  return ['TextInput', 'TextareaInput', 'NumberInput', 'AmountInput', 'SelectInput', 'MultipleSelect', 'DateTime'].includes(item.name)
}

function addItem(name) {
  const item = newFormItem(name)
  props.items.push(item)
  selected.value = item
  emit('changed')
}

function move(i, delta) {
  const arr = props.items
  const [it] = arr.splice(i, 1)
  arr.splice(i + delta, 0, it)
}

function remove(i) {
  if (selected.value === props.items[i]) selected.value = null
  props.items.splice(i, 1)
}
</script>

<style scoped>
.fd-layout { display: flex; gap: 14px; height: calc(100vh - 300px); }
.fd-palette { width: 180px; flex-shrink: 0; background: #fff; border-radius: 8px; padding: 12px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06); height: fit-content; }
.fd-palette h5, .fd-props h5 { color: #303133; margin-bottom: 10px; font-size: 13px; }
.fd-palette-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.fd-palette-item {
  display: flex; flex-direction: column; align-items: center; gap: 4px; padding: 10px 4px;
  border: 1px solid #ebeef5; border-radius: 8px; cursor: pointer; font-size: 12px; color: #606266;
}
.fd-palette-item:hover { border-color: #409eff; color: #409eff; }
.fd-tip { font-size: 11px; color: #c0c4cc; margin-top: 10px; line-height: 1.5; }
.fd-canvas { flex: 1; overflow: auto; background: #f7f8fa; border-radius: 8px; padding: 14px; }
.fd-field { background: #fff; border: 1.5px solid #ebeef5; border-radius: 8px; padding: 10px 12px;
  margin-bottom: 10px; cursor: pointer; }
.fd-field.selected { border-color: #409eff; box-shadow: 0 2px 8px rgba(64,158,255,0.15); }
.fd-field-head { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.fd-field-title { font-size: 13px; font-weight: 600; color: #303133; }
.fd-field-id { font-size: 11px; color: #c0c4cc; font-family: monospace; }
.fd-ops { margin-left: auto; display: flex; gap: 2px; }
.fd-props { width: 280px; flex-shrink: 0; background: #fff; border-radius: 8px; padding: 12px;
  overflow: auto; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
.fd-options { width: 100%; }
</style>

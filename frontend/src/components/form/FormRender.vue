<template>
  <div class="fr-wrap" :class="{ design: mode === 'design' }">
    <template v-for="item in items" :key="item.id">
      <!-- description -->
      <div v-if="item.name === 'Description'" class="fr-item desc">
        <el-alert type="info" :closable="false" :title="item.props.content || '说明文字'" />
      </div>

      <div v-else class="fr-item">
        <div class="fr-label">
          <span v-if="item.props.required" class="fr-required">*</span>{{ item.title }}
          <span class="fr-id" v-if="mode === 'design'">{{ item.id }}</span>
        </div>
        <div class="fr-control" @click="$emit('item-click', item)">

          <!-- fill mode: real inputs bound to model -->
          <template v-if="mode === 'fill'">
            <el-input v-if="item.name === 'TextInput'" v-model="model[item.id]"
              :placeholder="item.props.placeholder" :maxlength="item.props.maxLength || 200"
              :clearable="item.props.clearable" :show-word-limit="item.props.showWordLimit"
              :disabled="item.props.disabled" :readonly="item.props.readonly">
              <template v-if="item.props.prepend" #prepend>{{ item.props.prepend }}</template>
              <template v-if="item.props.append" #append>{{ item.props.append }}</template>
            </el-input>
            <el-input v-else-if="item.name === 'TextareaInput'" v-model="model[item.id]"
              type="textarea" :rows="item.props.rows || 3"
              :autosize="item.props.autosize ? { minRows: 2, maxRows: 8 } : false"
              :maxlength="item.props.maxLength || 500" :show-word-limit="item.props.showWordLimit"
              :placeholder="item.props.placeholder" :disabled="item.props.disabled"
              :readonly="item.props.readonly" />
            <el-input-number v-else-if="item.name === 'NumberInput'" v-model="model[item.id]"
              :placeholder="item.props.placeholder" style="width: 100%" controls-position="right"
              :min="item.props.min ?? undefined" :max="item.props.max ?? undefined"
              :step="item.props.step || 1" :precision="item.props.precision || undefined"
              :disabled="item.props.disabled" :readonly="item.props.readonly" />
            <template v-else-if="item.name === 'AmountInput'">
              <el-input-number v-model="model[item.id]" :precision="item.props.precision ?? 2"
                controls-position="right" style="width: 100%" :min="item.props.min ?? undefined"
                :disabled="item.props.disabled" />
              <div v-if="item.props.showChinese && model[item.id]" class="amount-cn">
                大写：{{ amountChinese(model[item.id]) }}
              </div>
            </template>
            <el-select v-else-if="item.name === 'SelectInput'" v-model="model[item.id]"
              :placeholder="item.props.placeholder || '请选择'" :clearable="item.props.clearable"
              :filterable="item.props.filterable" style="width: 100%"
              :disabled="item.props.disabled" :automatic-dropdown="item.props.expanding">
              <el-option v-for="o in item.props.options || []" :key="o" :value="o" :label="o" />
            </el-select>
            <el-select v-else-if="item.name === 'MultipleSelect'" v-model="model[item.id]"
              multiple collapse-tags :multiple-limit="item.props.multipleLimit || 0"
              :placeholder="item.props.placeholder || '请选择'" :clearable="item.props.clearable"
              :filterable="item.props.filterable" style="width: 100%" :disabled="item.props.disabled">
              <el-option v-for="o in item.props.options || []" :key="o" :value="o" :label="o" />
            </el-select>
            <el-date-picker v-else-if="item.name === 'DateTime'" v-model="model[item.id]"
              :type="dateTypeOf(item.props.format)" :value-format="item.props.format || 'YYYY-MM-DD'"
              :placeholder="item.props.placeholder || '选择日期'" :clearable="item.props.clearable"
              :disabled="item.props.disabled" style="width: 100%" />
            <el-date-picker v-else-if="item.name === 'DateTimeRange'" v-model="model[item.id]"
              type="datetimerange" :value-format="item.props.format || 'YYYY-MM-DD HH:mm'"
              :start-placeholder="item.props.placeholder || '开始'" end-placeholder="结束"
              style="width: 100%" />
            <UserPickerField v-else-if="item.name === 'UserPicker'"
              :model-value="userValueOf(item)" :multiple="!!item.props.multiple"
              :title="`选择${item.title}`"
              @change="(v) => onUserPicked(item, v)" />
            <el-date-picker v-else-if="item.name === 'DateTimeRange'" v-model="model[item.id]"
              type="datetimerange" value-format="YYYY-MM-DD HH:mm"
              start-placeholder="开始" end-placeholder="结束" style="width: 100%" />
            <template v-else-if="item.name === 'ImageUpload' || item.name === 'FileUpload'">
              <el-upload :file-list="uploadList(model[item.id])"
                :http-request="(opt) => checkAndUpload(item, opt)"
                :limit="item.props.maxNumber || 0"
                :accept="acceptOf(item)"
                :list-type="item.name === 'ImageUpload' ? 'picture-card' : 'text'"
                :on-exceed="() => emit('limit-exceed', item)"
                :on-remove="(f) => removeUpload(props.model[item.id], f)">
                <el-icon><Plus /></el-icon>
              </el-upload>
            </template>
            <table v-else-if="item.name === 'TableList'" class="fr-table">
              <thead><tr><th v-for="col in item.props.columns || []" :key="col.id">{{ col.title }}</th><th style="width: 40px"></th></tr></thead>
              <tbody>
                <tr v-for="(row, ri) in model[item.id] || []" :key="ri">
                  <td v-for="col in item.props.columns || []" :key="col.id">
                    <el-input v-if="col.name === 'TextInput'" v-model="row[col.id]" size="small" />
                    <el-input-number v-else-if="col.name === 'NumberInput'" v-model="row[col.id]" size="small"
                      controls-position="right" style="width: 100%" />
                    <el-input v-else v-model="row[col.id]" size="small" />
                  </td>
                  <td><el-button text type="danger" size="small"
                    @click="model[item.id].splice(ri, 1)"><el-icon><Close /></el-icon></el-button></td>
                </tr>
              </tbody>
            </table>
            <el-button v-if="item.name === 'TableList'" text size="small" :icon="Plus"
              @click="addRow(item)">加一行</el-button>
          </template>

          <!-- design mode: inert previews -->
          <template v-else>
            <el-input v-if="item.name === 'TextInput'" :placeholder="item.props.placeholder || '单行输入'" disabled />
            <el-input v-else-if="item.name === 'TextareaInput'" type="textarea" :rows="2" placeholder="多行输入" disabled />
            <el-input-number v-else-if="item.name === 'NumberInput'" placeholder="数字" disabled style="width: 100%" />
            <el-input v-else-if="item.name === 'AmountInput'" placeholder="0.00" disabled>
              <template #prepend>￥</template>
            </el-input>
            <el-select v-else-if="item.name === 'SelectInput'" :placeholder="(item.props.options || []).join(' / ') || '单选'" disabled style="width: 100%" />
            <el-select v-else-if="item.name === 'MultipleSelect'" :placeholder="(item.props.options || []).join(' / ') || '多选'" disabled multiple style="width: 100%" />
            <el-date-picker v-else-if="item.name === 'DateTime'" placeholder="选择日期" disabled style="width: 100%" />
            <el-select v-else-if="item.name === 'UserPicker'" placeholder="人员选择" disabled style="width: 100%" />
            <el-date-picker v-else-if="item.name === 'DateTimeRange'" type="datetimerange"
              start-placeholder="开始" end-placeholder="结束" disabled style="width: 100%" />
            <el-button v-else-if="item.name === 'ImageUpload' || item.name === 'FileUpload'" disabled
              :icon="Plus" round>{{ item.name === 'ImageUpload' ? '上传图片' : '上传附件' }}</el-button>
            <el-table v-else-if="item.name === 'TableList'" :data="(item.props.columns || []).map(() => ({}))"
              size="small" disabled>
              <el-table-column v-for="col in item.props.columns || []" :key="col.id" :label="col.title" />
            </el-table>
          </template>
        </div>
      </div>
    </template>
    <el-empty v-if="!items.length" description="暂无表单字段" :image-size="60" />
  </div>
</template>

<script setup>
import { Plus, Close } from '@element-plus/icons-vue'
import UserPickerField from '../common/UserPickerField.vue'

const props = defineProps({
  items: { type: Array, default: () => [] },
  mode: { type: String, default: 'fill' }, // fill | design
  model: { type: Object, default: () => ({}) },
  userOptions: { type: Array, default: () => [] },
  userLoading: { type: Boolean, default: false },
})
const emit = defineEmits(['item-click', 'search-users', 'upload', 'upload-error', 'limit-exceed'])

function dateTypeOf(format) {
  if (format === 'YYYY') return 'year'
  if (format === 'YYYY-MM') return 'month'
  return 'date'
}

function amountChinese(money) {
  const cnNums = ['零', '壹', '贰', '叁', '肆', '伍', '陆', '柒', '捌', '玖']
  const cnIntRadice = ['', '拾', '佰', '仟']
  const cnIntUnits = ['', '万', '亿']
  const cnDecUnits = ['角', '分']
  money = parseFloat(money)
  if (isNaN(money)) return ''
  let integerNum = Math.floor(money)
  let decimalNum = Math.round((money - integerNum) * 100)
  if (integerNum === 0 && decimalNum === 0) return '零元整'
  let intStr = String(integerNum)
  let chineseStr = ''
  const groups = []
  while (intStr.length > 0) {
    groups.unshift(intStr.slice(-4))
    intStr = intStr.slice(0, -4)
  }
  groups.forEach((grp, gi) => {
    let g = ''
    for (let i = 0; i < grp.length; i++) {
      const n = Number(grp[i])
      const pos = grp.length - i - 1
      if (n !== 0) g += cnNums[n] + cnIntRadice[pos]
      else if (g && !g.endsWith('零')) g += '零'
    }
    g = g.replace(/零+$/, '')
    if (g) g += cnIntUnits[groups.length - 1 - gi]
    chineseStr += g
  })
  chineseStr += '元'
  if (decimalNum > 0) {
    const jiao = Math.floor(decimalNum / 10)
    const fen = decimalNum % 10
    if (jiao) chineseStr += cnNums[jiao] + cnDecUnits[0]
    if (fen) chineseStr += cnNums[fen] + cnDecUnits[1]
  } else {
    chineseStr += '整'
  }
  return chineseStr
}

function userValueOf(item) {
  const v = props.model[item.id]
  if (item.props.multiple) return v || []
  return v || null
}
function onUserPicked(item, value) {
  if (item.props.multiple) props.model[item.id] = (value || []).map((u) => u.id)
  else props.model[item.id] = value ? value.id : null
  // keep display name for detail rendering
  props.model['__uname_' + item.id] = item.props.multiple
    ? (value || []).map((u) => u.username)
    : (value ? value.username : '')
}

function acceptOf(item) {
  const types = item.props.fileTypes || []
  return types.length ? types.map((t) => '.' + t).join(',') : ''
}

function checkAndUpload(item, opt) {
  if (item.props.maxSize && opt.file.size > item.props.maxSize * 1024 * 1024) {
    emit('upload-error', `文件超过 ${item.props.maxSize}MB 限制`)
    return
  }
  emit('upload', { item, opt })
}

function uploadList(v) {
  return (v || []).map((u) => ({ name: u.split('/').pop(), url: u }))
}
function removeUpload(arr, file) {
  const i = arr.indexOf(file.url)
  if (i >= 0) arr.splice(i, 1)
}
function addRow(item) {
  if (!props.model[item.id]) props.model[item.id] = []
  const row = {}
  for (const col of item.props.columns || []) {
    row[col.id] = col.name === 'NumberInput' ? 0 : ''
  }
  props.model[item.id].push(row)
}
</script>

<style scoped>
.fr-wrap { display: flex; flex-direction: column; gap: 14px; }
.amount-cn { font-size: 12px; color: #e6a23c; margin-top: 4px; }
.fr-table { width: 100%; border-collapse: collapse; }
.fr-table th, .fr-table td { border: 1px solid #ebeef5; padding: 4px 6px; font-size: 12px; }
.fr-item .fr-label { font-size: var(--ph-font-sm); color: var(--ph-text-regular); font-weight: 600;
  margin-bottom: 6px; display: flex; align-items: center; gap: 4px; }
.fr-required { color: #f56c6c; }
.fr-id { margin-left: auto; font-size: 11px; color: #c0c4cc; font-family: monospace; }
.fr-item.desc { margin-bottom: -4px; }
:deep(.el-input.is-disabled .el-input__inner), :deep(.el-textarea.is-disabled .el-input__inner) {
  background: #fafafa; color: #909399; -webkit-text-fill-color: #909399;
}
</style>

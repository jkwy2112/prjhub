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
              :placeholder="item.props.placeholder" maxlength="200" />
            <el-input v-else-if="item.name === 'TextareaInput'" v-model="model[item.id]"
              type="textarea" :rows="3" :placeholder="item.props.placeholder" />
            <el-input-number v-else-if="item.name === 'NumberInput'" v-model="model[item.id]"
              :placeholder="item.props.placeholder" style="width: 100%" :controls-position="'right'" />
            <el-input v-else-if="item.name === 'AmountInput'" v-model="model[item.id]">
              <template #prepend>￥</template>
            </el-input>
            <el-select v-else-if="item.name === 'SelectInput'" v-model="model[item.id]"
              :placeholder="item.props.placeholder || '请选择'" clearable style="width: 100%">
              <el-option v-for="o in item.props.options || []" :key="o" :value="o" :label="o" />
            </el-select>
            <el-select v-else-if="item.name === 'MultipleSelect'" v-model="model[item.id]"
              multiple :placeholder="item.props.placeholder || '请选择'" style="width: 100%">
              <el-option v-for="o in item.props.options || []" :key="o" :value="o" :label="o" />
            </el-select>
            <el-date-picker v-else-if="item.name === 'DateTime'" v-model="model[item.id]"
              type="date" value-format="YYYY-MM-DD" :placeholder="item.props.placeholder || '选择日期'"
              style="width: 100%" />
            <el-select v-else-if="item.name === 'UserPicker'" v-model="model[item.id]"
              filterable remote :remote-method="(q) => $emit('search-users', q)"
              :loading="userLoading" placeholder="搜索并选择人员" style="width: 100%" clearable>
              <el-option v-for="u in userOptions" :key="u.id" :value="u.id" :label="u.name || u.username" />
            </el-select>
            <el-date-picker v-else-if="item.name === 'DateTimeRange'" v-model="model[item.id]"
              type="datetimerange" value-format="YYYY-MM-DD HH:mm"
              start-placeholder="开始" end-placeholder="结束" style="width: 100%" />
            <template v-else-if="item.name === 'ImageUpload' || item.name === 'FileUpload'">
              <el-upload :file-list="uploadList(model[item.id])"
                :http-request="(opt) => $emit('upload', { item, opt })" list-type="picture-card"
                v-bind="item.name === 'FileUpload' ? {} : { 'list-type': 'picture-card' }"
                :on-remove="(f) => removeUpload(model[item.id], f)">
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

const props = defineProps({
  items: { type: Array, default: () => [] },
  mode: { type: String, default: 'fill' }, // fill | design
  model: { type: Object, default: () => ({}) },
  userOptions: { type: Array, default: () => [] },
  userLoading: { type: Boolean, default: false },
})
const emit = defineEmits(['item-click', 'search-users', 'upload'])

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
.fr-table { width: 100%; border-collapse: collapse; }
.fr-table th, .fr-table td { border: 1px solid #ebeef5; padding: 4px 6px; font-size: 12px; }
.fr-item .fr-label { font-size: 13px; color: #606266; margin-bottom: 6px; display: flex; align-items: center; gap: 4px; }
.fr-required { color: #f56c6c; }
.fr-id { margin-left: auto; font-size: 11px; color: #c0c4cc; font-family: monospace; }
.fr-item.desc { margin-bottom: -4px; }
:deep(.el-input.is-disabled .el-input__inner), :deep(.el-textarea.is-disabled .el-input__inner) {
  background: #fafafa; color: #909399; -webkit-text-fill-color: #909399;
}
</style>

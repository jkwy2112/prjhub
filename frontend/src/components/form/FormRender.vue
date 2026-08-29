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
          </template>
        </div>
      </div>
    </template>
    <el-empty v-if="!items.length" description="暂无表单字段" :image-size="60" />
  </div>
</template>

<script setup>
const props = defineProps({
  items: { type: Array, default: () => [] },
  mode: { type: String, default: 'fill' }, // fill | design
  model: { type: Object, default: () => ({}) },
})
defineEmits(['item-click'])
</script>

<style scoped>
.fr-wrap { display: flex; flex-direction: column; gap: 14px; }
.fr-item .fr-label { font-size: 13px; color: #606266; margin-bottom: 6px; display: flex; align-items: center; gap: 4px; }
.fr-required { color: #f56c6c; }
.fr-id { margin-left: auto; font-size: 11px; color: #c0c4cc; font-family: monospace; }
.fr-item.desc { margin-bottom: -4px; }
:deep(.el-input.is-disabled .el-input__inner), :deep(.el-textarea.is-disabled .el-input__inner) {
  background: #fafafa; color: #909399; -webkit-text-fill-color: #909399;
}
</style>

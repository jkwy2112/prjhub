<template>
  <div class="fc-wrap">
    <!-- ===== VForm-style: 基本属性 / 校验与状态 / 专属属性 ===== -->
    <el-collapse v-model="activeSections" class="fc-collapse">
      <el-collapse-item name="basic" title="基本属性">
        <el-form label-position="top" size="small">
          <el-form-item label="字段标签">
            <el-input v-model="item.title" maxlength="30" />
          </el-form-item>
          <el-form-item label="字段ID">
            <el-input v-model="item.id" maxlength="40" placeholder="条件/权限引用的变量名" />
          </el-form-item>
          <el-form-item label="占位提示">
            <el-input v-model="item.props.placeholder" placeholder="请设置提示语" />
          </el-form-item>
          <el-form-item label="默认值">
            <el-switch v-if="['SelectInput','MultipleSelect'].includes(item.name)"
              v-model="item.props.defaultValue" active-value="" inactive-value=""
              :active-icon="undefined" style="display:none" />
            <el-input v-if="['TextInput','TextareaInput'].includes(item.name)"
              v-model="item.props.defaultValue" :maxlength="item.props.maxLength || 200" />
            <el-input-number v-else-if="['NumberInput','AmountInput'].includes(item.name)"
              v-model="item.props.defaultValue" :precision="item.props.precision ?? 0"
              controls-position="right" style="width: 140px" />
            <el-select v-else-if="item.name === 'SelectInput'" v-model="item.props.defaultValue"
              clearable style="width: 100%">
              <el-option v-for="o in item.props.options || []" :key="o" :value="o" :label="o" />
            </el-select>
            <el-date-picker v-else-if="item.name === 'DateTime'" v-model="item.props.defaultValue"
              :type="dateTypeOf(item)" :value-format="item.props.format" style="width: 100%" />
            <span v-else class="fc-hint">该组件暂不支持默认值</span>
          </el-form-item>
          <el-form-item label="标签宽度(px, 空为自适应)">
            <el-input-number v-model="item.props.labelWidth" :min="60" :max="220" size="small"
              controls-position="right" style="width: 120px" placeholder="自适应" />
          </el-form-item>
          <el-form-item label="隐藏字段标签">
            <el-switch v-model="item.props.hiddenLabel" />
          </el-form-item>
        </el-form>
      </el-collapse-item>

      <!-- ===== per-control exclusive props ===== -->
      <el-collapse-item v-if="hasExclusive" name="exclusive" title="组件属性">
        <el-form label-position="top" size="small">
          <!-- TextInput -->
          <template v-if="item.name === 'TextInput'">
            <el-form-item label="最大长度">
              <el-input-number v-model="item.props.maxLength" :min="1" :max="500"
                controls-position="right" style="width: 120px" />
            </el-form-item>
            <el-form-item label="前缀 / 后缀">
              <div class="fc-inline">
                <el-input v-model="item.props.prepend" placeholder="前缀" style="width: 100px" />
                <el-input v-model="item.props.append" placeholder="后缀" style="width: 100px" />
              </div>
            </el-form-item>
            <el-form-item label="可清除">
              <el-switch v-model="item.props.clearable" />
            </el-form-item>
            <el-form-item label="显示字数统计">
              <el-switch v-model="item.props.showWordLimit" />
            </el-form-item>
          </template>

          <!-- Textarea -->
          <template v-if="item.name === 'TextareaInput'">
            <el-form-item label="行数">
              <el-input-number v-model="item.props.rows" :min="1" :max="12"
                controls-position="right" style="width: 120px" />
            </el-form-item>
            <el-form-item label="最大长度">
              <el-input-number v-model="item.props.maxLength" :min="1" :max="5000"
                controls-position="right" style="width: 120px" />
            </el-form-item>
            <el-form-item label="高度自适应">
              <el-switch v-model="item.props.autosize" />
            </el-form-item>
            <el-form-item label="显示字数统计">
              <el-switch v-model="item.props.showWordLimit" />
            </el-form-item>
          </template>

          <!-- Number -->
          <template v-if="item.name === 'NumberInput'">
            <el-form-item label="最小值 / 最大值">
              <div class="fc-inline">
                <el-input-number v-model="item.props.min" :controls="false" placeholder="不限"
                  style="width: 95px" />
                <span class="fc-hint">~</span>
                <el-input-number v-model="item.props.max" :controls="false" placeholder="不限"
                  style="width: 95px" />
              </div>
            </el-form-item>
            <el-form-item label="增减步长">
              <el-input-number v-model="item.props.step" :min="0.01" :precision="2"
                controls-position="right" style="width: 120px" />
            </el-form-item>
            <el-form-item label="精度(小数位)">
              <el-input-number v-model="item.props.precision" :min="0" :max="6"
                controls-position="right" style="width: 120px" />
            </el-form-item>
          </template>

          <!-- Amount -->
          <template v-if="item.name === 'AmountInput'">
            <el-form-item label="保留小数">
              <el-input-number v-model="item.props.precision" :min="0" :max="3"
                controls-position="right" style="width: 120px" /> 位
            </el-form-item>
            <el-form-item label="展示大写金额">
              <el-switch v-model="item.props.showChinese" />
            </el-form-item>
            <el-form-item label="最小值">
              <el-input-number v-model="item.props.min" :controls="false" placeholder="不限"
                style="width: 120px" />
            </el-form-item>
          </template>

          <!-- Select / Multiple -->
          <template v-if="item.name === 'SelectInput' || item.name === 'MultipleSelect'">
            <el-form-item label="选项设置">
              <draggable :list="item.props.options" item-key="index" handle=".drag-handle"
                :animation="300" class="option-list">
                <template #item="{ element, index }">
                  <div class="option-row">
                    <el-icon class="drag-handle"><Rank /></el-icon>
                    <el-input v-model="item.props.options[index]" size="small" placeholder="选项值">
                      <template #append>
                        <el-icon style="cursor: pointer; color: var(--ph-danger)"
                          @click="item.props.options.splice(index, 1)"><Close /></el-icon>
                      </template>
                    </el-input>
                  </div>
                </template>
              </draggable>
              <el-button text size="small" :icon="Plus"
                @click="item.props.options.push(`选项${item.props.options.length + 1}`)">增加选项</el-button>
            </el-form-item>
            <el-form-item label="选项平铺展开">
              <el-switch v-model="item.props.expanding" />
            </el-form-item>
            <el-form-item label="可搜索选项">
              <el-switch v-model="item.props.filterable" />
            </el-form-item>
            <el-form-item label="可清除已选">
              <el-switch v-model="item.props.clearable" />
            </el-form-item>
            <el-form-item v-if="item.name === 'MultipleSelect'" label="多选数量限制">
              <el-input-number v-model="item.props.multipleLimit" :min="0"
                controls-position="right" style="width: 120px" />
              <span class="fc-hint">0 = 不限</span>
            </el-form-item>
          </template>

          <!-- DateTime / Range -->
          <template v-if="item.name === 'DateTime' || item.name === 'DateTimeRange'">
            <el-form-item label="显示格式">
              <el-select v-model="item.props.format" style="width: 100%">
                <el-option value="YYYY" label="年" />
                <el-option value="YYYY-MM" label="年-月" />
                <el-option value="YYYY-MM-DD" label="年-月-日" />
                <el-option value="YYYY-MM-DD HH:mm" label="年-月-日 时:分" />
              </el-select>
            </el-form-item>
            <el-form-item label="可清除">
              <el-switch v-model="item.props.clearable" />
            </el-form-item>
          </template>

          <!-- UserPicker -->
          <template v-if="item.name === 'UserPicker'">
            <el-form-item label="多选">
              <el-switch v-model="item.props.multiple" />
              <span class="fc-hint" style="margin-left: 8px">可选作「表单联系人」审批人来源</span>
            </el-form-item>
          </template>

          <!-- ImageUpload -->
          <template v-if="item.name === 'ImageUpload'">
            <el-form-item label="数量限制">
              <el-input-number v-model="item.props.maxNumber" :min="0"
                controls-position="right" style="width: 120px" />
              <span class="fc-hint">0 不限</span>
            </el-form-item>
            <el-form-item label="单图大小限制(MB)">
              <el-input-number v-model="item.props.maxSize" :min="0" :precision="1"
                controls-position="right" style="width: 120px" />
            </el-form-item>
          </template>

          <!-- FileUpload -->
          <template v-if="item.name === 'FileUpload'">
            <el-form-item label="数量限制">
              <el-input-number v-model="item.props.maxNumber" :min="0"
                controls-position="right" style="width: 120px" />
            </el-form-item>
            <el-form-item label="单文件大小限制(MB)">
              <el-input-number v-model="item.props.maxSize" :min="0" :precision="1"
                controls-position="right" style="width: 120px" />
            </el-form-item>
            <el-form-item label="允许的文件类型">
              <el-select v-model="item.props.fileTypes" multiple collapse-tags size="small"
                style="width: 100%" placeholder="不选则不限制">
                <el-option v-for="t in ['pdf','doc','docx','xls','xlsx','ppt','pptx','txt','zip','rar']"
                  :key="t" :value="t" :label="t" />
              </el-select>
            </el-form-item>
          </template>

          <!-- TableList -->
          <template v-if="item.name === 'TableList'">
            <el-form-item label="明细列">
              <div v-for="(col, i) in item.props.columns || []" :key="i" class="col-row">
                <el-input v-model="col.title" size="small" placeholder="列标题" style="width: 100px" />
                <el-select v-model="col.name" size="small" style="width: 100px">
                  <el-option value="TextInput" label="文本" />
                  <el-option value="NumberInput" label="数字" />
                  <el-option value="AmountInput" label="金额" />
                </el-select>
                <el-button text type="danger" size="small"
                  @click="item.props.columns.splice(i, 1)"><el-icon><Close /></el-icon></el-button>
              </div>
              <el-button text size="small" :icon="Plus"
                @click="(item.props.columns = item.props.columns || []).push(
                  { id: 'c_' + Math.random().toString(36).slice(2, 6), title: '新列', name: 'TextInput' })">增加列</el-button>
            </el-form-item>
            <el-form-item label="最大行数">
              <el-input-number v-model="item.props.maxSize" :min="0"
                controls-position="right" style="width: 120px" />
              <span class="fc-hint">0 不限</span>
            </el-form-item>
            <el-form-item label="显示边框">
              <el-switch v-model="item.props.showBorder" />
            </el-form-item>
            <el-form-item label="汇总行">
              <el-switch v-model="item.props.showSummary" />
            </el-form-item>
          </template>

          <!-- Description -->
          <el-form-item v-if="item.name === 'Description'" label="说明内容">
            <el-input v-model="item.props.content" type="textarea" :rows="3" />
          </el-form-item>
        </el-form>
      </el-collapse-item>

      <!-- ===== validation & state ===== -->
      <el-collapse-item v-if="item.name !== 'Description'" name="valid" title="校验与状态">
        <el-form label-position="top" size="small">
          <el-form-item label="必填字段">
            <el-switch v-model="item.props.required" />
          </el-form-item>
          <el-form-item v-if="item.props.required" label="必填校验提示">
            <el-input v-model="item.props.requiredMsg" :placeholder="`请填写${item.title}`" />
          </el-form-item>
          <el-form-item label="是否禁用">
            <el-switch v-model="item.props.disabled" />
          </el-form-item>
          <el-form-item label="是否只读">
            <el-switch v-model="item.props.readonly" />
          </el-form-item>
          <el-form-item label="可打印">
            <el-switch v-model="item.props.enablePrint" />
          </el-form-item>
        </el-form>
      </el-collapse-item>
    </el-collapse>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { Plus, Close, Rank } from '@element-plus/icons-vue'
import draggable from 'vuedraggable'

const props = defineProps({
  item: { type: Object, required: true },
})

const activeSections = ref(['basic', 'exclusive', 'valid'])

const EXCLUSIVE_TYPES = ['TextInput', 'TextareaInput', 'NumberInput', 'AmountInput',
  'SelectInput', 'MultipleSelect', 'DateTime', 'DateTimeRange', 'UserPicker',
  'ImageUpload', 'FileUpload', 'TableList', 'Description']
const hasExclusive = computed(() => EXCLUSIVE_TYPES.includes(props.item.name))

function dateTypeOf(item) {
  if (item.props.format === 'YYYY') return 'year'
  if (item.props.format === 'YYYY-MM') return 'month'
  return 'date'
}
</script>

<style scoped>
.fc-wrap :deep(.el-collapse-item__header) {
  font-weight: 600; font-size: var(--ph-font-sm); color: var(--ph-text-primary);
  background: var(--ph-fill-light); padding: 0 var(--ph-space-3);
  border-radius: var(--ph-radius-base); margin-bottom: var(--ph-space-2); height: 36px;
}
.fc-wrap :deep(.el-collapse-item__wrap) { border: none; }
.fc-wrap :deep(.el-collapse-item__content) { padding-bottom: var(--ph-space-2); }
.fc-wrap :deep(.el-form-item__label) { font-weight: 600; color: var(--ph-text-primary);
  font-size: var(--ph-font-xs); padding-bottom: 4px; line-height: 1.4; }
.fc-wrap :deep(.el-form-item) { margin-bottom: var(--ph-space-3); }
.fc-inline { display: flex; align-items: center; gap: var(--ph-space-2); }
.fc-hint { font-size: 11px; color: var(--ph-text-secondary); margin-left: 6px; }
.option-list { margin-bottom: 6px; }
.option-row { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.drag-handle { color: var(--ph-text-disabled); cursor: move; }
.drag-handle:hover { color: var(--ph-primary); }
.col-row { display: flex; gap: 6px; align-items: center; margin-bottom: var(--ph-space-2); }
</style>

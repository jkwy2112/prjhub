<template>
  <div class="fc-wrap">
    <el-form label-width="90px" size="small" label-position="top" class="fc-form">
      <el-form-item label="表单名称">
        <el-input v-model="item.title" maxlength="30" />
      </el-form-item>

      <!-- TextInput / Textarea -->
      <el-form-item v-if="['TextInput', 'TextareaInput'].includes(item.name)" label="提示文字">
        <el-input v-model="item.props.placeholder" placeholder="请设置提示语" />
      </el-form-item>

      <!-- Number -->
      <el-form-item v-if="item.name === 'NumberInput'" label="提示文字">
        <el-input v-model="item.props.placeholder" />
      </el-form-item>

      <!-- Amount -->
      <template v-if="item.name === 'AmountInput'">
        <el-form-item label="提示文字">
          <el-input v-model="item.props.placeholder" />
        </el-form-item>
        <el-form-item label="保留小数">
          <el-input-number v-model="item.props.precision" :min="0" :max="3" size="small"
            controls-position="right" style="width: 100px" /> 位
        </el-form-item>
        <el-form-item label="展示大写">
          <el-switch v-model="item.props.showChinese" />
        </el-form-item>
      </template>

      <!-- Select / MultipleSelect -->
      <template v-if="item.name === 'SelectInput' || item.name === 'MultipleSelect'">
        <el-form-item label="提示文字">
          <el-input v-model="item.props.placeholder" />
        </el-form-item>
        <el-form-item label="选项设置">
          <draggable :list="item.props.options" item-key="index" handle=".drag-handle"
            :animation="300" class="option-list">
            <template #item="{ element, index }">
              <div class="option-row">
                <el-icon class="drag-handle"><Rank /></el-icon>
                <el-input v-model="item.props.options[index]" size="small" placeholder="选项值">
                  <template #append>
                    <el-icon style="cursor: pointer; color: #f56c6c"
                      @click="item.props.options.splice(index, 1)"><Close /></el-icon>
                  </template>
                </el-input>
              </div>
            </template>
          </draggable>
          <el-button text size="small" :icon="Plus"
            @click="item.props.options.push(`选项${item.props.options.length + 1}`)">新增选项</el-button>
        </el-form-item>
        <el-form-item label="选项展开">
          <el-switch v-model="item.props.expanding" />
        </el-form-item>
      </template>

      <!-- DateTime -->
      <template v-if="item.name === 'DateTime'">
        <el-form-item label="提示文字">
          <el-input v-model="item.props.placeholder" />
        </el-form-item>
        <el-form-item label="日期格式">
          <el-select v-model="item.props.format" style="width: 100%">
            <el-option value="YYYY" label="年" />
            <el-option value="YYYY-MM" label="年-月" />
            <el-option value="YYYY-MM-DD" label="年-月-日" />
            <el-option value="YYYY-MM-DD HH:mm" label="年-月-日 时:分" />
          </el-select>
        </el-form-item>
      </template>

      <!-- DateTimeRange -->
      <template v-if="item.name === 'DateTimeRange'">
        <el-form-item label="开始提示">
          <el-input v-model="item.props.placeholder" />
        </el-form-item>
        <el-form-item label="日期格式">
          <el-select v-model="item.props.format" style="width: 100%">
            <el-option value="YYYY-MM-DD" label="年-月-日" />
            <el-option value="YYYY-MM-DD HH:mm" label="年-月-日 时:分" />
          </el-select>
        </el-form-item>
      </template>

      <!-- UserPicker -->
      <el-form-item v-if="item.name === 'UserPicker'" label="多选">
        <el-switch v-model="item.props.multiple" />
        <span class="tip" style="margin-left: 8px">可选作「表单联系人」审批人来源</span>
      </el-form-item>

      <!-- ImageUpload -->
      <template v-if="item.name === 'ImageUpload'">
        <el-form-item label="提示文字">
          <el-input v-model="item.props.placeholder" />
        </el-form-item>
        <el-form-item label="数量限制">
          <el-input-number v-model="item.props.maxNumber" :min="0" size="small"
            controls-position="right" style="width: 110px" /> (0 不限)
        </el-form-item>
        <el-form-item label="大小限制">
          <el-input-number v-model="item.props.maxSize" :min="0" :precision="1" size="small"
            controls-position="right" style="width: 110px" /> MB
        </el-form-item>
      </template>

      <!-- FileUpload -->
      <template v-if="item.name === 'FileUpload'">
        <el-form-item label="提示文字">
          <el-input v-model="item.props.placeholder" />
        </el-form-item>
        <el-form-item label="数量限制">
          <el-input-number v-model="item.props.maxNumber" :min="0" size="small"
            controls-position="right" style="width: 110px" />
        </el-form-item>
        <el-form-item label="大小限制">
          <el-input-number v-model="item.props.maxSize" :min="0" :precision="1" size="small"
            controls-position="right" style="width: 110px" /> MB
        </el-form-item>
        <el-form-item label="文件类型">
          <el-select v-model="item.props.fileTypes" multiple collapse-tags size="small"
            style="width: 100%" placeholder="不选则不限制">
            <el-option v-for="t in ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'zip']"
              :key="t" :value="t" :label="t" />
          </el-select>
        </el-form-item>
      </template>

      <!-- TableList -->
      <template v-if="item.name === 'TableList'">
        <el-form-item label="行数限制">
          <el-input-number v-model="item.props.maxSize" :min="0" size="small"
            controls-position="right" style="width: 110px" /> (0 不限)
        </el-form-item>
        <el-form-item label="显示边框">
          <el-switch v-model="item.props.showBorder" />
        </el-form-item>
        <el-form-item label="汇总行">
          <el-switch v-model="item.props.showSummary" />
        </el-form-item>
        <el-form-item label="明细列">
          <div v-for="(col, i) in item.props.columns || []" :key="i" class="col-row">
            <el-input v-model="col.title" size="small" placeholder="列标题" style="width: 100px" />
            <el-select v-model="col.name" size="small" style="width: 96px">
              <el-option value="TextInput" label="文本" />
              <el-option value="NumberInput" label="数字" />
              <el-option value="AmountInput" label="金额" />
            </el-select>
            <el-button text type="danger" size="small"
              @click="item.props.columns.splice(i, 1)"><el-icon><Close /></el-icon></el-button>
          </div>
          <el-button text size="small" :icon="Plus"
            @click="(item.props.columns = item.props.columns || []).push(
              { id: 'c_' + Math.random().toString(36).slice(2, 6), title: '新列', name: 'TextInput' })">加列</el-button>
        </el-form-item>
      </template>

      <!-- Description -->
      <el-form-item v-if="item.name === 'Description'" label="内容">
        <el-input v-model="item.props.content" type="textarea" :rows="3" />
      </el-form-item>

      <el-form-item v-if="item.name !== 'Description'" label="必填项">
        <el-switch v-model="item.props.required" />
      </el-form-item>
      <el-form-item label="可打印">
        <el-switch v-model="item.props.enablePrint" />
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { Plus, Close, Rank } from '@element-plus/icons-vue'
import draggable from 'vuedraggable'

defineProps({
  item: { type: Object, required: true },
})
</script>

<style scoped>
.tip { font-size: 11px; color: #c0c4cc; }
.option-list { margin-bottom: 6px; }
.option-row { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.drag-handle { color: #c0c4cc; cursor: move; }
.col-row { display: flex; gap: 6px; align-items: center; margin-bottom: 6px; }
</style>

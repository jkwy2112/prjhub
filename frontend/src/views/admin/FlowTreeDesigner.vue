<template>
  <div class="wf-designer">
    <div class="wf-toolbar">
      <div class="wf-toolbar-left">
        <el-button :icon="Back" text @click="$router.push('/admin/flows')">返回</el-button>
        <el-steps :active="stepActive" align-center style="flex: 1; max-width: 460px; cursor: pointer"
          finish-status="success" process-status="process">
          <el-step title="基础信息" @click="tab = 'base'" />
          <el-step title="审批表单" @click="tab = 'form'" />
          <el-step title="审批流程" @click="tab = 'process'" />
        </el-steps>
      </div>
      <div>
        <el-radio-group v-model="tab" size="small" style="margin-right: 10px">
          <el-radio-button value="base">基础信息</el-radio-button>
          <el-radio-button value="form">表单设计</el-radio-button>
          <el-radio-button value="process">流程设计</el-radio-button>
        </el-radio-group>
        <el-button size="small" :icon="View" @click="checkPublish">检查并发布</el-button>
      </div>
    </div>

    <div class="wf-body">
      <div v-show="tab === 'base'" class="wf-base-pane">
        <el-card shadow="never" style="width: 620px; margin: 0 auto">
          <el-form label-position="top" size="default">
            <el-form-item label="流程图标">
              <span class="logo-preview" :style="{ background: logo.background }">
                <el-icon :size="22" style="color:#fff"><component :is="iconOf(logo.icon)" /></el-icon>
              </span>
              <el-color-picker v-model="logo.background" :predefine="PRESETS" size="small" style="margin: 0 12px" />
              <el-select v-model="logo.icon" style="width: 140px">
                <el-option v-for="(ic, i) in ICON_NAMES" :key="i" :value="ic">
                  <span style="display:flex;align-items:center;gap:6px"><el-icon><component :is="iconOf(ic)" /></el-icon>{{ ic }}</span>
                </el-option>
              </el-select>
            </el-form-item>
            <el-form-item label="流程名称" required>
              <el-input v-model="defName" maxlength="64" placeholder="如: 报销审批" />
            </el-form-item>
            <el-form-item label="流程标识" required>
              <el-input v-model="defKey" maxlength="64" placeholder="小写字母开头, 用于接口调用"
                :disabled="!!definitionId" />
            </el-form-item>
            <el-form-item label="所在分组">
              <el-select v-model="groupName" filterable allow-create default-first-option style="width: 240px">
                <el-option v-for="g in groupOptions" :key="g" :value="g" :label="g" />
              </el-select>
            </el-form-item>
            <el-form-item label="流程说明">
              <el-input v-model="remark" type="textarea" :rows="3" maxlength="500" show-word-limit />
            </el-form-item>
          </el-form>
        </el-card>
      </div>
      <div v-show="tab === 'form'" class="wf-form-pane">
        <el-alert type="info" :closable="false" style="margin-bottom: 12px; flex-shrink: 0"
          title="表单字段供发起人填写, 字段ID 可在流程设计的条件分支中引用 (数字/文本/多选支持比较)" />
        <div style="flex: 1; min-height: 0">
          <FormDesigner :items="formItems" />
        </div>
      </div>
      <div v-show="tab === 'process'" class="wf-canvas">
        <div v-if="errors.length" class="wf-errors">
          <div v-for="(e, i) in errors" :key="i" class="wf-error-item" @click="locateError(e)">
            <el-icon><Warning /></el-icon>{{ e.message }}
          </div>
        </div>
        <div class="wf-flow-col">
        <div class="wf-start-pill"><el-icon style="margin-right: 6px"><Promotion /></el-icon>发起人 · 所有人</div>
        <div class="wf-link"></div>
        <WfNode :node="tree" :selected="selected" :error-nodes="errorNodes" @select="selected = $event" @self-remove="tree.childNode = null" />
        <template v-if="!tree.childNode">
          <p class="wf-empty-tip">点击上方「+」添加第一个节点</p>
        </template>
        <div v-if="tree.childNode" class="wf-link"></div>
        <div v-if="tree.childNode" class="wf-end-pill">流程结束</div>
        </div>
      </div>

      <div class="wf-props" v-if="tab === 'process'">
        <el-empty v-if="!selected" description="点击节点配置属性" :image-size="70" />
        <template v-else>
          <h4>{{ typeLabel }}</h4>

          <!-- approval -->
          <template v-if="selected.type === 'APPROVAL'">
            <el-form label-width="90px" size="small">
              <el-form-item label="节点名称">
                <el-input v-model="selected.name" maxlength="32" />
              </el-form-item>
              <el-form-item label="审批人">
                <el-radio-group v-model="selected.props.assigneeType">
                  <el-radio-button value="users">固定成员</el-radio-button>
                  <el-radio-button value="runtime">发起时指定</el-radio-button>
                  <el-radio-button value="form">表单联系人</el-radio-button>
                  <el-radio-button value="self">发起人自己</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item v-if="selected.props.assigneeType === 'users'" label="成员">
                <el-select v-model="selected.props.users" multiple filterable remote
                  :remote-method="searchUsers" placeholder="搜索用户" style="width: 100%">
                  <el-option v-for="u in userOptions" :key="u.id" :value="u.id"
                    :label="u.name || u.username" />
                </el-select>
              </el-form-item>
              <el-form-item v-else-if="selected.props.assigneeType === 'form'" label="表单字段">
                <el-select v-model="selected.props.formField" style="width: 100%"
                  placeholder="选择人员选择字段">
                  <el-option v-for="f in userFields" :key="f.id" :value="f.id"
                    :label="`${f.title} (${f.id})`" />
                </el-select>
              </el-form-item>
              <el-form-item v-else label="说明">
                <span class="tip">发起审批时由发起人选择审批人</span>
              </el-form-item>
              <el-form-item label="签核模式">
                <el-radio-group v-model="selected.props.mode">
                  <el-radio-button value="any">或签</el-radio-button>
                  <el-radio-button value="all">会签</el-radio-button>
                  <el-radio-button value="count">票签</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item v-if="selected.props.mode === 'count'" label="通过票数">
                <el-input-number v-model="selected.props.count" :min="1" />
              </el-form-item>
              <el-form-item label="审批人为空">
                <el-select :model-value="nobodyHandler" @update:model-value="(v) => setNobody(selected, v)"
                  style="width: 100%">
                  <el-option value="to_admin" label="转交系统管理员" />
                  <el-option value="auto_pass" label="自动通过" />
                  <el-option value="auto_reject" label="自动驳回" />
                  <el-option value="to_user" label="转交指定人员" />
                </el-select>
              </el-form-item>
              <el-form-item label="驳回规则">
                <el-select v-model="selected.props.refuse" style="width: 100%">
                  <el-option value="TO_END" label="驳回即结束流程" />
                  <el-option value="TO_BEFORE" label="退回上一审批节点重审" />
                  <el-option value="TO_NODE" label="驳回到指定节点" />
                </el-select>
              </el-form-item>
              <el-form-item v-if="selected.props.refuse === 'TO_NODE'" label="目标节点">
                <el-select v-model="selected.props.refuseTarget" style="width: 100%"
                  placeholder="选择审批节点">
                  <el-option v-for="n in approvalNodeOptions" :key="n.bpmnId" :value="n.bpmnId"
                    :label="n.name" :disabled="n.bpmnId === selected.bpmnId" />
                </el-select>
              </el-form-item>
              <el-form-item v-if="nobodyHandler === 'to_user'" label="转交人员">
                <el-select v-model="selected.props.nobody.users" multiple filterable remote
                  :remote-method="searchUsers" placeholder="搜索用户" style="width: 100%">
                  <el-option v-for="u in userOptions" :key="u.id" :value="u.id" :label="u.name || u.username" />
                </el-select>
              </el-form-item>
              <el-form-item label="超时催办">
                <el-switch :model-value="!!selected.props.timeout?.enabled"
                  @change="(v) => toggleTimeout(selected, v)" />
                <template v-if="selected.props.timeout?.enabled">
                  <el-input-number v-model="selected.props.timeout.value" :min="1" size="small"
                    style="margin-left: 8px; width: 90px" />
                  <el-select v-model="selected.props.timeout.unit" size="small" style="width: 70px">
                    <el-option value="H" label="小时" /><el-option value="D" label="天" />
                  </el-select>
                  <el-select v-model="selected.props.timeout.handler" size="small" style="width: 110px">
                    <el-option value="NOTIFY" label="提醒" />
                    <el-option value="PASS" label="自动通过" />
                    <el-option value="REFUSE" label="自动驳回" />
                  </el-select>
                </template>
              </el-form-item>
              <template v-if="formItems.length">
                <el-divider style="margin: 8px 0">表单字段权限</el-divider>
                <div v-for="f in formItems.filter((x) => x.name !== 'Description')" :key="f.id"
                  class="perm-row">
                  <span class="perm-title">{{ f.title }}</span>
                  <el-select :model-value="permOf(selected, f.id)" size="small" style="width: 110px"
                    @update:model-value="(v) => setPerm(selected, f.id, v)">
                    <el-option value="visible" label="可见(只读)" />
                    <el-option value="editable" label="可编辑" />
                    <el-option value="hidden" label="隐藏" />
                  </el-select>
                </div>
              </template>
            </el-form>
          </template>

          <!-- TRIGGER -->
          <template v-else-if="selected.type === 'TRIGGER'">
            <el-form label-width="90px" size="small">
              <el-form-item label="节点名称">
                <el-input v-model="selected.name" maxlength="32" />
              </el-form-item>
              <el-form-item label="请求方法">
                <el-radio-group v-model="selected.props.method">
                  <el-radio-button value="GET">GET</el-radio-button>
                  <el-radio-button value="POST">POST</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="URL">
                <el-input v-model="selected.props.url" placeholder="https://..." />
              </el-form-item>
              <p class="tip">流程到达时自动发起回调(POST 携带事件与节点名), 失败不阻塞流程, 结果记入时间线</p>
            </el-form>
          </template>

          <!-- CC -->
          <template v-else-if="selected.type === 'CC'">
            <el-form label-width="90px" size="small">
              <el-form-item label="节点名称">
                <el-input v-model="selected.name" maxlength="32" />
              </el-form-item>
              <el-form-item label="抄送人">
                <el-radio-group v-model="selected.props.assigneeType">
                  <el-radio-button value="users">固定成员</el-radio-button>
                  <el-radio-button value="runtime">发起时指定</el-radio-button>
                  <el-radio-button value="form">表单联系人</el-radio-button>
                  <el-radio-button value="self">发起人自己</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item v-if="selected.props.assigneeType === 'users'" label="成员">
                <el-select v-model="selected.props.users" multiple filterable remote
                  :remote-method="searchUsers" placeholder="搜索用户" style="width: 100%">
                  <el-option v-for="u in userOptions" :key="u.id" :value="u.id" :label="u.name || u.username" />
                </el-select>
              </el-form-item>
              <p class="tip">抄送节点不阻塞流程: 到达时自动通过并向抄送人生成通知记录</p>
            </el-form>
          </template>

          <!-- condition branch -->
          <template v-else-if="selected.type === 'CONDITION'">
            <el-form label-width="90px" size="small">
              <el-form-item label="分支名称">
                <el-input v-model="selected.name" maxlength="32" />
              </el-form-item>
              <el-divider style="margin: 8px 0">满足以下条件</el-divider>
              <div v-for="(group, gi) in groupsWithCond" :key="gi" class="cond-group">
                <div class="cond-group-head">
                  <el-radio-group v-model="selected.props.groupsType" size="small" v-if="groupsWithCond.length > 1">
                    <el-radio-button value="AND">条件组 且</el-radio-button>
                    <el-radio-button value="OR">条件组 或</el-radio-button>
                  </el-radio-group>
                  <span v-else class="tip">条件组</span>
                  <el-button text type="danger" size="small" v-if="groupsWithCond.length > 1"
                    @click="selected.props.groups.splice(gi, 1)">删除组</el-button>
                </div>
                <div v-for="(cond, ci) in group.conditions" :key="ci" class="cond-row">
                  <el-select v-model="cond.field" filterable allow-create size="small" style="width: 130px"
                    placeholder="表单字段" @change="onCondFieldChange(cond)">
                    <el-option v-for="f in formFields" :key="f.id" :value="f.id"
                      :label="`${f.title} (${f.id})`" />
                  </el-select>
                  <el-select v-model="cond.compare" size="small" style="width: 86px">
                    <el-option v-for="c in comparesOf(cond)" :key="c.value" :value="c.value" :label="c.label" />
                  </el-select>
                  <template v-if="cond.compare === 'between'">
                    <el-input v-model="cond.value[0]" placeholder="下限" style="width: 70px" size="small" />
                    <el-input v-model="cond.value[1]" placeholder="上限" style="width: 70px" size="small" />
                  </template>
                  <template v-else-if="cond.compare === 'in' && fieldOptionsOf(cond).length">
                    <el-select v-model="cond.value" multiple size="small" style="width: 130px" placeholder="选项值">
                      <el-option v-for="o in fieldOptionsOf(cond)" :key="o" :value="o" :label="o" />
                    </el-select>
                  </template>
                  <el-input v-else v-model="cond.value[0]" placeholder="值" style="width: 90px" size="small" />
                  <el-button text type="danger" size="small" @click="group.conditions.splice(ci, 1)">
                    <el-icon><Close /></el-icon>
                  </el-button>
                </div>
                <div class="cond-ops">
                  <el-button v-if="group.conditions.length > 1" text size="small"
                    @click="group.groupType = group.groupType === 'AND' ? 'OR' : 'AND'">
                    组内: {{ group.groupType === 'AND' ? '且' : '或' }}
                  </el-button>
                  <el-button text size="small" :icon="Plus"
                    @click="group.conditions.push(newCondition())">加条件</el-button>
                </div>
              </div>
              <el-button text size="small" :icon="Plus"
                @click="selected.props.groups.push({ groupType: 'AND', conditions: [] })">加条件组</el-button>
              <el-alert v-if="!hasAnyCondition" type="warning" :closable="false" style="margin-top: 8px"
                title="无条件 = 默认分支 (前面条件都不满足时走此分支)" />
            </el-form>
          </template>

          <!-- branch (parallel) -->
          <template v-else-if="selected.type === 'BRANCH'">
            <el-form label-width="90px" size="small">
              <el-form-item label="分支名称">
                <el-input v-model="selected.name" maxlength="32" />
              </el-form-item>
              <p class="tip">并行分支内的节点同时执行, 全部完成后汇聚继续</p>
            </el-form>
          </template>

          <!-- group node itself -->
          <template v-else-if="selected.type === 'CONDITIONS' || selected.type === 'CONCURRENTS'">
            <p class="tip">
              {{ selected.type === 'CONDITIONS'
                ? '自上而下按优先级匹配, 命中一个分支即走 (无条件分支为默认兜底)'
                : '所有分支同时执行, 全部完成后汇聚到后续节点' }}
            </p>
          </template>
          <template v-else>
            <p class="tip">根节点无需配置</p>
          </template>
        </template>
      </div>
    </div>
  </div>
    <el-dialog v-model="checkVisible" title="发布前检查" width="560px">
      <el-steps :active="checkStep" align-center finish-status="success">
        <el-step v-for="(st, i) in CHECK_STEPS" :key="i" :title="st" :status="checkStepStatus(i)" />
      </el-steps>
      <el-result :icon="checkDone ? (checkErrors.length ? 'warning' : 'success') : 'info'"
        :title="checkDone ? (checkErrors.length ? `发现 ${checkErrors.length} 项错误` : '检查通过, 可以发布') : '检查中...'">
        <template #sub-title>
          <div v-for="(e, i) in visibleCheckErrors" :key="i" class="check-err">{{ e.message }}</div>
        </template>
        <template #extra>
          <el-button v-if="checkDone" type="primary" size="medium" :disabled="!!checkErrors.length"
            :loading="saving" @click="doPublish">{{ checkErrors.length ? '返回修改' : '确认发布' }}</el-button>
          <el-button v-if="checkDone" size="medium" @click="checkVisible = false">关闭</el-button>
        </template>
      </el-result>
    </el-dialog>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Back, Plus, Check, Close, User, Share, Operation, Promotion, Warning, Link, View, Document, Tickets, Money, ShoppingCart, Goods, Calendar, UserFilled, Star, Setting, Histogram } from '@element-plus/icons-vue'
import api from '../../api'
import WfNode from '../../components/flow/WfNode.vue'
import FormDesigner from '../../components/form/FormDesigner.vue'

const route = useRoute()
const definitionId = route.params.id ? Number(route.params.id) : null

const defKey = ref('')
const defName = ref('')
const tab = ref('base')
const stepActive = computed(() => ({ base: 0, form: 1, process: 2 }[tab.value] ?? 0))
const formItems = ref([])
const groupName = ref('默认分组')
const remark = ref('')
const logo = reactive({ icon: 'Document', background: '#409EFF' })
const checkVisible = ref(false)
const checkStep = ref(0)
const checkDone = ref(false)
const checkErrors = ref([])
const CHECK_STEPS = ['基础信息', '审批表单', '审批流程']

const ICON_NAMES = ['Document', 'Tickets', 'Money', 'ShoppingCart', 'Goods', 'Calendar',
  'User', 'UserFilled', 'Star', 'Warning', 'Setting', 'Link', 'Histogram', 'Promotion']
const PRESETS = ['#409EFF', '#67C23A', '#E6A23C', '#F56C6C', '#9254de', '#00ced1', '#1e90ff', '#ff4500']
const ICONS = { Document, Tickets, Money, ShoppingCart, Goods, Calendar, User, UserFilled,
  Star, Warning, Setting, Link, Histogram, Promotion, Back, Plus, Check, Close, Share, Operation, View }
const iconOf = (name) => ICONS[name] || Document

const groupOptions = ref(['默认分组'])
async function loadGroups() {
  try {
    const { data } = await api.get('/approvals/definitions')
    groupOptions.value = [...new Set(['默认分组', ...data.map((d) => d.group_name || '默认分组')])]
  } catch { /* ignore */ }
}
const tree = reactive({ type: 'ROOT', name: '发起人', childNode: null })
const selected = ref(null)
const saving = ref(false)
const userOptions = ref([])

const typeLabel = computed(() => ({
  APPROVAL: '审批节点', CONDITION: '条件分支', BRANCH: '并行分支',
  CONDITIONS: '条件分支组', CONCURRENTS: '并行分支组', ROOT: '发起人', CC: '抄送人',
  TRIGGER: '触发器',
}[selected.value?.type] || ''))

const groupsWithCond = computed(() => selected.value?.props?.groups || [])

// form-field aware condition editing
import { COMPARE_BY_TYPE } from '../../components/form/formComponents'
const formFields = computed(() => formItems.value.filter((i) => i.name !== 'Description'))
const userFields = computed(() => formItems.value.filter((i) => i.name === 'UserPicker'))

function toggleTimeout(node, enabled) {
  if (!node.props.timeout) node.props.timeout = {}
  node.props.timeout.enabled = !!enabled
  if (enabled) {
    if (!node.props.timeout.unit) node.props.timeout.unit = 'H'
    if (!node.props.timeout.value) node.props.timeout.value = 24
  }
}
const nobodyHandler = computed(() => {
  const n = selected.value?.props?.nobody
  return (typeof n === 'object' && n) ? (n.handler || 'to_admin') : (n || 'to_admin')
})
function setNobody(node, v) {
  node.props.nobody = { handler: v, users: [] }
}

const approvalNodeOptions = computed(() => {
  const out = []
  const walk = (node) => {
    if (!node) return
    if (node.type === 'APPROVAL' && node.bpmnId && node !== selected.value) {
      out.push({ bpmnId: node.bpmnId, name: node.name })
    }
    ;(node.branches || []).forEach((b) => walk(b.childNode))
    walk(node.childNode)
  }
  walk(tree.childNode)
  return out
})

function permOf(node, fid) {
  return node.props?.formPerms?.[fid] || 'visible'
}
function setPerm(node, fid, value) {
  if (!node.props.formPerms) node.props.formPerms = {}
  node.props.formPerms[fid] = value
}
const fieldOf = (cond) => formFields.value.find((f) => f.id === cond.field)
const comparesOf = (cond) => COMPARE_BY_TYPE[cond.valueType || fieldOf(cond)?.valueType || 'Number'] || COMPARE_BY_TYPE.Number
const fieldOptionsOf = (cond) => fieldOf(cond)?.props?.options || []
function onCondFieldChange(cond) {
  const f = fieldOf(cond)
  cond.valueType = f?.valueType || null
  const first = comparesOf(cond)[0]?.value || '=='
  cond.compare = first
  cond.value = first === 'between' ? [0, 0] : [null]
}
function newCondition() {
  const f = formFields.value[0]
  const cond = { field: f?.id || '', valueType: f?.valueType || null, compare: '==', value: [''] }
  const first = comparesOf(cond)[0]?.value
  if (first && first !== '==') {
    cond.compare = first
    cond.value = first === 'between' ? [0, 0] : ['']
  }
  return cond
}
const hasAnyCondition = computed(
  () => !(selected.value?.props?.groups || []).some((g) => (g.conditions || []).length))

async function searchUsers(q) {
  if (!q) return (userOptions.value = [])
  const { data } = await api.get('/users', { params: { q } })
  userOptions.value = data
}

const errorNodes = computed(() => new Set(errors.value.filter((e) => e.node).map((e) => e.node)))

function locateError(e) {
  if (!e.node) return
  selected.value = e.node
  nextTick(() => {
    document.querySelector('.wf-card.selected')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  })
}

function newNode(type) {
  if (type === 'TRIGGER') {
    return { type, name: '触发器', props: { url: '', method: 'POST' }, childNode: null }
  }
  if (type === 'CC') {
    return { type, name: '抄送人', props: { assigneeType: 'users', users: [] }, childNode: null }
  }
  if (type === 'APPROVAL') {
    return { type, name: '审批节点', props: { assigneeType: 'users', users: [], mode: 'any', count: 2,
      nobody: { handler: 'to_admin' }, refuse: 'TO_END', refuseTarget: '', formField: '',
      formPerms: {}, timeout: { enabled: false, unit: 'H', value: 24, handler: 'NOTIFY' } }, childNode: null }
  }
  if (type === 'CONDITIONS') {
    return {
      type, name: '条件分支', childNode: null,
      branches: [
        { type: 'CONDITION', name: '条件1', childNode: null,
          props: { groupsType: 'AND', groups: [{ groupType: 'AND', conditions: [] }] } },
        { type: 'CONDITION', name: '默认', childNode: null, props: { groupsType: 'AND', groups: [] } },
      ],
    }
  }
  return {
    type: 'CONCURRENTS', name: '并行分支', childNode: null,
    branches: [
      { type: 'BRANCH', name: '分支1', childNode: null },
      { type: 'BRANCH', name: '分支2', childNode: null },
    ],
  }
}

function addFirst(type) {
  const node = newNode(type)
  node.childNode = tree.childNode
  tree.childNode = node
  selected.value = node
}

function resetTree() {
  tree.childNode = null
  selected.value = null
}

async function loadUsersByIds(ids) {
  await Promise.all([...new Set(ids)].map(async (id) => {
    try {
      const { data } = await api.get('/users', { params: { q: String(id) } })
      const hit = data.find((u) => u.id === id)
      if (hit && !userOptions.value.some((u) => u.id === id)) userOptions.value.push(hit)
    } catch { /* ignore */ }
  }))
}

function normalizeNode(node) {
  if (!node) return
  if (node.type === 'APPROVAL') {
    node.props = { assigneeType: 'users', users: [], mode: 'any', count: 2,
                   nobody: 'to_admin', refuse: 'TO_END', formField: '',
                   formPerms: {}, timeout: { enabled: false, unit: 'H', value: 24 },
                   ...(node.props || {}) }
    if (!node.props.timeout || typeof node.props.timeout !== 'object') {
      node.props.timeout = { enabled: false, unit: 'H', value: 24 }
    }
  }
  if (node.type === 'CC') {
    node.props = { assigneeType: 'users', users: [], ...(node.props || {}) }
  }
  if (node.type === 'TRIGGER') {
    node.props = { url: '', method: 'POST', ...(node.props || {}) }
  }
  ;(node.branches || []).forEach((b) => normalizeNode(b.childNode))
  normalizeNode(node.childNode)
}

function collectUserIds(node, acc) {
  if (!node) return acc
  if (node.type === 'APPROVAL' || node.type === 'CC') acc.push(...(node.props?.users || []))
  ;(node.branches || []).forEach((b) => collectUserIds(b.childNode, acc))
  collectUserIds(node.childNode, acc)
  return acc
}

const errors = computed(() => {
  const errs = []
  if (tree.childNode) collectErrors(tree.childNode, errs)
  const ids = formItems.value.map((f) => f.id)
  const dup = ids.find((id, i) => ids.indexOf(id) !== i)
  if (dup) errs.push({ node: null, message: `表单字段ID重复: ${dup}` })
  return errs
})

function collectErrors(node, errs, step = 2) {
  if (!node) return
  if (node.type === 'APPROVAL') {
    if (node.props?.assigneeType === 'users' && !(node.props.users || []).length) {
      errs.push({ node, step, message: `「${node.name}」未指定审批成员` })
    }
  }
  if (node.type === 'CC' && node.props?.assigneeType === 'users' && !(node.props.users || []).length) {
    errs.push({ node, step, message: `「${node.name}」未指定抄送成员` })
  }
  if (node.type === 'TRIGGER' && !/^https?:\/\//.test(node.props?.url || '')) {
    errs.push({ node, step, message: `「${node.name}」的 URL 不合法` })
  }
  if (node.type === 'APPROVAL' && node.props?.assigneeType === 'form' && !node.props.formField) {
    errs.push({ node, step, message: `「${node.name}」未选择表单联系人字段` })
  }
  ;(node.branches || []).forEach((b) => {
    if (b.type === 'CONDITION') {
      const hasCond = (b.props?.groups || []).some((g) => (g.conditions || []).length)
      const validConds = (b.props?.groups || []).every((g) =>
        (g.conditions || []).every((c) => c.field && c.value?.length && c.value[0] !== ''))
      if (!hasCond) errs.push({ node: b, step, message: `条件分支「${b.name}」未设置条件 (无条件=默认分支)` })
      else if (!validConds) errs.push({ node: b, step, message: `条件分支「${b.name}」存在未填写完整的条件` })
    }
    collectErrors(b.childNode, errs, step)
  })
  collectErrors(node.childNode, errs, step)
}

const checkErrorsByStep = computed(() => {
  const by = {}
  for (const e of checkErrors.value) by[e.step] = [...(by[e.step] || []), e]
  return by
})
const visibleCheckErrors = computed(() => checkErrors.value.slice(0, 6))

function checkStepStatus(i) {
  if (!checkDone.value) return checkStep.value === i ? 'process' : 'wait'
  return (checkErrorsByStep.value[i]?.length ? 'error' : 'success')
}

function checkPublish() {
  checkVisible.value = true
  checkDone.value = false
  checkStep.value = 0
  checkErrors.value = []
  const timer = setInterval(() => {
    checkStep.value += 1
    if (checkStep.value >= 3) {
      clearInterval(timer)
      runAllChecks()
      checkDone.value = true
    }
  }, 350)
}

function runAllChecks() {
  const errs = []
  if (!defName.value.trim()) errs.push({ step: 0, message: '流程名称未设置' })
  if (!defKey.value.trim()) errs.push({ step: 0, message: '流程标识未设置' })
  else if (!/^[a-z][a-z0-9_]*$/.test(defKey.value.trim())) errs.push({ step: 0, message: '流程标识需小写字母开头 (仅 a-z0-9_)' })
  const ids = formItems.value.map((f) => f.id)
  const dup = ids.find((id, i) => ids.indexOf(id) !== i)
  if (dup) errs.push({ step: 1, message: `表单字段ID重复: ${dup}` })
  formItems.value.forEach((f) => {
    if (!f.title.trim()) errs.push({ step: 1, message: '存在未命名的表单字段' })
    if ((f.name === 'SelectInput' || f.name === 'MultipleSelect') && !(f.props.options || []).length) {
      errs.push({ step: 1, message: `「${f.title}」未设置选项` })
    }
  })
  if (!tree.childNode) errs.push({ step: 2, message: '流程至少需要一个审批节点' })
  else collectErrors(tree.childNode, errs, 2)
  checkErrors.value = errs
}

async function doPublish() {
  saving.value = true
  try {
    await api.post('/approvals/definitions/tree', {
      key: defKey.value.trim(), name: defName.value.trim(), tree,
      form_items: formItems.value,
      group_name: groupName.value, remark: remark.value, logo: { ...logo },
    })
    ElMessage.success('流程已发布 (新版本立即生效, 在途单按旧版跑完)')
    checkVisible.value = false
  } catch { /* interceptor shows compile error */ } finally {
    saving.value = false
  }
}

onMounted(async () => {
  loadGroups()
  if (definitionId) {
    const { data } = await api.get(`/approvals/definitions/${definitionId}/tree`)
    defKey.value = data.key
    defName.value = data.name
    formItems.value = data.form_items || []
    groupName.value = data.group_name || '默认分组'
    remark.value = data.remark || ''
    Object.assign(logo, data.logo || { icon: 'Document', background: '#409EFF' })
    const loaded = data.tree || { type: 'ROOT', childNode: null }
    normalizeNode(loaded.childNode)
    Object.assign(tree, loaded)
    await loadUsersByIds(collectUserIds(tree.childNode, []))
  }
})
</script>

<style scoped>
.wf-designer { display: flex; flex-direction: column; height: calc(100vh - 190px);
  background: #fff; border-radius: 8px; overflow: hidden; }
.wf-toolbar { display: flex; justify-content: space-between; align-items: center;
  padding: 8px 12px; border-bottom: 1px solid var(--ph-border-lighter); }
.wf-toolbar-left { display: flex; align-items: center; gap: 8px; }
.wf-body { flex: 1; display: flex; min-height: 0; }
.wf-form-pane { flex: 1; overflow: hidden; display: flex; flex-direction: column; }
.wf-form-pane :deep(.fd-layout) { flex: 1; }
.wf-base-pane { flex: 1; overflow: auto; padding-top: 10px; }
.logo-preview { width: 46px; height: 46px; border-radius: 10px; display: inline-flex;
  align-items: center; justify-content: center; vertical-align: middle; }
.check-err { color: #f56c6c; font-size: 12px; padding: 2px 0; display: flex; justify-content: center; }
.wf-canvas { flex: 1; overflow: auto; padding: 24px 40px 80px;
  background: radial-gradient(circle, #eef1f5 1px, transparent 1px) 0 0 / 20px 20px, #f7f8fa; }
.wf-flow-col { display: flex; flex-direction: column; align-items: center; margin: 0 auto; width: max-content; }
.wf-start-pill, .wf-end-pill { display: flex; align-items: center; padding: 6px 22px;
  border-radius: 18px; font-size: 13px; color: #fff; }
.wf-start-pill { background: var(--ph-primary); box-shadow: 0 2px 6px var(--ph-primary-light-5); }
.wf-end-pill { background: var(--ph-info); box-shadow: 0 2px 6px var(--ph-border); }
.wf-end-pill { background: #909399; }
.wf-link { width: 2px; height: 22px; background: #cacaca; margin: 0 auto; }
.wf-plus-row { position: relative; display: flex; justify-content: center; padding: 8px 0; width: 100%; }
.wf-plus-btn { width: 30px; height: 30px; border-radius: 50%; background: #fff; color: #1890ff;
  border: 1px solid #1890ff33; cursor: pointer; display: flex; align-items: center; justify-content: center;
  transition: all .15s; }
.wf-plus-btn:hover { background: #1890ff; color: #fff; transform: scale(1.1); box-shadow: 0 2px 8px #1890ff66; }
.wf-empty-tip { text-align: center; color: #c0c4cc; font-size: 12px; margin-top: 10px; }
.wf-errors {
  width: 420px; margin: 0 auto 12px; background: var(--ph-danger-light-9);
  border: 1px solid var(--ph-danger-light-3); border-radius: var(--ph-radius-lg); padding: 8px 10px;
}
.wf-error-item {
  display: flex; align-items: center; gap: 6px; color: var(--ph-danger); font-size: var(--ph-font-xs);
  padding: 3px 0; cursor: pointer;
}
.wf-error-item:hover { text-decoration: underline; }
.wf-menu { display: flex; flex-direction: column; gap: 4px; }
.wf-menu-item { display: flex; align-items: center; gap: 8px; padding: 7px 8px; cursor: pointer;
  border-radius: 6px; font-size: 13px; color: #606266; }
.wf-menu-item:hover { background: var(--ph-primary-light-9); color: var(--ph-primary); }
.mi-ic { width: 26px; height: 26px; border-radius: 6px; display: flex; align-items: center;
  justify-content: center; color: #fff; font-size: 13px; flex-shrink: 0; }
.perm-row { display: flex; align-items: center; justify-content: space-between; padding: 4px 0; }
.perm-title { font-size: 12px; color: #606266; }
.wf-menu { display: flex; flex-wrap: wrap; gap: 8px; }
.wf-menu-item { display: flex; align-items: center; gap: 6px; width: 115px; padding: 9px 10px;
  cursor: pointer; background: #f8f9f9; border-radius: 8px; font-size: 13px; color: #606266; }
.wf-menu-item:hover { background: #fff; box-shadow: 0 0 8px 2px #d6d6d6; }
.wf-props { width: 360px; border-left: 1px solid #ebeef5; padding: 14px; overflow: auto; }
.wf-props h4 { margin-bottom: 14px; color: #303133; }
.tip { color: #909399; font-size: 12px; }
.cond-group { border: 1px solid #ebeef5; border-radius: 8px; padding: 10px; margin-bottom: 10px; }
.cond-group-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.cond-row { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.cond-ops { display: flex; gap: 8px; margin-top: 4px; }
</style>

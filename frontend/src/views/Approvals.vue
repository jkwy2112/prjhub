<template>
  <div>
    <div class="toolbar">
      <el-radio-group v-model="tab">
        <el-radio-button value="launch">发起审批</el-radio-button>
        <el-radio-button value="pending">我的待办</el-radio-button>
        <el-radio-button value="submitted">我发起的</el-radio-button>
      </el-radio-group>
      <el-badge :value="pending.length" :hidden="!pending.length" type="danger" offset="-4">
        <span></span>
      </el-badge>
    </div>

    <!-- 模板画廊: 点击卡片直接发起 -->
    <div v-if="tab === 'launch'" class="tpl-gallery" v-loading="loading">
      <div v-for="(group, gname) in groupedTemplates" :key="gname" class="tpl-group">
        <div class="tpl-group-title">{{ gname }} <span class="tpl-cnt">({{ group.length }})</span></div>
        <div class="tpl-cards">
          <div v-for="d in group" :key="d.id" class="tpl-card"
            @click="launchTemplate(d)">
            <span class="tpl-logo" :style="{ background: (d.logo && d.logo.background) || 'var(--ph-primary)' }">
              <el-icon :size="20" style="color: #fff"><component :is="iconOf(d.logo && d.logo.icon)" /></el-icon>
            </span>
            <div class="tpl-info">
              <b class="tpl-name">{{ d.name }}</b>
              <span class="tpl-remark">{{ d.remark || '点击发起审批' }}</span>
            </div>
            <el-icon class="tpl-go"><ArrowRight /></el-icon>
          </div>
        </div>
      </div>
      <el-empty v-if="!loading && !definitions.length" description="暂无可用流程模板" />
    </div>

    <!-- 我的待办 -->
    <el-table v-if="tab === 'pending'" :data="pending" v-loading="loading" style="background: #fff; border-radius: 8px">
      <el-table-column label="审批单" min-width="220">
        <template #default="{ row }">{{ row.ticket.title }}</template>
      </el-table-column>
      <el-table-column label="当前环节" width="120">
        <template #default="{ row }">
          <el-tag size="small" color="#409EFF" style="border: none; color: #fff">{{ row.node_name }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="发起人" width="100">
        <template #default="{ row }">{{ userMap[row.ticket.submitted_by] || row.ticket.submitted_by }}</template>
      </el-table-column>
      <el-table-column v-if="pendingAmountLabel" :label="pendingAmountLabel" width="110">
        <template #default="{ row }">{{ amountText(row.ticket) }}</template>
      </el-table-column>
      <el-table-column label="提交时间" width="140">
        <template #default="{ row }">{{ fmtSubmit(row.ticket.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button type="success" size="small" @click="act(row.task_id, 'approve')">同意</el-button>
          <el-button type="danger" plain size="small" @click="act(row.task_id, 'reject')">驳回</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 我发起的 -->
    <el-table v-if="tab === 'submitted'" :data="submitted" v-loading="loading" style="background: #fff; border-radius: 8px"
      @row-click="openDetail" row-class-name="clickable">
      <el-table-column label="审批编号" width="150">
        <template #default="{ row }">
          <span class="tno">{{ fmtTicketNo(row.ticket_no) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="标题" min-width="200">
        <template #default="{ row }">{{ row.title }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag size="small" :type="statusMeta(row.status).type">{{ statusMeta(row.status).label }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column v-if="submittedAmountLabel" :label="submittedAmountLabel" width="110">
        <template #default="{ row }">{{ amountText(row) }}</template>
      </el-table-column>
      <el-table-column label="当前待审批" width="140">
        <template #default="{ row }">
          {{ row.tasks.filter((t) => t.status === 'pending').map((t) => t.node_name).join('、') || '-' }}
        </template>
      </el-table-column>
      <el-table-column label="提交时间" width="140">
        <template #default="{ row }">{{ fmtSubmit(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="80" fixed="right">
        <template #default="{ row }">
          <el-button v-if="row.status === 'running'" text type="danger" size="small"
            @click.stop="cancel(row.id)">撤回</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 发起审批 -->
    <el-dialog v-model="createVisible" title="发起审批" width="600px">
      <el-form :model="form" label-width="100px">
        <div class="launch-tpl">
          <span class="tpl-logo sm" :style="{ background: (currentDef?.logo)?.background || 'var(--ph-primary)' }">
            <el-icon :size="15" style="color:#fff"><component :is="iconOf(currentDef?.logo?.icon)" /></el-icon>
          </span>
          <b>{{ currentDef?.name }}</b>
          <el-tag v-if="currentDef?.visible_scope && currentDef.visible_scope !== 'all'" size="small"
            type="info" effect="plain" style="margin-left: 8px">
            {{ { dept: '部门可见', user: '指定成员' }[currentDef.visible_scope] }}
          </el-tag>
        </div>

        <template v-if="currentDef && currentDef.has_tree">
          <!-- dynamically render the designed form -->
          <template v-if="formFields.length">
            <el-form-item v-for="f in formFields" :key="f.id" :label="f.title" :required="f.props?.required">
              <el-input v-if="f.name === 'TextInput'" v-model="formValues[f.id]" :placeholder="f.props?.placeholder" />
              <el-input v-else-if="f.name === 'TextareaInput'" v-model="formValues[f.id]" type="textarea" :rows="2" />
              <el-input-number v-else-if="f.name === 'NumberInput'" v-model="formValues[f.id]" style="width: 200px" />
              <el-input v-else-if="f.name === 'AmountInput'" v-model="formValues[f.id]" style="width: 200px">
                <template #prepend>￥</template>
              </el-input>
              <el-select v-else-if="f.name === 'SelectInput'" v-model="formValues[f.id]" clearable style="width: 100%"
                :placeholder="f.props?.placeholder || '请选择'">
                <el-option v-for="o in f.props?.options || []" :key="o" :value="o" :label="o" />
              </el-select>
              <el-select v-else-if="f.name === 'MultipleSelect'" v-model="formValues[f.id]" multiple style="width: 100%"
                :placeholder="f.props?.placeholder || '请选择'">
                <el-option v-for="o in f.props?.options || []" :key="o" :value="o" :label="o" />
              </el-select>
              <el-date-picker v-else-if="f.name === 'DateTime'" v-model="formValues[f.id]" type="date"
                value-format="YYYY-MM-DD" style="width: 100%" />
              <el-select v-else-if="f.name === 'UserPicker'" v-model="formValues[f.id]" filterable
                remote :remote-method="searchUsers" clearable placeholder="搜索并选择人员" style="width: 100%">
                <el-option v-for="u in userOptions" :key="u.id" :value="u.id" :label="u.name || u.username" />
              </el-select>
              <el-date-picker v-else-if="f.name === 'DateTimeRange'" v-model="formValues[f.id]"
                type="datetimerange" value-format="YYYY-MM-DD HH:mm" start-placeholder="开始"
                end-placeholder="结束" style="width: 100%" />
              <el-upload v-else-if="f.name === 'ImageUpload' || f.name === 'FileUpload'"
                :file-list="(formValues[f.id] || []).map((u) => ({ name: u.split('/').pop(), url: u }))"
                :http-request="(opt) => doUpload(f, opt)" list-type="picture-card"
                :on-remove="(file) => { const arr = formValues[f.id]; const i = arr.indexOf(file.url); if (i >= 0) arr.splice(i, 1) }">
                <el-icon><Plus /></el-icon>
              </el-upload>
              <table v-else-if="f.name === 'TableList'" class="fr-table">
                <thead><tr><th v-for="col in f.props.columns || []" :key="col.id">{{ col.title }}</th><th style="width: 40px"></th></tr></thead>
                <tbody>
                  <tr v-for="(row, ri) in formValues[f.id] || []" :key="ri">
                    <td v-for="col in f.props.columns || []" :key="col.id">
                      <el-input v-if="col.name === 'TextInput'" v-model="row[col.id]" size="small" />
                      <el-input-number v-else-if="col.name === 'NumberInput'" v-model="row[col.id]" size="small"
                        controls-position="right" style="width: 100%" />
                      <el-input v-else v-model="row[col.id]" size="small" />
                    </td>
                    <td><el-button text type="danger" size="small"
                      @click="formValues[f.id].splice(ri, 1)"><el-icon><Close /></el-icon></el-button></td>
                  </tr>
                </tbody>
              </table>
              <el-button v-else-if="f.name === 'TableList'" text size="small"
                @click="(formValues[f.id] = formValues[f.id] || []).push(
                  Object.fromEntries((f.props.columns || []).map((c) => [c.id, c.name === 'NumberInput' ? 0 : ''])))">加一行</el-button>
              <el-alert v-else-if="f.name === 'Description'" type="info" :closable="false" :title="f.props?.content" />
            </el-form-item>
          </template>
          <el-alert v-else-if="currentDef?.has_tree" type="info" :closable="false"
            title="该流程未设计表单, 可直接发起" style="width: 100%" />
          <!-- runtime CC pickers from tree -->
          <el-form-item v-for="rc in runtimeCcs" :key="rc.tid" :label="rc.name + ' (抄送)'">
            <UserPickerField v-model="rc.userObjs" multiple :title="`选择${rc.name}抄送人`"
              @change="(v) => rc.users = v.map((x) => x.id)" />
          </el-form-item>
          <!-- runtime approvers from tree -->
          <el-form-item v-for="rt in runtimeApprovers" :key="rt.tid" :label="rt.name" required>
            <UserPickerField v-model="rt.userObjs" multiple :title="`选择${rt.name}`"
              @change="(v) => rt.users = v.map((x) => x.id)" />
          </el-form-item>
        </template>

        <template v-else-if="form.definition_key === 'parallel_approval'">
          <el-form-item label="一级审批人" required>
            <UserPickerField v-model="l1User" :multiple="false" title="选择一级审批人"
              @change="(v) => form.approver_l1 = v?.id || null" />
          </el-form-item>
          <el-form-item label="财务审批人" required>
            <UserPickerField v-model="finUser" :multiple="false" title="选择财务审批人"
              @change="(v) => form.approver_fin = v?.id || null" />
          </el-form-item>
          <el-form-item label="技术评审人" required>
            <UserPickerField v-model="techUser" :multiple="false" title="选择技术评审人"
              @change="(v) => form.approver_tech = v?.id || null" />
          </el-form-item>
        </template>

        <template v-else>
          <el-form-item label="金额" required>
            <el-input-number v-model="form.amount" :min="0" :step="100" />
            <span class="form-tip">金额 &gt; 1000 走「会签」分支</span>
          </el-form-item>
          <el-form-item label="一级审批人" required>
            <UserPickerField v-model="l1User" :multiple="false" title="选择一级审批人"
              @change="(v) => form.approver_l1 = v?.id || null" />
          </el-form-item>
          <el-form-item label="二级审批人">
            <UserPickerField v-model="l2User" :multiple="false" title="选择二级审批人"
              @change="(v) => form.approver_l2 = v?.id || null" />
          </el-form-item>
          <el-form-item label="会签人">
            <UserPickerField v-model="csUsers" multiple title="选择会签人"
              @change="(v) => form.countersigners = v.map((x) => x.id)" />
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="submit">提交</el-button>
      </template>
    </el-dialog>

    <!-- 详情抽屉 -->
    <el-drawer v-model="detailVisible" size="560px">
      <template #header>
        <div style="display: flex; align-items: center; justify-content: space-between; width: 100%">
          <b class="tk-title">{{ ticketHeadline }}</b>
          <el-button size="small" :icon="Printer" @click="printTicket">打印</el-button>
        </div>
      </template>
      <template v-if="detail">
        <div class="tk-info">
          <div class="tk-row">
            <span class="tk-k">审批编号</span>
            <span class="tk-v mono">{{ fmtTicketNo(detail.ticket_no) }}
              <el-icon class="tk-copy" title="复制" @click="copyNo(detail.ticket_no)"><CopyDocument /></el-icon>
            </span>
          </div>
          <div class="tk-row">
            <span class="tk-k">提交时间</span>
            <span class="tk-v">{{ fmtSubmit(detail.created_at) }}</span>
          </div>
          <div class="tk-row">
            <span class="tk-k">所在部门</span>
            <span class="tk-v">{{ submitterDept }}</span>
          </div>
          <div class="tk-row">
            <span class="tk-k">状态</span>
            <span class="tk-v">
              <el-tag size="small" :type="statusMeta(detail.status).type">{{ statusMeta(detail.status).label }}</el-tag>
            </span>
          </div>
        </div>
        <div v-if="detail.form_items?.length" class="tk-form">
          <div class="tk-form-grid">
            <div v-for="f in gridFormItems" :key="f.id" class="tk-cell">
              <span class="tk-cell-k">{{ f.title }}</span>
              <span class="tk-cell-v" :class="{ 'is-money': f.name === 'AmountInput' }">
                {{ displayValue(f) }}
                <el-tag v-if="isEditable(f)" size="small" type="warning" style="margin-left: 4px">可编辑</el-tag>
              </span>
            </div>
            <!-- 明细表格整行展示 -->
          </div>
          <!-- TableList / uploads rendered full-width below grid -->
          <template v-for="f in visibleFormItems" :key="'fw-' + f.id">
            <div v-if="f.name === 'TableList'" class="tk-full">
              <span class="tk-cell-k">{{ f.title }}</span>
              <table class="tk-table" v-if="(detail.form_values?.[f.id] || []).length">
                <thead>
                  <tr><th v-for="c in f.props.columns || []" :key="c.id">{{ c.title }}</th></tr>
                </thead>
                <tbody>
                  <tr v-for="(row, ri) in detail.form_values[f.id]" :key="ri">
                    <td v-for="c in f.props.columns || []" :key="c.id">
                      {{ row[c.id] ?? (c.name === 'NumberInput' ? 0 : '') }}
                    </td>
                  </tr>
                </tbody>
              </table>
              <span v-else class="tk-empty-inline">无明细</span>
            </div>
            <div v-else-if="f.name === 'ImageUpload' || f.name === 'FileUpload'" class="tk-full">
              <span class="tk-cell-k">{{ f.title }}</span>
              <div class="tk-files">
                <template v-if="(detail.form_values?.[f.id] || []).length">
                  <el-image v-for="(u, i) in detail.form_values[f.id]" :key="i" :src="u"
                    :preview-src-list="detail.form_values[f.id]" fit="cover" class="tk-img" />
                </template>
                <span v-else class="tk-empty-inline">无附件</span>
              </div>
            </div>
          </template>
        </div>
        <el-timeline>
          <el-timeline-item v-for="t in detail.tasks" :key="t.id" :timestamp="fmtDateTime(t.created_at)"
            placement="top" :color="timelineColor(t)" :hollow="t.status === 'pending'">
            <b>{{ t.node_name }}</b>
            <span style="margin-left: 8px; color: #909399; font-size: 12px">
              {{ userMap[t.assignee_id] || '未分配' }}
            </span>
            <div v-if="t.status === 'completed'" style="font-size: 13px; margin-top: 2px">
              <el-tag size="small" :type="t.action === 'approve' ? 'success' : 'danger'">
                {{ t.action === 'approve' ? '同意' : '驳回' }}
              </el-tag>
              <span v-if="t.comment" style="margin-left: 8px; color: #606266">{{ t.comment }}</span>
            </div>
            <div v-else-if="t.status === 'pending'" style="font-size: 12px; color: #e6a23c; margin-top: 2px">
              待审批
            </div>
            <div v-else style="font-size: 12px; color: #c0c4cc; margin-top: 2px">已自动取消</div>
          </el-timeline-item>
        </el-timeline>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Printer } from '@element-plus/icons-vue'
import UserPickerField from '../components/common/UserPickerField.vue'
import api from '../api'
import { fmtDateTime } from '../constants'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const tab = ref('pending')
const loading = ref(false)
const creating = ref(false)
const pending = ref([])
const submitted = ref([])
const userOptions = ref([])
const userMap = reactive({})
const createVisible = ref(false)
const detailVisible = ref(false)
const detail = ref(null)
const definitions = ref([])
const runtimeApprovers = ref([])
const runtimeCcs = ref([])
const formFields = ref([])
const formValues = reactive({})

const currentDef = computed(() => definitions.value.find((d) => d.key === form.definition_key))

const form = reactive({
  definition_key: 'generic_approval', title: '', amount: 100,
  approver_l1: null, approver_l2: null, countersigners: [],
  approver_fin: null, approver_tech: null,
})
const l1User = ref(null)
const l2User = ref(null)
const csUsers = ref([])
const finUser = ref(null)
const techUser = ref(null)

watch(() => form.definition_key, async (key) => {
  runtimeApprovers.value = []
  runtimeCcs.value = []
  formFields.value = []
  Object.keys(formValues).forEach((k) => delete formValues[k])
  const def = definitions.value.find((d) => d.key === key)
  if (!def?.has_tree) return
  try {
    const { data } = await api.get(`/approvals/definitions/${def.id}/tree`)
    formFields.value = (data.form_items || []).filter((i) => i.name !== 'Description')
    formFields.value.forEach((f) => {
      formValues[f.id] = f.valueType === 'Array' ? [] : (f.valueType === 'Number' ? 0 : '')
    })
    const found = []
    const walk = (node) => {
      if (!node) return
      if (node.type === 'APPROVAL' && node.props?.assigneeType === 'runtime' && node.bpmnId) {
        found.push({ tid: node.bpmnId, name: node.name, users: [], userObjs: [] })
      }
      ;(node.branches || []).forEach((b) => walk(b.childNode))
      walk(node.childNode)
    }
    walk(data.tree?.childNode)
    runtimeApprovers.value = found
    const ccs = []
    const walkCc = (node) => {
      if (!node) return
      if (node.type === 'CC' && node.props?.assigneeType === 'runtime' && node.bpmnId) {
        ccs.push({ tid: node.bpmnId, name: node.name, users: [], userObjs: [] })
      }
      ;(node.branches || []).forEach((b) => walkCc(b.childNode))
      walkCc(node.childNode)
    }
    walkCc(data.tree?.childNode)
    runtimeCcs.value = ccs
  } catch { /* ignore */ }
})

const STATUS = {
  running: { label: '审批中', type: 'primary' },
  approved: { label: '已通过', type: 'success' },
  rejected: { label: '已驳回', type: 'danger' },
  cancelled: { label: '已撤回', type: 'info' },
}

function statusMeta(s) {
  return STATUS[s] || { label: s, type: 'info' }
}


const ticketHeadline = computed(() => {
  const d = detail.value
  if (!d) return '审批详情'
  const who = userMap[d.submitted_by] || d.submitted_by || ''
  const t = d.title || ''
  // title like "vpn申请" → "user01的vpn申请"; already contains 的 → as-is
  return t.includes('的') ? t : `${who}的${t}`
})

const submitterDept = ref('-')
watch(() => detail.value?.submitted_by, async (uid) => {
  submitterDept.value = '-'
  if (!uid) return
  try {
    const { data } = await api.get('/users', { params: { q: String(uid) } })
    const u = data.find((x) => x.id === uid)
    submitterDept.value = u?.dept || '未设置'
  } catch { /* ignore */ }
}, { immediate: true })

function fmtTicketNo(no) {
  if (!no || no.length !== 14) return no || '-'
  return `${no.slice(0, 4)}-${no.slice(4, 6)}-${no.slice(6, 8)} ${no.slice(8, 10)}:${no.slice(10, 12)}:${no.slice(12, 14)}`
}

function fmtSubmit(v) {
  if (!v) return '-'
  const d = new Date(v)
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}/${p(d.getMonth() + 1)}/${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}
async function copyNo(no) {
  if (!no) return
  try { await navigator.clipboard.writeText(no); ElMessage.success('已复制') } catch { /* ignore */ }
}

function amountFieldOf(ticket) {
  const items = ticket?.form_items || []
  const designed = items.find((f) => f.name === 'AmountInput')
    || items.find((f) => f.name === 'NumberInput' && /金额|amount/i.test(f.title + ' ' + f.id))
  if (designed) return designed
  // built-in templates (no designed form) whose variables contain amount
  if (!items.length && ticket?.variables && 'amount' in ticket.variables
    && ticket.variables.amount !== '' && ticket.variables.amount !== null) {
    return { id: 'amount', title: '金额', name: 'AmountInput' }
  }
  return null
}
const pendingAmountLabel = computed(() => {
  for (const row of pending.value) {
    const f = amountFieldOf(row.ticket)
    if (f) return f.title
  }
  return ''
})
const submittedAmountLabel = computed(() => {
  for (const row of submitted.value) {
    const f = amountFieldOf(row)
    if (f) return f.title
  }
  return ''
})

function amountText(ticket) {
  const f = amountFieldOf(ticket)
  if (!f) return '-'
  const v = ticket?.variables?.[f.id]
  if (v === undefined || v === null || v === '') return '-'
  return f.name === 'AmountInput' ? `￥${v}` : String(v)
}

const visibleFormItems = computed(() =>
  (detail.value?.form_items || []).filter((f) => f.name !== 'Description'
    && (detail.value?.my_node_form_perms || {})[f.id] !== 'hidden'))
const gridFormItems = computed(() =>
  visibleFormItems.value.filter((f) => !['TableList', 'ImageUpload', 'FileUpload'].includes(f.name)))
const permHiddenCount = computed(() =>
  (detail.value?.form_items || []).filter((f) => f.name !== 'Description'
    && (detail.value?.my_node_form_perms || {})[f.id] === 'hidden').length)
const isEditable = (f) => (detail.value?.my_node_form_perms || {})[f.id] === 'editable'
  && !!detail.value?.my_pending_task_id

function displayValue(f) {
  const v = detail.value?.form_values?.[f.id]
  if (v === undefined || v === null || v === '') return '—'
  if (Array.isArray(v)) return v.join('、')
  return String(v)
}

function printTicket() {
  const d = detail.value
  if (!d) return
  const ACTION = { approve: '同意', reject: '驳回', cc: '抄送', trigger: '触发器' }
  const rows = (d.tasks || []).map((t) => `
    <tr><td>${t.node_name}</td><td>${t.assignee_id ? (userMap[t.assignee_id] || t.assignee_id) : '系统'}</td>
    <td>${ACTION[t.action] || (t.status === 'pending' ? '待处理' : t.status === 'cancelled' ? '已取消' : '已处理')}</td>
    <td>${(t.comment || '').replace(/</g, '&lt;')}</td><td>${t.finished_at ? fmtDateTime(t.finished_at) : '—'}</td></tr>`).join('')
  const formRows = (d.form_items || []).filter((f) => f.name !== 'Description').map((f) => `
    <tr><td>${f.title}</td><td>${displayValue(f)}</td></tr>`).join('')
  const win = window.open('', '_blank')
  win.document.write(`<html><head><title>${d.title} - 审批单</title>
    <style>body{font-family:'PingFang SC',sans-serif;padding:24px;color:#303133}
    h2{margin-bottom:4px} .no{font-family:Menlo,monospace;letter-spacing:1px;color:#606266;font-size:15px;margin-bottom:4px}
    .meta{color:#909399;font-size:12px;margin-bottom:16px}
    table{width:100%;border-collapse:collapse;margin-bottom:16px}
    td,th{border:1px solid #dcdfe6;padding:6px 10px;font-size:13px;text-align:left}
    th{background:#f5f7fa}</style></head><body>
    <h2>${(() => d.title.includes('的') ? d.title : `${userMap[d.submitted_by] || d.submitted_by}的${d.title}`)()}</h2>
    <div class="no">审批编号: ${fmtTicketNo(d.ticket_no)}</div>
    <div class="meta">提交时间: ${fmtSubmit(d.created_at)} | 所在部门: ${submitterDept.value} | 状态: ${statusMeta(d.status).label}</div>
    ${formRows ? `<table><tr><th style="width:140px">表单字段</th><th>内容</th></tr>${formRows}</table>` : ''}
    <table><tr><th>环节</th><th>处理人</th><th>动作</th><th>意见</th><th>时间</th></tr>${rows}</table>
    </body></html>`)
  win.document.close()
  win.print()
}

function timelineColor(t) {
  if (t.status === 'completed') return t.action === 'approve' ? '#67C23A' : '#F56C6C'
  if (t.status === 'pending') return '#E6A23C'
  return '#C0C4CC'
}

async function load() {
  loading.value = true
  try {
    const [p, s, d] = await Promise.all([
      api.get('/approvals/my-pending'),
      api.get('/approvals/my-submitted'),
      api.get('/approvals/definitions'),
    ])
    definitions.value = d.data
    // attach form_items (from definition) to pending tickets so amount col can detect
    const defMap = Object.fromEntries(d.data.map((x) => [x.id, x]))
    p.data.forEach((row) => {
      const def = defMap[row.ticket.definition_id]
      if (def?.has_form) row.ticket.form_items = row.ticket.form_items || null // filled lazily below
    })
    // lazily fetch trees for designed defs (cached)
    for (const row of p.data) {
      const def = defMap[row.ticket.definition_id]
      if (def?.has_form && !row.ticket.form_items) {
        try {
          const { data } = await api.get(`/approvals/definitions/${def.id}/tree`)
          row.ticket.form_items = data.form_items || []
        } catch { row.ticket.form_items = [] }
      }
    }
    pending.value = p.data
    submitted.value = s.data
    const ids = new Set()
    p.data.forEach((x) => ids.add(x.ticket.submitted_by))
    s.data.forEach((x) => { ids.add(x.submitted_by); x.tasks.forEach((t) => t.assignee_id && ids.add(t.assignee_id)) })
    await Promise.all([...ids].map(async (id) => {
      if (userMap[id]) return
      try {
        const { data } = await api.get('/users', { params: { q: String(id) } })
        const hit = data.find((u) => u.id === id)
        if (hit) userMap[id] = hit.username
      } catch { /* ignore */ }
    }))
  } finally {
    loading.value = false
  }
}

async function doUpload(field, opt) {
  const fd = new FormData()
  fd.append('file', opt.file)
  const { data } = await api.post('/uploads', fd)
  if (!Array.isArray(formValues[field.id])) formValues[field.id] = []
  formValues[field.id].push(data.url)
  opt.onSuccess(data)
}

async function searchUsers(q) {
  if (!q) return (userOptions.value = [])
  const { data } = await api.get('/users', { params: { q } })
  userOptions.value = data
}

const groupedTemplates = computed(() => {
  const map = {}
  for (const d of definitions.value) {
    ;(map[d.group_name || '默认分组'] = map[d.group_name || '默认分组'] || []).push(d)
  }
  return map
})

import { Document, Tickets, Money, ShoppingCart, Goods, Calendar, User, UserFilled,
  Star, Warning, Setting, Link, Histogram, Promotion, ArrowRight } from '@element-plus/icons-vue'
const TPL_ICONS = { Document, Tickets, Money, ShoppingCart, Goods, Calendar, User, UserFilled,
  Star, Warning, Setting, Link, Histogram, Promotion }
const iconOf = (name) => TPL_ICONS[name] || Document

function launchTemplate(def) {
  form.definition_key = def.key
  openCreate()
}

function openCreate() {
  Object.assign(form, {
    definition_key: definitions.value[0]?.key || 'generic_approval', title: '', amount: 100,
    approver_l1: null, approver_l2: null, countersigners: [], approver_fin: null, approver_tech: null,
  })
  l1User.value = null; l2User.value = null; csUsers.value = []
  finUser.value = null; techUser.value = null
  runtimeApprovers.value.forEach((rt) => { rt.userObjs = [] })
  runtimeCcs.value.forEach((rc) => { rc.userObjs = [] })
  createVisible.value = true
}

async function submit() {
  let variables
  if (currentDef.value?.has_tree) {
    const missingField = formFields.value.find((f) => f.props?.required &&
      (Array.isArray(formValues[f.id]) ? !formValues[f.id].length : !formValues[f.id] && formValues[f.id] !== 0))
    if (missingField) return ElMessage.warning(`请填写「${missingField.title}」`)
    const missing = runtimeApprovers.value.find((rt) => !rt.users.length)
    if (missing) return ElMessage.warning(`请选择「${missing.name}」的审批人`)
    variables = { ...formValues }
    runtimeApprovers.value.forEach((rt) => { variables[`approver_${rt.tid}`] = rt.users })
    runtimeCcs.value.forEach((rc) => { if (rc.users.length) variables[`cc_${rc.tid}`] = rc.users })
  } else if (form.definition_key === 'parallel_approval') {
    if (!form.approver_fin || !form.approver_tech) return ElMessage.warning('并行分支审批人不能为空')
    variables = {
      approver_l1: form.approver_l1,
      approver_fin: form.approver_fin,
      approver_tech: form.approver_tech,
    }
  } else {
    if (!form.approver_l1) return ElMessage.warning('请选择一级审批人')
    if (form.amount > 1000 && !form.countersigners.length) {
      return ElMessage.warning('大额审批需选择会签人')
    }
    variables = {
      amount: form.amount,
      approver_l1: form.approver_l1,
      approver_l2: form.approver_l2 || form.approver_l1,
      countersigners: form.countersigners,
      cs_total: form.countersigners.length,
      cs_pass: 2,
    }
  }
  creating.value = true
  try {
    const defName = currentDef.value?.name || definitions.value.find((d) => d.key === form.definition_key)?.name || '审批单'
    await api.post('/approvals', {
      definition_key: form.definition_key,
      title: defName,
      variables,
    })
    ElMessage.success('审批已发起')
    createVisible.value = false
    load()
  } catch { /* interceptor */ } finally {
    creating.value = false
  }
}

async function act(taskId, action) {
  const word = action === 'approve' ? '同意' : '驳回'
  let comment = ''
  try {
    const { value } = await ElMessageBox.prompt(`确认${word}该审批单?`, word + '审批', {
      inputPlaceholder: '审批意见(可留空)', inputValue: '',
    })
    comment = value || ''
  } catch { return }
  const { data } = await api.post(`/approvals/tasks/${taskId}/complete`, { action, comment })
  ElMessage.success(data.status === 'running' ? `已${word}, 流转至下一环节` : `已${word}, 审批单${statusMeta(data.status).label}`)
  load()
}

async function cancel(id) {
  await ElMessageBox.confirm('确认撤回该审批单?', '撤回', { type: 'warning' })
  await api.post(`/approvals/${id}/cancel`)
  ElMessage.success('已撤回')
  load()
}

async function openDetail(row) {
  const { data } = await api.get(`/approvals/${row.id}`)
  detail.value = data
  detailVisible.value = true
  data.tasks.forEach((t) => t.assignee_id && !userMap[t.assignee_id] && load())
}

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }

.tpl-gallery { min-height: 200px; }
.tpl-group { margin-bottom: 20px; }
.tpl-group-title { font-size: 14px; font-weight: 600; color: var(--ph-text-primary); margin-bottom: 10px; }
.tpl-cnt { color: var(--ph-text-secondary); font-weight: normal; margin-left: 4px; }
.tpl-cards { display: flex; flex-wrap: wrap; gap: 12px; }
.tpl-card {
  display: flex; align-items: center; gap: 12px; width: 320px; padding: 14px;
  background: var(--ph-fill-blank, #fff); border: 1px solid var(--ph-border-lighter);
  border-radius: var(--ph-radius-lg); cursor: pointer;
  transition: all .15s; box-shadow: var(--ph-shadow-1);
}
.tpl-card:hover { box-shadow: var(--ph-shadow-3); transform: translateY(-2px);
  border-color: var(--ph-primary-light-5); }
.tpl-logo { width: 42px; height: 42px; border-radius: 10px; display: flex;
  align-items: center; justify-content: center; flex-shrink: 0; }
.tpl-logo.sm { width: 26px; height: 26px; border-radius: 7px; }
.tpl-info { flex: 1; min-width: 0; line-height: 1.4; }
.tpl-name { display: block; font-size: var(--ph-font-sm); color: var(--ph-text-primary);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tpl-remark { font-size: 11px; color: var(--ph-text-secondary);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; display: block; }
.tpl-go { color: var(--ph-text-disabled); transition: all .15s; }
.tpl-card:hover .tpl-go { color: var(--ph-primary); transform: translateX(3px); }
.launch-tpl { display: flex; align-items: center; gap: 8px; padding: 8px 12px; margin-bottom: 14px;
  background: var(--ph-fill-light); border-radius: var(--ph-radius-md); }
.form-tip { font-size: 12px; color: var(--ph-text-disabled); margin-left: 10px; }
.tno { font-family: monospace; color: var(--ph-text-secondary); font-size: 12px; letter-spacing: .5px; }

/* ===== ticket info (申请单式) ===== */
.tk-title { font-size: var(--ph-font-md); color: var(--ph-text-primary); }
.tk-info { background: var(--ph-fill-light); border-radius: var(--ph-radius-lg);
  padding: var(--ph-space-2) var(--ph-space-4); margin-bottom: var(--ph-space-4); }
.tk-row { display: flex; align-items: center; padding: 6px 0; }
.tk-row + .tk-row { border-top: 1px dashed var(--ph-border-lighter); }
.tk-k { width: 84px; flex-shrink: 0; color: var(--ph-text-secondary); font-size: var(--ph-font-xs); }
.tk-v { color: var(--ph-text-primary); font-size: var(--ph-font-sm); display: inline-flex; align-items: center; gap: 6px; }
.tk-v.mono { font-family: 'SF Mono', Menlo, Consolas, monospace; letter-spacing: .5px; }
.tk-copy { cursor: pointer; color: var(--ph-text-secondary); font-size: 14px; }
.tk-copy:hover { color: var(--ph-primary); }

/* ===== form content ===== */
.tk-form { background: var(--ph-fill-blank, #fff); border: 1px solid var(--ph-border-lighter);
  border-radius: var(--ph-radius-lg); margin-bottom: var(--ph-space-4); overflow: hidden; }
.tk-form-grid { display: flex; flex-direction: column; }
.tk-cell { display: flex; padding: 9px var(--ph-space-4); border-bottom: 1px dashed var(--ph-border-lighter);
  align-items: baseline; }
.tk-cell:last-child { border-bottom: none; }
.tk-cell-k { width: 96px; flex-shrink: 0; color: var(--ph-text-secondary); font-size: var(--ph-font-xs); }
.tk-cell-v { color: var(--ph-text-primary); font-size: var(--ph-font-sm); word-break: break-all; flex: 1; }
.tk-cell-v.is-money { color: var(--ph-danger); font-weight: 700; font-variant-numeric: tabular-nums; }
.tk-full { padding: 10px var(--ph-space-4); border-top: 1px dashed var(--ph-border-lighter); }
.tk-table { width: 100%; border-collapse: collapse; margin-top: 6px; }
.tk-table th, .tk-table td { border: 1px solid var(--ph-border-lighter); padding: 5px 10px;
  font-size: var(--ph-font-xs); text-align: left; }
.tk-table th { background: var(--ph-fill-light); color: var(--ph-text-secondary); font-weight: 600; }
.tk-files { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 6px; }
.tk-img { width: 64px; height: 64px; border-radius: var(--ph-radius-base); border: 1px solid var(--ph-border-lighter); }
.tk-empty-inline { color: var(--ph-text-disabled); font-size: var(--ph-font-xs); }
:deep(.clickable) { cursor: pointer; }
</style>

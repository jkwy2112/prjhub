<template>
  <div>
    <div class="toolbar">
      <el-radio-group v-model="tab">
        <el-radio-button value="pending">我的待办</el-radio-button>
        <el-radio-button value="submitted">我发起的</el-radio-button>
      </el-radio-group>
      <el-button type="primary" :icon="Plus" @click="openCreate">发起审批</el-button>
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
      <el-table-column label="发起时间" width="160">
        <template #default="{ row }">{{ fmtDateTime(row.ticket.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button type="success" size="small" @click="act(row.task_id, 'approve')">同意</el-button>
          <el-button type="danger" plain size="small" @click="act(row.task_id, 'reject')">驳回</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 我发起的 -->
    <el-table v-else :data="submitted" v-loading="loading" style="background: #fff; border-radius: 8px"
      @row-click="openDetail" row-class-name="clickable">
      <el-table-column label="标题" min-width="200">
        <template #default="{ row }">{{ row.title }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag size="small" :type="statusMeta(row.status).type">{{ statusMeta(row.status).label }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="流程" width="200">
        <template #default="{ row }">{{ row.definition_name || '通用审批流' }} v{{ row.definition_version }}</template>
      </el-table-column>
      <el-table-column v-if="submittedAmountLabel" :label="submittedAmountLabel" width="110">
        <template #default="{ row }">{{ amountText(row) }}</template>
      </el-table-column>
      <el-table-column label="当前待审批" width="140">
        <template #default="{ row }">
          {{ row.tasks.filter((t) => t.status === 'pending').map((t) => t.node_name).join('、') || '-' }}
        </template>
      </el-table-column>
      <el-table-column label="发起时间" width="160">
        <template #default="{ row }">{{ fmtDateTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="80" fixed="right">
        <template #default="{ row }">
          <el-button v-if="row.status === 'running'" text type="danger" size="small"
            @click.stop="cancel(row.id)">撤回</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 发起审批 -->
    <el-dialog v-model="createVisible" title="发起审批" width="560px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="流程模板">
          <el-select v-model="form.definition_key" style="width: 100%">
            <el-option v-for="d in definitions" :key="d.key" :value="d.key" :label="d.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="标题" required><el-input v-model="form.title" maxlength="255" /></el-form-item>

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
            <el-select v-model="rc.users" multiple filterable remote :remote-method="searchUsers"
              placeholder="搜索并选择抄送人(可选)" style="width: 100%">
              <el-option v-for="u in userOptions" :key="u.id" :value="u.id" :label="u.name || u.username" />
            </el-select>
          </el-form-item>
          <!-- runtime approvers from tree -->
          <el-form-item v-for="rt in runtimeApprovers" :key="rt.tid" :label="rt.name" required>
            <el-select v-model="rt.users" multiple filterable remote :remote-method="searchUsers"
              placeholder="搜索并选择审批人" style="width: 100%">
              <el-option v-for="u in userOptions" :key="u.id" :value="u.id" :label="u.name || u.username" />
            </el-select>
          </el-form-item>
        </template>

        <template v-else-if="form.definition_key === 'parallel_approval'">
          <el-form-item label="一级审批人" required>
            <el-select v-model="form.approver_l1" filterable remote :remote-method="searchUsers"
              placeholder="搜索用户" style="width: 100%">
              <el-option v-for="u in userOptions" :key="u.id" :value="u.id" :label="u.name || u.username" />
            </el-select>
          </el-form-item>
          <el-form-item label="财务审批人" required>
            <el-select v-model="form.approver_fin" filterable remote :remote-method="searchUsers"
              placeholder="并行分支 A" style="width: 100%">
              <el-option v-for="u in userOptions" :key="u.id" :value="u.id" :label="u.name || u.username" />
            </el-select>
          </el-form-item>
          <el-form-item label="技术评审人" required>
            <el-select v-model="form.approver_tech" filterable remote :remote-method="searchUsers"
              placeholder="并行分支 B" style="width: 100%">
              <el-option v-for="u in userOptions" :key="u.id" :value="u.id" :label="u.name || u.username" />
            </el-select>
          </el-form-item>
        </template>

        <template v-else>
          <el-form-item label="金额" required>
            <el-input-number v-model="form.amount" :min="0" :step="100" />
            <span class="form-tip">金额 &gt; 1000 走「会签」分支</span>
          </el-form-item>
          <el-form-item label="一级审批人" required>
            <el-select v-model="form.approver_l1" filterable remote :remote-method="searchUsers"
              placeholder="搜索用户" style="width: 100%">
              <el-option v-for="u in userOptions" :key="u.id" :value="u.id" :label="u.name || u.username" />
            </el-select>
          </el-form-item>
          <el-form-item label="二级审批人">
            <el-select v-model="form.approver_l2" filterable remote :remote-method="searchUsers" clearable
              placeholder="小额分支的二级审批人" style="width: 100%">
              <el-option v-for="u in userOptions" :key="u.id" :value="u.id" :label="u.name || u.username" />
            </el-select>
          </el-form-item>
          <el-form-item label="会签人">
            <el-select v-model="form.countersigners" multiple filterable remote :remote-method="searchUsers"
              placeholder="大额分支会签(2人通过即过)" style="width: 100%">
              <el-option v-for="u in userOptions" :key="u.id" :value="u.id" :label="u.name || u.username" />
            </el-select>
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
          <b>{{ detail?.title || '审批详情' }}</b>
          <el-button size="small" :icon="Printer" @click="printTicket">打印</el-button>
        </div>
      </template>
      <template v-if="detail">
        <el-descriptions :column="2" border size="small" style="margin-bottom: 16px">
          <el-descriptions-item label="状态">
            <el-tag size="small" :type="statusMeta(detail.status).type">{{ statusMeta(detail.status).label }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="流程版本">v{{ detail.definition_version }}</el-descriptions-item>
          <el-descriptions-item v-if="amountFieldOf(detail)" :label="amountFieldOf(detail).title">
            {{ amountText(detail) }}
          </el-descriptions-item>
          <el-descriptions-item label="发起时间">{{ fmtDateTime(detail.created_at) }}</el-descriptions-item>
        </el-descriptions>
        <el-card v-if="detail.form_items?.length" shadow="never" style="margin-bottom: 14px">
          <template #header><b>表单内容</b><span v-if="permHiddenCount" style="font-size: 12px; color: #c0c4cc; margin-left: 8px">({{ permHiddenCount }} 个字段按权限隐藏)</span></template>
          <div v-for="f in visibleFormItems" :key="f.id" class="form-value-row">
            <span class="form-value-label">{{ f.title }}</span>
            <span class="form-value-text">{{ displayValue(f) }}
              <el-tag v-if="isEditable(f)" size="small" type="warning" style="margin-left: 4px">可编辑</el-tag>
            </span>
          </div>
        </el-card>
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
        found.push({ tid: node.bpmnId, name: node.name, users: [] })
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
        ccs.push({ tid: node.bpmnId, name: node.name, users: [] })
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
    h2{margin-bottom:4px} .meta{color:#909399;font-size:12px;margin-bottom:16px}
    table{width:100%;border-collapse:collapse;margin-bottom:16px}
    td,th{border:1px solid #dcdfe6;padding:6px 10px;font-size:13px;text-align:left}
    th{background:#f5f7fa}</style></head><body>
    <h2>${d.title}</h2>
    <div class="meta">流程: ${d.definition_name || ''} v${d.definition_version} | 状态: ${statusMeta(d.status).label} | 发起: ${fmtDateTime(d.created_at)}</div>
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
        if (hit) userMap[id] = hit.name || hit.username
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

function openCreate() {
  Object.assign(form, {
    definition_key: definitions.value[0]?.key || 'generic_approval', title: '', amount: 100,
    approver_l1: null, approver_l2: null, countersigners: [], approver_fin: null, approver_tech: null,
  })
  createVisible.value = true
}

async function submit() {
  if (!form.title.trim()) return ElMessage.warning('请填写标题')
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
    await api.post('/approvals', {
      definition_key: form.definition_key,
      title: form.title,
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
.toolbar { display: flex; justify-content: space-between; margin-bottom: 14px; }
.form-tip { font-size: 12px; color: #c0c4cc; margin-left: 10px; }
:deep(.clickable) { cursor: pointer; }
</style>

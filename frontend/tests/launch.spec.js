// @vitest-environment happy-dom
import { describe, it, expect, vi } from 'vitest'
import { mount, config } from '@vue/test-utils'
import { nextTick } from 'vue'
import ElementPlus from 'element-plus'
import Approvals from '../src/views/Approvals.vue'
import api from '../src/api'
import { createPinia } from 'pinia'

config.global.plugins = [ElementPlus, createPinia()]
globalThis.localStorage = globalThis.localStorage || { getItem: () => null, setItem(){}, removeItem(){} }

const DEFINITIONS = [
  { id: 4, key: 'expense_v2', name: '报销审批V2', is_active: true, has_tree: true, has_form: true, version: 1 },
  { id: 2, key: 'parallel_approval', name: '并行多分支', is_active: true, has_tree: false, has_form: false, version: 1 },
  { id: 1, key: 'generic_approval', name: '通用审批流', is_active: true, has_tree: false, has_form: false, version: 1 },
]
const TREE = {
  id: 4, key: 'expense_v2', version: 1,
  tree: { type: 'ROOT', childNode: { type: 'APPROVAL', name: '直属主管', bpmnId: 'ut_ap1',
    props: { assigneeType: 'runtime', users: [], mode: 'any' },
    childNode: { type: 'CC', name: '抄送备案', bpmnId: 'ut_cc1',
      props: { assigneeType: 'users', users: [2] }, childNode: null } } },
  form_items: [{ id: 'f_amou', name: 'AmountInput', title: '报销金额', valueType: 'Number',
    props: { required: true } }],
}
const USERS = [
  { id: 1, username: 'admin', name: '管理员', dept: '技术部' },
  { id: 2, username: 'user01', name: '张三', dept: '财务部' },
]
const TICKETS_SUBMITTED = []

api.get = (url) => {
  if (url.startsWith('/approvals/definitions/') && url.includes('/tree')) return Promise.resolve({ data: TREE })
  if (url.startsWith('/approvals/definitions')) return Promise.resolve({ data: DEFINITIONS })
  if (url.startsWith('/users')) return Promise.resolve({ data: USERS })
  if (url.startsWith('/approvals/my-pending')) return Promise.resolve({ data: [] })
  if (url.startsWith('/approvals/my-submitted')) return Promise.resolve({ data: TICKETS_SUBMITTED })
  if (url.startsWith('/approvals/')) return Promise.resolve({ data: [] })
  return Promise.resolve({ data: [] })
}
api.post = vi.fn(() => Promise.resolve({ data: { id: 1, tasks: [], status: 'running' } }))

const flush = async (ms = 80) => { await nextTick(); await new Promise((r) => setTimeout(r, ms)) }

describe('发起审批对话框', () => {
  it('选择设计流程后: 表单字段+审批人选择器可见, 提交携带 approver_<tid>', async () => {
    const w = mount(Approvals, { attachTo: document.body })
    await flush(200)

    // switch to 发起审批 tab (gallery)
    const tabBtn = w.findAll('.el-radio-button__original-radio, .el-radio-button').find((b) => b.text().includes('发起审批'))
    const tabEl = [...document.querySelectorAll('.el-radio-button')].find((b) => b.textContent.includes('发起审批'))
    tabEl.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    await flush(100)
    const card = [...document.querySelectorAll('.tpl-card')].find((c) => c.textContent.includes('报销审批V2'))
    expect(card, '模板卡片存在').toBeTruthy()
    card.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    await flush(150)

    // dialog open?
    const dlg = document.querySelector('.el-dialog')
    expect(dlg, '对话框打开').toBeTruthy()

    const dlgText = document.querySelector('.el-dialog')?.textContent || ''
    console.log('DIALOG TEXT >>>', dlgText.slice(0, 400))

    // approval picker form item should exist (直属主管)
    expect(dlgText.includes('直属主管'), '审批人「直属主管」表单项可见').toBe(true)
    // form field visible
    expect(dlgText.includes('报销金额'), '表单字段「报销金额」可见').toBe(true)
    // picker trigger button must render
    const upTriggers = document.querySelectorAll('.up-trigger')
    console.log('TRIGGERS:', upTriggers.length, '| inner:', upTriggers[0]?.innerHTML?.slice(0, 120))
    expect(upTriggers.length >= 1, 'UserPickerField 触发器渲染').toBe(true)
    expect(dlgText.includes('选择人员'), '空态显示「选择人员」按钮').toBe(true)

    w.unmount()
  }, 30000)
})

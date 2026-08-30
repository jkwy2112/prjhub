// @vitest-environment happy-dom
import { describe, it, expect } from 'vitest'
import { mount, config } from '@vue/test-utils'
import { nextTick } from 'vue'
import ElementPlus from 'element-plus'
import UserPickerField from '../src/components/common/UserPickerField.vue'
import api from '../src/api'

config.global.plugins = [ElementPlus]

const USERS = [
  { id: 1, username: 'admin', name: '管理员', dept: '技术部' },
  { id: 2, username: 'user01', name: '张三', dept: '财务部' },
]
api.get = (url) => {
  if (url.startsWith('/users')) return Promise.resolve({ data: USERS })
  return Promise.resolve({ data: [] })
}
api.post = () => Promise.resolve({ data: {} })

describe('UserPickerField', () => {
  it('多选: 预选渲染 tags, 空态显示选择人员按钮', () => {
    const w = mount(UserPickerField, { props: {
      modelValue: [{ id: 1, username: 'admin', name: '管理员' }, { id: 2, username: 'user01', name: '张三' }],
      multiple: true } })
    expect(w.findAll('.el-tag').length).toBe(2)
    const w2 = mount(UserPickerField, { props: { modelValue: [], multiple: true } })
    expect(w2.text()).toContain('选择人员')
  })

  it('单选: 头像胶囊显示姓名', () => {
    const w = mount(UserPickerField, { props: {
      modelValue: { id: 1, username: 'admin', name: '管理员' }, multiple: false } })
    expect(w.text()).toContain('管理员')
  })

  it('点击打开弹窗, 列出人员, 选择后 change 事件携带用户对象数组', async () => {
    const w = mount(UserPickerField, {
      props: { modelValue: [], multiple: true },
      attachTo: document.body,
    })
    await w.find('.up-trigger').trigger('click')
    await nextTick()
    await new Promise((r) => setTimeout(r, 80))
    const items = document.querySelectorAll('.up-item')
    expect(items.length).toBe(2)
    items[0].dispatchEvent(new MouseEvent('click', { bubbles: true }))
    await nextTick()
    await new Promise((r) => setTimeout(r, 30))
    const ok = [...document.querySelectorAll('.el-dialog__footer .el-button')].find((b) => b.textContent.includes('确'))
    ok.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    await nextTick()
    await new Promise((r) => setTimeout(r, 30))
    const emitted = w.emitted('change')
    expect(Array.isArray(emitted[0][0])).toBe(true)
    expect(emitted[0][0].length).toBe(1)
    expect(emitted[0][0][0].username).toBe('admin')
    w.unmount()
  })
})

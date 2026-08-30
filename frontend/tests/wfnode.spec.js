// @vitest-environment happy-dom
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import WfNode from '../src/components/flow/WfNode.vue'

const approval = (name, child = null) => ({ type: 'APPROVAL', name,
  props: { assigneeType: 'users', users: [1], mode: 'any' }, childNode: child })

const conditions = () => ({
  type: 'CONDITIONS', name: '条件分支',
  branches: [
    { type: 'CONDITION', name: '条件1', childNode: approval('A审批') },
    { type: 'CONDITION', name: '默认', childNode: approval('B审批') },
    { type: 'CONDITION', name: '条件3', childNode: null },
  ],
  childNode: approval('终审'),
})

const mountNode = (node) => mount(WfNode, {
  props: { node, selected: null, errorNodes: null },
  global: { plugins: [ElementPlus] },
})
const findCardDel = (w, name) => {
  for (const c of w.findAll('.wf-card')) if (c.text().includes(name)) return c.find('.wf-del')
  return null
}

describe('WfNode interactions', () => {
  it('T1: 分支头删除只删该分支, 不影响分支组和后续链', async () => {
    const node = conditions()
    const w = mountNode(node)
    const dels = w.findAll('.wf-cond-ops .del')
    expect(dels.length).toBe(3)
    await dels[0].trigger('click')
    expect(node.branches.length).toBe(2)
    expect(node.type).toBe('CONDITIONS')
    expect(node.childNode.name).toBe('终审')
    expect(node.branches[0].name).toBe('默认')
  })

  it('T2: 删除分支内链尾节点(C)不影响链头(A)', async () => {
    const node = conditions()
    node.branches[0].childNode.childNode = approval('C审批')
    const w = mountNode(node)
    const cDel = findCardDel(w, 'C审批')
    expect(cDel).toBeTruthy()
    await cDel.trigger('click')
    expect(node.branches[0].childNode.name).toBe('A审批')
    expect(node.branches[0].childNode.childNode).toBeNull()
  })

  it('T3: 删除分支内唯一节点 → 分支置空, 分支组不动', async () => {
    const node = conditions()
    const w = mountNode(node)
    await findCardDel(w, 'A审批').trigger('click')
    expect(node.branches[0].childNode).toBeNull()
    expect(node.type).toBe('CONDITIONS')
    expect(node.branches.length).toBe(3)
  })

  it('T4: 删除分支组本身 → 被汇聚后的子链替换', async () => {
    const node = conditions()
    const w = mountNode(node)
    await findCardDel(w, '条件分支').trigger('click')
    expect(node.type).toBe('APPROVAL')
    expect(node.name).toBe('终审')
  })

  it('T5: 空画布 ROOT 只有 1 个 +', () => {
    const w = mountNode({ type: 'ROOT', name: '发起人', childNode: null })
    expect(w.findAll('.wf-plus-btn').length).toBe(1)
  })

  it('T6: A→B 链 3 个插入点 (ROOT/A/B 各一, wflow 语义)', () => {
    const w = mountNode({ type: 'ROOT', name: '发起人', childNode: approval('A', approval('B')) })
    expect(w.findAll('.wf-plus-btn').length).toBe(3)
  })
})

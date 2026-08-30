<template>
  <div class="wf-seg">
    <!-- node card (wflow Node.vue visual spec: 220px, color header, hover shadow) -->
    <div class="wf-card" :class="[`t-${node.type.toLowerCase()}`, { selected: selected === node }]"
      :style="{ '--c': color }" @click="$emit('select', node)">
      <div v-if="node.type !== 'ROOT'" class="wf-del" @click.stop="removeSelf"><el-icon><Close /></el-icon></div>

      <div class="wf-card-in" v-if="node.type === 'ROOT'">
        <div class="wf-root-row">
          <el-icon class="wf-root-ic"><Promotion /></el-icon>
          <div class="wf-root-info">
            <p class="wf-name">{{ node.name || '发起人' }}</p>
            <p class="wf-desc">{{ summary }}</p>
          </div>
        </div>
      </div>

      <div class="wf-card-in" v-else>
        <div class="wf-head">
          <span class="wf-head-ic"><el-icon><component :is="icon" /></el-icon></span>
          <p class="wf-name">{{ node.name || defaultName }}</p>
          <span v-if="badges.length" class="wf-badges">
            <span v-for="b in badges" :key="b" class="wf-badge" :class="b.cls">{{ b.text }}</span>
          </span>
        </div>
        <div class="wf-body-row">
          <p class="wf-desc">{{ summary }}</p>
          <el-icon class="wf-arrow"><ArrowRight /></el-icon>
        </div>
        <span v-if="hasError" class="wf-err-dot" />
      </div>
    </div>

    <!-- insert plus (wflow: circle btn on the vertical line) -->
    <div v-if="node.type !== 'CONDITIONS' && node.type !== 'CONCURRENTS'" class="wf-plus-row">
      <el-popover placement="right-start" trigger="hover" width="290">
        <template #reference>
          <span class="wf-plus-btn"><el-icon><Plus /></el-icon></span>
        </template>
        <div class="wf-menu">
          <div class="wf-menu-item" @click="insert('APPROVAL')">
            <span class="mi-ic" style="background: #ff943e"><el-icon><Stamp /></el-icon></span>审批人
          </div>
          <div class="wf-menu-item" @click="insert('CC')">
            <span class="mi-ic" style="background: #3296fa"><el-icon><Promotion /></el-icon></span>抄送人
          </div>
          <div class="wf-menu-item" @click="insert('CONDITIONS')">
            <span class="mi-ic" style="background: #15bc83"><el-icon><Share /></el-icon></span>条件分支
          </div>
          <div class="wf-menu-item" @click="insert('CONCURRENTS')">
            <span class="mi-ic" style="background: #718dff"><el-icon><Operation /></el-icon></span>并行分支
          </div>
          <div class="wf-menu-item" @click="insert('TRIGGER')">
            <span class="mi-ic" style="background: #9254de"><el-icon><Link /></el-icon></span>触发器
          </div>
        </div>
      </el-popover>
    </div>

    <!-- branch group: wflow fork/join rails + spine + cover lines -->
    <div v-if="node.type === 'CONDITIONS' || node.type === 'CONCURRENTS'" class="wf-branch-group">
      <div class="wf-branch-add" @click="addBranch">
        <el-button size="small" round>添加{{ node.type === 'CONDITIONS' ? '条件' : '分支' }}</el-button>
      </div>
      <div class="wf-branch-cols">
        <div v-for="(branch, i) in node.branches" :key="i" class="wf-branch-col">
          <span v-if="i === 0" class="cover tl" /><span v-if="i === 0" class="cover bl" />
          <span v-if="i === node.branches.length - 1" class="cover tr" /><span v-if="i === node.branches.length - 1" class="cover br" />

          <div class="wf-cond-head" @click="$emit('select', branch)">
            <span class="wf-cond-lv">优先级{{ i + 1 }}</span>
            <p class="wf-cond-name">{{ branch.name || `条件${i + 1}` }}</p>
            <span class="wf-cond-ops">
              <el-icon v-if="node.type === 'CONDITIONS' && i > 0" class="op" @click.stop="moveBranch(i, -1)"><ArrowLeft /></el-icon>
              <el-icon v-if="node.type === 'CONDITIONS' && i < node.branches.length - 1" class="op"
                @click.stop="moveBranch(i, 1)"><ArrowRight /></el-icon>
              <el-icon v-if="node.branches.length > 2" class="op del" @click.stop="node.branches.splice(i, 1)"><Close /></el-icon>
            </span>
          </div>

          <div class="wf-branch-chain">
            <WfNode v-if="branch.childNode" :node="branch.childNode" :selected="selected"
              :error-nodes="errorNodes"
              @select="$emit('select', $event)" @self-remove="branch.childNode = null"
              @changed="$emit('changed')" />
            <div v-else class="wf-branch-empty" @click="$emit('select', branch)">
              <el-icon><Plus /></el-icon>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- child chain -->
    <WfNode v-if="node.childNode" :node="node.childNode" :selected="selected"
      :error-nodes="errorNodes"
      @select="$emit('select', $event)" @self-remove="removeChild" @changed="$emit('changed')" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Plus, Close, ArrowRight, ArrowLeft, Stamp, Promotion, Share, Operation, Link } from '@element-plus/icons-vue'

defineOptions({ name: 'WfNode' })

const props = defineProps({
  node: { type: Object, required: true },
  selected: { type: Object, default: null },
  errorNodes: { type: Object, default: null },
})
const emit = defineEmits(['select', 'self-remove', 'changed'])

const iconMap = {
  ROOT: Promotion, APPROVAL: Stamp, CONDITIONS: Share, CONCURRENTS: Operation,
  CC: Promotion, TRIGGER: Link,
}
const icon = computed(() => iconMap[props.node.type] || Stamp)
const defaultName = computed(() => ({
  ROOT: '发起人', APPROVAL: '审批', CONDITIONS: '条件分支', CONCURRENTS: '并行分支',
  CC: '抄送人', TRIGGER: '触发器',
}[props.node.type] || ''))
const color = computed(() => ({
  ROOT: 'var(--ph-node-root)', APPROVAL: 'var(--ph-node-approval)',
  CONDITIONS: 'var(--ph-node-condition)', CONCURRENTS: 'var(--ph-node-concurrent)',
  CC: 'var(--ph-node-cc)', TRIGGER: 'var(--ph-node-trigger)',
}[props.node.type] || 'var(--ph-node-root)'))
const hasError = computed(() => !!props.errorNodes?.has?.(props.node)
  || !!(props.node.type === 'CONDITION' && props.errorNodes?.has?.(props.node)))

const badges = computed(() => {
  const n = props.node
  const out = []
  if (n.type === 'APPROVAL') {
    if ((n.props?.users || []).length > 1 || n.props?.assigneeType === 'runtime') out.push({ text: '多人', cls: 'b-blue' })
    if (n.props?.mode === 'all') out.push({ text: '会签', cls: 'b-orange' })
    if (n.props?.mode === 'next') out.push({ text: '依次', cls: 'b-orange' })
    if (n.props?.mode === 'count') out.push({ text: `票${n.props?.count}`, cls: 'b-orange' })
    if (n.props?.assigneeType === 'runtime') out.push({ text: '发起时指定', cls: 'b-blue' })
    if (n.props?.assigneeType === 'form') out.push({ text: '表单联系人', cls: 'b-green' })
    if (n.props?.assigneeType === 'self') out.push({ text: '发起人', cls: 'b-green' })
    if (n.props?.refuse === 'TO_BEFORE') out.push({ text: '驳回退回上节点', cls: 'b-gray' })
    if (n.props?.refuse === 'TO_NODE') out.push({ text: '驳回指定节点', cls: 'b-gray' })
    if (n.props?.timeout?.enabled) out.push({ text: `限时${n.props.timeout.value}${n.props.timeout.unit === 'H' ? '时' : '天'}`, cls: 'b-red' })
  }
  return out.slice(0, 3)
})

const summary = computed(() => {
  const n = props.node
  if (n.type === 'ROOT') return '所有人'
  if (n.type === 'APPROVAL') {
    if (n.props?.assigneeType === 'self') return '发起人自己审批'
    if (n.props?.assigneeType === 'form') return '表单联系人审批'
    if (n.props?.assigneeType === 'runtime') return '发起时选择审批人'
    const c = (n.props?.users || []).length
    return c ? `${c} 名成员` : '未设置审批人'
  }
  if (n.type === 'CC') {
    if (n.props?.assigneeType === 'runtime') return '发起时选择'
    const c = (n.props?.users || []).length
    return c ? `${c} 人接收通知` : '未设置抄送人'
  }
  if (n.type === 'TRIGGER') {
    return `${n.props?.method || 'GET'} ${(n.props?.url || '未配置').replace(/^https?:\/\//, '').slice(0, 24)}`
  }
  if (n.type === 'CONDITIONS' || n.type === 'CONCURRENTS') {
    return `${n.branches?.length || 0} 个分支`
  }
  return ''
})

function insert(type) {
  const child = newNode(type)
  child.childNode = props.node.childNode || null
  props.node.childNode = child
  emit('select', child)
  emit('changed')
}

function newNode(type) {
  if (type === 'APPROVAL') {
    return { type, name: '审批节点', props: { assigneeType: 'users', users: [], mode: 'any', count: 2,
      nobody: { handler: 'to_admin' }, refuse: 'TO_END', refuseTarget: '', formField: '',
      formPerms: {}, timeout: { enabled: false, unit: 'H', value: 24, handler: 'NOTIFY' } }, childNode: null }
  }
  if (type === 'TRIGGER') {
    return { type, name: '触发器', props: { url: '', method: 'POST' }, childNode: null }
  }
  if (type === 'CC') {
    return { type, name: '抄送人', props: { assigneeType: 'users', users: [] }, childNode: null }
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

function addBranch() {
  const n = props.node
  if (n.branches.length >= 8) return
  if (n.type === 'CONDITIONS') {
    const defIdx = n.branches.findIndex((b) => !(b.props?.groups || []).some((g) => (g.conditions || []).length))
    const branch = { type: 'CONDITION', name: `条件${n.branches.length}`, childNode: null,
      props: { groupsType: 'AND', groups: [{ groupType: 'AND', conditions: [] }] } }
    if (defIdx >= 0) n.branches.splice(defIdx, 0, branch)
    else n.branches.push(branch)
  } else {
    n.branches.push({ type: 'BRANCH', name: `分支${n.branches.length + 1}`, childNode: null })
  }
  emit('changed')
}

function moveBranch(i, delta) {
  const arr = props.node.branches
  const [item] = arr.splice(i, 1)
  arr.splice(i + delta, 0, item)
  emit('changed')
}

function removeSelf() {
  const n = props.node
  if (n.childNode) {
    Object.assign(n, JSON.parse(JSON.stringify(n.childNode)))
    emit('changed')
  } else {
    emit('self-remove')
  }
}

// my direct child asked to be removed -> replace it with ITS child chain
function removeChild() {
  const n = props.node
  n.childNode = n.childNode?.childNode || null
  emit('changed')
}
</script>

<style scoped>
/* ===== wflow Node.vue visual spec ===== */
.wf-seg { display: flex; flex-direction: column; align-items: center; width: 100%; }

.wf-card {
  position: relative; width: 232px; background: var(--ph-fill-blank, #fff);
  border-radius: var(--ph-radius-lg); border: 1px solid var(--ph-border-lighter);
  cursor: pointer; box-shadow: var(--ph-shadow-1); transition: box-shadow .2s, border-color .2s, transform .15s;
}
.wf-card:hover { box-shadow: var(--ph-shadow-2); transform: translateY(-1px); }
.wf-card.selected { border-color: var(--ph-primary); box-shadow: 0 0 0 2px var(--ph-primary-light-7), var(--ph-shadow-2); }
.wf-card.t-ROOT { box-shadow: none; background: transparent; border-color: transparent; }

.wf-card-in { padding: 0; }
.wf-head {
  display: flex; align-items: center; gap: 8px; padding: 10px 12px 4px;
}
.wf-head-ic {
  display: flex; align-items: center; justify-content: center; width: 24px; height: 24px;
  border-radius: var(--ph-radius-md); font-size: 13px; flex-shrink: 0;
  background: color-mix(in srgb, var(--c) 12%, white); color: var(--c);
}
.wf-name { color: var(--ph-text-primary); font-size: var(--ph-font-sm); font-weight: 600; flex: 1;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.wf-badges { display: flex; gap: 3px; flex-shrink: 0; }
.wf-badge {
  font-size: 10px; line-height: 15px; padding: 0 5px; border-radius: var(--ph-radius-sm);
  background: color-mix(in srgb, var(--c) 10%, white); color: var(--c);
  border: 1px solid color-mix(in srgb, var(--c) 22%, white);
}
.wf-body-row { display: flex; align-items: center; padding: 6px 12px 10px; min-height: 34px; }
.wf-desc { flex: 1; color: var(--ph-text-secondary); font-size: var(--ph-font-xs);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.wf-arrow { color: var(--ph-text-placeholder); font-size: 12px; flex-shrink: 0; }

/* ROOT pill */
.wf-root-row { display: flex; align-items: center; gap: 10px; padding: 8px 12px; }
.wf-root-ic { width: 36px; height: 36px; border-radius: 50%;
  background: var(--ph-info-light-8); color: var(--ph-info);
  display: flex; align-items: center; justify-content: center; font-size: 17px; flex-shrink: 0; }
.wf-root-info .wf-name { color: var(--ph-text-primary); }
.wf-root-info .wf-desc { margin-top: 1px; }

.wf-del {
  position: absolute; top: -8px; right: -8px; width: 18px; height: 18px; border-radius: 50%;
  background: var(--ph-fill-blank, #fff); color: var(--ph-danger); border: 1px solid var(--ph-border-lighter);
  display: none; align-items: center; justify-content: center; font-size: 11px; cursor: pointer; z-index: 3;
  box-shadow: var(--ph-shadow-1);
}
.wf-card:hover .wf-del { display: flex; }
.wf-del:hover { background: var(--ph-danger); color: #fff; border-color: var(--ph-danger); }

.wf-err-dot { position: absolute; right: -9px; top: 12px; width: 17px; height: 17px; border-radius: 50%;
  background: var(--ph-danger); color: #fff; font-size: 11px; display: flex; align-items: center;
  justify-content: center; box-shadow: var(--ph-shadow-1); }
.wf-err-dot::after { content: '!'; font-weight: 700; }

/* ===== vertical line + plus (wflow: 2px #cacaca, round blue btn) ===== */
.wf-plus-row { position: relative; display: flex; justify-content: center; padding: 10px 0; width: 100%; }
.wf-plus-row::before { content: ''; position: absolute; top: -8px; bottom: 50%; left: 50%;
  transform: translateX(-1px); width: 2px; background: var(--ph-line); }
.wf-plus-btn {
  width: 28px; height: 28px; border-radius: 50%;
  background: var(--ph-fill-blank, #fff); color: var(--ph-primary);
  border: 1px solid var(--ph-primary-light-5); display: flex; align-items: center; justify-content: center;
  cursor: pointer; font-size: 14px; transition: all .15s; z-index: 2; box-shadow: var(--ph-shadow-1);
}
.wf-plus-btn:hover { background: var(--ph-primary); color: #fff; border-color: var(--ph-primary);
  transform: scale(1.08); box-shadow: 0 2px 8px var(--ph-primary-light-5); }

.wf-menu { display: flex; flex-direction: column; gap: 2px; }
.wf-menu-item { display: flex; align-items: center; gap: 10px; padding: 8px 10px; cursor: pointer;
  border-radius: var(--ph-radius-md); font-size: var(--ph-font-sm); color: var(--ph-text-regular);
  transition: background .15s; }
.wf-menu-item:hover { background: var(--ph-primary-light-9); color: var(--ph-primary); }
.mi-ic { width: 26px; height: 26px; border-radius: var(--ph-radius-md); display: flex; align-items: center;
  justify-content: center; color: #fff; font-size: 13px; flex-shrink: 0; }

/* ===== branch group (wflow: rails top/bottom + column spine + covers) ===== */
.wf-branch-group {
  position: relative; width: 100%; display: flex; flex-direction: column; align-items: center;
  border-top: 2px solid var(--ph-border); border-bottom: 2px solid var(--ph-border);
  padding: 26px 10px 4px; margin-top: 2px;
}
.wf-branch-add { position: absolute; top: -14px; left: 50%; transform: translateX(-50%); z-index: 4; }
.wf-branch-cols { display: flex; justify-content: center; flex-wrap: nowrap; }
.wf-branch-col {
  position: relative; display: flex; flex-direction: column; align-items: center;
  min-width: 240px; padding: 0 10px;
}
.wf-branch-col:not(:first-child) { border-left: 2px solid var(--ph-border); }
.wf-branch-col::before {
  content: ''; position: absolute; top: 0; left: calc(50% - 1px); width: 2px; height: 14px;
  background: var(--ph-border);
}
.cover { position: absolute; width: 50%; height: 4px; background: var(--ph-bg-page, #f2f3f5); z-index: 1; }
.cover.tl { top: -3px; left: -1px; }
.cover.tr { top: -3px; right: -1px; }
.cover.bl { bottom: -3px; left: -1px; }
.cover.br { bottom: -3px; right: -1px; }

/* condition head (wflow ConditionNode: green title + priority + ops) */
.wf-cond-head {
  position: relative; z-index: 3; display: flex; align-items: center; gap: 5px; max-width: 210px;
  margin: 6px 0 4px; padding: 3px 8px; cursor: pointer;
}
.wf-cond-lv { font-size: 10px; color: var(--ph-text-placeholder); flex-shrink: 0; }
.wf-cond-name { color: var(--ph-node-condition); font-size: var(--ph-font-xs); font-weight: 600; overflow: hidden;
  text-overflow: ellipsis; white-space: nowrap; max-width: 110px; }
.wf-cond-ops { display: none; align-items: center; gap: 4px; flex-shrink: 0; }
.wf-cond-head:hover .wf-cond-ops { display: flex; }
.wf-cond-head:hover .wf-cond-lv { display: none; }
.wf-cond-ops .op { font-size: 12px; color: var(--ph-text-placeholder); padding: 2px; border-radius: var(--ph-radius-sm); }
.wf-cond-ops .op:hover { color: var(--ph-primary); background: var(--ph-primary-light-9); }
.wf-cond-ops .del:hover { color: var(--ph-danger); background: var(--ph-danger-light-9); }

.wf-branch-chain { position: relative; z-index: 2; display: flex; flex-direction: column;
  align-items: center; width: 100%; }
.wf-branch-empty {
  width: 200px; height: 46px; margin: 8px 0; border: 1.5px dashed var(--ph-border);
  border-radius: var(--ph-radius-md); display: flex; align-items: center; justify-content: center;
  color: var(--ph-text-disabled); cursor: pointer; background: var(--ph-fill-blank, #fff);
  transition: all .15s;
}
.wf-branch-empty:hover { border-color: var(--ph-primary); color: var(--ph-primary);
  background: var(--ph-primary-light-9); }
</style>

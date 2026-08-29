<template>
  <div class="wf-seg">
    <!-- node card -->
    <div class="wf-card" :class="[`wf-${node.type.toLowerCase()}`, { selected: selected === node, error: hasError }]"
      :style="{ '--card-color': color }" @click="$emit('select', node)">
      <span class="wf-del" v-if="node.type !== 'ROOT'" @click.stop="removeSelf"><el-icon><Close /></el-icon></span>
      <div class="wf-card-head">
        <el-icon class="wf-icon"><component :is="icon" /></el-icon>
        <span class="wf-title">{{ node.name || defaultName }}</span>
        <span v-if="node.type === 'APPROVAL' && multiUsers" class="wf-badge">多人</span>
        <span v-if="node.type === 'APPROVAL' && node.props?.mode === 'all'" class="wf-badge cs">会签</span>
        <span v-if="node.type === 'APPROVAL' && node.props?.mode === 'count'" class="wf-badge cs">
          票签{{ node.props?.count }}
        </span>
        <span v-if="node.type === 'APPROVAL' && node.props?.assigneeType === 'runtime'" class="wf-badge rt">发起时指定</span>
        <span v-if="node.type === 'APPROVAL' && node.props?.refuse === 'TO_BEFORE'" class="wf-badge cs">驳回退回上节点</span>
      </div>
      <div class="wf-card-body">{{ summary }}</div>
    </div>

    <!-- insert plus (below card / below branch group) -->
    <div v-if="node.type !== 'ROOT' && node.type !== 'CONDITIONS' && node.type !== 'CONCURRENTS'"
      class="wf-plus-row">
      <el-popover placement="bottom-start" trigger="click" width="290">
        <template #reference>
          <span class="wf-plus-btn"><el-icon><Plus /></el-icon></span>
        </template>
        <div class="wf-menu">
          <div class="wf-menu-item" @click="insert('APPROVAL')">
            <el-icon style="color: #ff943e"><User /></el-icon>审批人
          </div>
          <div class="wf-menu-item" @click="insert('CC')">
            <el-icon style="color: #3296fa"><Promotion /></el-icon>抄送人
          </div>
          <div class="wf-menu-item" @click="insert('CONDITIONS')">
            <el-icon style="color: #15bc83"><Share /></el-icon>条件分支
          </div>
          <div class="wf-menu-item" @click="insert('CONCURRENTS')">
            <el-icon style="color: #718dff"><Operation /></el-icon>并行分支
          </div>
        </div>
      </el-popover>
    </div>

    <!-- branch group (dingtalk-style cover lines create fork/join visuals, see wflow ProcessTree) -->
    <div v-if="node.type === 'CONDITIONS' || node.type === 'CONCURRENTS'" class="wf-branch-group">
      <div class="wf-branch-add" @click="addBranch">
        <el-button size="small" round>添加{{ node.type === 'CONDITIONS' ? '条件' : '分支' }}</el-button>
      </div>
      <div class="wf-branch-cols">
        <div v-for="(branch, i) in node.branches" :key="i" class="wf-branch-col">
          <span v-if="i === 0" class="cover tl" /><span v-if="i === 0" class="cover bl" />
          <span v-if="i === node.branches.length - 1" class="cover tr" /><span v-if="i === node.branches.length - 1" class="cover br" />
          <div class="wf-branch-col-head" :class="{ 'head-error': errorNodes?.has?.(branch) }" @click="$emit('select', branch)">
            <span class="wf-branch-col-move" v-if="node.type === 'CONDITIONS' && i > 0"
              @click.stop="moveBranch(i, -1)"><el-icon><ArrowLeft /></el-icon></span>
            <span class="wf-branch-col-title">{{ branch.name || `条件${i + 1}` }}</span>
            <span class="wf-branch-col-move" v-if="node.type === 'CONDITIONS' && i < node.branches.length - 1"
              @click.stop="moveBranch(i, 1)"><el-icon><ArrowRight /></el-icon></span>
            <span class="wf-branch-col-del" v-if="node.branches.length > 2"
              @click.stop="removeBranch(i)"><el-icon><Close /></el-icon></span>
          </div>
          <div class="wf-branch-chain">
            <WfNode v-if="branch.childNode" :node="branch.childNode" :selected="selected"
              :error-nodes="errorNodes"
              @select="$emit('select', $event)" @self-remove="branch.childNode = null"
              @changed="$emit('changed')" />
            <div v-else class="wf-branch-empty" @click="$emit('select', branch)">点击设置分支内容</div>
          </div>
        </div>
      </div>
    </div>

    <!-- child chain -->
    <WfNode v-if="node.childNode" :node="node.childNode" :selected="selected"
      :error-nodes="errorNodes"
      @select="$emit('select', $event)" @self-remove="removeSelf" @changed="$emit('changed')" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Plus, Close, User, Share, Operation, ArrowLeft, ArrowRight, Stamp, Promotion } from '@element-plus/icons-vue'

defineOptions({ name: 'WfNode' })

const props = defineProps({
  node: { type: Object, required: true },
  selected: { type: Object, default: null },
  errorNodes: { type: Object, default: null },
})
const hasError = computed(() => !!props.errorNodes?.has?.(props.node))
const emit = defineEmits(['select', 'self-remove', 'changed'])

const iconMap = {
  ROOT: Promotion, APPROVAL: Stamp, CONDITIONS: Share, CONCURRENTS: Operation, CC: Promotion,
}
const icon = computed(() => iconMap[props.node.type] || Stamp)
const defaultName = computed(() => ({ ROOT: '发起人', APPROVAL: '审批', CONDITIONS: '条件分支', CONCURRENTS: '并行分支', CC: '抄送人' }[props.node.type] || ''))
const color = computed(() => ({
  ROOT: '#409EFF', APPROVAL: '#ff943e', CONDITIONS: '#15bc83', CONCURRENTS: '#718dff', CC: '#3296fa',
}[props.node.type] || '#909399'))
const multiUsers = computed(() => (props.node.props?.users?.length || 0) > 1 || props.node.props?.assigneeType === 'runtime')

const summary = computed(() => {
  const n = props.node
  if (n.type === 'ROOT') return '所有人可发起'
  if (n.type === 'CC') {
    if (n.props?.assigneeType === 'runtime') return '发起时指定'
    return `${(n.props?.users || []).length || '未指定'} 人接收通知`
  }
  if (n.type === 'APPROVAL') {
    if (n.props?.assigneeType === 'runtime') return `发起时指定 · ${modeLabel(n.props?.mode)}`
    const names = (n.props?.users || []).length
    return `${names ? names + ' 人' : '未指定'} · ${modeLabel(n.props?.mode)}`
  }
  if (n.type === 'CONDITIONS') {
    const empty = n.branches?.filter((b) => !b.props?.groups?.some((g) => g.conditions?.length)).length
    return `${n.branches?.length || 0} 个条件分支${empty ? ` · ${empty} 个默认` : ''}`
  }
  return `${n.branches?.length || 0} 个并行分支`
})

function modeLabel(mode) {
  if (mode === 'all') return '会签(全部通过)'
  if (mode === 'count') return '票签(N人通过)'
  return '或签(任一通过)'
}

function insert(type) {
  const child = newNode(type)
  child.childNode = props.node.childNode || null
  props.node.childNode = child
  emit('select', child)
  emit('changed')
}

function newNode(type) {
  if (type === 'CC') {
    return { type, name: '抄送人', props: { assigneeType: 'users', users: [] }, childNode: null }
  }
  if (type === 'APPROVAL') {
    return { type, name: '审批节点', props: { assigneeType: 'users', users: [], mode: 'any', count: 2 }, childNode: null }
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
  if (n.branches.length >= 8) return  // wflow convention: max 8 branches
  if (n.type === 'CONDITIONS') {
    const defIdx = n.branches.findIndex((b) => !b.props?.groups?.some((g) => g.conditions?.length))
    const branch = { type: 'CONDITION', name: `条件${n.branches.length}`, childNode: null,
      props: { groupsType: 'AND', groups: [{ groupType: 'AND', conditions: [] }] } }
    if (defIdx >= 0) n.branches.splice(defIdx, 0, branch)
    else n.branches.push(branch)
  } else {
    n.branches.push({ type: 'BRANCH', name: `分支${n.branches.length + 1}`, childNode: null })
  }
}

function removeBranch(i) {
  const n = props.node
  // keep >= 2 branches by design; deleting is disabled in UI when only 2 remain
  n.branches.splice(i, 1)
}

function moveBranch(i, delta) {
  const arr = props.node.branches
  const [item] = arr.splice(i, 1)
  arr.splice(i + delta, 0, item)
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
</script>

<style scoped>
.wf-seg { display: flex; flex-direction: column; align-items: center; }
.wf-card {
  position: relative; width: 260px; background: #fff; border-radius: 8px; cursor: pointer;
  border: 1.5px solid var(--card-color); box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  transition: box-shadow .15s, transform .15s;
}
.wf-card:hover { box-shadow: 0 4px 14px rgba(0,0,0,0.13); transform: translateY(-1px); }
.wf-card.selected { outline: 2px solid var(--card-color); outline-offset: 1px; }
.wf-card.error { border-color: #f56c6c; box-shadow: 0 0 0 2px rgba(245, 108, 108, 0.25); }
.wf-card.error::after {
  content: '!'; position: absolute; right: -10px; top: -10px; width: 20px; height: 20px;
  border-radius: 50%; background: #f56c6c; color: #fff; font-size: 13px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
}
.wf-branch-col-head.head-error { border-color: #f56c6c; color: #f56c6c; background: #fef0f0; }
.wf-card-head { display: flex; align-items: center; gap: 6px; padding: 8px 12px 2px; color: var(--card-color); }
.wf-title { font-size: 14px; font-weight: 600; color: #303133; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.wf-badge { font-size: 11px; padding: 0 7px; border-radius: 9px; border: 1px solid #e1f3d8; background: #f0f9eb; color: #67c23a; }
.wf-badge.cs { background: #fdf6ec; color: #e6a23c; border-color: #faecd8; }
.wf-badge.rt { background: #ecf5ff; color: #409eff; border-color: #d9ecff; }
.wf-card-body { padding: 4px 12px 10px; font-size: 12px; color: #909399; }
.wf-del {
  position: absolute; top: -9px; right: -9px; width: 20px; height: 20px; border-radius: 50%;
  background: #f56c6c; color: #fff; display: none; align-items: center; justify-content: center;
  font-size: 12px; cursor: pointer; z-index: 2;
}
.wf-card:hover .wf-del { display: flex; }
.wf-plus-row { display: flex; justify-content: center; padding: 6px 0; position: relative; }
.wf-plus-row::before { content: ""; position: absolute; left: 50%; top: -6px; bottom: 50%; width: 2px; background: #cacaca; }
.wf-plus-btn {
  width: 28px; height: 28px; border-radius: 50%; background: #409eff; color: #fff; cursor: pointer;
  display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 6px rgba(64,158,255,.4);
  transition: transform .15s;
}
.wf-plus-btn:hover { transform: scale(1.12); }
.wf-menu { display: flex; flex-wrap: wrap; gap: 8px; }
.wf-menu-item {
  display: flex; align-items: center; gap: 6px; width: 115px; padding: 9px 10px; cursor: pointer;
  background: #f8f9f9; border-radius: 8px; font-size: 13px; color: #606266;
}
.wf-menu-item:hover { background: #fff; box-shadow: 0 0 8px 2px #d6d6d6; }

/* dingtalk-style branch group: top/bottom rails + per-column spine + cover lines */
.wf-branch-group {
  position: relative; width: 100%; display: flex; flex-direction: column; align-items: center;
  padding: 18px 14px 14px; background: rgba(64,158,255,.02);
  border-top: 2px solid #cccccc; border-bottom: 2px solid #cccccc;
}
.wf-branch-add { position: absolute; top: -16px; left: 50%; transform: translateX(-50%); z-index: 3; }
.wf-branch-cols { display: flex; justify-content: center; flex-wrap: wrap; }
.wf-branch-col {
  position: relative; display: flex; flex-direction: column; align-items: center;
  min-width: 270px; padding: 10px 14px;
  border-top: 2px solid #cccccc; border-bottom: 2px solid #cccccc; background: transparent;
}
.wf-branch-col::before {
  content: ""; position: absolute; top: 0; left: calc(50% - 1px); width: 2px; height: 100%;
  background: #cacaca;
}
.cover { position: absolute; width: 50%; height: 4px; background: #fff; z-index: 1; }
.cover.tl { top: -2px; left: -1px; }
.cover.tr { top: -2px; right: -1px; }
.cover.bl { bottom: -2px; left: -1px; }
.cover.br { bottom: -2px; right: -1px; }
.wf-branch-col-head {
  position: relative; z-index: 2; display: flex; align-items: center; justify-content: center; gap: 6px;
  padding: 4px 10px; background: #f0faf7; border: 1px solid #15bc83; color: #15bc83;
  border-radius: 14px; font-size: 12px; font-weight: 600; cursor: pointer; margin-bottom: 10px;
}
.wf-branch-col-head:hover { background: #e2f7f0; }
.wf-branch-col-move, .wf-branch-col-del { color: #909399; display: flex; align-items: center; }
.wf-branch-col-del:hover { color: #f56c6c; }
.wf-branch-chain { position: relative; z-index: 2; display: flex; flex-direction: column; align-items: center; }
.wf-branch-empty {
  width: 220px; text-align: center; padding: 14px 0; color: #c0c4cc; font-size: 12px;
  border: 1px dashed #dcdfe6; border-radius: 8px; cursor: pointer; background: #fff;
}
</style>

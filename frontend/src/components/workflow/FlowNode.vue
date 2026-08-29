<template>
  <div class="flow-seg">
    <div class="af-node-wrap">
      <div class="af-node" :class="{ initial: node.is_initial, done: node.is_done, converged: isConverged }"
        :style="{ '--node-color': node.color }" @click="$emit('edit', node)">
        <span class="af-node-del" v-if="!node.is_initial" @click.stop="$emit('remove', node)">
          <el-icon><Close /></el-icon>
        </span>
        <div class="af-node-head">
          <span class="af-dot"></span>
          <span class="af-node-name">{{ node.name }}</span>
          <span v-if="node.is_initial" class="af-badge">入口</span>
          <span v-if="node.is_done" class="af-badge done">完成态</span>
          <span v-if="branchTargets.length > 1" class="af-badge branch">分支×{{ branchTargets.length }}</span>
          <span v-if="isConverged" class="af-badge converge">汇聚</span>
        </div>
        <div class="af-node-sub">
          <span>处理: {{ handlerLabel(node) }}</span>
          <span class="af-next">流转: {{ nextNames || '—' }}</span>
        </div>
        <div class="af-node-foot">点击配置</div>
      </div>
    </div>

    <!-- single outgoing: linear chain -->
    <template v-if="branchTargets.length === 1">
      <div class="af-plus" @click="$emit('insert', node)">
        <span class="af-plus-btn"><el-icon><Plus /></el-icon></span>
      </div>
      <FlowNode v-if="!nextVisited(branchTargets[0].key)" :node="branchTargets[0]" :nodes="nodes"
        :visited="[...visited, node.key]" @edit="$emit('edit', $event)" @insert="$emit('insert', $event)"
        @remove="$emit('remove', $event)" @add-branch="$emit('add-branch', $event)"
        @remove-branch="$emit('remove-branch', $event)" />
      <div v-else class="af-converge-hint" @click="$emit('edit', branchTargets[0])">
        ↳ 已流转回「{{ branchTargets[0].name }}」(汇聚点, 点击配置)
      </div>
    </template>

    <!-- multiple outgoing: parallel branch group (AntFlow style) -->
    <div v-else-if="branchTargets.length > 1" class="branch-group">
      <div class="branch-group-head" @click="$emit('add-branch', node)">
        <span class="branch-add-btn"><el-icon><Plus /></el-icon> 添加分支</span>
      </div>
      <div class="branch-columns">
        <div v-for="t in branchTargets" :key="t.key" class="branch-col">
          <div class="branch-col-head" :style="{ '--branch-color': t.color }">
            <span class="branch-col-title" @click.stop="$emit('edit', t)">{{ t.name }}</span>
            <span class="branch-col-del" @click.stop="$emit('remove-branch', { parent: node, key: t.key })">
              <el-icon><Close /></el-icon>
            </span>
          </div>
          <FlowNode v-if="!nextVisited(t.key)" :node="t" :nodes="nodes" :visited="[...visited, node.key]"
            @edit="$emit('edit', $event)" @insert="$emit('insert', $event)" @remove="$emit('remove', $event)"
            @add-branch="$emit('add-branch', $event)" @remove-branch="$emit('remove-branch', $event)" />
          <div v-else class="af-converge-hint" @click="$emit('edit', t)">
            ↳ 汇聚到「{{ t.name }}」
          </div>
        </div>
      </div>
    </div>

    <!-- terminal -->
    <div v-else class="af-terminal">
      <div class="terminal-pill end">流程终点</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Plus, Close } from '@element-plus/icons-vue'

const props = defineProps({
  node: { type: Object, required: true },
  nodes: { type: Array, required: true },
  visited: { type: Array, default: () => [] },
})

defineEmits(['edit', 'insert', 'remove', 'add-branch', 'remove-branch'])

const HANDLER_LABELS = { any: '任何人', assignee: '负责人', admins: '项目管理员', members: '指定成员' }

function handlerLabel(n) {
  return HANDLER_LABELS[n.handler_type] || '任何人'
}

const branchTargets = computed(() =>
  (props.node.next_keys || [])
    .map((k) => props.nodes.find((x) => x.key === k))
    .filter(Boolean)
)

const nextNames = computed(() => branchTargets.value.map((t) => t.name).join('、'))

// converged: this node is reachable again from an ancestor (drawn before) -> show hint, do not recurse
const isConverged = computed(() => false)

function nextVisited(key) {
  return props.visited.includes(key)
}
</script>

<style scoped>
.flow-seg { display: flex; flex-direction: column; align-items: center; }
.af-node-wrap { display: flex; justify-content: center; width: 100%; }
.af-node {
  position: relative; width: 100%; min-width: 240px; background: #fff; border-radius: 10px;
  border: 1.5px solid var(--node-color, #dcdfe6); cursor: pointer;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06); transition: box-shadow 0.15s, transform 0.15s;
}
.af-node:hover { box-shadow: 0 4px 14px rgba(0, 0, 0, 0.12); transform: translateY(-1px); }
.af-node-head { display: flex; align-items: center; gap: 8px; padding: 12px 14px 4px; flex-wrap: wrap; }
.af-dot { width: 10px; height: 10px; border-radius: 50%; background: var(--node-color); flex-shrink: 0; }
.af-node-name { font-size: 15px; font-weight: 600; color: #303133; }
.af-badge {
  font-size: 11px; padding: 1px 8px; border-radius: 10px;
  background: #f0f9eb; color: #67c23a; border: 1px solid #e1f3d8;
}
.af-badge.done { background: #ecf5ff; color: #409eff; border-color: #d9ecff; }
.af-badge.branch { background: #fdf6ec; color: #e6a23c; border-color: #faecd8; }
.af-badge.converge { background: #f4f4f5; color: #909399; border-color: #e9e9eb; }
.af-node-sub { padding: 4px 14px 8px; display: flex; flex-direction: column; gap: 2px;
  font-size: 12px; color: #909399; }
.af-next { color: #606266; }
.af-node-foot { border-top: 1px dashed #ebeef5; text-align: center; font-size: 11px;
  color: #c0c4cc; padding: 4px 0; }
.af-node-del {
  position: absolute; top: -9px; right: -9px; width: 20px; height: 20px;
  border-radius: 50%; background: #f56c6c; color: #fff; cursor: pointer;
  display: none; align-items: center; justify-content: center; font-size: 12px; z-index: 2;
}
.af-node:hover .af-node-del { display: flex; }

.af-plus { display: flex; justify-content: center; height: 30px; align-items: center; }
.af-plus-btn {
  width: 26px; height: 26px; border-radius: 50%; background: #409eff; color: #fff;
  display: flex; align-items: center; justify-content: center; cursor: pointer;
  box-shadow: 0 2px 6px rgba(64, 158, 255, 0.4); transition: transform 0.15s;
}
.af-plus-btn:hover { transform: scale(1.15); }

.af-terminal { display: flex; justify-content: center; padding: 8px 0; }
.terminal-pill { padding: 6px 22px; border-radius: 20px; font-size: 13px; color: #fff; }
.terminal-pill.end { background: #909399; }

.af-converge-hint {
  margin: 8px 0; padding: 6px 14px; border-radius: 16px; background: #f4f4f5;
  color: #909399; font-size: 12px; cursor: pointer; border: 1px dashed #dcdfe6;
}

.branch-group {
  width: 100%; display: flex; flex-direction: column; align-items: center;
  border-left: 2px dashed #c8d0da; border-right: 2px dashed #c8d0da;
  border-bottom: 2px dashed #c8d0da; border-radius: 0 0 14px 14px; padding: 0 12px 16px;
  margin-top: 2px; background: rgba(64, 158, 255, 0.02);
}
.branch-group-head { display: flex; justify-content: center; padding: 8px 0; }
.branch-add-btn {
  font-size: 12px; color: #409eff; background: #ecf5ff; border: 1px solid #d9ecff;
  border-radius: 14px; padding: 3px 12px; cursor: pointer; display: flex; align-items: center; gap: 3px;
}
.branch-add-btn:hover { background: #d9ecff; }
.branch-columns { display: flex; gap: 14px; justify-content: center; flex-wrap: wrap; }
.branch-col {
  display: flex; flex-direction: column; min-width: 250px; max-width: 340px; flex: 1;
}
.branch-col-head {
  display: flex; align-items: center; justify-content: space-between; gap: 6px;
  background: color-mix(in srgb, var(--branch-color, #409eff) 12%, #fff);
  border: 1px solid var(--branch-color, #409eff);
  border-radius: 8px; padding: 5px 10px; margin: 4px 0 10px;
}
.branch-col-title { font-size: 13px; font-weight: 600; color: var(--branch-color); cursor: pointer; }
.branch-col-del { color: #f56c6c; cursor: pointer; font-size: 13px; display: flex; align-items: center; }
</style>

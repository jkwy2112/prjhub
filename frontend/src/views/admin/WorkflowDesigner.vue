<template>
  <div class="designer" v-if="wf">
    <div class="toolbar">
      <div class="toolbar-left">
        <el-button :icon="Back" text @click="$router.push('/admin/workflows')">返回</el-button>
        <el-input v-model="wf.name" style="width: 200px" size="small" maxlength="64" />
        <el-input v-model="wf.description" style="width: 280px" size="small" placeholder="描述" maxlength="255" />
      </div>
      <div class="toolbar-right">
        <el-button size="small" :icon="Plus" @click="addNode">添加状态节点</el-button>
        <el-button size="small" @click="autoLayout">自动排列</el-button>
        <el-button size="small" type="primary" :loading="saving" :icon="Check" @click="save">保存</el-button>
      </div>
    </div>

    <div class="body">
      <div class="canvas-wrap" ref="wrap">
        <svg ref="svgEl" :width="CANVAS_W" :height="CANVAS_H"
          @pointerdown="onCanvasPointerDown" @pointermove="onPointerMove"
          @pointerup="onPointerUp" @pointercancel="cancelInteraction">
          <defs>
            <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7"
              orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#b0b6bf" />
            </marker>
          </defs>

          <path v-for="e in edges" :key="e.from + '->' + e.to" :d="e.path" class="edge"
            :marker-end="'url(#arrow)'" @pointerdown.stop="removeEdge(e)" />
          <path v-if="linking" :d="tempPath" class="edge linking" />

          <g v-for="n in nodes" :key="n.key" class="node"
            :class="{ selected: selected?.key === n.key, 'link-target': linking && hoverTarget?.key === n.key && linkFrom?.key !== n.key }"
            :transform="`translate(${n.x},${n.y})`"
            @pointerdown.stop="onNodePointerDown($event, n)">
            <rect :width="NODE_W" :height="NODE_H" rx="10" :fill="n.color" fill-opacity="0.12"
              :stroke="n.color" stroke-width="1.5" />
            <text :x="NODE_W / 2" :y="26" text-anchor="middle" class="node-name">{{ n.name }}</text>
            <text :x="NODE_W / 2" :y="44" text-anchor="middle" class="node-sub">{{ handlerLabel(n) }}</text>
            <circle v-if="n.is_initial" cx="14" cy="-8" r="9" fill="#67C23A" />
            <text v-if="n.is_initial" x="14" y="-4" text-anchor="middle" class="badge-text">始</text>
            <circle v-if="n.is_done" :cx="NODE_W - 14" cy="-8" r="9" fill="#409EFF" />
            <text v-if="n.is_done" :x="NODE_W - 14" y="-4" text-anchor="middle" class="badge-text">完</text>
            <circle :cx="NODE_W" :cy="NODE_H / 2" r="9" class="anchor"
              @pointerdown.stop.prevent="startLink($event, n)">
              <title>拖拽拉出连线</title>
            </circle>
          </g>

          <text v-if="linking" :x="linkPos.x + 14" :y="linkPos.y - 10" class="link-hint">
            拖到目标节点松开完成连线 (Esc 取消)
          </text>
        </svg>
      </div>

      <div class="props" v-if="selected">
        <h4>节点属性 <span class="props-key">{{ selected.key }}</span></h4>
        <el-form label-width="80px" size="small">
          <el-form-item label="名称">
            <el-input v-model="selected.name" maxlength="32" />
          </el-form-item>
          <el-form-item label="颜色">
            <el-color-picker v-model="selected.color" />
          </el-form-item>
          <el-form-item label="初始状态">
            <el-switch :model-value="selected.is_initial" @change="setInitial(selected)" />
          </el-form-item>
          <el-form-item label="完成状态">
            <el-switch v-model="selected.is_done" />
          </el-form-item>
          <el-divider style="margin: 10px 0">谁可流转到此状态</el-divider>
          <el-form-item label="处理人">
            <el-radio-group v-model="selected.handler_type">
              <el-radio-button value="any">任何人</el-radio-button>
              <el-radio-button value="assignee">负责人</el-radio-button>
              <el-radio-button value="admins">项目管理员</el-radio-button>
              <el-radio-button value="members">指定成员</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="selected.handler_type === 'members'" label="成员">
            <el-select v-model="selected.handler_user_ids" multiple filterable remote
              :remote-method="searchUsers" placeholder="搜索用户" style="width: 100%">
              <el-option v-for="u in userOptions" :key="u.id" :value="u.id"
                :label="u.name || u.username" />
            </el-select>
          </el-form-item>
          <el-form-item label="可流转到">
            <el-select :model-value="selected.next_keys" multiple style="width: 100%"
              @update:model-value="(v) => setNextKeys(selected, v)">
              <el-option v-for="o in nodes.filter((x) => x.key !== selected.key)" :key="o.key"
                :value="o.key" :label="o.name" />
            </el-select>
          </el-form-item>
          <el-button text type="danger" size="small" :icon="Delete" @click="removeNode(selected)">
            删除此节点
          </el-button>
        </el-form>
      </div>
      <div class="props empty" v-else>
        <p>点击节点编辑属性</p>
        <p>拖拽节点移动位置</p>
        <p>从右侧锚点拉出连线, 点击连线删除</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Back, Plus, Check, Delete } from '@element-plus/icons-vue'
import api from '../../api'

const NODE_W = 168
const NODE_H = 62
const CANVAS_W = 1600
const CANVAS_H = 900
const DRAG_THRESHOLD = 3 // px before a press becomes a drag (mature-editor convention)

const route = useRoute()
const wfId = Number(route.params.id)

const wf = ref(null)
const nodes = ref([])
const selected = ref(null)
const saving = ref(false)
const userOptions = ref([])

const svgEl = ref(null)
const wrap = ref(null)

// single interaction state machine: null | {type:'press'|'drag',...} | {type:'link',...}
let interaction = null
const linking = ref(null)      // source node while pulling an edge
const hoverTarget = ref(null)  // node under cursor while linking (highlight)
const linkPos = ref({ x: 0, y: 0 })

const HANDLER_LABELS = { any: '任何人', assignee: '负责人', admins: '管理员', members: '指定成员' }

function handlerLabel(n) {
  return HANDLER_LABELS[n.handler_type] || '任何人'
}

const linkFrom = computed(() => linking.value)

const edges = computed(() => {
  const out = []
  for (const n of nodes.value) {
    for (const to of n.next_keys || []) {
      const target = nodes.value.find((x) => x.key === to)
      if (!target) continue
      out.push({ from: n.key, to, path: edgePath(n, target), fromName: n.name, toName: target.name })
    }
  }
  return out
})

const tempPath = computed(() => {
  if (!linking.value) return ''
  const n = linking.value
  return bezier(n.x + NODE_W, n.y + NODE_H / 2, linkPos.value.x, linkPos.value.y)
})

function edgePath(a, b) {
  return bezier(a.x + NODE_W, a.y + NODE_H / 2, b.x, b.y + NODE_H / 2)
}

function bezier(x1, y1, x2, y2) {
  const dx = Math.max(40, Math.abs(x2 - x1) / 2)
  return `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`
}

// ---------- screen -> svg coordinate conversion (standard: getScreenCTM) ----------

function toSvgPoint(clientX, clientY) {
  const ctm = svgEl.value.getScreenCTM()
  if (!ctm) return { x: 0, y: 0 }
  const p = new DOMPoint(clientX, clientY).matrixTransform(ctm.inverse())
  return { x: p.x, y: p.y }
}

function nodeUnderPointer(ev) {
  const { x, y } = toSvgPoint(ev.clientX, ev.clientY)
  return nodes.value.find(
    (n) => x >= n.x && x <= n.x + NODE_W && y >= n.y && y <= n.y + NODE_H
  )
}

// ---------- interaction lifecycle (pointer events + capture, X6/LogicFlow style) ----------

function onCanvasPointerDown() {
  selected.value = null // click empty canvas deselects
}

function onNodePointerDown(ev, node) {
  if (ev.button !== 0) return
  const start = toSvgPoint(ev.clientX, ev.clientY)
  interaction = { type: 'press', node, start, moved: false }
  svgEl.value.setPointerCapture(ev.pointerId)
}

function startLink(ev, node) {
  if (ev.button !== 0) return
  linking.value = node
  hoverTarget.value = null
  linkPos.value = { x: node.x + NODE_W + 40, y: node.y + NODE_H / 2 }
  svgEl.value.setPointerCapture(ev.pointerId)
}

function onPointerMove(ev) {
  if (linking.value) {
    const p = toSvgPoint(ev.clientX, ev.clientY)
    linkPos.value = p
    hoverTarget.value = nodeUnderPointer(ev) || null
    return
  }
  if (interaction?.type === 'press') {
    const p = toSvgPoint(ev.clientX, ev.clientY)
    const dx = p.x - interaction.start.x
    const dy = p.y - interaction.start.y
    if (!interaction.moved && Math.hypot(dx, dy) > DRAG_THRESHOLD) {
      interaction = { ...interaction, type: 'drag', offX: dx, offY: dy }
    }
    if (interaction.type === 'drag') {
      const node = interaction.node
      node.x = Math.max(0, Math.round(p.x - interaction.offX))
      node.y = Math.max(0, Math.round(p.y - interaction.offY))
    }
  }
}

function onPointerUp(ev) {
  if (linking.value) {
    const target = nodeUnderPointer(ev)
    const from = linking.value
    if (target && target.key !== from.key) {
      if (!(from.next_keys || []).includes(target.key)) {
        from.next_keys = [...(from.next_keys || []), target.key]
        ElMessage.success(`「${from.name}」→「${target.name}」已连线`)
      }
    }
    cancelInteraction()
    return
  }
  if (interaction) {
    if (interaction.type === 'press') {
      selected.value = interaction.node // no movement -> treat as click/select
    }
    interaction = null
    try { svgEl.value.releasePointerCapture(ev.pointerId) } catch { /* ignore */ }
  }
}

function cancelInteraction() {
  interaction = null
  linking.value = null
  hoverTarget.value = null
}

function onKeydown(ev) {
  if (ev.key === 'Escape') cancelInteraction()
  if ((ev.key === 'Delete' || ev.key === 'Backspace') && selected.value) {
    // only when focus is not inside an input
    const tag = document.activeElement?.tagName
    if (!['INPUT', 'TEXTAREA'].includes(tag)) removeNode(selected.value)
  }
}

function removeEdge(e) {
  const from = nodes.value.find((n) => n.key === e.from)
  if (from) {
    from.next_keys = from.next_keys.filter((k) => k !== e.to)
    ElMessage.info(`已删除「${from.name}」→「${e.toName}」连线`)
  }
}

// ---------- node ops ----------

function setNextKeys(node, keys) {
  node.next_keys = keys
}

function setInitial(node) {
  nodes.value.forEach((n) => (n.is_initial = n.key === node.key))
}

function addNode() {
  const n = nodes.value.length + 1
  nodes.value.push({
    key: `node_${Date.now().toString(36)}`,
    name: `新状态${n}`,
    color: '#9254de',
    x: 80 + (nodes.value.length % 5) * 260,
    y: 140 + Math.floor(nodes.value.length / 5) * 160,
    is_initial: false,
    is_done: false,
    next_keys: [],
    handler_type: 'any',
    handler_user_ids: [],
  })
}

function removeNode(node) {
  if (node.is_initial) return ElMessage.warning('初始状态不能删除, 请先把其他节点设为初始')
  nodes.value = nodes.value.filter((n) => n.key !== node.key)
  nodes.value.forEach((n) => (n.next_keys = (n.next_keys || []).filter((k) => k !== node.key)))
  if (selected.value?.key === node.key) selected.value = null
}

function autoLayout() {
  nodes.value.forEach((n, i) => {
    n.x = 60 + (i % 4) * 320
    n.y = 120 + Math.floor(i / 4) * 220
  })
}

// ---------- users / save ----------

async function searchUsers(q) {
  if (!q) return (userOptions.value = [])
  const { data } = await api.get('/users', { params: { q } })
  userOptions.value = data
}

async function loadUsersByIds(ids) {
  if (!ids?.length) return
  await Promise.all(ids.map(async (id) => {
    try {
      const { data } = await api.get('/users', { params: { q: String(id) } })
      const hit = data.find((u) => u.id === id)
      if (hit && !userOptions.value.some((u) => u.id === id)) userOptions.value.push(hit)
    } catch { /* ignore */ }
  }))
}

async function save() {
  if (!wf.value.name.trim()) return ElMessage.warning('请填写工作流名称')
  const initials = nodes.value.filter((n) => n.is_initial)
  if (initials.length !== 1) return ElMessage.warning('必须且只能有一个初始状态')
  saving.value = true
  try {
    const payload = {
      name: wf.value.name,
      description: wf.value.description || '',
      nodes: nodes.value.map((n) => ({
        key: n.key, name: n.name, color: n.color, x: Math.round(n.x), y: Math.round(n.y),
        is_initial: !!n.is_initial, is_done: !!n.is_done,
        next_keys: (n.next_keys || []).filter((k) => k !== n.key && nodes.value.some((x) => x.key === k)),
        handler_type: n.handler_type || 'any',
        handler_user_ids: n.handler_user_ids || [],
      })),
    }
    const { data } = await api.put(`/workflows/${wfId}`, payload)
    if (data.migrated) ElMessage.warning(`已保存, ${data.migrated} 个任务被迁移到初始状态`)
    else ElMessage.success('工作流已保存')
  } catch { /* interceptor */ } finally {
    saving.value = false
  }
}

onMounted(async () => {
  const { data } = await api.get(`/workflows/${wfId}`)
  wf.value = { id: data.id, name: data.name, description: data.description, is_default: data.is_default }
  nodes.value = data.nodes.map((n) => ({ ...n, next_keys: [...n.next_keys], handler_user_ids: [...n.handler_user_ids] }))
  await loadUsersByIds(nodes.value.flatMap((n) => n.handler_user_ids || []))
  window.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
})
</script>

<style scoped>
.designer { display: flex; flex-direction: column; height: calc(100vh - 96px); background: #fff;
  border-radius: 8px; overflow: hidden; }
.toolbar { display: flex; justify-content: space-between; align-items: center; padding: 8px 12px;
  border-bottom: 1px solid #ebeef5; }
.toolbar-left { display: flex; align-items: center; gap: 8px; }
.body { flex: 1; display: flex; min-height: 0; }
.canvas-wrap { flex: 1; overflow: auto; background:
  radial-gradient(circle, #e8ebf0 1px, transparent 1px) 0 0 / 22px 22px, #fafbfc; }
.props { width: 300px; border-left: 1px solid #ebeef5; padding: 14px; overflow: auto; }
.props.empty { color: #c0c4cc; font-size: 13px; display: flex; flex-direction: column;
  justify-content: center; text-align: center; gap: 6px; }
.props h4 { margin-bottom: 14px; }
.props-key { color: #c0c4cc; font-size: 12px; font-weight: normal; }
.edge { stroke: #b0b6bf; stroke-width: 2; fill: none; cursor: pointer; }
.edge:hover { stroke: #f56c6c; }
.edge.linking { stroke: #409eff; stroke-dasharray: 6 4; pointer-events: none; }
.node { cursor: grab; user-select: none; }
.node:active { cursor: grabbing; }
.node.selected rect { stroke-width: 3; filter: drop-shadow(0 2px 6px rgba(64, 158, 255, 0.4)); }
.node.link-target rect { stroke: #409eff; stroke-width: 3; stroke-dasharray: 5 3; }
.node-name { font-size: 14px; font-weight: 600; fill: #303133; }
.node-sub { font-size: 11px; fill: #909399; }
.badge-text { font-size: 10px; fill: #fff; }
.anchor { fill: #fff; stroke: #409eff; stroke-width: 2; cursor: crosshair; }
.anchor:hover { fill: #409eff; r: 11; }
.link-hint { font-size: 12px; fill: #409eff; }
</style>
